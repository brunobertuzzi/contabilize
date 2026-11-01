import logging
import os
import secrets
import sys
from datetime import timedelta
from typing import ClassVar

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()


class Config:
    # Configurações básicas
    VERSION = "1.0.0"
    APP_NAME = "Contabilize"
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    TESTING = False

    # Configurações de segurança - Chave secreta
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        # Tenta ler de arquivo existente ou gera nova chave
        secret_key_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), ".secret_key"
        )
        try:
            with open(secret_key_file, "rb") as f:
                SECRET_KEY = f.read()
                if len(SECRET_KEY) < 32:
                    raise ValueError("Chave muito curta")
        except (FileNotFoundError, ValueError):
            SECRET_KEY = secrets.token_bytes(64)  # 512 bits para maior segurança
            with open(secret_key_file, "wb") as f:
                f.write(SECRET_KEY)
            logger.warning(
                "SEGURANÇA: Nova chave secreta gerada. Configure SECRET_KEY como variável de ambiente para produção."
            )

    # Configurações de sessão e cookies
    SESSION_COOKIE_NAME = "contabilize_session"
    SESSION_COOKIE_SECURE = not DEBUG  # True em produção
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    REMEMBER_COOKIE_SECURE = not DEBUG
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"

    # Configurações de segurança adicionais
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hora
    BCRYPT_LOG_ROUNDS = 12  # Custo do hash de senha
    MAX_LOGIN_ATTEMPTS = 5  # Máximo de tentativas de login antes do bloqueio
    LOGIN_LOCKOUT_DURATION = timedelta(
        minutes=15
    )  # Duração do bloqueio após tentativas falhas

    # Configurações do banco de dados (PostgreSQL com fallback automático para SQLite)
    DATABASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database")
    DATABASE_PATH = os.path.join(DATABASE_DIR, "main.db")

    _raw_db_url = os.environ.get("DATABASE_URL")
    if _raw_db_url:
        if _raw_db_url.startswith("postgres://"):
            _raw_db_url = _raw_db_url.replace(
                "postgres://", "postgresql+psycopg2://", 1
            )
        elif _raw_db_url.startswith("postgresql://") and not _raw_db_url.startswith(
            "postgresql+"
        ):
            _raw_db_url = _raw_db_url.replace(
                "postgresql://", "postgresql+psycopg2://", 1
            )
        DATABASE_URL = _raw_db_url
    else:
        DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = DEBUG
    DATABASE_CONNECT_OPTIONS: ClassVar[dict] = {}

    # Configurações de log (padrão 12-factor / stdout para Docker e nuvem)
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Configurações de upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS: ClassVar[set[str]] = {"txt", "pdf", "csv", "xml"}

    @classmethod
    def init_app(cls, app):
        # Cria diretórios necessários de runtime
        for directory in [cls.DATABASE_DIR, cls.UPLOAD_FOLDER]:
            os.makedirs(directory, exist_ok=True)

        # Configuração de logs para stdout (capturados pelo docker compose logs)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(logging.Formatter(cls.LOG_FORMAT))
        stream_handler.setLevel(getattr(logging, cls.LOG_LEVEL.upper()))

        app.logger.handlers = [stream_handler]
        app.logger.setLevel(getattr(logging, cls.LOG_LEVEL.upper()))

        if not cls.DEBUG:
            # Configurações de produção
            app.config["PROPAGATE_EXCEPTIONS"] = False
            app.config["PRESERVE_CONTEXT_ON_EXCEPTION"] = False
            app.config["TRAP_HTTP_EXCEPTIONS"] = False
            app.config["TRAP_BAD_REQUEST_ERRORS"] = False
            app.config["PREFERRED_URL_SCHEME"] = "https"

            # Headers de segurança
            @app.after_request
            def add_security_headers(response):
                response.headers["Strict-Transport-Security"] = (
                    "max-age=31536000; includeSubDomains"
                )
                response.headers["X-Content-Type-Options"] = "nosniff"
                response.headers["X-Frame-Options"] = "SAMEORIGIN"
                response.headers["X-XSS-Protection"] = "1; mode=block"
                return response

        # Configurações de upload
        app.config["MAX_CONTENT_LENGTH"] = cls.MAX_CONTENT_LENGTH
        app.config["UPLOAD_FOLDER"] = cls.UPLOAD_FOLDER

        # Configurações de sessão
        app.config["PERMANENT_SESSION_LIFETIME"] = cls.PERMANENT_SESSION_LIFETIME
