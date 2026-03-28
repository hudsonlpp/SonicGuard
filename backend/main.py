"""
main.py — API FastAPI do SonicGuard (MVP).

Endpoints:
  POST /api/compare  — Compara dois áudios via motor DSP v2
  GET  /api/health   — Health check

Processamento síncrono: a comparação leva ~40s.
O frontend deve exibir um loading state durante a request.
"""

import gc
import time
import traceback
import asyncio

from fastapi import FastAPI, HTTPException, Depends, status, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

# Core 
import os
import shutil
import tempfile
from typing import Optional
from schemas import CompareRequest, CompareResponse, HealthResponse, ErrorResponse
from downloader import load_audio
from dsp_engine import extract_features_combined
from matcher import compare
from legal import detectar_padrao, selecionar_artigos, gerar_analise_estatica, PADROES
from legal_llm import gerar_analise_llm

# Auth & Database
import database, models, crud, auth, schemas_auth

# Inicializa as tabelas do SQLite automaticamente
models.Base.metadata.create_all(bind=database.engine)


# ═════════════════════════════════════════════════════════════════════════════
#  APP & CONCURRENCY
# ═════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="SonicGuard API",
    description="Motor de Detecção de Plágio Musical — DSP Multi-Dimensional",
    version="2.0.0",
)

# CORS: permitir o frontend acessar a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Em produção, restringir ao domínio do frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Semáforo para limitar processamento concorrente do Motor DSP (evita crash por RAM na VPS)
# Valor 1: Apenas 1 música processada por vez (Garante uso < 1GB RAM)
dsp_semaphore = asyncio.Semaphore(1)


# ═════════════════════════════════════════════════════════════════════════════
#  AUTH ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

@app.post("/api/auth/register", response_model=schemas_auth.UserResponse)
def register(user: schemas_auth.UserCreate, db: Session = Depends(database.get_db)):
    """Cria uma nova conta na plataforma e deposita 2 créditos grátis."""
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="E-mail já registrado")
    
    new_user = crud.create_user(db=db, user=user)
    
    # Montando a resposta explicitamente pro Pydantic ignorar a senha
    return schemas_auth.UserResponse(
        id=new_user.id,
        email=new_user.email,
        credits=crud.get_credits(db, new_user.id)
    )

@app.post("/api/auth/login", response_model=schemas_auth.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    """
    Login padrão Oauth2 usando form-data (username e password).
    Em nosso caso, username = email.
    """
    user = crud.get_user_by_email(db, email=form_data.username)
    if not user or not crud.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas. Verifique seu e-mail e senha.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Gera JWT 
    access_token_expires = auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ═════════════════════════════════════════════════════════════════════════════
#  CORE ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/api/health", response_model=HealthResponse)
async def health():
    """Health check — verifica se a API está online."""
    return HealthResponse()

@app.get("/api/me")
def get_me(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    """Retorna os dados do usuário autenticado, incluindo saldo atualizado."""
    creditos = crud.get_credits(db, current_user.id)
    return {"email": current_user.email, "credits": creditos}


@app.post(
    "/api/compare",
    response_model=CompareResponse,
    responses={
        400: {"model": ErrorResponse}, 
        401: {"model": ErrorResponse, "description": "Token inválido/ausente"},
        402: {"model": ErrorResponse, "description": "Sem créditos"},
        500: {"model": ErrorResponse}
    },
)
async def compare_audios(
    request: Request,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    [PROTECTED] Compara dois áudios via motor DSP v2.
    Requer Header 'Authorization: Bearer <token>'.
    Custa 1 crédito da carteira do usuário.
    """
    # ── 1. Paywall: Checa se o usuário tem saldo ──
    # creditos_atuais = crud.get_credits(db, current_user.id)
    # if creditos_atuais <= 0:
    #     raise HTTPException(
    #         status_code=402, 
    #         detail="Você não possui mais créditos para análise. Faça um upgrade ou recarregue."
    #     )

    start = time.time()
    
    # ── 1. Super-Parser Resiliente (JSON + MultiPart) ──
    # Tenta extrair os dados de qualquer fonte possível para evitar erros de cabeçalho.
    source_a = None
    source_b = None
    temp_files = []

    try:
        # Tenta JSON primeiro (mais comum para YouTube)
        if "application/json" in request.headers.get("Content-Type", "").lower():
            data = await request.json()
            source_a = data.get("source_a")
            source_b = data.get("source_b")
        
        # Se não achou no JSON, ou se for Multipart, tenta Form
        if not source_a or not source_b:
            form = await request.form()
            
            # Prioridade para Arquivos reais
            f_a = form.get("file_a")
            if f_a and hasattr(f_a, "filename") and f_a.filename:
                tmp_dir = tempfile.mkdtemp(prefix="sg_up_a_")
                tmp_path = os.path.join(tmp_dir, f"audio_a{os.path.splitext(f_a.filename)[1] or '.wav'}")
                with open(tmp_path, "wb") as buf:
                    shutil.copyfileobj(f_a.file, buf)
                source_a = tmp_path
                temp_files.append(tmp_dir)
            else:
                source_a = source_a or form.get("source_a")

            f_b = form.get("file_b")
            if f_b and hasattr(f_b, "filename") and f_b.filename:
                tmp_dir = tempfile.mkdtemp(prefix="sg_up_b_")
                tmp_path = os.path.join(tmp_dir, f"audio_b{os.path.splitext(f_b.filename)[1] or '.wav'}")
                with open(tmp_path, "wb") as buf:
                    shutil.copyfileobj(f_b.file, buf)
                source_b = tmp_path
                temp_files.append(tmp_dir)
            else:
                source_b = source_b or form.get("source_b")

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Falha na leitura dos dados: {str(e)}")

    if not source_a or not source_b:
        raise HTTPException(
            status_code=400, 
            detail="Dois áudios são necessários (Parametros ausentes ou incorretos)."
        )

    try:
        # A trava de concorrência entra aqui. 
        # Quem apertar o botão junto fica aguardando nesta linha até o anterior terminar.
        async with dsp_semaphore:
            # ── Carregar Áudio A ──
            signal_a, sr_a = load_audio(source_a)
            # TRUNCAR PARA DEMO (MAX 120 SEGUNDOS) PARA EVITAR TIMEOUT NO RENDER
            signal_a = signal_a[:sr_a * 120]

            # ── Extrair Features A ──
            features_a, combined_a = extract_features_combined(signal_a, sr=sr_a)
            del signal_a # Liberar RAM imediatamente
            gc.collect()

            # ── Carregar Áudio B ──
            signal_b, sr_b = load_audio(source_b)
            # TRUNCAR PARA DEMO (MAX 120 SEGUNDOS) PARA EVITAR TIMEOUT NO RENDER
            signal_b = signal_b[:sr_b * 120]

            # ── Extrair Features B ──
            features_b, combined_b = extract_features_combined(signal_b, sr=sr_b)
            del signal_b # Liberar RAM imediatamente
            gc.collect()

            # ── Comparar via Two-Pass DTW ──
            result = compare(features_a, features_b, combined_a, combined_b)
            gc.collect()

        elapsed = round(time.time() - start, 2)

        # ── Montar response ──
        data = result.to_dict()

        # ── Análise Jurídica (Híbrido: regras + LLM + validação) ──
        padrao = detectar_padrao(data["score"], data["breakdown"])
        padrao_info = PADROES.get(padrao, PADROES["baixa"])
        artigos = selecionar_artigos(padrao)

        # Tentar Gemini Flash
        texto_llm = gerar_analise_llm(
            score=data["score"],
            breakdown=data["breakdown"],
            padrao=padrao,
            padrao_nome=padrao_info["nome"],
            veredicto=data["verdict"],
            artigos=[{"referencia": a["referencia"], "texto": a["texto"]} for a in artigos],
        )

        if texto_llm:
            legal_data = {
                "pattern": padrao,
                "pattern_name": padrao_info["nome"],
                "severity": padrao_info["gravidade"],
                "articles": [{"reference": a["referencia"], "text": a["texto"]} for a in artigos],
                "analysis": texto_llm,
                "recommendation": padrao_info["recomendacao"],
                "source": "gemini",
            }
        else:
            # Fallback: análise estática
            legal_data = gerar_analise_estatica(data["score"], data["breakdown"], padrao)

        # ── 3. Lógica de Negócio Pós-Análise (Crédito + Histórico) ──
        # Debita 1 crédito
        # crud.decrement_credit(db, current_user.id)
        # Salva log da análise para o usuário
        crud.log_analysis(
            db=db, 
            user_id=current_user.id, 
            source_a=request.source_a, 
            source_b=request.source_b,
            score=data["score"], 
            verdict=data["verdict"]
        )

        elapsed = round(time.time() - start, 2)

        return CompareResponse(
            score=data["score"],
            verdict=data["verdict"],
            breakdown=data["breakdown"],
            legal_analysis=legal_data,
            dtw_cost=data["dtw_cost"],
            path_length=data["path_length"],
            frames_a=data["frames_a"],
            frames_b=data["frames_b"],
            elapsed_seconds=elapsed,
            source_a=request.source_a,
            source_b=request.source_b,
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=f"Arquivo não encontrado: {e}")

    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=f"Erro no processamento: {e}")

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro interno: {e}")
