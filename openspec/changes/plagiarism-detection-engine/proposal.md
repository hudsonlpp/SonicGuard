## Why

O projeto SonicGuard precisa de um script Python isolado e autocontido que funcione como motor de detecção de plágio musical. Atualmente, a lógica de comparação de áudio está acoplada à estrutura FastAPI do backend, dificultando testes independentes e reutilização em outros contextos. Este motor será **100% baseado em Processamento Digital de Sinais (DSP)**, sem qualquer dependência de redes neurais, modelos de IA, PyTorch ou Transformers — garantindo execução leve, determinística e compatível com hardware limitado.

## What Changes

- **Novo script Python standalone** (`plagiarism_engine.py`) que encapsula todo o pipeline de detecção de plágio via DSP:
  - Download de áudio a partir de URLs do YouTube via `yt-dlp`
  - Carregamento de arquivos de áudio locais com `librosa` (`sr=22050`, `mono=True`)
  - **Extração de características via Chromagrama** (`librosa.feature.chroma_stft`) — representação tonal das 12 classes de pitch
  - **Comparação via Dynamic Time Warping (DTW)** (`librosa.sequence.dtw`) — alinhamento temporal não-linear entre os dois chromagramas
  - Normalização do custo DTW em score de similaridade (0.0 a 1.0)
  - Classificação do resultado (alta/média/baixa similaridade) com score de probabilidade
- **Otimização rigorosa de RAM**:
  - `del` explícito de arrays intermediários após cada etapa do pipeline
  - `gc.collect()` após liberação de memória
  - Processamento sequencial (nunca carregar dois áudios completos simultaneamente)
- **Interface CLI** para execução via linha de comando com dois inputs (arquivos locais ou URLs do YouTube)
- **Saída estruturada** com score de similaridade, veredicto e metadados da comparação
- **Módulos internos desacoplados**: downloader, dsp_engine (extração de features), e matcher (DTW + classificação)

## Capabilities

### New Capabilities
- `audio-download`: Download e pré-processamento de áudio a partir de URLs do YouTube e arquivos locais (`sr=22050`, `mono=True`)
- `chroma-extraction`: Extração de Chromagrama via `librosa.feature.chroma_stft` para representação tonal do áudio
- `dtw-matching`: Comparação via Dynamic Time Warping (`librosa.sequence.dtw`), normalização do custo e classificação do resultado
- `cli-interface`: Interface de linha de comando para execução do pipeline completo
- `ram-optimization`: Gestão agressiva de memória com `del`, `gc.collect()` e processamento sequencial

### Modified Capabilities
<!-- Nenhuma capability existente será modificada -->

## Impact

- **Código**: Novo script standalone em `backend/plagiarism_engine.py` com módulos auxiliares (`downloader.py`, `dsp_engine.py`, `matcher.py`)
- **Dependências**: `librosa`, `numpy`, `scipy`, `yt-dlp` — **zero dependências de IA/ML** (sem torch, transformers, ou qualquer modelo neural)
- **Sistemas**: Nenhum impacto em sistemas existentes — script completamente isolado
- **APIs**: Nenhuma API afetada — execução exclusivamente via CLI
- **Hardware**: Consumo mínimo de RAM e CPU — compatível com máquinas de recursos limitados
