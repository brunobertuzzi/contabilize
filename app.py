import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, jsonify, request, current_app, session, redirect, url_for, flash, make_response
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from scripts.database import User, get_db
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

    def _handle_failed_login(username):
        """Incrementa o contador de falhas de login para um usuário."""
        now = datetime.now(timezone.utc)
        failed_attempts = session.get('failed_attempts', {})
        user_attempts = failed_attempts.get(username, {'count': 0})
        user_attempts['count'] += 1
        user_attempts['last_attempt'] = now.isoformat()
        failed_attempts[username] = user_attempts
        session['failed_attempts'] = failed_attempts
        
        remaining_attempts = Config.MAX_LOGIN_ATTEMPTS - user_attempts['count']
        if remaining_attempts > 0:
            flash(f'Nome de usuário ou senha inválidos. Tentativas restantes: {remaining_attempts}', 'danger')
        else:
            flash('Conta temporariamente bloqueada devido a múltiplas tentativas falhas.', 'danger')

    def _clear_failed_login_attempts(username):
        """Limpa as tentativas de falha de login para um usuário."""
        failed_attempts = session.get('failed_attempts', {})
        if username in failed_attempts:
            del failed_attempts[username]
            session['failed_attempts'] = failed_attempts
            
    def _check_and_handle_lockout(username):
        """Verifica se o usuário está bloqueado devido a múltiplas tentativas falhas."""
        now = datetime.now(timezone.utc)
        failed_attempts = session.get('failed_attempts', {})
        user_attempts = failed_attempts.get(username, {'count': 0, 'last_attempt': None})

        if user_attempts.get('last_attempt') and user_attempts['count'] >= Config.MAX_LOGIN_ATTEMPTS:
            try:
                last_attempt = datetime.fromisoformat(user_attempts['last_attempt'])
                lockout_end = last_attempt + Config.LOGIN_LOCKOUT_DURATION
                
                if now < lockout_end:
                    remaining_time = (lockout_end - now).total_seconds() / 60
                    flash(f'Conta temporariamente bloqueada. Tente novamente em {int(remaining_time) + 1} minutos.', 'danger')
                    return render_template('login.html', last_username=username)
                else:
                    # Se o tempo de bloqueio passou, reseta as tentativas
                    user_attempts['count'] = 0
                    failed_attempts[username] = user_attempts
                    session['failed_attempts'] = failed_attempts
            except (ValueError, TypeError):
                pass
        return None

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
                return render_template('login.html', last_username=username)

            lockout_response = _check_and_handle_lockout(username)
            if lockout_response:
                # Se o usuário estiver bloqueado, retorna a resposta de erro (ex: 429 Too Many Requests)
                return lockout_response

            try:
                with get_db() as db:
                    user = db.query(User).filter_by(username=username).first()
                    
                    if user and user.check_password(password):
                        _clear_failed_login_attempts(username)
                        login_user(user, remember=remember_me)
                        session['logged_in'] = True
                        session['is_admin'] = user.is_admin
                        session.permanent = True
                        
                        logging.info(f"Login bem-sucedido para usuário: {user.username}")
                        
                        next_url = session.pop('next_url', url_for('index'))
                        response = make_response(redirect(next_url))
                        
                        if remember_me:
                            response.set_cookie(
                                'last_username',
                                user.username,
                                max_age=int(Config.REMEMBER_COOKIE_DURATION.total_seconds()),
                                httponly=True,
                                samesite='Lax',
                                secure=not current_app.debug
                            )
                        
                        flash('Login bem-sucedido!', 'success')
                        return response
                    else:
                        _handle_failed_login(username)
                        if user:
                            count = session.get('failed_attempts', {}).get(username, {}).get('count', 0)
                            logging.warning(f"Senha incorreta para o usuário: {username}. Tentativa {count}")
                        else:
                            logging.warning(f"Usuário não encontrado: {username}")
                            
            except Exception as e:
                logging.error(f"Erro durante o login: {e}")
                flash('Ocorreu um erro durante o login. Por favor, tente novamente.', 'danger')
            
            return render_template('login.html', last_username=username)
        
        return render_template('login.html', last_username=request.cookies.get('last_username'))

    @app.route('/logout')
    @login_required
    def logout():
        try:
            username = current_user.username
            logout_user()
            
            logging.info(f"Logout do usuário: {username}")
            
            response = make_response(redirect(url_for('login')))
            response.delete_cookie('last_username')
            
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