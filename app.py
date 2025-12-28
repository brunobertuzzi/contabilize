import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, jsonify, request, current_app, session, redirect, url_for, flash, make_response
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from scripts.database import User, LoginAttempt, get_db
from scripts.config import Config
from scripts.initialization import initialize_database, has_admin_user, create_admin_user, validate_password_strength
from scripts.security_middleware import apply_security_headers
from gui import start_gui

def create_app(testing=False):
    """Cria e configura a aplicação Flask."""
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.config.from_object(Config)
    Config.init_app(app)

    if testing:
        app.config['TESTING'] = True
        app.config['DATABASE'] = 'sqlite:///:memory:'
    
    # Garante que o banco de dados e as tabelas sejam criados se não existirem.
    initialize_database(app)
    
    app.secret_key = Config.SECRET_KEY

    # Inicializa o Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Por favor, faça login para acessar o sistema.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        with get_db() as db:
            return db.get(User, int(user_id))

    # Import e registro de blueprints
    from scripts.sped import sped_bp
    from scripts.user_management import user_management_bp
    from scripts.backup_restore import backup_restore_bp

    app.register_blueprint(sped_bp, url_prefix='/sped')
    app.register_blueprint(user_management_bp)
    app.register_blueprint(backup_restore_bp)

    # Aplica cabeçalhos de segurança em todas as respostas
    @app.after_request
    def add_security_headers(response):
        return apply_security_headers(response)

    # Handlers de erro
    @app.errorhandler(404)
    def not_found_error(error):
        current_app.logger.error(f"404 Not Found: {request.url}")
        return jsonify({"error": "Not Found", "message": "A URL solicitada não foi encontrada no servidor."}), 404

    @app.errorhandler(500)
    def internal_error(error):
        current_app.logger.exception("500 Internal Server Error")
        return jsonify({"error": "Internal Server Error", "message": "Ocorreu um erro inesperado."}), 500

    # Rotas principais
    @app.route('/')
    def index():
        # Verifica se precisa configurar o primeiro administrador
        if not has_admin_user():
            return redirect(url_for('setup_admin'))
        
        # Verifica se o usuário está logado
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
            
        return render_template('index.html', active_page='index')

    @app.route('/about')
    @login_required
    def about():
        return render_template('about.html', active_page='about')

    def _record_login_attempt(username: str, success: bool):
        """Registra tentativa de login no banco de dados."""
        try:
            with get_db() as db:
                attempt = LoginAttempt(
                    username=username,
                    ip_address=request.remote_addr or '0.0.0.0',
                    success=success
                )
                db.add(attempt)
                db.commit()
        except Exception as e:
            logging.error(f"Erro ao registrar tentativa de login: {e}")

    def _check_lockout(username: str):
        """Verifica se o usuário está bloqueado. Retorna (is_locked, remaining_minutes)."""
        try:
            with get_db() as db:
                return LoginAttempt.is_locked_out(
                    db, 
                    username, 
                    max_attempts=Config.MAX_LOGIN_ATTEMPTS,
                    window_minutes=int(Config.LOGIN_LOCKOUT_DURATION.total_seconds() / 60)
                )
        except Exception as e:
            logging.error(f"Erro ao verificar lockout: {e}")
            return False, 0

    def _clear_login_attempts(username: str):
        """Limpa tentativas de login após sucesso."""
        try:
            with get_db() as db:
                LoginAttempt.clear_attempts(db, username)
        except Exception as e:
            logging.error(f"Erro ao limpar tentativas de login: {e}")

    def _get_remaining_attempts(username: str) -> int:
        """Retorna número de tentativas restantes."""
        try:
            with get_db() as db:
                failed_count = LoginAttempt.get_failed_attempts_count(
                    db, 
                    username,
                    window_minutes=int(Config.LOGIN_LOCKOUT_DURATION.total_seconds() / 60)
                )
                return max(0, Config.MAX_LOGIN_ATTEMPTS - failed_count)
        except Exception:
            return Config.MAX_LOGIN_ATTEMPTS

    @app.route('/setup-admin', methods=['GET', 'POST'])
    def setup_admin():
        # Verifica se já existe um administrador
        if has_admin_user():
            flash('Sistema já configurado. Faça login normalmente.', 'info')
            return redirect(url_for('login'))

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')

            # Validações
            if not username or not password or not confirm_password:
                flash('Por favor, preencha todos os campos.', 'error')
                return render_template('setup_admin.html')

            if len(username) < 3:
                flash('Nome de usuário deve ter pelo menos 3 caracteres.', 'error')
                return render_template('setup_admin.html')

            if len(username) > 50:
                flash('Nome de usuário deve ter no máximo 50 caracteres.', 'error')
                return render_template('setup_admin.html')

            if password != confirm_password:
                flash('As senhas não coincidem.', 'error')
                return render_template('setup_admin.html')

            try:
                validate_password_strength(password)
            except ValueError as e:
                flash(str(e), 'error')
                return render_template('setup_admin.html')

            try:
                create_admin_user(username, password)
                flash('Usuário administrador criado com sucesso! Faça login para continuar.', 'success')
                return redirect(url_for('login'))
            except ValueError as e:
                flash(str(e), 'error')
                return render_template('setup_admin.html')
            except Exception as e:
                logging.error(f"Erro ao criar usuário administrador: {e}")
                flash('Erro interno. Tente novamente.', 'error')
                return render_template('setup_admin.html')

        return render_template('setup_admin.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        # Verifica se precisa configurar o primeiro administrador
        if not has_admin_user():
            return redirect(url_for('setup_admin'))

        if current_user.is_authenticated:
            return redirect(url_for('index'))

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            remember_me = request.form.get('remember_me') == 'on'

            if not username or not password:
                flash('Por favor, preencha todos os campos.', 'warning')
                return render_template('login.html')

            # Verifica lockout baseado em banco de dados
            is_locked, remaining_minutes = _check_lockout(username)
            if is_locked:
                flash(f'Conta temporariamente bloqueada. Tente novamente em {remaining_minutes} minutos.', 'danger')
                return render_template('login.html')

            try:
                with get_db() as db:
                    user = db.query(User).filter_by(username=username).first()
                    
                    if user and user.check_password(password):
                        # Login bem-sucedido
                        _clear_login_attempts(username)
                        _record_login_attempt(username, success=True)
                        
                        login_user(user, remember=remember_me)
                        session['logged_in'] = True
                        session['is_admin'] = user.is_admin
                        session.permanent = True
                        
                        logging.info(f"AUDIT: Login bem-sucedido para usuário: {user.username} de IP: {request.remote_addr}")
                        
                        next_url = session.pop('next_url', url_for('index'))
                        response = make_response(redirect(next_url))
                        
                        flash('Login bem-sucedido!', 'success')
                        return response
                    else:
                        # Login falhou
                        _record_login_attempt(username, success=False)
                        remaining = _get_remaining_attempts(username)
                        
                        if user:
                            logging.warning(f"AUDIT: Senha incorreta para o usuário: {username} de IP: {request.remote_addr}")
                        else:
                            logging.warning(f"AUDIT: Tentativa de login com usuário inexistente: {username} de IP: {request.remote_addr}")
                        
                        if remaining > 0:
                            flash(f'Nome de usuário ou senha inválidos. Tentativas restantes: {remaining}', 'danger')
                        else:
                            flash('Conta temporariamente bloqueada devido a múltiplas tentativas falhas.', 'danger')
                            
            except Exception as e:
                logging.error(f"Erro durante o login: {e}")
                flash('Ocorreu um erro durante o login. Por favor, tente novamente.', 'danger')
            
            return render_template('login.html')
        
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        try:
            username = current_user.username
            logout_user()
            
            logging.info(f"AUDIT: Logout do usuário: {username}")
            
            response = make_response(redirect(url_for('login')))
            
            flash('Você foi desconectado com sucesso.', 'info')
            return response
            
        except Exception as e:
            logging.error(f"Erro durante o logout: {e}")
            flash('Ocorreu um erro durante o logout.', 'danger')
            return redirect(url_for('index'))

    return app

def start_application():
    """Inicializa e inicia a aplicação."""
    try:
        app = create_app()
        initialize_database(app)
        
        # A GUI (pywebview) precisa ser iniciada no thread principal
        start_gui(app)

    except Exception as e:
        logging.error(f"Erro ao iniciar a aplicação: {e}")
        sys.exit(1)

if __name__ == '__main__':
    start_application()