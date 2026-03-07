"""
dsp_engine.py — Módulo de extração de características via DSP (v2).

Extrai 4 dimensões de features independentes:
  🎵 Melodia  — Contorno melódico via pyin (12, T) monophonic chroma
  🎹 Harmonia — Chromagrama (chroma_stft) polifônico (12, T)
  🎸 Timbre   — MFCCs (13, T)
  🥁 Ritmo    — Tempograma compacto (12, T)

Retorna as features como dicionário para análise multi-dimensional.

100% Processamento Digital de Sinais — zero dependências de IA/ML.
"""

import gc
from typing import Dict, Tuple

import librosa
import numpy as np


# ── Constantes ──────────────────────────────────────────────────────────────
DEFAULT_N_FFT = 2048       # Janela FFT padrão
DEFAULT_HOP_LENGTH = 512   # Salto entre janelas
N_CHROMA = 12              # 12 classes de pitch (C, C#, D, ..., B)
N_MFCC = 13               # 13 coeficientes MFCC (timbre/textura)
TEMPO_WIN_LENGTH = 64      # Janela do tempograma (autocorrelação)
N_TEMPO = 12               # Nº de lags rítmicos a reter (compacto)

# Faixa de frequência para detecção de melodia (pyin)
MELODY_FMIN = librosa.note_to_hz('C2')   # ~65 Hz (baixo)
MELODY_FMAX = librosa.note_to_hz('C7')   # ~2093 Hz (voz aguda/solo)


# ═════════════════════════════════════════════════════════════════════════════
#  EXTRATORES INDIVIDUAIS
# ═════════════════════════════════════════════════════════════════════════════

def extract_chromagram(
    signal: np.ndarray,
    sr: int = 22050,
    n_fft: int = DEFAULT_N_FFT,
    hop_length: int = DEFAULT_HOP_LENGTH,
) -> np.ndarray:
    """
    Extrai o Chromagrama polifônico (chroma_stft) do sinal.
    Captura TODAS as notas presentes (harmonia geral).

    Retorna:
        np.ndarray de shape (12, T).
    """
    chroma = librosa.feature.chroma_stft(
        y=signal,
        sr=sr,
        n_fft=n_fft,
        hop_length=hop_length,
        n_chroma=N_CHROMA,
    )
    return chroma


def extract_mfcc(
    signal: np.ndarray,
    sr: int = 22050,
    n_fft: int = DEFAULT_N_FFT,
    hop_length: int = DEFAULT_HOP_LENGTH,
) -> np.ndarray:
    """
    Extrai os MFCCs (timbre/textura) do sinal.

    Retorna:
        np.ndarray de shape (13, T).
    """
    mfcc = librosa.feature.mfcc(
        y=signal,
        sr=sr,
        n_mfcc=N_MFCC,
        n_fft=n_fft,
        hop_length=hop_length,
    )
    return mfcc


def extract_tempogram(
    signal: np.ndarray,
    sr: int = 22050,
    hop_length: int = DEFAULT_HOP_LENGTH,
) -> np.ndarray:
    """
    Extrai um Tempograma compacto (ritmo/estrutura).

    Retorna:
        np.ndarray de shape (N_TEMPO, T).
    """
    onset_env = librosa.onset.onset_strength(
        y=signal, sr=sr, hop_length=hop_length,
    )

    tempogram = librosa.feature.tempogram(
        onset_envelope=onset_env,
        sr=sr,
        hop_length=hop_length,
        win_length=TEMPO_WIN_LENGTH,
    )

    del onset_env

    # Subsample: manter N_TEMPO lags espaçados uniformemente
    indices = np.linspace(0, tempogram.shape[0] - 1, N_TEMPO, dtype=int)
    tempogram = tempogram[indices, :]

    return tempogram


def extract_melody(
    signal: np.ndarray,
    sr: int = 22050,
    hop_length: int = DEFAULT_HOP_LENGTH,
) -> np.ndarray:
    """
    Extrai o contorno melódico dominante via librosa.yin.

    Usa o algoritmo YIN bruto (sem decodificação de Viterbi/HMM)
    para detecção rápida de F0. Converte a frequência fundamental
    em Chroma Monofônico (12, T): apenas a nota dominante é marcada
    com 1.0 em cada frame, as demais ficam em 0.0.

    Diferença do chroma_stft:
      - chroma_stft: energia de TODAS as notas (polifônico)
      - melody chroma: apenas a nota PRINCIPAL (monofônico)

    Frames sem pitch detectável (silêncio, percussão) ficam zerados.

    Retorna:
        np.ndarray de shape (12, T).
    """
    f0 = librosa.yin(
        y=signal,
        sr=sr,
        fmin=MELODY_FMIN,
        fmax=MELODY_FMAX,
        hop_length=hop_length,
    )

    T = len(f0)
    melody_chroma = np.zeros((12, T), dtype=np.float32)

    # yin retorna fmin para frames sem pitch; filtrar frames válidos
    voiced_mask = np.isfinite(f0) & (f0 > MELODY_FMIN) & (f0 < MELODY_FMAX)
    if np.any(voiced_mask):
        midi_notes = librosa.hz_to_midi(f0[voiced_mask])
        pitch_classes = np.round(midi_notes).astype(int) % 12
        voiced_indices = np.where(voiced_mask)[0]
        melody_chroma[pitch_classes, voiced_indices] = 1.0

    # Liberar array intermediário
    del f0

    return melody_chroma


# ═════════════════════════════════════════════════════════════════════════════
#  PIPELINE DE EXTRAÇÃO
# ═════════════════════════════════════════════════════════════════════════════

def _normalize_and_sanitize(matrix: np.ndarray) -> np.ndarray:
    """Normaliza L2 por coluna e remove NaN/Inf."""
    matrix = librosa.util.normalize(matrix, axis=0)
    matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)
    return matrix


def extract_features(
    signal: np.ndarray, sr: int = 22050
) -> Dict[str, np.ndarray]:
    """
    Pipeline completo de extração — retorna 4 dimensões separadas.

    Processo:
      1. Extrai Melodia (12, T) — contorno melódico monofônico
      2. Extrai Harmonia (12, T) — chroma polifônico
      3. Extrai Timbre (13, T) — MFCCs
      4. Extrai Ritmo (12, T) — tempograma compacto
      5. Normaliza cada grupo (L2) + sanitiza NaN
      6. Alinha frame counts (trim ao mínimo T)

    Parâmetros:
        signal: np.ndarray mono float32 do áudio.
        sr:     Taxa de amostragem (padrão 22050).

    Retorna:
        dict com chaves: "melodia", "harmonia", "timbre", "ritmo"
        Cada valor é np.ndarray normalizado.
    """
    # 1. Extrair cada dimensão
    melodia = extract_melody(signal, sr=sr)
    harmonia = extract_chromagram(signal, sr=sr)
    timbre = extract_mfcc(signal, sr=sr)
    ritmo = extract_tempogram(signal, sr=sr)

    # ── Liberar sinal original ──
    del signal
    gc.collect()

    # 2. Alinhar frame counts (podem diferir por ±1)
    min_T = min(
        melodia.shape[1], harmonia.shape[1],
        timbre.shape[1], ritmo.shape[1],
    )
    melodia = melodia[:, :min_T]
    harmonia = harmonia[:, :min_T]
    timbre = timbre[:, :min_T]
    ritmo = ritmo[:, :min_T]

    # 3. Normalizar e sanitizar cada grupo independentemente
    melodia = _normalize_and_sanitize(melodia)
    harmonia = _normalize_and_sanitize(harmonia)
    timbre = _normalize_and_sanitize(timbre)
    ritmo = _normalize_and_sanitize(ritmo)

    return {
        "melodia": melodia,
        "harmonia": harmonia,
        "timbre": timbre,
        "ritmo": ritmo,
    }


def extract_features_combined(
    signal: np.ndarray, sr: int = 22050
) -> Tuple[Dict[str, np.ndarray], np.ndarray]:
    """
    Extrai features individuais E a matriz combinada (empilhada).

    Retorna:
        (features_dict, combined_matrix)
        - features_dict: dict com 4 matrizes individuais
        - combined_matrix: np.ndarray (49, T) para Phase 1 do DTW
    """
    features = extract_features(signal, sr=sr)

    # Empilhar para Phase 1: (12 + 12 + 13 + 12, T) = (49, T)
    combined = np.vstack([
        features["melodia"],
        features["harmonia"],
        features["timbre"],
        features["ritmo"],
    ])

    return features, combined
