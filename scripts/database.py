from sqlalchemy import create_engine, Column, String, Integer, ForeignKey, UniqueConstraint, Date, Float, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, backref
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import contextlib
import logging

from flask_login import UserMixin
# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler()
logger.addHandler(stream_handler)

# Define the database file path
import os

# Define the database file path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'database', 'main.db')}"

# Create a SQLAlchemy engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create a SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a declarative base
Base = declarative_base()

class DocumentoFiscalSped(Base):
    __tablename__ = 'documento_fiscal_sped'
    id = Column(Integer, primary_key=True)
    num_documento = Column(String(60), nullable=False)
    serie = Column(String(3), nullable=False)
    data = Column(Date, nullable=False)
    valor_total = Column(Float, nullable=False)
    ind_oper = Column(String(1), nullable=False) # 0=Entrada; 1=Saída
    ind_pagamento = Column(String(1), nullable=False) # 0=À vista; 1=A prazo; 2=Outros
    data_importacao = Column(Date, default=datetime.now().date)

    __table_args__ = (
        UniqueConstraint('num_documento', 'serie', name='_num_serie_uc'),
    )

# Define the Cfop model
class Cfop(Base):
    __tablename__ = "cfops"

    cfop = Column(String(4), primary_key=True, comment="Código CFOP de 4 dígitos")
    data_criacao = Column(Date, nullable=False, default=date.today, comment="Data de criação do registro")

    acumuladores = relationship(
        "Acumulador",
        back_populates="cfop_rel",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint('cfop', name='uq_cfop'),
        {"comment": "Tabela de CFOPs (Código Fiscal de Operações e Prestações)"}
    )

# Define the Acumulador model
class Acumulador(Base):
    __tablename__ = "acumuladores"

    codigo = Column(String(10), primary_key=True, comment="Código do acumulador")
    descricao = Column(String(100), nullable=False, comment="Descrição do acumulador")
    cfop = Column(String(4), ForeignKey("cfops.cfop", ondelete="RESTRICT"), nullable=False)
    data_criacao = Column(Date, nullable=False, default=date.today)
    data_alteracao = Column(Date, nullable=True, onupdate=date.today)

    cfop_rel = relationship(
        "Cfop",
        back_populates="acumuladores",
        lazy="joined"
    )
    produtos = relationship(
        "ProdutoSped",
        back_populates="acumulador_rel",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint('codigo', name='uq_acumulador_codigo'),
        {"comment": "Tabela de acumuladores para agrupamento de produtos por CFOP"}
    )

# Define the ProdutoSped model
class ProdutoSped(Base):
    __tablename__ = "produtos_sped"

    codigo_item = Column(String(60), primary_key=True, comment="Código do item no sistema do contribuinte")
    descricao_item = Column(String(200), nullable=False, comment="Descrição do item")
    unidade = Column(String(6), nullable=False, comment="Unidade de medida do item")
    ncm = Column(String(8), nullable=False, comment="Código NCM do item")
    acumulador = Column(
        String(10),
        ForeignKey("acumuladores.codigo", ondelete="RESTRICT"),
        nullable=True,
        comment="Código do acumulador associado"
    )
    data_cadastro = Column(Date, nullable=False, default=date.today)
    data_alteracao = Column(Date, nullable=True, onupdate=date.today)
    aliquota_icms = Column(Float, nullable=True, comment="Alíquota de ICMS padrão do produto")
    cest = Column(String(7), nullable=True, comment="Código CEST do produto")
    cod_barras = Column(String(14), nullable=True, comment="Código de barras do produto")

    acumulador_rel = relationship(
        "Acumulador",
        back_populates="produtos",
        lazy="joined"
    )
    vendas = relationship(
        "VendaSped", backref="produto_rel", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint('codigo_item', name='uq_produto_codigo'),
        {"comment": "Tabela de produtos do SPED Fiscal"}
    )

# Define the VendaSped model
class VendaSped(Base):
    __tablename__ = "vendas_sped"

    id = Column(Integer, primary_key=True, autoincrement=True)
    documento_id = Column(Integer, ForeignKey('documento_fiscal_sped.id'), nullable=False)
    data = Column(Date, nullable=False, index=True) # Redundante, mas útil para queries
    codigo_item = Column(
        String(60),
        ForeignKey("produtos_sped.codigo_item", ondelete="RESTRICT"),
        nullable=False,
        comment="Código do item vendido"
    )

    quantidade = Column(Float, nullable=False, comment="Quantidade vendida")
    valor_unitario = Column(Float, nullable=False, comment="Valor unitário do item")
    valor_total = Column(Float, nullable=False, comment="Valor total da venda")
    valor_desconto = Column(Float, nullable=True, default=0, comment="Valor do desconto")
    base_icms = Column(Float, nullable=True, comment="Base de cálculo do ICMS")
    valor_icms = Column(Float, nullable=True, comment="Valor do ICMS")
    aliquota_icms = Column(Float, nullable=True, comment="Alíquota do ICMS aplicada")
    data_importacao = Column(Date, nullable=False, default=date.today)

    documento_rel = relationship("DocumentoFiscalSped", backref=backref("itens", cascade="all, delete-orphan"))

    __table_args__ = (
        UniqueConstraint('documento_id', 'codigo_item', name='_documento_item_uc'),
        {"comment": "Tabela de vendas do SPED Fiscal"}
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