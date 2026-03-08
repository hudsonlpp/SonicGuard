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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from schemas import CompareRequest, CompareResponse, HealthResponse, ErrorResponse
from downloader import load_audio
from dsp_engine import extract_features_combined
from matcher import compare


# ═════════════════════════════════════════════════════════════════════════════
#  APP
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


# ═════════════════════════════════════════════════════════════════════════════
#  ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/api/health", response_model=HealthResponse)
async def health():
    """Health check — verifica se a API está online."""
    return HealthResponse()


@app.post(
    "/api/compare",
    response_model=CompareResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def compare_audios(request: CompareRequest):
    """
    Compara dois áudios via motor DSP v2 (Two-Pass DTW Multi-Dimensional).

    Aceita URLs do YouTube ou caminhos de arquivos locais.
    Processamento síncrono — tempo médio: ~40 segundos.
    """
    start = time.time()

    # ── Validação básica ──
    if not request.source_a or not request.source_b:
        raise HTTPException(status_code=400, detail="source_a e source_b são obrigatórios.")

    try:
        # ── Carregar Áudio A ──
        signal_a, sr_a = load_audio(request.source_a)

        # ── Extrair Features A ──
        features_a, combined_a = extract_features_combined(signal_a, sr=sr_a)
        del signal_a
        gc.collect()

        # ── Carregar Áudio B ──
        signal_b, sr_b = load_audio(request.source_b)

        # ── Extrair Features B ──
        features_b, combined_b = extract_features_combined(signal_b, sr=sr_b)
        del signal_b
        gc.collect()

        # ── Comparar via Two-Pass DTW ──
        result = compare(features_a, features_b, combined_a, combined_b)
        gc.collect()

        elapsed = round(time.time() - start, 2)

        # ── Montar response ──
        data = result.to_dict()
        return CompareResponse(
            score=data["score"],
            verdict=data["verdict"],
            breakdown=data["breakdown"],
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
