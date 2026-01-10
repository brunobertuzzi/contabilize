import os
import secrets
import logging
from datetime import timedelta, datetime
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()


class Config:
    # Configurações básicas
    VERSION = "1.0.0"
    APP_NAME = "Contabilize"
    DEBUG = os.environ.get("FLASK_DEBUG", "1") == "1"
    TESTING = False

    # Configurações de segurança - Chave secreta
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        # Tenta ler de arquivo existente ou gera nova chave
        secret_key_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".secret_key")
        try:
            with open(secret_key_file, "rb") as f:
                SECRET_KEY = f.read()
                if len(SECRET_KEY) < 32:
                    raise ValueError("Chave muito curta")
        except (FileNotFoundError, ValueError):
            SECRET_KEY = secrets.token_bytes(64)  # 512 bits para maior segurança
            with open(secret_key_file, "wb") as f:
                f.write(SECRET_KEY)
            logging.warning(
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
    LOGIN_LOCKOUT_DURATION = timedelta(minutes=15)  # Duração do bloqueio após tentativas falhas

    # Configurações do banco de dados
    DATABASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database")
    DATABASE_PATH = os.path.join(DATABASE_DIR, "main.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = DEBUG
    DATABASE_CONNECT_OPTIONS = {}

    # Configurações de backup
    BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backups")
    MAX_BACKUP_FILES = 10

    # Configurações de log
    LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5

    # Configurações de upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {"txt", "pdf", "csv", "xml"}

    @classmethod
    def init_app(cls, app):
        # Cria diretórios necessários
        for directory in [cls.DATABASE_DIR, cls.BACKUP_DIR, cls.LOG_DIR, cls.UPLOAD_FOLDER]:
            os.makedirs(directory, exist_ok=True)

        # Configuração de logs
        log_file = os.path.join(cls.LOG_DIR, "app.log")
        file_handler = RotatingFileHandler(log_file, maxBytes=cls.LOG_MAX_SIZE, backupCount=cls.LOG_BACKUP_COUNT)
        file_handler.setFormatter(logging.Formatter(cls.LOG_FORMAT))
        file_handler.setLevel(getattr(logging, cls.LOG_LEVEL.upper()))

        # Adiciona handlers ao logger do app
        app.logger.addHandler(file_handler)
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
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
                response.headers["X-Content-Type-Options"] = "nosniff"
                response.headers["X-Frame-Options"] = "SAMEORIGIN"
                response.headers["X-XSS-Protection"] = "1; mode=block"
                return response

        # Configurações de upload
        app.config["MAX_CONTENT_LENGTH"] = cls.MAX_CONTENT_LENGTH
        app.config["UPLOAD_FOLDER"] = cls.UPLOAD_FOLDER

        # Configurações de sessão
        app.config["PERMANENT_SESSION_LIFETIME"] = cls.PERMANENT_SESSION_LIFETIME
