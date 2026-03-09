"""
Testes de Integração para a API (main.py).
Usa o TestClient do FastAPI e Mock do motor DSP para não precisar baixar áudio.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Importa o app do main.py
from main import app
from schemas import DimensionScore

# Inicializa o cliente de testes (emula o uvicorn)
client = TestClient(app)

def test_health_check():
    """Testa se o endpoint de health check está respondendo 200 OK corretamente."""
    response = client.get("/api/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "ok"
    assert "SonicGuard v2" in json_data["engine"]

@patch('main.load_audio')
@patch('main.extract_features_combined')
@patch('main.compare')
def test_compare_endpoint_success(mock_compare, mock_extract, mock_load):
    """
    Testa o fluxo principal /api/compare mockando as chamadas 
    pesadas de librosa, yt-dlp e dtw.
    """
    # ── 1. Setup dos Mocks ──
    # mock_load_audio
    mock_load.return_value = (MagicMock(), 22050)
    
    # mock_extract_features_combined
    mock_extract.return_value = ({"melodia": MagicMock()}, MagicMock())
    
    # mock_compare (precisa retornar um objeto com um método to_dict())
    mock_result = MagicMock()
    mock_result.to_dict.return_value = {
        "score": 0.88,
        "verdict": "alta_similaridade",
        "breakdown": {
            "melodia": {"score": 0.90, "dtw_cost": 0.1, "path_length": 100, "weight": 0.40},
            "harmonia": {"score": 0.85, "dtw_cost": 0.2, "path_length": 100, "weight": 0.25},
            "ritmo": {"score": 0.90, "dtw_cost": 0.1, "path_length": 100, "weight": 0.20},
            "timbre": {"score": 0.80, "dtw_cost": 0.3, "path_length": 100, "weight": 0.15},
        },
        "dtw_cost": 0.15,
        "path_length": 1000,
        "frames_a": 500,
        "frames_b": 510,
    }
    mock_compare.return_value = mock_result

    # ── 2. Executar a Chamada de API ──
    payload = {
        "source_a": "https://youtube.com/test_A",
        "source_b": "https://youtube.com/test_B"
    }
    response = client.post("/api/compare", json=payload)

    # ── 3. Validações ──
    assert response.status_code == 200
    data = response.json()

    # Valida presença e valores dos campos principais
    assert data["score"] == 0.88
    assert data["verdict"] == "alta_similaridade"
    assert "breakdown" in data
    assert "melodia" in data["breakdown"]

    # Valida que o módulo legal foi acionado (legal_analysis)
    assert "legal_analysis" in data
    legal = data["legal_analysis"]
    # Com 0.85+ de score geral e 0.90 melodia, o motor legal no main.py 
    # aciona `detectar_padrao` com esses dados de mock.
    # O padrão 'vocal' (melodia >= 0.85) tem prioridade sobre 'alta_geral', 
    # mas o 'sample' tem sobre o vocal se ritmo e harm >= 0.80.
    # Aqui, harmonia e ritmo são 0.85/0.90 -> Padrão deve ser "sample"!
    assert legal["pattern"] == "sample"
    assert legal["severity"] == "alta"
    assert len(legal["articles"]) > 0

def test_compare_endpoint_missing_params():
    """Garante que a API bloqueia a ausência dos parâmetros."""
    payload = {"source_a": "https://youtube.com/test_A"}  # Faltando source_b
    response = client.post("/api/compare", json=payload)
    
    # FastAPI com Pydantic retorna 422 Unprocessable Entity automático
    assert response.status_code == 422
