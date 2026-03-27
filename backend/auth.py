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
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)


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
    # Bypassed authentication: always inject the presentation user regardless of token
    user = crud.get_user_by_email(db, email="hudsonluizperes@poli.ufrj.br")
    return user
