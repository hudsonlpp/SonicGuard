"""
database.py — Configuração do SQLAlchemy e conexão com SQLite.
Para o SonicGuard MVP, o SQLite é rápido, leve e não exige infraestrutura.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Cria o arquivo sqlalchemy.db na raiz do backend
SQLALCHEMY_DATABASE_URL = "sqlite:///./sonicguard.db"

# engine: responsável pela conexão real com o banco
# connect_args={"check_same_thread": False} é necessário apenas para SQLite no FastAPI
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# SessionLocal: fábrica de sessões do banco de dados para injetar nas rotas
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base: classe mãe que nossos modelos (User, Credit) vão herdar
Base = declarative_base()

def get_db():
    """Dependency do FastAPI para gerenciar o ciclo de vida da sessão do banco."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
