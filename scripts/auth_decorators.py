from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user, login_required as flask_login_required

def admin_required(f):
    """Decorador que verifica se o usuário está autenticado e é administrador."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        if not current_user.is_admin:
            flash('Acesso negado: Apenas administradores podem acessar esta página.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function
