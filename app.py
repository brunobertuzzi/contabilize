import argparse
import logging
import sys

from flask import (
    Flask,
    current_app,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from scripts.config import Config
from scripts.database import (
    Acumulador,
    DocumentoFiscalSped,
    Empresa,
    LoginAttempt,
    ProdutoSped,
    User,
    VendaSped,
    format_competencia_col,
    get_db,
)
from scripts.initialization import (
    create_admin_user,
    has_admin_user,
    initialize_database,
    validate_password_strength,
)
from scripts.security_middleware import apply_security_headers

logger = logging.getLogger(__name__)


def create_app(testing=False):
    """Cria e configura a aplicação Flask."""
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config.from_object(Config)
    Config.init_app(app)

    if testing:
        app.config["TESTING"] = True
        app.config["DATABASE"] = "sqlite:///:memory:"

    # Garante que o banco de dados e as tabelas sejam criados se não existirem.
    initialize_database(app)

    app.secret_key = Config.SECRET_KEY
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.jinja_env.auto_reload = True

    # Inicializa o Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login"
    login_manager.login_message = "Por favor, faça login para acessar o sistema."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        with get_db() as db:
            return db.get(User, int(user_id))

    # Importação e registro de blueprints
    from scripts.backup_restore import backup_restore_bp
    from scripts.empresa_service import empresa_bp
    from scripts.sped import sped_bp
    from scripts.user_management import user_management_bp

    app.register_blueprint(sped_bp, url_prefix="/sped")
    app.register_blueprint(user_management_bp)
    app.register_blueprint(backup_restore_bp)
    app.register_blueprint(empresa_bp)

    # Aplica cabeçalhos de segurança em todas as respostas
    @app.after_request
    def add_security_headers(response):
        response = apply_security_headers(response)
        # Evitar cache para garantir que logout/login funcione corretamente e testes não peguem versões antigas
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # Handlers de erro
    @app.errorhandler(404)
    def not_found_error(error):
        current_app.logger.error(f"404 Not Found: {request.url}")
        return jsonify(
            {
                "error": "Not Found",
                "message": "A URL solicitada não foi encontrada no servidor.",
            }
        ), 404

    @app.errorhandler(500)
    def internal_error(error):
        current_app.logger.error("500 Internal Server Error: %s", error)
        return jsonify(
            {"error": "Internal Server Error", "message": "Ocorreu um erro inesperado."}
        ), 500

    # Rotas principais
    @app.route("/")
    def index():
        # Verifica se precisa configurar o primeiro administrador
        if not has_admin_user():
            return redirect(url_for("setup_admin"))

        # Verifica se o usuário está logado
        if not current_user.is_authenticated:
            return redirect(url_for("login"))

        stats = {
            "total_empresas": 0,
            "total_produtos": 0,
            "produtos_sem_acumulador": 0,
            "total_acumuladores": 0,
            "total_documentos": 0,
            "empresa_ativa": None,
        }
        try:
            with get_db() as db:
                stats["total_empresas"] = db.query(Empresa).count()
                empresa_id = session.get("empresa_id")
                if empresa_id:
                    empresa = db.get(Empresa, empresa_id)
                    if empresa:
                        stats["empresa_ativa"] = {
                            "id": empresa.id,
                            "razao_social": empresa.razao_social,
                            "cnpj": empresa.cnpj,
                        }
                    stats["total_produtos"] = (
                        db.query(ProdutoSped).filter_by(empresa_id=empresa_id).count()
                    )
                    stats["produtos_sem_acumulador"] = (
                        db.query(ProdutoSped)
                        .filter_by(empresa_id=empresa_id, acumulador_id=None)
                        .count()
                    )
                    stats["total_acumuladores"] = (
                        db.query(Acumulador).filter_by(empresa_id=empresa_id).count()
                    )
                    stats["total_documentos"] = (
                        db.query(DocumentoFiscalSped)
                        .filter_by(empresa_id=empresa_id)
                        .count()
                    )
                else:
                    stats["total_produtos"] = db.query(ProdutoSped).count()
                    stats["produtos_sem_acumulador"] = (
                        db.query(ProdutoSped)
                        .filter(ProdutoSped.acumulador_id.is_(None))
                        .count()
                    )
                    stats["total_acumuladores"] = db.query(Acumulador).count()
                    stats["total_documentos"] = db.query(DocumentoFiscalSped).count()

                tot_p = stats["total_produtos"]
                sem_a = stats["produtos_sem_acumulador"]
                stats["taxa_conciliacao"] = (
                    round(((tot_p - sem_a) / tot_p * 100), 1) if tot_p > 0 else 100.0
                )

                stats["competencias_recentes"] = []
                try:
                    comp_col = format_competencia_col(VendaSped.data)
                    c_query = db.query(
                        comp_col.label("comp"),
                        func.count(VendaSped.id).label("qtd_vendas"),
                        func.sum(VendaSped.valor_total).label("total_faturado"),
                    )
                    if empresa_id:
                        c_query = c_query.join(
                            DocumentoFiscalSped,
                            VendaSped.documento_id == DocumentoFiscalSped.id,
                        ).filter(DocumentoFiscalSped.empresa_id == empresa_id)
                    c_rows = (
                        c_query.group_by(comp_col)
                        .order_by(comp_col.desc())
                        .limit(5)
                        .all()
                    )
                    for r in c_rows:
                        if r.comp:
                            stats["competencias_recentes"].append(
                                {
                                    "competencia": r.comp,
                                    "qtd_vendas": r.qtd_vendas or 0,
                                    "total_faturado": float(r.total_faturado or 0),
                                }
                            )
                except Exception as ex:  # noqa: BLE001
                    current_app.logger.warning("Erro ao buscar competências: %s", ex)
        except Exception as e:  # noqa: BLE001
            current_app.logger.warning(
                "Erro ao calcular estatísticas do dashboard: %s", e
            )

        return render_template("index.html", active_page="index", stats=stats)

    @app.route("/about")
    @login_required
    def about():
        return render_template("about.html", active_page="about")

    def _record_login_attempt(username: str, success: bool):
        """Registra tentativa de login no banco de dados."""
        try:
            with get_db() as db:
                attempt = LoginAttempt(
                    username=username,
                    ip_address=request.remote_addr or "0.0.0.0",
                    success=success,
                )
                db.add(attempt)
                db.commit()
        except SQLAlchemyError as e:
            logger.error("Erro ao registrar tentativa de login: %s", e)

    def _check_lockout(username: str):
        """Verifica se o usuário está bloqueado. Retorna (is_locked, remaining_minutes)."""
        try:
            with get_db() as db:
                return LoginAttempt.is_locked_out(
                    db,
                    username,
                    max_attempts=Config.MAX_LOGIN_ATTEMPTS,
                    window_minutes=int(
                        Config.LOGIN_LOCKOUT_DURATION.total_seconds() / 60
                    ),
                )
        except SQLAlchemyError as e:
            logger.error("Erro ao verificar lockout: %s", e)
            return False, 0

    def _clear_login_attempts(username: str):
        """Limpa tentativas de login após sucesso."""
        try:
            with get_db() as db:
                LoginAttempt.clear_attempts(db, username)
        except SQLAlchemyError as e:
            logger.error("Erro ao limpar tentativas de login: %s", e)

    def _get_remaining_attempts(username: str) -> int:
        """Retorna número de tentativas restantes."""
        try:
            with get_db() as db:
                failed_count = LoginAttempt.get_failed_attempts_count(
                    db,
                    username,
                    window_minutes=int(
                        Config.LOGIN_LOCKOUT_DURATION.total_seconds() / 60
                    ),
                )
                return max(0, Config.MAX_LOGIN_ATTEMPTS - failed_count)
        except SQLAlchemyError:
            return Config.MAX_LOGIN_ATTEMPTS

    @app.route("/setup-admin", methods=["GET", "POST"])
    def setup_admin():
        # Verifica se já existe um administrador
        if has_admin_user():
            flash("Sistema já configurado. Faça login normalmente.", "info")
            return redirect(url_for("login"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")

            # Validações
            if not username or not password or not confirm_password:
                flash("Por favor, preencha todos os campos.", "error")
                return render_template("setup_admin.html")

            if len(username) < 3:
                flash("Nome de usuário deve ter pelo menos 3 caracteres.", "error")
                return render_template("setup_admin.html")

            if len(username) > 50:
                flash("Nome de usuário deve ter no máximo 50 caracteres.", "error")
                return render_template("setup_admin.html")

            if password != confirm_password:
                flash("As senhas não coincidem.", "error")
                return render_template("setup_admin.html")

            try:
                validate_password_strength(password)
            except ValueError as e:
                flash(str(e), "error")
                return render_template("setup_admin.html")

            try:
                create_admin_user(username, password)
                flash(
                    "Usuário administrador criado com sucesso! Faça login para continuar.",
                    "success",
                )
                return redirect(url_for("login"))
            except ValueError as e:
                flash(str(e), "error")
                return render_template("setup_admin.html")
            except Exception as e:  # noqa: BLE001
                logger.error("Erro ao criar usuário administrador: %s", e)
                flash("Erro interno. Tente novamente.", "error")
                return render_template("setup_admin.html")

        return render_template("setup_admin.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        # Verifica se precisa configurar o primeiro administrador
        if not has_admin_user():
            return redirect(url_for("setup_admin"))

        if current_user.is_authenticated:
            return redirect(url_for("index"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            remember_me = request.form.get("remember_me") == "on"

            if not username or not password:
                flash("Por favor, preencha todos os campos.", "warning")
                return render_template("login.html")

            # Verifica lockout baseado em banco de dados
            is_locked, remaining_minutes = _check_lockout(username)
            if is_locked:
                flash(
                    f"Conta temporariamente bloqueada. Tente novamente em {remaining_minutes} minutos.",
                    "danger",
                )
                return render_template("login.html")

            try:
                with get_db() as db:
                    user = db.query(User).filter_by(username=username).first()

                    if user and user.check_password(password):
                        # Login bem-sucedido
                        _clear_login_attempts(username)
                        _record_login_attempt(username, success=True)

                        login_user(user, remember=remember_me)
                        session["logged_in"] = True
                        session["is_admin"] = user.is_admin
                        session.permanent = True

                        logger.info(
                            "AUDIT: Login bem-sucedido para usuário: %s de IP: %s",
                            user.username,
                            request.remote_addr,
                        )

                        next_url = session.pop("next_url", url_for("index"))
                        response = make_response(redirect(next_url))

                        flash("Login bem-sucedido!", "success")
                        return response
                    else:
                        # Login falhou
                        _record_login_attempt(username, success=False)
                        remaining = _get_remaining_attempts(username)

                        if user:
                            logger.warning(
                                "AUDIT: Senha incorreta para o usuário: %s de IP: %s",
                                username,
                                request.remote_addr,
                            )
                        else:
                            logger.warning(
                                "AUDIT: Tentativa de login com usuário inexistente: %s de IP: %s",
                                username,
                                request.remote_addr,
                            )

                        if remaining > 0:
                            flash(
                                f"Nome de usuário ou senha inválidos. Tentativas restantes: {remaining}",
                                "danger",
                            )
                        else:
                            flash(
                                "Conta temporariamente bloqueada devido a múltiplas tentativas falhas.",
                                "danger",
                            )

            except Exception as e:  # noqa: BLE001
                logger.error("Erro durante o login: %s", e)
                flash(
                    "Ocorreu um erro durante o login. Por favor, tente novamente.",
                    "danger",
                )

            return render_template("login.html")

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        try:
            username = current_user.username
            logout_user()

            # Limpar completamente a sessão
            session.clear()

            logger.info("AUDIT: Logout do usuário: %s", username)

            response = make_response(redirect(url_for("login")))

            flash("Você foi desconectado com sucesso.", "info")
            return response

        except Exception as e:  # noqa: BLE001
            logger.error("Erro durante o logout: %s", e)
            flash("Ocorreu um erro durante o logout.", "danger")
            return redirect(url_for("index"))

    return app


def start_application():
    """Inicializa e inicia o servidor web da aplicação."""
    import os

    parser = argparse.ArgumentParser(description="Contabilize Web Application Server")
    parser.add_argument(
        "--host",
        type=str,
        default=os.environ.get("HOST", "0.0.0.0"),
        help="Endereço de bind (padrão: 0.0.0.0 ou env HOST)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "5000")),
        help="Porta de escuta (padrão: 5000 ou env PORT)",
    )
    args = parser.parse_args()

    try:
        app = create_app()
        logger.info("Iniciando Contabilize em http://%s:%s", args.host, args.port)
        app.run(
            host=args.host,
            port=args.port,
            debug=app.config.get("DEBUG", False),
            threaded=True,
        )
    except Exception as e:  # noqa: BLE001
        logger.error("Erro ao iniciar a aplicação: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    start_application()
