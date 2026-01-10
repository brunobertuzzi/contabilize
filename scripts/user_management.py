from flask import Blueprint, render_template, jsonify, request, current_app, session, redirect, url_for
from flask_login import current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from .database import get_db, User
from .auth_decorators import admin_required
from .initialization import validate_password_strength

user_management_bp = Blueprint("user_management", __name__)


@user_management_bp.route("/settings", methods=["GET"])
@login_required
def settings():
    try:
        with get_db() as db:
            users = db.query(User).all()
            return render_template("settings.html", users=users, active_page="settings")
    except Exception as e:
        current_app.logger.exception("Erro ao carregar página de configurações:")
        return jsonify({"success": False, "message": f"Erro interno ao carregar a página de configurações: {str(e)}"}), 500


@user_management_bp.route("/settings/add_user", methods=["POST"])
@admin_required
def add_user():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "Dados JSON inválidos."}), 400

        username = data.get("username")
        password = data.get("password")
        is_admin = data.get("is_admin", False)

        if not username or not password:
            return jsonify({"success": False, "message": "Nome de usuário e senha são obrigatórios."}), 400

        # Validações de entrada
        username = username.strip()
        if len(username) < 3:
            return jsonify({"success": False, "message": "Nome de usuário deve ter pelo menos 3 caracteres."}), 400

        if len(username) > 50:
            return jsonify({"success": False, "message": "Nome de usuário deve ter no máximo 50 caracteres."}), 400

        # Validação de força da senha
        try:
            validate_password_strength(password)
        except ValueError as e:
            return jsonify({"success": False, "message": str(e)}), 400

        with get_db() as db:
            existing_user = db.query(User).filter_by(username=username).first()
            if existing_user:
                return jsonify({"success": False, "message": "Nome de usuário já existe."}), 409

            new_user = User(username=username, is_admin=is_admin)
            new_user.password = password  # O setter do modelo cuidará do hash
            db.add(new_user)
            db.commit()
            db.refresh(new_user)

            return (
                jsonify(
                    {
                        "success": True,
                        "message": f"Usuário {username} adicionado com sucesso!",
                        "user": {"id": new_user.id, "username": new_user.username, "is_admin": new_user.is_admin},
                    }
                ),
                201,
            )
    except Exception as e:
        current_app.logger.exception("Erro ao adicionar usuário:")
        return jsonify({"success": False, "message": f"Erro interno ao adicionar usuário: {str(e)}"}), 500


@user_management_bp.route("/settings/edit_user/<int:user_id>", methods=["POST"])
@login_required
def edit_user(user_id):
    if not current_user.is_admin and current_user.id != user_id:
        return jsonify({"success": False, "message": "Você não tem permissão para editar este usuário."}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "Dados JSON inválidos."}), 400

        username = data.get("username")
        is_admin = data.get("is_admin", False)
        new_password = data.get("new_password")
        confirm_new_password = data.get("confirm_new_password")

        if not username:
            return jsonify({"success": False, "message": "Nome de usuário é obrigatório."}), 400

        with get_db() as db:
            user = db.query(User).filter_by(id=user_id).first()
            if not user:
                return jsonify({"success": False, "message": "Usuário não encontrado."}), 404

            if username != user.username:
                existing_user = db.query(User).filter_by(username=username).first()
                if existing_user and existing_user.id != user_id:
                    return jsonify({"success": False, "message": "Nome de usuário já existe."}), 409

            user.username = username

            if current_user.is_admin:
                user.is_admin = is_admin

            if new_password:
                if new_password != confirm_new_password:
                    return (
                        jsonify(
                            {"success": False, "message": "A nova senha e a confirmação da nova senha não coincidem."}
                        ),
                        400,
                    )

                # Validação de força da nova senha
                try:
                    validate_password_strength(new_password)
                except ValueError as e:
                    return jsonify({"success": False, "message": f"Nova senha: {str(e)}"}), 400

                user.password = new_password

            db.commit()
            db.refresh(user)
            return (
                jsonify(
                    {
                        "success": True,
                        "message": f"Usuário {user.username} atualizado com sucesso!",
                        "user": {"id": user.id, "username": user.username, "is_admin": user.is_admin},
                    }
                ),
                200,
            )
    except Exception as e:
        current_app.logger.exception(f"Erro ao editar usuário {user_id}:")
        return jsonify({"success": False, "message": f"Erro interno ao editar usuário: {str(e)}"}), 500


@user_management_bp.route("/settings/delete_user/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    try:
        with get_db() as db:
            user = db.query(User).filter_by(id=user_id).first()
            if not user:
                return jsonify({"success": False, "message": "Usuário não encontrado."}), 404

            if user.id == current_user.id:
                return jsonify({"success": False, "message": "Você não pode excluir seu próprio usuário."}), 403

            db.delete(user)
            db.commit()
            return jsonify({"success": True, "message": f"Usuário {user.username} excluído com sucesso!"}), 200
    except Exception as e:
        current_app.logger.exception(f"Erro ao excluir usuário {user_id}:")
        return jsonify({"success": False, "message": f"Erro interno ao excluir usuário: {str(e)}"}), 500
