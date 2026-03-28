FROM python:3.10-slim

# Instala as bibliotecas do sistema que o librosa e o soundfile exigem
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do app
COPY . .

# Expõe e inicia a API. O Render injeta $PORT automaticamente
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}
