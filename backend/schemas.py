"""
schemas.py — Modelos Pydantic para a API do SonicGuard.

Define os schemas de request/response para validação automática.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class CompareRequest(BaseModel):
    """Request para comparar dois áudios."""
    source_a: str = Field(
        ...,
        description="URL do YouTube ou caminho do áudio A",
        examples=["https://www.youtube.com/watch?v=xxx"],
    )
    source_b: str = Field(
        ...,
        description="URL do YouTube ou caminho do áudio B",
        examples=["https://www.youtube.com/watch?v=yyy"],
    )


class DimensionScore(BaseModel):
    """Score de uma dimensão individual."""
    score: float
    dtw_cost: float
    path_length: int
    weight: float


class LegalArticle(BaseModel):
    """Artigo da Lei citado na análise."""
    reference: str
    text: str


class LegalAnalysis(BaseModel):
    """Análise jurídica gerada pelo módulo legal."""
    pattern: str = Field(..., description="sample | vocal | vibe | alta_geral | media | baixa")
    pattern_name: str
    severity: str = Field(..., description="alta | media | baixa")
    articles: List[LegalArticle]
    analysis: str
    recommendation: str
    source: str = Field(..., description="gemini | static")


class CompareResponse(BaseModel):
    """Response com resultado da comparação multi-dimensional."""
    score: float = Field(..., description="Score geral 0.0–1.0")
    verdict: str = Field(..., description="alta_similaridade | media_similaridade | baixa_similaridade")
    breakdown: Dict[str, DimensionScore]
    legal_analysis: Optional[LegalAnalysis] = None
    dtw_cost: float
    path_length: int
    frames_a: int
    frames_b: int
    elapsed_seconds: float
    source_a: str
    source_b: str


class HealthResponse(BaseModel):
    """Response do health check."""
    status: str = "ok"
    engine: str = "SonicGuard v2 — DSP Multi-Dimensional"


class ErrorResponse(BaseModel):
    """Response de erro."""
    detail: str
