"""
legal.py — Módulo Jurídico do SonicGuard (Camada 1: Regras Estáticas).

Base de conhecimento verificada da Lei 9.610/98 (Lei de Direitos Autorais)
+ detecção de padrão de plágio + análise estática (fallback).

Este módulo:
  1. Detecta o PADRÃO de plágio (sample, vocal, vibe, etc.)
  2. Seleciona os artigos da lei aplicáveis ao padrão
  3. Gera uma análise estática (usado como fallback se LLM falhar)
"""

from typing import Dict, List


# ═════════════════════════════════════════════════════════════════════════════
#  BASE DE CONHECIMENTO — ARTIGOS VERIFICADOS DA LEI 9.610/98
# ═════════════════════════════════════════════════════════════════════════════

ARTIGOS = {
    "art_7_viii": {
        "lei": "Lei 9.610/98",
        "referencia": "Art. 7º, VIII",
        "texto": "São obras intelectuais protegidas as criações do espírito, "
                 "expressas por qualquer meio ou fixadas em qualquer suporte, "
                 "tangível ou intangível, conhecido ou que se invente no futuro, "
                 "tais como: VIII — as composições musicais, tenham ou não letra.",
    },
    "art_22": {
        "lei": "Lei 9.610/98",
        "referencia": "Art. 22",
        "texto": "Pertencem ao autor os direitos morais e patrimoniais "
                 "sobre a obra que criou.",
    },
    "art_24_iv": {
        "lei": "Lei 9.610/98",
        "referencia": "Art. 24, IV",
        "texto": "São direitos morais do autor: IV — o de assegurar a "
                 "integridade da obra, opondo-se a quaisquer modificações.",
    },
    "art_29_i": {
        "lei": "Lei 9.610/98",
        "referencia": "Art. 29, I",
        "texto": "Depende de autorização prévia e expressa do autor a "
                 "utilização da obra, por quaisquer modalidades, tais como: "
                 "I — a reprodução parcial ou integral.",
    },
    "art_29_ii": {
        "lei": "Lei 9.610/98",
        "referencia": "Art. 29, II",
        "texto": "Depende de autorização prévia e expressa do autor: "
                 "II — a edição.",
    },
    "art_29_iii": {
        "lei": "Lei 9.610/98",
        "referencia": "Art. 29, III",
        "texto": "Depende de autorização prévia e expressa do autor: "
                 "III — a adaptação, o arranjo musical e quaisquer outras "
                 "transformações.",
    },
    "art_33": {
        "lei": "Lei 9.610/98",
        "referencia": "Art. 33",
        "texto": "Ninguém pode reproduzir obra que não pertença ao domínio "
                 "público, a pretexto de anotá-la, comentá-la ou melhorá-la, "
                 "sem permissão do autor.",
    },
    "art_46_viii": {
        "lei": "Lei 9.610/98",
        "referencia": "Art. 46, VIII",
        "texto": "Não constitui ofensa aos direitos autorais: VIII — a "
                 "reprodução, em quaisquer obras, de pequenos trechos de "
                 "obras preexistentes, de qualquer natureza, desde que a "
                 "reprodução em si não seja o objetivo principal da obra nova "
                 "e que não prejudique a exploração normal da obra reproduzida "
                 "nem cause um prejuízo injustificado aos legítimos interesses "
                 "dos autores.",
    },
    "art_102": {
        "lei": "Lei 9.610/98",
        "referencia": "Art. 102",
        "texto": "O titular cuja obra seja fraudulentamente reproduzida, "
                 "divulgada ou de qualquer forma utilizada, poderá requerer "
                 "a apreensão dos exemplares reproduzidos ou a suspensão da "
                 "divulgação, sem prejuízo da indenização cabível.",
    },
    "art_103": {
        "lei": "Lei 9.610/98",
        "referencia": "Art. 103",
        "texto": "Quem editar obra literária, artística ou científica, sem "
                 "autorização do titular, perderá para este os exemplares que "
                 "se apreenderem e pagar-lhe-á o preço dos que tiver vendido.",
    },
    "art_104": {
        "lei": "Lei 9.610/98",
        "referencia": "Art. 104",
        "texto": "Quem vender, expuser a venda, ocultar, adquirir, "
                 "distribuir, tiver em depósito ou utilizar obra ou fonograma "
                 "reproduzidos com fraude, com a finalidade de vender, obter "
                 "ganho, vantagem, proveito, lucro direto ou indireto, para "
                 "si ou para outrem, será solidariamente responsável com o "
                 "contrafator.",
    },
    "art_5_viii_g": {
        "lei": "Lei 9.610/98",
        "referencia": "Art. 5º, VIII, g",
        "texto": "Para os efeitos desta Lei, considera-se: VIII — obra: "
                 "g) derivada — a que, constituindo criação intelectual nova, "
                 "resulta da transformação de obra originária.",
    },
}


# ═════════════════════════════════════════════════════════════════════════════
#  PADRÕES DE PLÁGIO → ARTIGOS APLICÁVEIS
# ═════════════════════════════════════════════════════════════════════════════

PADROES = {
    "sample": {
        "nome": "Amostragem (Sampling)",
        "descricao": "Elementos harmônicos e rítmicos substancialmente idênticos, "
                     "indicando reprodução do instrumental original.",
        "artigos": ["art_7_viii", "art_29_i", "art_29_iii", "art_102", "art_104"],
        "gravidade": "alta",
        "recomendacao": "A reprodução parcial de elementos musicais sem autorização "
                        "configura violação dos direitos patrimoniais do autor. "
                        "Recomenda-se consultar um advogado especializado em "
                        "propriedade intelectual para avaliar a viabilidade de "
                        "ação judicial ou acordo extrajudicial para licenciamento.",
    },
    "vocal": {
        "nome": "Plágio Melódico",
        "descricao": "A linha melódica principal apresenta similaridade substancial, "
                     "indicando possível reprodução do contorno vocal/melódico.",
        "artigos": ["art_7_viii", "art_22", "art_29_i", "art_33", "art_102"],
        "gravidade": "alta",
        "recomendacao": "A melodia é o elemento mais protegido pela legislação autoral "
                        "musical. A similaridade substancial no contorno melódico "
                        "fortalece a tese de plágio. Recomenda-se perícia técnica "
                        "musical e consulta com advogado especializado.",
    },
    "vibe": {
        "nome": "Apropriação de Identidade Sonora",
        "descricao": "Timbre e ritmo apresentam similaridade significativa, indicando "
                     "possível apropriação da identidade sonora (groove/feel).",
        "artigos": ["art_7_viii", "art_5_viii_g", "art_24_iv", "art_29_iii"],
        "gravidade": "media",
        "recomendacao": "A apropriação de identidade sonora é uma área cinzenta do "
                        "direito autoral. Embora a 'vibe' de uma música não seja "
                        "protegida diretamente, a combinação de elementos pode "
                        "configurar obra derivada. Recomenda-se análise pericial "
                        "detalhada. Precedente relevante: Marvin Gaye v. Robin Thicke "
                        "(2015, EUA).",
    },
    "suspeita_interpolacao": {
        "nome": "Suspeita de Interpolação (Obra Derivada)",
        "descricao": "O score geral é baixo, mas há alta similaridade em dimensões "
                     "específicas (timbre ou harmonia). Isso é comum na 'interpolação', "
                     "onde a melodia é regravada ou alterada, mas a roupagem instrumental "
                     "ou harmônica é mantida de forma dissimulada.",
        "artigos": ["art_5_viii_g", "art_24_iv", "art_29_iii", "art_33"],
        "gravidade": "media",
        "recomendacao": "A baixa similaridade matemática geral não descarta violação. "
                        "A apropriação de elementos singulares (interpolação) pode configurar "
                        "criação de obra derivada não autorizada, ferindo os direitos morais "
                        "e patrimoniais do autor original. Recomendada análise musicológica detalhada.",
    },
    "alta_geral": {
        "nome": "Alta Similaridade Geral",
        "descricao": "Múltiplas dimensões musicais apresentam similaridade substancial.",
        "artigos": ["art_7_viii", "art_29_i", "art_102", "art_103"],
        "gravidade": "alta",
        "recomendacao": "A convergência de similaridade em múltiplas dimensões "
                        "fortalece significativamente a hipótese de plágio. "
                        "Recomenda-se buscar orientação jurídica imediata.",
    },
    "media": {
        "nome": "Similaridade Moderada",
        "descricao": "Elementos parcialmente coincidentes que podem indicar "
                     "inspiração ou coincidência dentro do gênero musical.",
        "artigos": ["art_7_viii", "art_46_viii", "art_5_viii_g"],
        "gravidade": "media",
        "recomendacao": "A similaridade moderada pode ser resultado de elementos "
                        "comuns ao gênero musical, inspiração legítima ou coincidência. "
                        "Não configura necessariamente plágio, mas uma análise pericial "
                        "mais detalhada é recomendável para um parecer conclusivo.",
    },
    "baixa": {
        "nome": "Baixa Similaridade",
        "descricao": "As obras apresentam diferenças substanciais em todas as "
                     "dimensões analisadas.",
        "artigos": ["art_46_viii"],
        "gravidade": "baixa",
        "recomendacao": "As diferenças encontradas indicam que as obras são "
                        "substancialmente distintas. Eventuais coincidências "
                        "são consistentes com elementos comuns ao gênero. "
                        "Não há indícios de violação autoral.",
    },
}


# ═════════════════════════════════════════════════════════════════════════════
#  FUNÇÕES PÚBLICAS
# ═════════════════════════════════════════════════════════════════════════════

def detectar_padrao(score: float, breakdown: Dict[str, dict]) -> str:
    """
    Detecta o padrão de plágio a partir dos scores por dimensão.

    Retorna: "sample", "vocal", "vibe", "alta_geral", "media", ou "baixa".
    """
    s_melodia = breakdown.get("melodia", {}).get("score", 0.0)
    s_harmonia = breakdown.get("harmonia", {}).get("score", 0.0)
    s_ritmo = breakdown.get("ritmo", {}).get("score", 0.0)
    s_timbre = breakdown.get("timbre", {}).get("score", 0.0)

    # Mesma lógica dos overrides do matcher.py
    if s_harmonia >= 0.80 and s_ritmo >= 0.80:
        return "sample"

    if s_melodia >= 0.85:
        return "vocal"

    if s_timbre >= 0.85 and s_ritmo >= 0.70:
        return "vibe"

    if score >= 0.85:
        return "alta_geral"

    if score >= 0.45:
        return "media"

    # Se o score geral caiu em "baixa", mas uma das dimensões de fundo bateu alto,
    # levanta a suspeita de interpolação (regravação dissimulada).
    if s_timbre >= 0.70 or s_harmonia >= 0.60:
        return "suspeita_interpolacao"

    return "baixa"


def selecionar_artigos(padrao: str) -> List[dict]:
    """Retorna lista de artigos verificados aplicáveis ao padrão."""
    info = PADROES.get(padrao, PADROES["baixa"])
    return [ARTIGOS[key] for key in info["artigos"] if key in ARTIGOS]


def gerar_analise_estatica(
    score: float,
    breakdown: Dict[str, dict],
    padrao: str,
) -> dict:
    """
    Gera análise jurídica estática (fallback, sem LLM).

    Retorna dict com: pattern, pattern_name, severity, articles,
    description, recommendation, analysis.
    """
    info = PADROES.get(padrao, PADROES["baixa"])
    artigos = selecionar_artigos(padrao)

    # Montar descrição das dimensões
    dims = []
    dim_labels = {
        "melodia": "Melodia", "harmonia": "Harmonia",
        "ritmo": "Ritmo", "timbre": "Timbre",
    }
    for dim_name, label in dim_labels.items():
        dim_data = breakdown.get(dim_name, {})
        s = dim_data.get("score", 0.0)
        dims.append(f"{label}: {s:.1%}")

    dims_text = " | ".join(dims)
    refs = [a["referencia"] for a in artigos]

    analysis = (
        f"{info['descricao']} "
        f"Dimensões analisadas — {dims_text}. "
        f"Base legal: {', '.join(refs)} ({artigos[0]['lei']}). "
        f"{info['recomendacao']}"
    )

    return {
        "pattern": padrao,
        "pattern_name": info["nome"],
        "severity": info["gravidade"],
        "articles": [
            {"reference": a["referencia"], "text": a["texto"]}
            for a in artigos
        ],
        "analysis": analysis,
        "recommendation": info["recomendacao"],
        "source": "static",
    }
