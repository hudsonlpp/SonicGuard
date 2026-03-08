"""
legal_llm.py — Camada 2+3: Integração Gemini Flash + Validação.

Fluxo:
  1. Recebe scores + padrão + artigos verificados do legal.py
  2. Envia prompt restrito ao Gemini Flash (gratuito)
  3. Valida output: verifica se LLM só citou artigos do banco
  4. Se válido → retorna análise LLM
  5. Se inválido ou erro → retorna fallback estático do legal.py
"""

import os
import re
from typing import Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
_MODEL_NAME = "gemini-2.0-flash"


def _get_model():
    """Inicializa o model Gemini (lazy)."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=_GEMINI_API_KEY)
        return genai.GenerativeModel(_MODEL_NAME)
    except Exception:
        return None


_model = None


def _ensure_model():
    """Garante model inicializado (singleton)."""
    global _model
    if _model is None and _GEMINI_API_KEY:
        _model = _get_model()
    return _model


# ═════════════════════════════════════════════════════════════════════════════
#  PROMPT TEMPLATE
# ═════════════════════════════════════════════════════════════════════════════

_PROMPT_TEMPLATE = """Você é um consultor jurídico especializado em direito autoral musical brasileiro.

REGRAS OBRIGATÓRIAS:
1. Use APENAS os artigos listados abaixo na seção "ARTIGOS DISPONÍVEIS"
2. NÃO invente artigos, incisos, alíneas ou jurisprudência que não estejam listados
3. Cite os artigos entre parênteses, ex: (Art. 7º, VIII, Lei 9.610/98)
4. Seja objetivo e profissional
5. Escreva em português brasileiro
6. REGRA DE SEGURANÇA MÁXIMA: NUNCA afirme categoricamente que ocorreu plágio. Use sempre termos como "indícios", "suspeita", "similaridade matemática" ou "possível violação", e termine SEMPRE recomendando a consulta a um advogado especializado.
7. Se o padrão for "Suspeita de Interpolação", enfatize que a baixa similaridade matemática geral (áudio) NÃO afasta a possibilidade de plágio da composição (obra derivada), alertando o usuário sobre apropriação dissimulada.
8. Gere uma análise de 4 a 6 linhas

ARTIGOS DISPONÍVEIS (use SOMENTE estes):
{artigos_formatados}

RESULTADO DA COMPARAÇÃO MUSICAL:
- Padrão detectado: {padrao_nome} ({padrao})
- Score geral: {score:.1%}
- Melodia: {melodia:.1%}
- Harmonia: {harmonia:.1%}
- Ritmo: {ritmo:.1%}
- Timbre: {timbre:.1%}
- Veredicto do motor: {veredicto}

Com base EXCLUSIVAMENTE nos artigos acima e nos dados da comparação, forneça:
1. Uma análise jurídica concisa explicando o que os dados indicam
2. Os artigos aplicáveis (apenas dos listados acima)
3. Uma recomendação prática ao usuário
"""


# ═════════════════════════════════════════════════════════════════════════════
#  VALIDAÇÃO DO OUTPUT DO LLM
# ═════════════════════════════════════════════════════════════════════════════

def _extrair_citacoes(texto: str) -> List[str]:
    """Extrai todas as citações de artigos do texto do LLM."""
    padrao = r'Art\.?\s*(\d+[º°]?(?:\s*,\s*[IVXLC]+)?)'
    matches = re.findall(padrao, texto, re.IGNORECASE)
    return [f"Art. {m}" for m in matches]


def _validar_citacoes(
    texto_llm: str,
    artigos_permitidos: List[dict],
) -> bool:
    """
    Verifica se o LLM só citou artigos que estavam no banco.
    Retorna True se válido, False se inventou algo.
    """
    citacoes = _extrair_citacoes(texto_llm)
    refs_permitidas = {a["referencia"] for a in artigos_permitidos}

    # Extrair o número base de cada referência permitida
    numeros_permitidos = set()
    for ref in refs_permitidas:
        match = re.search(r'(\d+)', ref)
        if match:
            numeros_permitidos.add(match.group(1))

    # Verificar cada citação
    for citacao in citacoes:
        match = re.search(r'(\d+)', citacao)
        if match:
            numero = match.group(1)
            if numero not in numeros_permitidos:
                return False

    return True


# ═════════════════════════════════════════════════════════════════════════════
#  FUNÇÃO PRINCIPAL
# ═════════════════════════════════════════════════════════════════════════════

def gerar_analise_llm(
    score: float,
    breakdown: Dict[str, dict],
    padrao: str,
    padrao_nome: str,
    veredicto: str,
    artigos: List[dict],
) -> Optional[str]:
    """
    Gera análise jurídica via Gemini Flash com validação.

    Retorna:
      - str com a análise (se válida)
      - None (se falhou, rate limit, ou validação rejeitou)
    """
    model = _ensure_model()
    if model is None:
        return None

    # Formatar artigos para o prompt
    artigos_formatados = "\n".join([
        f"- {a['referencia']}: {a['texto']}"
        for a in artigos
    ])

    s_melodia = breakdown.get("melodia", {}).get("score", 0.0)
    s_harmonia = breakdown.get("harmonia", {}).get("score", 0.0)
    s_ritmo = breakdown.get("ritmo", {}).get("score", 0.0)
    s_timbre = breakdown.get("timbre", {}).get("score", 0.0)

    prompt = _PROMPT_TEMPLATE.format(
        artigos_formatados=artigos_formatados,
        padrao_nome=padrao_nome,
        padrao=padrao,
        score=score,
        melodia=s_melodia,
        harmonia=s_harmonia,
        ritmo=s_ritmo,
        timbre=s_timbre,
        veredicto=veredicto,
    )

    try:
        response = model.generate_content(prompt)
        texto = response.text.strip()

        # Camada 3: Validação
        if _validar_citacoes(texto, artigos):
            return texto
        else:
            # LLM inventou artigos → rejeitar
            return None

    except Exception:
        # Rate limit, rede, ou qualquer erro → fallback
        return None
