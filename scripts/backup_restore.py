import os
import shutil
import sqlite3
import tempfile
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_login import login_required

from .auth_decorators import admin_required

backup_restore_bp = Blueprint("backup_restore", __name__)

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backups")
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

# Tamanho máximo para arquivo de backup (100MB)
MAX_BACKUP_SIZE = 100 * 1024 * 1024


def _validate_sqlite_file(file_path: str) -> bool:
    """Valida se o arquivo é um banco SQLite válido e contém as tabelas esperadas."""
    try:
        # Verifica header SQLite (primeiros 16 bytes)
        with open(file_path, "rb") as f:
            header = f.read(16)
            if not header.startswith(b"SQLite format 3"):
                return False

        # Tenta abrir e verificar tabelas essenciais
        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()

        # Verifica se as tabelas principais existem
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        required_tables = {"users", "produtos_sped", "vendas_sped"}
        if not required_tables.issubset(tables):
            conn.close()
            return False

        # Verifica integridade básica
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        conn.close()

        return result[0] == "ok"
    except Exception:
        return False


def create_backup():
    """Cria um backup do banco de dados e limpa os antigos."""
    try:
        db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "database", "main.db"
        )
        if not os.path.exists(db_path):
            raise FileNotFoundError("Banco de dados não encontrado.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"main_db_backup_{timestamp}.db"
        backup_path = os.path.join(BACKUP_DIR, backup_filename)

        shutil.copy(db_path, backup_path)

        # Limpa backups antigos
        _cleanup_old_backups()

        current_app.logger.info(f"AUDIT: Backup criado: {backup_filename}")
        return backup_path
    except Exception:
        current_app.logger.exception("Erro ao criar backup do banco de dados:")
        raise


def _cleanup_old_backups():
    """Remove os arquivos de backup mais antigos se excederem o limite configurado."""
    try:
        backup_files = sorted(
            [
                os.path.join(BACKUP_DIR, f)
                for f in os.listdir(BACKUP_DIR)
                if f.endswith(".db")
            ],
            key=os.path.getmtime,
        )

        max_backups = current_app.config.get("MAX_BACKUP_FILES", 10)

        if len(backup_files) > max_backups:
            files_to_delete = backup_files[: len(backup_files) - max_backups]
            for f in files_to_delete:
                os.remove(f)
                current_app.logger.info(
                    f"Backup antigo removido: {os.path.basename(f)}"
                )
    except Exception:
        current_app.logger.exception("Erro ao limpar backups antigos:")


@backup_restore_bp.route("/settings/backup_database", methods=["GET"])
@admin_required
def backup_database():
    """Cria o backup e envia o arquivo como download para o navegador."""
    try:
        backup_path = create_backup()
        return send_file(backup_path, as_attachment=True)
    except Exception:
        current_app.logger.exception("Erro ao criar/servir backup:")
        return jsonify(
            {"success": False, "message": "Erro interno ao criar backup."}
        ), 500


@backup_restore_bp.route("/settings/restore_database", methods=["POST"])
@admin_required
def restore_database():
    """Restaura o banco de dados a partir de um arquivo de backup validado."""
    try:
        if "backup_file" not in request.files:
            return jsonify(
                {"success": False, "message": "Nenhum arquivo selecionado."}
            ), 400

        backup_file = request.files["backup_file"]
        if backup_file.filename == "":
            return jsonify(
                {"success": False, "message": "Nenhum arquivo selecionado."}
            ), 400

        # Validação de extensão
        if not backup_file.filename.endswith(".db"):
            return jsonify(
                {
                    "success": False,
                    "message": "Formato inválido. Apenas arquivos .db são aceitos.",
                }
            ), 400

        # Salva temporariamente para validação
        temp_fd, temp_path = tempfile.mkstemp(suffix=".db")
        try:
            backup_file.save(temp_path)

            # Verifica tamanho
            if os.path.getsize(temp_path) > MAX_BACKUP_SIZE:
                return jsonify(
                    {
                        "success": False,
                        "message": "Arquivo muito grande. Máximo: 100MB.",
                    }
                ), 400

            # Valida integridade SQLite
            if not _validate_sqlite_file(temp_path):
                current_app.logger.warning(
                    f"SEGURANÇA: Tentativa de restauração com arquivo inválido: {backup_file.filename}"
                )
                return jsonify(
                    {
                        "success": False,
                        "message": "Arquivo de backup inválido ou corrompido.",
                    }
                ), 400

            db_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "..", "database", "main.db"
            )

            # Cria backup de segurança antes de sobrescrever
            if os.path.exists(db_path):
                safety_backup = os.path.join(
                    BACKUP_DIR,
                    f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
                )
                shutil.copy(db_path, safety_backup)
                current_app.logger.info(
                    f"AUDIT: Backup de segurança criado antes da restauração: {safety_backup}"
                )

            # Substitui o banco de dados
            shutil.copy(temp_path, db_path)

            current_app.logger.info(
                f"AUDIT: Banco de dados restaurado a partir de: {backup_file.filename}"
            )
            return jsonify(
                {"success": True, "message": "Banco de dados restaurado com sucesso!"}
            ), 200

        finally:
            os.close(temp_fd)
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Exception:
        current_app.logger.exception("Erro ao restaurar banco de dados:")
        return jsonify(
            {"success": False, "message": "Erro interno ao restaurar banco de dados."}
        ), 500
