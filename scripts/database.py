import contextlib
import logging
import os
from datetime import date, datetime, timedelta

from flask_login import UserMixin
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import backref, declarative_base, relationship, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

# Configure logger
logger = logging.getLogger(__name__)

# Define the database file path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'database', 'main.db')}"

# Create a SQLAlchemy engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    pool_pre_ping=True,  # Verifica conexão antes de usar (evita conexões fechadas)
)

# Create a SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a declarative base
Base = declarative_base()


class DocumentoFiscalSped(Base):
    __tablename__ = "documento_fiscal_sped"
    id = Column(Integer, primary_key=True)
    num_documento = Column(String(60), nullable=False, index=True)
    serie = Column(String(3), nullable=False)
    data = Column(Date, nullable=False, index=True)
    valor_total = Column(Float, nullable=False)
    ind_oper = Column(String(1), nullable=False, index=True)  # 0=Entrada; 1=Saída
    ind_pagamento = Column(
        String(1), nullable=False, index=True
    )  # 0=À vista; 1=A prazo; 2=Outros
    data_importacao = Column(Date, default=date.today)

    __table_args__ = (UniqueConstraint("num_documento", "serie", name="_num_serie_uc"),)


# Define the Cfop model
class Cfop(Base):
    __tablename__ = "cfops"

    cfop = Column(String(4), primary_key=True, comment="Código CFOP de 4 dígitos")
    data_criacao = Column(
        Date, nullable=False, default=date.today, comment="Data de criação do registro"
    )

    acumuladores = relationship(
        "Acumulador", back_populates="cfop_rel", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("cfop", name="uq_cfop"),
        {"comment": "Tabela de CFOPs (Código Fiscal de Operações e Prestações)"},
    )


# Define the Acumulador model
class Acumulador(Base):
    __tablename__ = "acumuladores"

    codigo = Column(String(10), primary_key=True, comment="Código do acumulador")
    descricao = Column(String(100), nullable=False, comment="Descrição do acumulador")
    cfop = Column(
        String(4), ForeignKey("cfops.cfop", ondelete="RESTRICT"), nullable=False
    )
    data_criacao = Column(Date, nullable=False, default=date.today)
    data_alteracao = Column(Date, nullable=True, onupdate=date.today)

    cfop_rel = relationship("Cfop", back_populates="acumuladores", lazy="joined")
    produtos = relationship(
        "ProdutoSped", back_populates="acumulador_rel", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("codigo", name="uq_acumulador_codigo"),
        {"comment": "Tabela de acumuladores para agrupamento de produtos por CFOP"},
    )


# Define the ProdutoSped model
class ProdutoSped(Base):
    __tablename__ = "produtos_sped"

    codigo_item = Column(
        String(60),
        primary_key=True,
        comment="Código do item no sistema do contribuinte",
    )
    descricao_item = Column(
        String(200), nullable=False, index=True, comment="Descrição do item"
    )
    unidade = Column(String(6), nullable=False, comment="Unidade de medida do item")
    ncm = Column(String(8), nullable=False, index=True, comment="Código NCM do item")
    acumulador = Column(
        String(10),
        ForeignKey("acumuladores.codigo", ondelete="RESTRICT"),
        nullable=True,
        comment="Código do acumulador associado",
    )
    data_cadastro = Column(Date, nullable=False, default=date.today)
    data_alteracao = Column(Date, nullable=True, onupdate=date.today)
    aliquota_icms = Column(
        Float, nullable=True, comment="Alíquota de ICMS padrão do produto"
    )
    cest = Column(String(7), nullable=True, comment="Código CEST do produto")
    cod_barras = Column(
        String(14), nullable=True, comment="Código de barras do produto"
    )

    acumulador_rel = relationship(
        "Acumulador", back_populates="produtos", lazy="joined"
    )
    vendas = relationship(
        "VendaSped", backref="produto_rel", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("codigo_item", name="uq_produto_codigo"),
        {"comment": "Tabela de produtos do SPED Fiscal"},
    )


# Define the VendaSped model
class VendaSped(Base):
    __tablename__ = "vendas_sped"

    id = Column(Integer, primary_key=True, autoincrement=True)
    documento_id = Column(
        Integer, ForeignKey("documento_fiscal_sped.id"), nullable=False, index=True
    )
    data = Column(Date, nullable=False, index=True)  # Redundante, mas útil para queries
    codigo_item = Column(
        String(60),
        ForeignKey("produtos_sped.codigo_item", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Código do item vendido",
    )

    quantidade = Column(Float, nullable=False, comment="Quantidade vendida")
    valor_unitario = Column(Float, nullable=False, comment="Valor unitário do item")
    valor_total = Column(Float, nullable=False, comment="Valor total da venda")
    valor_desconto = Column(
        Float, nullable=True, default=0, comment="Valor do desconto"
    )
    base_icms = Column(Float, nullable=True, comment="Base de cálculo do ICMS")
    valor_icms = Column(Float, nullable=True, comment="Valor do ICMS")
    aliquota_icms = Column(Float, nullable=True, comment="Alíquota do ICMS aplicada")
    data_importacao = Column(Date, nullable=False, default=date.today)

    documento_rel = relationship(
        "DocumentoFiscalSped", backref=backref("itens", cascade="all, delete-orphan")
    )

    __table_args__ = (
        UniqueConstraint("documento_id", "codigo_item", name="_documento_item_uc"),
        {"comment": "Tabela de vendas do SPED Fiscal"},
    )


# Define the User model
class User(Base, UserMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    _password = Column("password", String, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    @property
    def password(self):
        raise AttributeError("password is not a readable attribute")

    @password.setter
    def password(self, password):
        self._password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self._password, password)


# Model for tracking login attempts (database-based lockout)
class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, index=True)
    ip_address = Column(String(45), nullable=False)  # Suporta IPv6
    attempt_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    success = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_login_attempts_username_time", "username", "attempt_time"),
        {"comment": "Tabela de tentativas de login para controle de bloqueio"},
    )

    @classmethod
    def get_failed_attempts_count(
        cls, session, username: str, window_minutes: int = 15
    ) -> int:
        """Conta tentativas falhas recentes para um usuário."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)
        return (
            session.query(cls)
            .filter(
                cls.username == username,
                cls.success == False,
                cls.attempt_time >= cutoff_time,
            )
            .count()
        )

    @classmethod
    def is_locked_out(
        cls, session, username: str, max_attempts: int = 5, window_minutes: int = 15
    ) -> tuple:
        """Verifica se o usuário está bloqueado e retorna tempo restante."""
        failed_count = cls.get_failed_attempts_count(session, username, window_minutes)
        if failed_count >= max_attempts:
            # Busca a última tentativa falha para calcular tempo restante
            last_attempt = (
                session.query(cls)
                .filter(cls.username == username, cls.success == False)
                .order_by(cls.attempt_time.desc())
                .first()
            )

            if last_attempt:
                lockout_end = last_attempt.attempt_time + timedelta(
                    minutes=window_minutes
                )
                now = datetime.utcnow()
                if now < lockout_end:
                    remaining = (lockout_end - now).total_seconds() / 60
                    return True, int(remaining) + 1
        return False, 0

    @classmethod
    def clear_attempts(cls, session, username: str):
        """Limpa tentativas de login para um usuário (após login bem-sucedido)."""
        session.query(cls).filter(cls.username == username).delete()
        session.commit()


# Function to create database tables
def create_db_tables():
    Base.metadata.create_all(bind=engine)


# Dependency to get the database session
@contextlib.contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
