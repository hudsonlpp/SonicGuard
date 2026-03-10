"""
auth.py — Lógica de Autenticação JWT e middlewares de proteção.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from dotenv import load_dotenv

import database, crud

load_dotenv()

# Senha mestre para assinar os tokens (nunca commitar em prod - via ENV)
SECRET_KEY = os.getenv("SECRET_KEY", "sonicguard_super_secret_dev_key_123")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 dias logado

# Middleware FastAPI que "caça" o header: Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Gera o JWT assinado com a nossa SECRET_KEY."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    # 'jwt.encode' nativo da PyJWT
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    """
    Função injetada nas rotas protegidas. 
    1. Pega o token do header
    2. Decodifica e extrai o e-mail
    3. Busca no banco e retorna o usuário. Se não achar/expirado, joga 401.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub") # 'sub' é o subject padrão do JWT
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError: # Captura token expirado ou inválido
        raise credentials_exception
    
    user = crud.get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
        
    return user
