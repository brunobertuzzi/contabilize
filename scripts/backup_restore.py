import os
import shutil
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app, send_file, flash
from flask_login import login_required

backup_restore_bp = Blueprint('backup_restore', __name__)

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backups')
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

def create_backup():
    """Cria um backup do banco de dados e limpa os antigos."""
    try:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'database', 'main.db')
        if not os.path.exists(db_path):
            raise FileNotFoundError("Banco de dados não encontrado.")

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'main_db_backup_{timestamp}.db'
        backup_path = os.path.join(BACKUP_DIR, backup_filename)

        shutil.copy(db_path, backup_path)
        
        # Limpa backups antigos
        _cleanup_old_backups()
        
        return backup_path
    except Exception as e:
        current_app.logger.exception("Erro ao criar backup do banco de dados:")
        raise e

def _cleanup_old_backups():
    """Remove os arquivos de backup mais antigos se excederem o limite configurado."""
    try:
        backup_files = sorted(
            [os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR) if f.endswith('.db')],
            key=os.path.getmtime
        )
        
        max_backups = current_app.config.get('MAX_BACKUP_FILES', 10)
        
        if len(backup_files) > max_backups:
            files_to_delete = backup_files[:len(backup_files) - max_backups]
            for f in files_to_delete:
                os.remove(f)
                current_app.logger.info(f"Backup antigo removido: {os.path.basename(f)}")
    except Exception as e:
        current_app.logger.exception("Erro ao limpar backups antigos:")

@backup_restore_bp.route('/settings/backup_database', methods=['GET'])
@login_required
def backup_database():
    """Cria o backup e envia o arquivo como download para o navegador.

    Isso permite que o usuário escolha a pasta/local onde salvar via diálogo do navegador.
    """
    try:
        backup_path = create_backup()
        # Envia o arquivo criado ao cliente como um anexo para download
        return send_file(backup_path, as_attachment=True)
    except Exception as e:
        current_app.logger.exception("Erro ao criar/servir backup:")
        return jsonify({'success': False, 'message': f"Erro interno ao criar backup do banco de dados: {str(e)}"}), 500

@backup_restore_bp.route('/settings/restore_database', methods=['POST'])
@login_required
def restore_database():
    try:
        if 'backup_file' not in request.files:
            return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado para restauração.'}), 400

        backup_file = request.files['backup_file']
        if backup_file.filename == '':
            return jsonify({'success': False, 'message': 'Nenhum arquivo selecionado para restauração.'}), 400

        if backup_file and backup_file.filename.endswith('.db'):
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'database', 'main.db')
            backup_file.save(db_path)
            return jsonify({'success': True, 'message': 'Banco de dados restaurado com sucesso!'}), 200
        else:
            return jsonify({'success': False, 'message': 'Formato de arquivo inválido. Por favor, selecione um arquivo .db.'}), 400
    except Exception as e:
        current_app.logger.exception("Erro ao restaurar banco de dados:")
        return jsonify({'success': False, 'message': f"Erro interno ao restaurar banco de dados: {str(e)}"}), 500
