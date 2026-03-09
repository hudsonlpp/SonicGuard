"""
Testes unitários para o módulo `legal.py` (Regras Estáticas + Base de Conhecimento).
"""

from legal import detectar_padrao, selecionar_artigos, gerar_analise_estatica, PADROES

def test_detectar_padrao_sample():
    """Testa se harmonia e ritmo altos acionam o padrão 'sample' (amostragem)."""
    breakdown = {
        "melodia": {"score": 0.10},
        "harmonia": {"score": 0.85},
        "ritmo": {"score": 0.90},
        "timbre": {"score": 0.20},
    }
    score = 0.50
    padrao = detectar_padrao(score, breakdown)
    assert padrao == "sample"

def test_detectar_padrao_vocal():
    """Testa se melodia muito alta aciona o padrão 'vocal' independente do score geral."""
    breakdown = {
        "melodia": {"score": 0.95},
        "harmonia": {"score": 0.10},
        "ritmo": {"score": 0.20},
        "timbre": {"score": 0.10},
    }
    score = 0.40  # Baixo porque o resto é baixo (melodia pesa 40%)
    padrao = detectar_padrao(score, breakdown)
    assert padrao == "vocal"

def test_detectar_padrao_suspeita_interpolacao():
    """Testa a regra de edge case (Olivia Rodrigo vs Paramore): score baixo, mas timbre alto."""
    breakdown = {
        "melodia": {"score": 0.05},
        "harmonia": {"score": 0.20},
        "ritmo": {"score": 0.30},
        "timbre": {"score": 0.80},
    }
    score = 0.25  # Score geral < 45% (baixa similaridade geral)
    padrao = detectar_padrao(score, breakdown)
    # Timbre alto (>= 70%) levanta suspeita de interpolação
    assert padrao == "suspeita_interpolacao"

def test_detectar_padrao_alta_geral():
    """Testa se um score alto não coberto pelas regras finas cai em 'alta_geral'."""
    breakdown = {
        "melodia": {"score": 0.84},  # Perto de vocal (0.85) mas não bate 
        "harmonia": {"score": 0.79}, # Perto de sample (0.80) mas não bate
        "ritmo": {"score": 0.99},    # Ritmo alto compensa na matemática
        "timbre": {"score": 0.84},   # Perto mas não bate vibe (0.85)
    }
    # (0.4 * 0.84) + (0.25 * 0.79) + (0.2 * 0.99) + (0.15 * 0.84) = 0.8575
    score = 0.8575
    padrao = detectar_padrao(score, breakdown)
    assert padrao == "alta_geral"

def test_selecionar_artigos():
    """Testa se o seletor de artigos retorna as referências corretas do banco."""
    # Testando o caso de Obra Derivada
    artigos_interpolacao = selecionar_artigos("suspeita_interpolacao")
    refs = [a["referencia"] for a in artigos_interpolacao]
    assert "Art. 5º, VIII, g" in refs
    assert "Art. 24, IV" in refs

    # Testando o caso genérico
    artigos_baixa = selecionar_artigos("baixa")
    refs_baixa = [a["referencia"] for a in artigos_baixa]
    assert "Art. 46, VIII" in refs_baixa

def test_gerar_analise_estatica():
    """Testa a geração do fallback estático garante que a estrutura retorna certa."""
    breakdown = {
        "melodia": {"score": 0.0},
        "harmonia": {"score": 0.80},
        "ritmo": {"score": 0.80},
        "timbre": {"score": 0.0},
    }
    score = 0.36
    resultado = gerar_analise_estatica(score, breakdown, "sample")
    
    assert resultado["pattern"] == "sample"
    assert resultado["severity"] == PADROES["sample"]["gravidade"]
    assert "source" in resultado and resultado["source"] == "static"
    # Deve conter a palavra 'Harmonia' no texto
    assert "Harmonia: 80.0%" in resultado["analysis"]
