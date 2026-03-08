"""
matcher.py — Módulo de comparação multi-dimensional via Two-Pass DTW (v2).

Arquitetura de Análise Multi-Dimensional:
  OTI:             Transposição global ótima de B para alinhar tom com A
  Phase 1 (Busca): Subsequence DTW na matriz combinada (49 dims)
  Phase 2 (Valid): 4× Global DTW restrito por dimensão
  Fusão:           Média ponderada + Rule-Based Overrides

Dimensões e pesos:
  🎵 Melodia  (40%) — contorno melódico dominante
  🎹 Harmonia (25%) — progressão de acordes
  🥁 Ritmo    (20%) — padrão rítmico
  🎸 Timbre   (15%) — sonoridade/textura

Overrides (detecção por padrão):
  🔴 Sample Rule:  Harmonia >= 80% E Ritmo >= 80% → score >= 85%
  🔴 Vocal Rule:   Melodia >= 85% → score >= 85%
  🟡 Vibe Rule:    Timbre >= 85% E Ritmo >= 70% → score >= 65%

100% determinístico — baseado exclusivamente em Dynamic Time Warping.
"""

import gc
import math
from dataclasses import dataclass
from typing import Dict

import librosa
import numpy as np
from scipy.spatial.distance import cdist


# ── Constantes de Classificação ─────────────────────────────────────────────
THRESHOLD_HIGH = 0.85
THRESHOLD_MEDIUM = 0.45

# ── Parâmetros da Curva Sigmoide (calibrados por dimensão) ────────────────────
SIGMOID_PARAMS = {
    "melodia":  {"midpoint": 0.60, "steepness": 40},
    "harmonia": {"midpoint": 0.22, "steepness": 60},
    "ritmo":    {"midpoint": 0.08, "steepness": 80},
    "timbre":   {"midpoint": 0.16, "steepness": 60},
}

# ── Pesos das Dimensões ─────────────────────────────────────────────────────
DIMENSION_WEIGHTS = {
    "melodia":  0.40,
    "harmonia": 0.25,
    "ritmo":    0.20,
    "timbre":   0.15,
}

# ── Restrições do DTW ────────────────────────────────────────────────────────
_STEP_PENALTY = 0.05
_SAKOE_CHIBA_FRACTION = 0.20

# ── Penalidade de Cobertura ──────────────────────────────────────────────────
_MIN_COVERAGE = 0.10

# ── Step sizes e weights ────────────────────────────────────────────────────
_STEP_SIZES = np.array([[1, 1], [0, 1], [1, 0]])
_WEIGHTS_ADD = np.array([0.0, _STEP_PENALTY, _STEP_PENALTY])


@dataclass
class MatchResult:
    """Resultado estruturado da comparação multi-dimensional."""
    score: float
    verdict: str
    breakdown: Dict[str, dict]
    dtw_cost: float
    path_length: int
    frames_a: int
    frames_b: int

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 4),
            "verdict": self.verdict,
            "breakdown": {
                dim: {k: round(v, 4) if isinstance(v, float) else v
                      for k, v in data.items()}
                for dim, data in self.breakdown.items()
            },
            "dtw_cost": round(self.dtw_cost, 4),
            "path_length": self.path_length,
            "frames_a": self.frames_a,
            "frames_b": self.frames_b,
        }


# ═════════════════════════════════════════════════════════════════════════════
#  OTI — OPTIMAL TRANSPOSITION INDEX
# ═════════════════════════════════════════════════════════════════════════════

def _compute_oti(
    harmonia_a: np.ndarray, harmonia_b: np.ndarray
) -> int:
    """
    Calcula o Optimal Transposition Index entre dois áudios.
    Custo: ~zero (12 dot products em vetores de 12 dims).
    Retorna int (0–11).
    """
    profile_a = harmonia_a.mean(axis=1)
    profile_b = harmonia_b.mean(axis=1)

    norm_a = np.linalg.norm(profile_a)
    norm_b = np.linalg.norm(profile_b)

    if norm_a < 1e-10 or norm_b < 1e-10:
        return 0

    best_shift = 0
    best_sim = -1.0

    for shift in range(12):
        shifted = np.roll(profile_b, shift)
        sim = np.dot(profile_a, shifted) / (norm_a * np.linalg.norm(shifted))
        if sim > best_sim:
            best_sim = sim
            best_shift = shift

    return best_shift


def _apply_oti(
    features_b: Dict[str, np.ndarray],
    combined_b: np.ndarray,
    oti_shift: int,
) -> None:
    """
    Aplica o OTI shift nas features tonais de B (in-place).
    Linhas 0–11: melodia, 12–23: harmonia. Timbre e ritmo intocados.
    """
    if oti_shift == 0:
        return

    features_b["melodia"] = np.roll(features_b["melodia"], oti_shift, axis=0)
    features_b["harmonia"] = np.roll(features_b["harmonia"], oti_shift, axis=0)

    combined_b[:12] = np.roll(combined_b[:12], oti_shift, axis=0)
    combined_b[12:24] = np.roll(combined_b[12:24], oti_shift, axis=0)


# ═════════════════════════════════════════════════════════════════════════════
#  PHASE 1 — BUSCA (Subsequence DTW)
# ═════════════════════════════════════════════════════════════════════════════

def _phase1_search(combined_a: np.ndarray, combined_b: np.ndarray):
    """
    Localiza a janela do possível plágio via Subsequence DTW.

    Usa downsampling 2× para reduzir consumo de RAM:
      10k×10k (~850 MiB) → 5k×5k (~212 MiB)

    As coordenadas são escaladas de volta para a resolução original.
    Retorna (start_a, end_a, start_b, end_b).
    """
    # Downsample 2×: pega 1 a cada 2 frames
    _DS = 2
    ds_a = combined_a[:, ::_DS]
    ds_b = combined_b[:, ::_DS]

    C = cdist(ds_a.T, ds_b.T, metric="cosine").astype(np.float32)

    del ds_a, ds_b
    gc.collect()

    np.nan_to_num(C, copy=False, nan=np.float32(2.0), posinf=np.float32(2.0), neginf=np.float32(0.0))

    D, wp = librosa.sequence.dtw(
        C=C,
        step_sizes_sigma=_STEP_SIZES,
        weights_add=_WEIGHTS_ADD,
        subseq=True,
    )

    # Escalando coordenadas de volta para resolução original
    start_a = int(wp[-1, 0]) * _DS
    start_b = int(wp[-1, 1]) * _DS
    end_a = min(int(wp[0, 0]) * _DS, combined_a.shape[1] - 1)
    end_b = min(int(wp[0, 1]) * _DS, combined_b.shape[1] - 1)

    del C, D, wp
    gc.collect()

    return start_a, end_a, start_b, end_b


# ═════════════════════════════════════════════════════════════════════════════
#  PHASE 2 — VALIDAÇÃO PER-DIMENSION (Global DTW Restrito)
# ═════════════════════════════════════════════════════════════════════════════

def _apply_sakoe_chiba_band(C: np.ndarray, fraction: float) -> np.ndarray:
    """Aplica restrição Sakoe-Chiba in-place."""
    N, M = C.shape
    bandwidth = max(int(fraction * min(N, M)), 1)

    for i in range(N):
        j_center = int(i * M / N)
        j_low = max(0, j_center - bandwidth)
        j_high = min(M, j_center + bandwidth + 1)

        if j_low > 0:
            C[i, :j_low] = 1e9
        if j_high < M:
            C[i, j_high:] = 1e9

    return C


def _phase2_validate_dimension(crop_a: np.ndarray, crop_b: np.ndarray):
    """
    Fase 2 para UMA dimensão: Global DTW restrito no trecho isolado.
    Retorna (custo_total, path_length).
    """
    C_sub = cdist(crop_a.T, crop_b.T, metric="cosine").astype(np.float32)
    np.nan_to_num(C_sub, copy=False, nan=np.float32(2.0), posinf=np.float32(2.0), neginf=np.float32(0.0))
    C_sub = _apply_sakoe_chiba_band(C_sub, _SAKOE_CHIBA_FRACTION)

    D, wp = librosa.sequence.dtw(
        C=C_sub,
        step_sizes_sigma=_STEP_SIZES,
        weights_add=_WEIGHTS_ADD,
        subseq=False,
    )

    total_cost = float(D[-1, -1])
    path_length = len(wp)

    if not np.isfinite(total_cost):
        total_cost = 2.0 * path_length if path_length > 0 else 0.0

    del C_sub, D, wp
    gc.collect()

    return total_cost, path_length


# ═════════════════════════════════════════════════════════════════════════════
#  NORMALIZAÇÃO, OVERRIDES E CLASSIFICAÇÃO
# ═════════════════════════════════════════════════════════════════════════════

def _sigmoid_score(dtw_cost: float, path_length: int, dim_name: str) -> float:
    """Aplica a curva Sigmoide calibrada para a dimensão específica."""
    if path_length <= 0:
        return 0.0

    avg_cost = dtw_cost / path_length
    if not math.isfinite(avg_cost):
        return 0.0

    params = SIGMOID_PARAMS[dim_name]
    score = 1.0 / (1.0 + math.exp(
        params["steepness"] * (avg_cost - params["midpoint"])
    ))

    return max(0.0, min(score, 1.0))


def _apply_override_rules(score: float, breakdown: Dict[str, dict]) -> float:
    """
    Rule-Based Fusion: overrides dinâmicos baseados em padrões de plágio.

    🔴 Sample Rule:  Harmonia >= 80% E Ritmo >= 80% → score >= 85%
    🔴 Vocal Rule:   Melodia >= 85% → score >= 85%
    🟡 Vibe Rule:    Timbre >= 85% E Ritmo >= 70% → score >= 65%
    """
    s_melodia = breakdown["melodia"]["score"]
    s_harmonia = breakdown["harmonia"]["score"]
    s_ritmo = breakdown["ritmo"]["score"]
    s_timbre = breakdown["timbre"]["score"]

    if s_harmonia >= 0.80 and s_ritmo >= 0.80:
        score = max(score, 0.85)

    if s_melodia >= 0.85:
        score = max(score, 0.85)

    if s_timbre >= 0.85 and s_ritmo >= 0.70:
        score = max(score, 0.65)

    return score


def _apply_coverage_penalty(
    score: float,
    crop_len_a: int, crop_len_b: int,
    frames_a: int, frames_b: int,
) -> float:
    """Penalidade de cobertura dupla."""
    coverage_a = crop_len_a / frames_a if frames_a > 0 else 0.0
    coverage_b = crop_len_b / frames_b if frames_b > 0 else 0.0
    coverage = max(coverage_a, coverage_b)

    if coverage < _MIN_COVERAGE:
        score *= coverage / _MIN_COVERAGE

    return max(0.0, min(score, 1.0))


def _classify(score: float) -> str:
    """Classifica o score de similaridade em veredicto textual."""
    if score >= THRESHOLD_HIGH:
        return "alta_similaridade"
    elif score >= THRESHOLD_MEDIUM:
        return "media_similaridade"
    else:
        return "baixa_similaridade"


# ═════════════════════════════════════════════════════════════════════════════
#  PIPELINE PRINCIPAL (TWO-PASS MULTI-DIMENSIONAL)
# ═════════════════════════════════════════════════════════════════════════════

def compare(
    features_a: Dict[str, np.ndarray],
    features_b: Dict[str, np.ndarray],
    combined_a: np.ndarray,
    combined_b: np.ndarray,
) -> MatchResult:
    """
    Compara dois áudios via Two-Pass DTW Multi-Dimensional.

    OTI:       Transposição global ótima de B para alinhar tom com A
    Phase 1:   Subsequence DTW (combined 49×T) → localiza janela
    Phase 2:   4× Global DTW restrito por dimensão → valida janela
    Fusão:     Média ponderada + Rule-Based Overrides
    """
    frames_a = combined_a.shape[1]
    frames_b = combined_b.shape[1]

    # ══ OTI: Transposição Global Ótima ══
    oti_shift = _compute_oti(features_a["harmonia"], features_b["harmonia"])
    _apply_oti(features_b, combined_b, oti_shift)

    # ══ PHASE 1: Busca via Subsequence DTW ══
    start_a, end_a, start_b, end_b = _phase1_search(combined_a, combined_b)

    del combined_a, combined_b
    gc.collect()

    crop_len_a = end_a - start_a + 1
    crop_len_b = end_b - start_b + 1

    # ══ PHASE 2: Validação por dimensão ══
    breakdown = {}
    weighted_score = 0.0
    weighted_cost = 0.0
    melody_path_length = 0

    for dim_name, weight in DIMENSION_WEIGHTS.items():
        crop_a = features_a[dim_name][:, start_a:end_a + 1]
        crop_b = features_b[dim_name][:, start_b:end_b + 1]

        dtw_cost, path_length = _phase2_validate_dimension(crop_a, crop_b)

        dim_score = _sigmoid_score(dtw_cost, path_length, dim_name)

        cost_per_step = dtw_cost / path_length if path_length > 0 else 0.0
        if not math.isfinite(cost_per_step):
            cost_per_step = 0.0

        breakdown[dim_name] = {
            "score": dim_score,
            "dtw_cost": cost_per_step,
            "path_length": path_length,
            "weight": weight,
        }

        weighted_score += weight * dim_score
        weighted_cost += weight * cost_per_step

        if dim_name == "melodia":
            melody_path_length = path_length

        del crop_a, crop_b
        gc.collect()

    # ══ SCORE FINAL ══

    # 1. Penalidade de cobertura
    final_score = _apply_coverage_penalty(
        weighted_score,
        crop_len_a, crop_len_b,
        frames_a, frames_b,
    )

    # 2. Rule-Based Overrides
    final_score = _apply_override_rules(final_score, breakdown)

    if not math.isfinite(final_score):
        final_score = 0.0

    verdict = _classify(final_score)

    del features_a, features_b
    gc.collect()

    return MatchResult(
        score=final_score,
        verdict=verdict,
        breakdown=breakdown,
        dtw_cost=weighted_cost,
        path_length=melody_path_length,
        frames_a=frames_a,
        frames_b=frames_b,
    )
