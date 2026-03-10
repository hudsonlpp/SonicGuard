"""
Schemas extras para a fase 4 (Autenticação).
Adicionando Pydantic models para Request/Response de Usuários e Tokens.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional

# ── Schemas de Usuário ──
class UserCreate(BaseModel):
    """Payload para registro (POST /api/auth/register)."""
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    """Resposta do cadastro/info (esconde a senha)."""
    id: int
    email: str
    credits: int

    class Config:
        from_attributes = True

# ── Schemas de Auth (Token) ──
class Token(BaseModel):
    """Retorno do Login (POST /api/auth/login)."""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Dados embutidos no Payload do JWT."""
    email: Optional[str] = None
