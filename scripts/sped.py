from flask import Blueprint, current_app, jsonify, render_template, request, session
from flask_login import login_required

from .database import Empresa, get_db
from .empresa_service import get_empresa_id_from_session
from .product_analyzer import ProductAnalyzer
from .security_middleware import secure_api_endpoint
from .sped_service import SpedService

sped_bp = Blueprint("sped", __name__)


@sped_bp.route("/", methods=["GET"])
@login_required
def sped_index():
    """Renderiza a página principal do SPED, pré-carregando dados necessários."""
    try:
        empresa_id = get_empresa_id_from_session()
        acumuladores = SpedService.get_acumuladores(empresa_id=empresa_id)
        cfops = SpedService.get_cfops(empresa_id=empresa_id)

        # Buscar todas as empresas
        with get_db() as db:
            empresas = db.query(Empresa).order_by(Empresa.razao_social).all()
            empresas_list = [{"id": e.id, "cnpj": e.cnpj, "razao_social": e.razao_social} for e in empresas]

        empresa_selecionada = None
        if empresa_id:
            with get_db() as db:
                empresa = db.get(Empresa, empresa_id)
                if empresa:
                    empresa_selecionada = {
                        "id": empresa.id,
                        "cnpj": empresa.cnpj,
                        "razao_social": empresa.razao_social,
                    }

        return render_template(
            "sped.html",
            acumuladores=acumuladores,
            cfops=cfops,
            empresas=empresas_list,
            empresa_selecionada=empresa_selecionada,
            active_page="sped",
        )
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar a página SPED: {e}")
        return (
            render_template(
                "error.html",
                error_message="Não foi possível carregar os dados da página SPED.",
            ),
            500,
        )


@sped_bp.route("/importar", methods=["POST"])
@login_required
@secure_api_endpoint(max_requests=10, window_minutes=5)  # Limite mais restritivo para upload
def importar_sped():
    current_app.logger.debug("Iniciando importação do arquivo SPED")

    if "arquivo_sped" not in request.files:
        current_app.logger.warning("Tentativa de importação sem arquivo")
        return jsonify({"success": False, "error": "Nenhum arquivo enviado"}), 400

    file = request.files["arquivo_sped"]
    current_app.logger.debug(f"Arquivo recebido: {file.filename}")

    if file.filename == "":
        current_app.logger.warning("Nome do arquivo está vazio")
        return jsonify({"success": False, "error": "Nenhum arquivo selecionado"}), 400

    # Validação de extensão do arquivo
    allowed_extensions = {".txt", ".sped", ".efd"}
    file_ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if file_ext not in allowed_extensions:
        current_app.logger.warning(f"SEGURANÇA: Tentativa de upload com extensão não permitida: {file.filename}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Tipo de arquivo não permitido. Use .txt, .sped ou .efd",
                }
            ),
            400,
        )

    # Validação de tamanho (50MB máximo para arquivos SPED)
    max_sped_size = 50 * 1024 * 1024
    file.seek(0, 2)  # Move para o final
    file_size = file.tell()
    file.seek(0)  # Volta para o início
    if file_size > max_sped_size:
        return jsonify({"success": False, "error": "Arquivo muito grande. Máximo: 50MB"}), 400

    try:
        current_app.logger.debug("Iniciando processamento do arquivo")
        # Obtém o ID da empresa selecionada na sessão
        empresa_selecionada_id = get_empresa_id_from_session()
        success, message, empresa_id = SpedService.import_sped_file(file, empresa_selecionada_id)
        if success:
            if empresa_id:
                # Atualizar a sessão com a empresa importada
                session["empresa_id"] = empresa_id
                current_app.logger.info(f"Sessão atualizada para empresa ID: {empresa_id}")

            current_app.logger.info(f"Arquivo SPED importado com sucesso: {message}")
            return jsonify({"success": True, "message": message, "empresa_id": empresa_id})
        else:
            current_app.logger.error(f"Falha ao importar arquivo SPED: {message}")
            return jsonify({"success": False, "error": message}), 400
    except Exception as e:
        current_app.logger.exception("Erro durante importação do arquivo SPED")
        return jsonify({"success": False, "error": "Erro interno durante a importação."}), 500


# Rotas para Acumuladores
@sped_bp.route("/acumuladores", methods=["GET"])
@login_required
def get_acumuladores():
    try:
        empresa_id = get_empresa_id_from_session()
        if not empresa_id:
            return jsonify([])  # Retorna lista vazia se não houver empresa
        search_term = request.args.get("search")
        acumuladores = SpedService.get_acumuladores(search_term=search_term, empresa_id=empresa_id)
        return jsonify(acumuladores)
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar acumuladores: {e}")
        return jsonify({"success": False, "error": "Erro ao buscar acumuladores"}), 500


@sped_bp.route("/acumuladores", methods=["POST"])
@login_required
@secure_api_endpoint(max_requests=30, window_minutes=1)
def add_acumulador():
    try:
        empresa_id = get_empresa_id_from_session()
        if not empresa_id:
            return jsonify({"success": False, "error": "Selecione uma empresa antes de cadastrar acumuladores"}), 400

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Dados inválidos"}), 400

        success, message_or_error = SpedService.add_acumulador(
            data.get("codigo"), data.get("descricao"), data.get("cfop"), empresa_id=empresa_id
        )
        if success:
            return jsonify({"success": True, "message": message_or_error}), 201
        return jsonify({"success": False, "error": message_or_error}), 400
    except Exception as e:
        current_app.logger.error(f"Erro ao adicionar acumulador: {e}")
        return jsonify({"success": False, "error": "Erro ao processar a requisição"}), 500


@sped_bp.route("/acumuladores/<codigo>", methods=["GET"])
@login_required
def get_acumulador(codigo):
    # Esta rota é usada para popular o formulário de edição
    acumulador = SpedService.get_acumulador_by_codigo(codigo)
    if acumulador:
        return jsonify(acumulador)
    return jsonify({"success": False, "error": "Acumulador não encontrado"}), 404


@sped_bp.route("/acumuladores/<codigo>", methods=["PUT"])
@login_required
def update_acumulador(codigo):
    data = request.get_json()
    success, message_or_error = SpedService.update_acumulador(codigo, data.get("descricao"), data.get("cfop"))
    if success:
        return jsonify({"success": True, "message": message_or_error})
    return jsonify({"success": False, "error": message_or_error}), 400


@sped_bp.route("/acumuladores/<codigo>", methods=["DELETE"])
@login_required
def delete_acumulador(codigo):
    success, message_or_error = SpedService.delete_acumulador(codigo)
    if success:
        return jsonify({"success": True, "message": message_or_error})
    return jsonify({"success": False, "error": message_or_error}), 400


# Rotas para CFOPs
@sped_bp.route("/cfops", methods=["GET"])
@login_required
def get_cfops():
    try:
        empresa_id = get_empresa_id_from_session()
        if not empresa_id:
            return jsonify([])  # Retorna lista vazia se não houver empresa
        search_term = request.args.get("search")
        cfops = SpedService.get_cfops(search_term=search_term, empresa_id=empresa_id)
        return jsonify(cfops)
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar CFOPs: {e}")
        return jsonify({"success": False, "error": "Erro ao buscar CFOPs"}), 500


@sped_bp.route("/cfops", methods=["POST"])
@login_required
@secure_api_endpoint(max_requests=30, window_minutes=1)
def add_cfop():
    try:
        empresa_id = get_empresa_id_from_session()
        if not empresa_id:
            return jsonify({"success": False, "error": "Selecione uma empresa antes de cadastrar CFOPs"}), 400

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Dados inválidos"}), 400

        success, message_or_error = SpedService.add_cfop(data.get("cfop"), empresa_id=empresa_id)
        if success:
            return jsonify({"success": True, "message": message_or_error}), 201
        return jsonify({"success": False, "error": message_or_error}), 400
    except Exception as e:
        current_app.logger.error(f"Erro ao adicionar CFOP: {e}")
        return jsonify({"success": False, "error": "Erro ao processar a requisição"}), 500


@sped_bp.route("/cfops/<cfop>", methods=["GET"])
@login_required
def get_cfop(cfop):
    # Rota para buscar um único CFOP para edição
    cfop_data = SpedService.get_cfop_by_codigo(cfop)
    if cfop_data:
        return jsonify(cfop_data)
    return jsonify({"success": False, "error": "CFOP não encontrado"}), 404


@sped_bp.route("/cfops/<cfop>", methods=["PUT"])
@login_required
def update_cfop(cfop):
    data = request.get_json()
    new_cfop = data.get("cfop")
    if not new_cfop:
        return jsonify({"success": False, "error": "CFOP é obrigatório"}), 400

    success, message_or_error = SpedService.update_cfop(cfop, new_cfop)
    if success:
        return jsonify({"success": True, "message": message_or_error})
    return jsonify({"success": False, "error": message_or_error}), 400


@sped_bp.route("/cfops/<cfop>", methods=["DELETE"])
@login_required
def delete_cfop(cfop):
    success, message_or_error = SpedService.delete_cfop(cfop)
    if success:
        return jsonify({"success": True, "message": message_or_error})
    return jsonify({"success": False, "error": message_or_error}), 400


# Rotas para Produtos
@sped_bp.route("/produtos", methods=["GET"])
@login_required
def get_produtos():
    empresa_id = get_empresa_id_from_session()
    if not empresa_id:
        return jsonify(
            {
                "items": [],
                "total": 0,
                "page": 1,
                "per_page": 50,
                "total_pages": 0,
            }
        )

    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    filter_opt = request.args.get("filter")
    search_term = request.args.get("search")

    items, total = SpedService.get_produtos(
        filter_opt=filter_opt, search_term=search_term, page=page, per_page=per_page, empresa_id=empresa_id
    )

    return jsonify(
        {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if per_page > 0 else 0,
        }
    )


@sped_bp.route("/produtos/<codigo>", methods=["DELETE"])
@login_required
def delete_produto(codigo):
    success, message = SpedService.delete_produto(codigo)
    return jsonify({"success": success, "message": message})


@sped_bp.route("/produtos/atualizar_acumulador", methods=["POST"])
@login_required
def update_produto_acumulador():
    data = request.get_json()
    codigo_produto = data.get("codigo")
    codigo_acumulador = data.get("acumulador")
    success, message = SpedService.update_produto_acumulador(codigo_produto, codigo_acumulador)
    return jsonify({"success": success, "message": message})


@sped_bp.route("/produtos/bulk_update_acumulador", methods=["POST"])
@login_required
def bulk_update_produto_acumulador():
    data = request.get_json()
    product_codes = data.get("product_codes")
    acumulador_code = data.get("acumulador_code")

    success, message = SpedService.bulk_update_produto_acumulador(product_codes, acumulador_code)
    if success:
        return jsonify({"success": True, "message": message})
    return jsonify({"success": False, "error": message}), 400


@sped_bp.route("/vendas", methods=["GET"])
@login_required
def get_vendas():
    """Busca o relatório de resumo de vendas."""
    try:
        empresa_id = get_empresa_id_from_session()
        if not empresa_id:
            return jsonify(
                {
                    "total_vendas": 0.0,
                    "total_avista": 0.0,
                    "total_prazo": 0.0,
                    "percentual_avista": 0.0,
                    "percentual_prazo": 0.0,
                }
            )

        competencia = request.args.get("competencia")
        relatorio = SpedService.get_vendas(competencia=competencia, empresa_id=empresa_id)
        return jsonify(relatorio)
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar vendas: {e}")
        return jsonify({"success": False, "error": "Erro ao buscar vendas"}), 500


@sped_bp.route("/competencias", methods=["GET"])
@login_required
def get_competencias():
    try:
        empresa_id = get_empresa_id_from_session()
        competencias = SpedService.get_competencias(empresa_id=empresa_id)
        return jsonify(competencias)
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar competências: {e}")
        return jsonify({"success": False, "error": "Erro ao buscar competências"}), 500


@sped_bp.route("/relatorio_vendas", methods=["GET"])
@login_required
def get_relatorio_vendas():
    competencia = request.args.get("competencia")
    try:
        empresa_id = get_empresa_id_from_session()
        if not empresa_id:
            return jsonify({"total_geral": 0.0, "acumuladores": []})

        relatorio = SpedService.get_relatorio_vendas(competencia, empresa_id=empresa_id)
        return jsonify(relatorio)
    except ValueError as ve:  # Captura o erro específico de validação
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar relatório de vendas: {e}")
        return jsonify({"success": False, "error": "Erro ao gerar relatório"}), 500


@sped_bp.route("/relatorio_cfop", methods=["GET"])
@login_required
def get_relatorio_cfop():
    competencia = request.args.get("competencia")
    timestamp = request.args.get("_t")  # Para invalidar cache

    current_app.logger.info(f"Requisição relatório CFOP - Competência: {competencia}, Timestamp: {timestamp}")

    try:
        empresa_id = get_empresa_id_from_session()
        if not empresa_id:
            # Retorno vazio se não houver empresa
            response = jsonify([])
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response

        # Passa empresa_id para o serviço (que deve retornar lista)
        relatorio = SpedService.get_relatorio_cfop(competencia, empresa_id=empresa_id) or []
        current_app.logger.info(f"Relatório CFOP gerado com {len(relatorio)} itens")

        # Adiciona headers para evitar cache
        response = jsonify(relatorio)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

        return response
    except ValueError as ve:  # Captura o erro específico de validação
        current_app.logger.warning(f"Erro de validação no relatório CFOP: {str(ve)}")
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar relatório de CFOP: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Erro ao gerar relatório"}), 500


@sped_bp.route("/classificar_produtos", methods=["POST"])
@login_required
def classificar_produtos_auto():
    """Sugere classificações automáticas para produtos sem acumulador (não aplica automaticamente)."""
    try:
        analyzer = ProductAnalyzer()

        # Apenas analisa - NÃO cria acumuladores nem aplica
        resultados = analyzer.analisar_produtos_sem_acumulador()

        # Filtra apenas produtos com sugestão válida
        sugestoes = [r for r in resultados if r["acumulador_sugerido"]]
        sem_sugestao = [r for r in resultados if not r["acumulador_sugerido"]]

        current_app.logger.info(
            f"Análise automática: {len(sugestoes)} sugestões, {len(sem_sugestao)} sem classificação"
        )

        return jsonify(
            {
                "success": True,
                "message": f"{len(sugestoes)} produto(s) com sugestão de acumulador.",
                "sugestoes": sugestoes[:100],  # Limita a 100 para performance
                "total_sugestoes": len(sugestoes),
                "total_sem_sugestao": len(sem_sugestao),
            }
        )
    except Exception as e:
        current_app.logger.error(f"Erro na análise automática: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@sped_bp.route("/aprovar_sugestao", methods=["POST"])
@login_required
def aprovar_sugestao():
    """Aprova uma sugestão de acumulador para um produto."""
    try:
        data = request.json
        codigo_item = data.get("codigo_item")
        acumulador = data.get("acumulador")

        if not codigo_item or not acumulador:
            return jsonify({"success": False, "error": "Dados incompletos"}), 400

        from .sped_service import SpedService

        success, message = SpedService.update_produto_acumulador(codigo_item, acumulador)

        if success:
            return jsonify({"success": True, "message": message})
        return jsonify({"success": False, "error": message}), 404

    except Exception as e:
        current_app.logger.error(f"Erro ao aprovar sugestão: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@sped_bp.route("/analisar_produtos", methods=["GET"])
@login_required
def analisar_produtos():
    """Retorna análise prévia dos produtos sem acumulador."""
    try:
        analyzer = ProductAnalyzer()
        resultados = analyzer.analisar_produtos_sem_acumulador()

        return jsonify(
            {
                "success": True,
                "total": len(resultados),
                "produtos": resultados[:50],  # Limita a 50 para a prévia
            }
        )
    except Exception as e:
        current_app.logger.error(f"Erro ao analisar produtos: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@sped_bp.route("/analisar_inconsistencias", methods=["GET"])
@login_required
def analisar_inconsistencias():
    """Analisa produtos com descrições similares mas acumuladores diferentes."""
    try:
        analyzer = ProductAnalyzer()
        inconsistencias = analyzer.analisar_inconsistencias()

        return jsonify(
            {
                "success": True,
                "total": len(inconsistencias),
                "inconsistencias": inconsistencias,
            }
        )
    except Exception as e:
        current_app.logger.error(f"Erro ao analisar inconsistências: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
