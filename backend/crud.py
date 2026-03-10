"""
crud.py — Lógica de acesso ao banco (Criar Usuário, Gastar Crédito, etc).
Separa as querys SQL (SQLAlchemy) das rotas do FastAPI.
"""

from sqlalchemy.orm import Session
import models, schemas_auth
from passlib.context import CryptContext

# Configuração do Hashing de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Gera um hash irreversível da senha."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha plana bate com o hash salvo."""
    return pwd_context.verify(plain_password, hashed_password)

# ── Operações de Usuário ──

def get_user_by_email(db: Session, email: str):
    """Busca um usuário pelo email."""
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas_auth.UserCreate):
    """
    Cria a conta do usuário (com senha protegida) e já insere
    os 2 créditos iniciais do Freemium.
    """
    hashed_pwd = get_password_hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_pwd)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Injeta créditos iniciais
    db_credit = models.Credit(user_id=db_user.id, balance=2)
    db.add(db_credit)
    db.commit()

    return db_user

# ── Operações de Monetização/Monitoramento ──

def get_credits(db: Session, user_id: int):
    """Retorna saldo do usuário."""
    credit_record = db.query(models.Credit).filter(models.Credit.user_id == user_id).first()
    return credit_record.balance if credit_record else 0

def decrement_credit(db: Session, user_id: int):
    """Subtrai 1 crédito do usuário após a análise rodar."""
    credit_record = db.query(models.Credit).filter(models.Credit.user_id == user_id).first()
    if credit_record and credit_record.balance > 0:
        credit_record.balance -= 1
        db.commit()
        return True
    return False

def log_analysis(db: Session, user_id: int, source_a: str, source_b: str, score: float, verdict: str):
    """Salva a prova no banco de dados para o histórico do usuário."""
    log = models.AnalysisHistory(
        user_id=user_id,
        source_a=source_a,
        source_b=source_b,
        score=score,
        verdict=verdict
    )
    db.add(log)
    db.commit()
    return log
