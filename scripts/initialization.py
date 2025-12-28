import logging
import sys

from scripts.database import User, create_db_tables, get_db

# Cache simples para has_admin_user (invalidado após criar admin)
_admin_user_cache = {"exists": None}


def initialize_database(app):
    """Cria as tabelas do banco de dados."""
    try:
        with app.app_context():
            create_db_tables()
    except Exception as e:
        logging.error(f"Erro ao inicializar o banco de dados: {e}")
        sys.exit(1)


def has_admin_user():
    """Verifica se existe pelo menos um usuário administrador no sistema."""
    # Usa cache para evitar queries repetidas
    if _admin_user_cache["exists"] is not None:
        return _admin_user_cache["exists"]

    with get_db() as db:
        exists = db.query(User).filter_by(is_admin=True).first() is not None
        _admin_user_cache["exists"] = exists
        return exists


def _invalidate_admin_cache():
    """Invalida o cache de admin user."""
    _admin_user_cache["exists"] = None


def validate_password_strength(password):
    """Valida a força da senha."""
    if len(password) < 8:
        raise ValueError("Senha deve ter pelo menos 8 caracteres")

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

    strength_count = sum([has_upper, has_lower, has_digit, has_special])

    if strength_count < 2:
        raise ValueError(
            "Senha deve conter pelo menos 2 tipos de caracteres: maiúsculas, minúsculas, números ou símbolos"
        )


def create_admin_user(username, password, force_first_only=True):
    """Cria um novo usuário administrador."""
    # Validações básicas
    if not username or not username.strip():
        raise ValueError("Nome de usuário é obrigatório")

    if not password:
        raise ValueError("Senha é obrigatória")

    username = username.strip()

    if len(username) < 3:
        raise ValueError("Nome de usuário deve ter pelo menos 3 caracteres")

    if len(username) > 50:
        raise ValueError("Nome de usuário deve ter no máximo 50 caracteres")

    # Validação de força da senha
    validate_password_strength(password)

    with get_db() as db:
        # Verifica se já existe um admin (apenas para o primeiro setup)
        if force_first_only and db.query(User).filter_by(is_admin=True).first():
            raise ValueError("Já existe um usuário administrador no sistema")

        # Verifica se o nome de usuário já existe
        if db.query(User).filter_by(username=username).first():
            raise ValueError("Nome de usuário já existe")

        admin_user = User(username=username, password=password, is_admin=True)
        db.add(admin_user)
        db.commit()
        _invalidate_admin_cache()  # Invalida cache após criar admin
        logging.warning(f"SEGURANÇA: Usuário administrador '{username}' criado")


def create_additional_admin(username, password):
    """Cria um usuário administrador adicional (sem restrição de primeiro acesso)."""
    return create_admin_user(username, password, force_first_only=False)


def list_admin_users():
    """Lista todos os usuários administradores."""
    with get_db() as db:
        admins = db.query(User).filter_by(is_admin=True).all()
        return [(admin.id, admin.username) for admin in admins]


def disable_user(username):
    """Desabilita um usuário (marca como inativo)."""
    with get_db() as db:
        user = db.query(User).filter_by(username=username).first()
        if not user:
            raise ValueError(f"Usuário '{username}' não encontrado")

        # Verifica se não é o último admin
        if user.is_admin:
            admin_count = db.query(User).filter_by(is_admin=True).count()
            if admin_count <= 1:
                raise ValueError("Não é possível desabilitar o último administrador")

        # Como não temos campo 'active', vamos deletar o usuário
        # Em produção, seria melhor ter um campo 'is_active'
        db.delete(user)
        db.commit()
        logging.warning(f"SEGURANÇA: Usuário '{username}' removido do sistema")
