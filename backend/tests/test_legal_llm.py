"""
Testes unitários para a Camada de Integração LLM e Validação do Módulo Jurídico.
"""

from legal_llm import _validar_citacoes, _extrair_citacoes

# Mock de artigos permitidos (como vêm do legal.py)
ARTIGOS_PERMITIDOS = [
    {"referencia": "Art. 7º, VIII", "texto": "obras"},
    {"referencia": "Art. 29, I", "texto": "reprodução"},
    {"referencia": "Art. 102", "texto": "apreensão"},
]

def test_extrair_citacoes():
    """Testa a regex extratora de citações 'Art. XX' de um texto gerado por LLM."""
    texto_llm = "De acordo com o Art. 7º, VIII da Lei e também o Art. 29, I, vemos que..."
    citacoes = _extrair_citacoes(texto_llm)
    
    # A extração deve formatar "Art. {número}" para casar com nossa validação
    # Como a regex pega o contexto, ela busca o número após a palavra Art.
    extracao_crua = [c.replace(" ", "") for c in citacoes]
    assert any("Art.7" in c for c in extracao_crua)
    assert any("Art.29" in c for c in extracao_crua)

def test_validar_citacoes_valido():
    """Testa cenário ideal: LLM obedeceu o prompt e só citou artigos autorizados."""
    texto_valido = (
        "Há indícios de cópia baseados na proteção de composições "
        "conforme o Art. 7º, VIII. A reprodução sem autorização "
        "fere o Art. 29, I."
    )
    is_valid = _validar_citacoes(texto_valido, ARTIGOS_PERMITIDOS)
    assert is_valid is True

def test_validar_citacoes_invalido_alucinacao():
    """Testa firewall/safe harbor: LLM inventou um artigo que não estava no prompt."""
    texto_invalido = (
        "Há indícios de plágio violando o Art. 7º, VIII, mas também "
        "o Art. 184 do Código Penal que fala sobre crime."
    )
    # A presença do "Art. 184" deve fazer a validação falhar, 
    # pois não está nos ARTIGOS_PERMITIDOS (7, 29, 102)
    is_valid = _validar_citacoes(texto_invalido, ARTIGOS_PERMITIDOS)
    assert is_valid is False

def test_validar_citacoes_invalido_artigo_real_nao_listado():
    """Mesmo que o artigo exista na lei real, se não foi injetado pelo legal.py, deve falhar."""
    texto_invalido = (
        "A similaridade melódica ofende o Art. 22 e o Art. 24 da Lei 9.610/98."
    )
    # Os Arts. 22 e 24 existem na nossa base no legal.py, mas neste MOCK test
    # estamos simulando que o legal.py só autorizou o 7, 29 e 102.
    is_valid = _validar_citacoes(texto_invalido, ARTIGOS_PERMITIDOS)
    assert is_valid is False
