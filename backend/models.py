"""
models.py — Definição das tabelas do banco de dados (SQLAlchemy).
- User: Guardará e-mail e hash da senha.
- Credit: Guardará as moedas do usuário (para cobrar/limitar).
- AnalysisHistory: Histórico de plágios detectados.
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
import datetime

from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relacionamentos para facilitar buscas na ORM
    credits = relationship("Credit", back_populates="owner", uselist=False)
    history = relationship("AnalysisHistory", back_populates="owner")


class Credit(Base):
    """Saldo de análises disponíveis para o usuário."""
    __tablename__ = "credits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    balance = Column(Integer, default=2)  # Todo usuário começa com 2 créditos grátis (Freemium)

    owner = relationship("User", back_populates="credits")


class AnalysisHistory(Base):
    """Log de análises (útil para o usuário ver depois e para gente debugar)."""
    __tablename__ = "analysis_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    source_a = Column(String, nullable=False)
    source_b = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    verdict = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="history")
