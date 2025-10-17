
import logging
import sys
from scripts.database import create_db_tables, User, get_db
from scripts.config import Config

def initialize_database(app):
    """Cria as tabelas do banco de dados e o usuário administrador padrão."""
    try:
        with app.app_context():
            create_db_tables()
            _create_default_admin()
    except Exception as e:
        logging.error(f"Erro ao inicializar o banco de dados: {e}")
        sys.exit(1)

def _create_default_admin():
    """Cria o usuário administrador padrão se não existir."""
    with get_db() as db:
        if not db.query(User).filter_by(is_admin=True).first():
            admin_username = Config.DEFAULT_ADMIN_USERNAME
            admin_password = Config.DEFAULT_ADMIN_PASSWORD
            
            if not all([admin_username, admin_password]):
                logging.error("Credenciais de administrador padrão não configuradas!")
                sys.exit(1)
            
            default_admin = User(username=admin_username, password=admin_password, is_admin=True)
            db.add(default_admin)
            db.commit()
            logging.warning(f"Usuário administrador padrão '{admin_username}' criado. ALTERE A SENHA!")
