#!/usr/bin/env python3
"""
plagiarism_engine.py — Motor de Detecção de Plágio Musical (SonicGuard v2)

Pipeline 100% DSP com Análise Multi-Dimensional:
  1. Download / carregamento de áudio
  2. Extração de 4 dimensões de features (Melodia, Harmonia, Timbre, Ritmo)
  3. Two-Pass DTW multi-dimensional com fusão ponderada
  4. Classificação e exibição do resultado com breakdown

Uso:
  python plagiarism_engine.py <audio_a> <audio_b>

Onde <audio_a> e <audio_b> podem ser caminhos locais ou URLs do YouTube.
"""

import argparse
import gc
import json
import sys
import time

from downloader import load_audio
from dsp_engine import extract_features_combined
from matcher import compare, DIMENSION_WEIGHTS


# ── Emojis e labels das dimensões ───────────────────────────────────────────
_DIM_EMOJI = {
    "melodia":  "🎵",
    "harmonia": "🎹",
    "ritmo":    "🥁",
    "timbre":   "🎸",
}

_DIM_LABEL = {
    "melodia":  "Melodia ",
    "harmonia": "Harmonia",
    "ritmo":    "Ritmo   ",
    "timbre":   "Timbre  ",
}


def _print_header():
    """Exibe cabeçalho do SonicGuard."""
    print("=" * 60)
    print("  🔊 SonicGuard v2 — Motor de Detecção de Plágio Musical")
    print("  📐 Modo: DSP Multi-Dimensional (Two-Pass DTW)")
    print("=" * 60)
    print()


def _print_result(result, elapsed: float, source_a: str, source_b: str):
    """Exibe o resultado formatado da comparação multi-dimensional."""
    data = result.to_dict()

    verdict_emoji = {
        "alta_similaridade": "🔴",
        "media_similaridade": "🟡",
        "baixa_similaridade": "🟢",
    }

    verdict_label = {
        "alta_similaridade": "ALTA SIMILARIDADE — Possível plágio!",
        "media_similaridade": "MÉDIA SIMILARIDADE — Requer investigação",
        "baixa_similaridade": "BAIXA SIMILARIDADE — Provavelmente original",
    }

    emoji = verdict_emoji.get(data["verdict"], "⚪")
    label = verdict_label.get(data["verdict"], data["verdict"])

    print()
    print("─" * 60)
    print(f"  {emoji}  VEREDICTO: {label}")
    print("─" * 60)
    print(f"  Score Geral          : {data['score']:.2%}")
    print()

    # Breakdown por dimensão
    print("  📊 Breakdown por Dimensão:")
    for dim_name in DIMENSION_WEIGHTS:
        dim_data = data["breakdown"][dim_name]
        dim_emoji = _DIM_EMOJI.get(dim_name, "•")
        dim_label = _DIM_LABEL.get(dim_name, dim_name)
        weight_pct = int(dim_data["weight"] * 100)
        print(f"    {dim_emoji} {dim_label} ({weight_pct:2d}%): "
              f"{dim_data['score']:.2%}  "
              f"(custo: {dim_data['dtw_cost']:.4f})")

    print()
    print(f"  Custo DTW Ponderado  : {data['dtw_cost']:.4f}")
    print(f"  Path Length (Melodia): {data['path_length']} passos")
    print(f"  Frames Áudio A       : {data['frames_a']}")
    print(f"  Frames Áudio B       : {data['frames_b']}")
    print(f"  Tempo de execução    : {elapsed:.2f}s")
    print("─" * 60)
    print()
    print(f"  Áudio A: {source_a}")
    print(f"  Áudio B: {source_b}")
    print("─" * 60)

    # Saída JSON para integração programática
    output = {
        **data,
        "elapsed_seconds": round(elapsed, 2),
        "source_a": source_a,
        "source_b": source_b,
    }
    print()
    print("📋 JSON:")
    print(json.dumps(output, indent=2, ensure_ascii=False))


def run_pipeline(source_a: str, source_b: str) -> dict:
    """
    Executa o pipeline completo de comparação multi-dimensional.

    Processamento sequencial para economia de RAM:
      1. Carrega áudio A → extrai features (dict + combined) → libera sinal A
      2. Carrega áudio B → extrai features (dict + combined) → libera sinal B
      3. Compara via Two-Pass DTW multi-dimensional → libera features

    Retorna dicionário com resultado da comparação.
    """
    start = time.time()

    # ── Passo 1: Carregar e processar Áudio A ──
    print("  [1/4] Carregando Áudio A...")
    signal_a, sr_a = load_audio(source_a)
    print(f"        ✔ Carregado ({len(signal_a)} amostras, sr={sr_a})")

    print("  [2/4] Extraindo Features A (Melodia + Harmonia + Timbre + Ritmo)...")
    features_a, combined_a = extract_features_combined(signal_a, sr=sr_a)
    del signal_a
    gc.collect()
    print(f"        ✔ Features A: {len(features_a)} dimensões, "
          f"combined shape {combined_a.shape}")

    # ── Passo 2: Carregar e processar Áudio B ──
    print("  [3/4] Carregando Áudio B...")
    signal_b, sr_b = load_audio(source_b)
    print(f"        ✔ Carregado ({len(signal_b)} amostras, sr={sr_b})")

    print("  [4/4] Extraindo Features B e comparando via Two-Pass DTW...")
    features_b, combined_b = extract_features_combined(signal_b, sr=sr_b)
    del signal_b
    gc.collect()
    print(f"        ✔ Features B: {len(features_b)} dimensões, "
          f"combined shape {combined_b.shape}")

    # ── Passo 3: Comparação Multi-Dimensional ──
    result = compare(features_a, features_b, combined_a, combined_b)
    # features e combined já foram liberados dentro de compare
    gc.collect()

    elapsed = time.time() - start

    _print_result(result, elapsed, source_a, source_b)

    return {
        **result.to_dict(),
        "elapsed_seconds": round(elapsed, 2),
        "source_a": source_a,
        "source_b": source_b,
    }


def main():
    """Ponto de entrada CLI."""
    parser = argparse.ArgumentParser(
        description="SonicGuard v2 — Motor de Detecção de Plágio Musical (DSP)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python plagiarism_engine.py musica1.wav musica2.wav
  python plagiarism_engine.py musica1.mp3 "https://youtube.com/watch?v=xxx"
  python plagiarism_engine.py "https://youtu.be/aaa" "https://youtu.be/bbb"
        """,
    )
    parser.add_argument(
        "audio_a",
        help="Caminho do arquivo de áudio A ou URL do YouTube",
    )
    parser.add_argument(
        "audio_b",
        help="Caminho do arquivo de áudio B ou URL do YouTube",
    )

    args = parser.parse_args()

    _print_header()

    try:
        run_pipeline(args.audio_a, args.audio_b)
    except FileNotFoundError as e:
        print(f"\n❌ Erro: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"\n❌ Erro: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
