# SonicGuard API — Contrato de Interface (Backend ↔ Frontend)

## Base URL
```
http://localhost:8000/api
```

## Endpoints

### POST /api/compare
Compara dois áudios e retorna análise multi-dimensional de plágio.

**Request** (multipart/form-data OU JSON):
```json
{
  "source_a": "https://www.youtube.com/watch?v=xxx",
  "source_b": "https://www.youtube.com/watch?v=yyy"
}
```

**Response** (200 OK):
```json
{
  "score": 0.85,
  "verdict": "alta_similaridade",
  "breakdown": {
    "melodia":  { "score": 0.0396, "dtw_cost": 0.6797, "path_length": 10563, "weight": 0.4 },
    "harmonia": { "score": 0.8554, "dtw_cost": 0.1904, "path_length": 10610, "weight": 0.25 },
    "ritmo":    { "score": 0.9165, "dtw_cost": 0.0501, "path_length": 10209, "weight": 0.2 },
    "timbre":   { "score": 0.0603, "dtw_cost": 0.2058, "path_length": 10317, "weight": 0.15 }
  },
  "dtw_cost": 0.3604,
  "path_length": 10563,
  "frames_a": 10209,
  "frames_b": 10899,
  "elapsed_seconds": 46.5,
  "source_a": "https://www.youtube.com/watch?v=xxx",
  "source_b": "https://www.youtube.com/watch?v=yyy"
}
```

**Verdicts possíveis:**
- `"alta_similaridade"` — score >= 85%
- `"media_similaridade"` — score >= 45%
- `"baixa_similaridade"` — score < 45%

**Breakdown dimensions:**
- `melodia` (40%) — contorno melódico dominante
- `harmonia` (25%) — progressão de acordes
- `ritmo` (20%) — padrão rítmico
- `timbre` (15%) — sonoridade/textura

### GET /api/health
Health check.

**Response**: `{ "status": "ok" }`

## Stack
- **Backend**: Python, FastAPI, librosa, scipy (pasta `backend/`)
- **Frontend**: A definir (pasta `frontend/`)
- **Processamento**: ~35-50s por comparação (músicas de ~4 min)
