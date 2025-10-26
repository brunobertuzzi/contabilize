from datetime import datetime
from flask import Blueprint, jsonify, request, render_template, current_app
from flask_login import login_required
from .sped_service import SpedService
from .security_middleware import secure_api_endpoint

sped_bp = Blueprint('sped', __name__)

@sped_bp.route('/', methods=['GET'])
@login_required
def sped_index():
    """Renderiza a página principal do SPED, pré-carregando dados necessários."""
    try:
        acumuladores = SpedService.get_acumuladores()
        cfops = SpedService.get_cfops()
        return render_template('sped.html', acumuladores=acumuladores, cfops=cfops, active_page='sped')
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar a página SPED: {e}")
        return render_template('error.html', error_message="Não foi possível carregar os dados da página SPED."), 500

@sped_bp.route('/importar', methods=['POST'])
@login_required
@secure_api_endpoint(max_requests=10, window_minutes=5)  # Limite mais restritivo para upload
def importar_sped():
    current_app.logger.debug("Iniciando importação do arquivo SPED")
    
    if 'arquivo_sped' not in request.files:
        current_app.logger.warning("Tentativa de importação sem arquivo")
        return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['arquivo_sped']
    current_app.logger.debug(f"Arquivo recebido: {file.filename}")
    
    if file.filename == '':
        current_app.logger.warning("Nome do arquivo está vazio")
        return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'}), 400
    
    try:
        current_app.logger.debug("Iniciando processamento do arquivo")
        success, message = SpedService.import_sped_file(file)
        if success:
            current_app.logger.info(f"Arquivo SPED importado com sucesso: {message}")
            return jsonify({'success': True, 'message': message})
        else:
            current_app.logger.error(f"Falha ao importar arquivo SPED: {message}")
            return jsonify({'success': False, 'error': message}), 500
    except Exception as e:
        current_app.logger.exception("Erro durante importação do arquivo SPED")
        return jsonify({'success': False, 'error': str(e)}), 500

# Rotas para Acumuladores
@sped_bp.route('/acumuladores', methods=['GET'])
@login_required
def get_acumuladores():
    try:
        search_term = request.args.get('search')
        acumuladores = SpedService.get_acumuladores(search_term=search_term)
        return jsonify(acumuladores)
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar acumuladores: {e}")
        return jsonify({"success": False, "error": "Erro ao buscar acumuladores"}), 500

@sped_bp.route('/acumuladores', methods=['POST'])
@login_required
@secure_api_endpoint(max_requests=30, window_minutes=1)
def add_acumulador():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Dados inválidos'}), 400
        
        success, message_or_error = SpedService.add_acumulador(
            data.get('codigo'),
            data.get('descricao'),
            data.get('cfop')
        )
        if success:
            return jsonify({'success': True, 'message': message_or_error}), 201
        return jsonify({'success': False, 'error': message_or_error}), 400
    except Exception as e:
        current_app.logger.error(f"Erro ao adicionar acumulador: {e}")
        return jsonify({'success': False, 'error': 'Erro ao processar a requisição'}), 500

@sped_bp.route('/acumuladores/<codigo>', methods=['GET'])
@login_required
def get_acumulador(codigo):
    # Esta rota é usada para popular o formulário de edição
    acumulador = SpedService.get_acumulador_by_codigo(codigo)
    if acumulador:
        return jsonify(acumulador)
    return jsonify({'success': False, 'error': 'Acumulador não encontrado'}), 404

@sped_bp.route('/acumuladores/<codigo>', methods=['PUT'])
@login_required
def update_acumulador(codigo):
    data = request.get_json()
    success, message_or_error = SpedService.update_acumulador(codigo, data.get('descricao'), data.get('cfop'))
    if success:
        return jsonify({'success': True, 'message': message_or_error})
    return jsonify({'success': False, 'error': message_or_error}), 400

@sped_bp.route('/acumuladores/<codigo>', methods=['DELETE'])
@login_required
def delete_acumulador(codigo):
    success, message_or_error = SpedService.delete_acumulador(codigo)
    if success:
        return jsonify({'success': True, 'message': message_or_error})
    return jsonify({'success': False, 'error': message_or_error}), 400

# Rotas para CFOPs
@sped_bp.route('/cfops', methods=['GET'])
@login_required
def get_cfops():
    try:
        search_term = request.args.get('search')
        cfops = SpedService.get_cfops(search_term=search_term)
        return jsonify(cfops)
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar CFOPs: {e}")
        return jsonify({"success": False, "error": "Erro ao buscar CFOPs"}), 500

@sped_bp.route('/cfops', methods=['POST'])
@login_required
@secure_api_endpoint(max_requests=30, window_minutes=1)
def add_cfop():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Dados inválidos'}), 400
            
        success, message_or_error = SpedService.add_cfop(data.get('cfop'))
        if success:
            return jsonify({'success': True, 'message': message_or_error}), 201
        return jsonify({'success': False, 'error': message_or_error}), 400
    except Exception as e:
        current_app.logger.error(f"Erro ao adicionar CFOP: {e}")
        return jsonify({'success': False, 'error': 'Erro ao processar a requisição'}), 500

@sped_bp.route('/cfops/<cfop>', methods=['GET'])
@login_required
def get_cfop(cfop):
    # Rota para buscar um único CFOP para edição
    cfop_data = SpedService.get_cfop_by_codigo(cfop)
    if cfop_data:
        return jsonify(cfop_data)
    return jsonify({'success': False, 'error': 'CFOP não encontrado'}), 404

@sped_bp.route('/cfops/<cfop>', methods=['PUT'])
@login_required
def update_cfop(cfop):
    data = request.get_json()
    new_cfop = data.get('cfop')
    if not new_cfop:
        return jsonify({'success': False, 'error': 'CFOP é obrigatório'}), 400
    
    success, message_or_error = SpedService.update_cfop(cfop, new_cfop)
    if success:
        return jsonify({'success': True, 'message': message_or_error})
    return jsonify({'success': False, 'error': message_or_error}), 400

@sped_bp.route('/cfops/<cfop>', methods=['DELETE'])
@login_required
def delete_cfop(cfop):
    success, message_or_error = SpedService.delete_cfop(cfop)
    if success:
        return jsonify({'success': True, 'message': message_or_error})
    return jsonify({'success': False, 'error': message_or_error}), 400

# Rotas para Produtos
@sped_bp.route('/produtos', methods=['GET'])
@login_required
def get_produtos():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    filter_opt = request.args.get('filter')
    search_term = request.args.get('search')
    
    items, total = SpedService.get_produtos(
        filter_opt=filter_opt,
        search_term=search_term,
        page=page,
        per_page=per_page
    )
    
    return jsonify({
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page if per_page > 0 else 0
    })

@sped_bp.route('/produtos/<codigo>', methods=['DELETE'])
@login_required
def delete_produto(codigo):
    success, message = SpedService.delete_produto(codigo)
    return jsonify({'success': success, 'message': message})

@sped_bp.route('/produtos/atualizar_acumulador', methods=['POST'])
@login_required
def update_produto_acumulador():
    data = request.get_json()
    codigo_produto = data.get('codigo')
    codigo_acumulador = data.get('acumulador')
    success, message = SpedService.update_produto_acumulador(codigo_produto, codigo_acumulador)
    return jsonify({'success': success, 'message': message})

@sped_bp.route('/produtos/bulk_update_acumulador', methods=['POST'])
@login_required
def bulk_update_produto_acumulador():
    data = request.get_json()
    product_codes = data.get('product_codes')
    acumulador_code = data.get('acumulador_code')
    
    success, message = SpedService.bulk_update_produto_acumulador(product_codes, acumulador_code)
    if success:
        return jsonify({'success': True, 'message': message})
    return jsonify({'success': False, 'error': message}), 400

@sped_bp.route('/vendas', methods=['GET'])
@login_required
def get_vendas():
    """Busca o relatório de resumo de vendas."""
    try:
        competencia = request.args.get('competencia')
        relatorio = SpedService.get_vendas(competencia=competencia)
        return jsonify(relatorio)
    except ValueError as ve:
        return jsonify({'success': False, 'error': str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar vendas: {e}")
        return jsonify({"success": False, "error": "Erro ao buscar vendas"}), 500

@sped_bp.route('/competencias', methods=['GET'])
@login_required
def get_competencias():
    try:
        competencias = SpedService.get_competencias()
        return jsonify(competencias)
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar competências: {e}")
        return jsonify({"success": False, "error": "Erro ao buscar competências"}), 500

@sped_bp.route('/relatorio_vendas', methods=['GET'])
@login_required
def get_relatorio_vendas():
    competencia = request.args.get('competencia')
    try:
        relatorio = SpedService.get_relatorio_vendas(competencia)
        return jsonify(relatorio)
    except ValueError as ve: # Captura o erro específico de validação
        return jsonify({'success': False, 'error': str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar relatório de vendas: {e}")
        return jsonify({"success": False, "error": "Erro ao gerar relatório"}), 500

@sped_bp.route('/relatorio_cfop', methods=['GET'])
@login_required
def get_relatorio_cfop():
    competencia = request.args.get('competencia')
    timestamp = request.args.get('_t')  # Para invalidar cache
    
    current_app.logger.info(f"Requisição relatório CFOP - Competência: {competencia}, Timestamp: {timestamp}")
    
    try:
        relatorio = SpedService.get_relatorio_cfop(competencia) or []
        current_app.logger.info(f"Relatório CFOP gerado com {len(relatorio)} itens")
        
        # Adiciona headers para evitar cache
        response = jsonify(relatorio or [])
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
    except ValueError as ve: # Captura o erro específico de validação
        current_app.logger.warning(f"Erro de validação no relatório CFOP: {str(ve)}")
        return jsonify({'success': False, 'error': str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar relatório de CFOP: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Erro ao gerar relatório"}), 500