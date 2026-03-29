"""
downloader.py — Módulo de download e carregamento de áudio.

Responsável por:
  - Baixar áudio de URLs do YouTube via yt-dlp
  - Carregar arquivos de áudio locais
  - Normalizar todo áudio para sr=22050, mono=True
  - Liberar memória agressivamente após cada operação
"""

import gc
import os
import tempfile
from pathlib import Path
from typing import Tuple

import librosa
import numpy as np


# ── Constantes ──────────────────────────────────────────────────────────────
SAMPLE_RATE = 22050  # Taxa de amostragem padrão (leve e suficiente para análise tonal)
MONO = True          # Sempre mono para reduzir uso de RAM


def _is_youtube_url(source: str) -> bool:
    """Verifica se a string é uma URL do YouTube."""
    yt_domains = ("youtube.com", "youtu.be", "www.youtube.com", "m.youtube.com")
    return any(domain in source for domain in yt_domains)


def _download_from_youtube(url: str, output_dir: str) -> str:
    """
    Baixa o áudio de uma URL do YouTube usando yt-dlp.

    Retorna o caminho do arquivo WAV baixado.
    Levanta RuntimeError se o download falhar.
    """
    try:
        import yt_dlp
    except ImportError:
        raise ImportError(
            "yt-dlp não está instalado. Instale com: pip install yt-dlp"
        )

    output_template = os.path.join(output_dir, "%(id)s.%(ext)s")
    # Resolve caminho absoluto pro cookies.txt (mesma pasta que este script no Docker)
    cookie_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")
    
    # Lista de clientes para tentar em sequência (Bypass agressivo)
    clients = [
        ["ios"],
        ["android"],
        ["web"],
        ["mweb"],
        ["tv", "web"]
    ]

    last_error = None
    for client_list in clients:
        ydl_opts = {
            "format": "worstaudio/worst", # DOWNLOAD RELÂMPAGO (qualidade baixa é suficiente para DSP)
            "outtmpl": output_template,
            "socket_timeout": 15, # Timeout rápido por tentativa
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                    "preferredquality": "128", # Menor qualidade = mais rápido
                }
            ],
            "quiet": True,
            "no_warnings": True,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "referer": "https://www.youtube.com/",
            "nocheckcertificate": True,
            "cookiefile": cookie_path if os.path.exists(cookie_path) else None,
            "extractor_args": {
                "youtube": {
                    "player_client": client_list,
                    "skip": ["dash", "hls"]
                }
            }
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_id = info.get("id", "audio")
                # Se chegou aqui, funcionou!
                break
        except Exception as e:
            last_error = e
            continue
    else:
        # Se saiu do loop sem o break, todos falharam
        raise RuntimeError(f"Download falhou após tentar múltiplos métodos. Erro final: {last_error}")

    wav_path = os.path.join(output_dir, f"{video_id}.wav")

    if not os.path.exists(wav_path):
        # yt-dlp pode gerar com extensão diferente; procurar pelo ID
        for f in os.listdir(output_dir):
            if f.startswith(video_id):
                wav_path = os.path.join(output_dir, f)
                break

    if not os.path.exists(wav_path):
        raise RuntimeError(f"Falha no download. Arquivo não encontrado para: {url}")

    return wav_path


def load_audio(source: str) -> Tuple[np.ndarray, int]:
    """
    Carrega áudio de um arquivo local ou URL do YouTube.

    Parâmetros:
        source: Caminho de arquivo local ou URL do YouTube.

    Retorna:
        Tupla (signal, sample_rate) onde signal é np.ndarray mono float32
        e sample_rate é sempre 22050.

    Levanta:
        FileNotFoundError: se o arquivo local não existir.
        RuntimeError: se o download do YouTube falhar.
    """
    temp_dir = None

    try:
        if _is_youtube_url(source):
            temp_dir = tempfile.mkdtemp(prefix="sonicguard_")
            audio_path = _download_from_youtube(source, temp_dir)
        else:
            audio_path = str(Path(source).resolve())
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Arquivo não encontrado: {audio_path}")

        # Carregar com librosa — sr=22050, mono=True (regra rígida)
        signal, sr = librosa.load(audio_path, sr=SAMPLE_RATE, mono=MONO)

        return signal, sr

    finally:
        # Limpar arquivos temporários do YouTube
        if temp_dir is not None:
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
            del temp_dir
            gc.collect()
