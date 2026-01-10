"""Rotas e serviços para gerenciamento de empresas."""

import logging

from flask import Blueprint, jsonify, request, session
from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from scripts.database import Empresa, get_db

logger = logging.getLogger(__name__)

empresa_bp = Blueprint("empresa", __name__)


@empresa_bp.route("/empresas", methods=["GET"])
@login_required
def get_empresas():
    """Retorna todas as empresas cadastradas."""
    try:
        with get_db() as db:
            empresas = db.query(Empresa).order_by(Empresa.razao_social).all()
            return jsonify(
                [
                    {
                        "id": e.id,
                        "cnpj": e.cnpj,
                        "razao_social": e.razao_social,
                        "nome_fantasia": e.nome_fantasia,
                        "inscricao_estadual": e.inscricao_estadual,
                        "uf": e.uf,
                    }
                    for e in empresas
                ]
            )
    except Exception as e:
        logger.error(f"Erro ao buscar empresas: {e}")
        return jsonify({"success": False, "error": "Erro ao buscar empresas"}), 500


@empresa_bp.route("/empresas/<int:empresa_id>", methods=["GET"])
@login_required
def get_empresa(empresa_id):
    """Retorna uma empresa específica."""
    try:
        with get_db() as db:
            empresa = db.get(Empresa, empresa_id)
            if not empresa:
                return jsonify({"success": False, "error": "Empresa não encontrada"}), 404
            return jsonify(
                {
                    "id": empresa.id,
                    "cnpj": empresa.cnpj,
                    "razao_social": empresa.razao_social,
                    "nome_fantasia": empresa.nome_fantasia,
                    "inscricao_estadual": empresa.inscricao_estadual,
                    "uf": empresa.uf,
                }
            )
    except Exception as e:
        logger.error(f"Erro ao buscar empresa {empresa_id}: {e}")
        return jsonify({"success": False, "error": "Erro ao buscar empresa"}), 500


@empresa_bp.route("/empresas/selecionar/<int:empresa_id>", methods=["POST"])
@login_required
def selecionar_empresa(empresa_id):
    """Seleciona uma empresa para trabalhar ou desseleciona se ID for 0."""
    try:
        # Se empresa_id for 0, desseleciona (mostra todas)
        if empresa_id == 0:
            session.pop("empresa_id", None)
            session.pop("empresa_razao_social", None)
            session.pop("empresa_cnpj", None)

            logger.info("Empresa desselecionada - mostrando todas")
            return jsonify(
                {
                    "success": True,
                    "message": "Mostrando todas as empresas",
                    "empresa": None,
                }
            )

        with get_db() as db:
            empresa = db.get(Empresa, empresa_id)
            if not empresa:
                return jsonify({"success": False, "error": "Empresa não encontrada"}), 404

            # Salva na sessão
            session["empresa_id"] = empresa_id
            session["empresa_razao_social"] = empresa.razao_social
            session["empresa_cnpj"] = empresa.cnpj

            logger.info(f"Empresa selecionada: {empresa.razao_social} (ID: {empresa_id})")
            return jsonify(
                {
                    "success": True,
                    "message": f"Empresa '{empresa.razao_social}' selecionada",
                    "empresa": {
                        "id": empresa.id,
                        "cnpj": empresa.cnpj,
                        "razao_social": empresa.razao_social,
                    },
                }
            )
    except Exception as e:
        logger.error(f"Erro ao selecionar empresa {empresa_id}: {e}")
        return jsonify({"success": False, "error": "Erro ao selecionar empresa"}), 500


@empresa_bp.route("/empresas/selecionada", methods=["GET"])
@login_required
def get_empresa_selecionada():
    """Retorna a empresa atualmente selecionada."""
    empresa_id = session.get("empresa_id")
    if not empresa_id:
        return jsonify({"success": True, "empresa": None})

    try:
        with get_db() as db:
            empresa = db.get(Empresa, empresa_id)
            if not empresa:
                # Limpa sessão se empresa não existe mais
                session.pop("empresa_id", None)
                session.pop("empresa_razao_social", None)
                session.pop("empresa_cnpj", None)
                return jsonify({"success": True, "empresa": None})

            return jsonify(
                {
                    "success": True,
                    "empresa": {
                        "id": empresa.id,
                        "cnpj": empresa.cnpj,
                        "razao_social": empresa.razao_social,
                        "nome_fantasia": empresa.nome_fantasia,
                    },
                }
            )
    except Exception as e:
        logger.error(f"Erro ao buscar empresa selecionada: {e}")
        return jsonify({"success": False, "error": "Erro ao buscar empresa selecionada"}), 500


def get_empresa_id_from_session():
    """Retorna o ID da empresa selecionada na sessão atual."""
    return session.get("empresa_id")


def get_or_create_empresa(db, cnpj: str, razao_social: str, inscricao_estadual: str = None, uf: str = None):
    """
    Busca uma empresa pelo CNPJ ou cria uma nova se não existir.

    Esta função é thread-safe e trata race conditions quando múltiplas
    requisições tentam criar a mesma empresa simultaneamente.

    Args:
        db: Sessão do banco de dados
        cnpj: CNPJ da empresa (somente números)
        razao_social: Razão social da empresa
        inscricao_estadual: Inscrição estadual (opcional)
        uf: UF da empresa (opcional)

    Returns:
        Tupla (empresa, is_new) onde empresa é o objeto Empresa e is_new indica se foi criada
    """
    # Remove caracteres não numéricos do CNPJ
    cnpj_limpo = "".join(filter(str.isdigit, cnpj))

    # Busca empresa existente
    empresa = db.query(Empresa).filter_by(cnpj=cnpj_limpo).first()

    if empresa:
        return empresa, False

    # Tenta criar nova empresa com tratamento de race condition
    try:
        nova_empresa = Empresa(
            cnpj=cnpj_limpo,
            razao_social=razao_social,
            inscricao_estadual=inscricao_estadual,
            uf=uf,
        )
        db.add(nova_empresa)
        db.flush()  # Garante que o ID seja gerado

        logger.info(f"Nova empresa cadastrada automaticamente: {razao_social} (CNPJ: {cnpj_limpo})")
        return nova_empresa, True

    except IntegrityError:
        # Race condition: outra requisição criou a empresa entre a consulta e a inserção
        db.rollback()

        # Busca a empresa que foi criada pela outra requisição
        empresa = db.query(Empresa).filter_by(cnpj=cnpj_limpo).first()
        if empresa:
            logger.info(f"Empresa já existente (race condition detectada): {empresa.razao_social} (CNPJ: {cnpj_limpo})")
            return empresa, False

        # Se ainda não encontrou, propaga o erro
        raise
