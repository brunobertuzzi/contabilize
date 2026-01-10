import logging
from collections import Counter
from datetime import datetime
from io import TextIOWrapper
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, case, func, or_, text
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError
from sqlalchemy.orm import joinedload  # Eager loading para otimização

from scripts.database import (
    Acumulador,
    Cfop,
    DocumentoFiscalSped,
    Empresa,
    ProdutoSped,
    VendaSped,
    get_db,
)
from scripts.empresa_service import get_empresa_id_from_session, get_or_create_empresa
from scripts.validators import (
    ValidationError,
    log_security_event,
    sanitize_search_term,
    validate_cfop,
    validate_codigo_acumulador,
    validate_competencia,
    validate_descricao,
    validate_pagination,
)

logger = logging.getLogger(__name__)


class SpedService:
    @staticmethod
    def import_sped_file(
        file, empresa_selecionada_id: Optional[int] = None
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Processa um arquivo SPED Fiscal e importa os dados para o banco de dados.

        Este método realiza a leitura linha a linha do arquivo SPED, extrai informações
        de produtos (registro 0200), documentos fiscais de saída (registro C100) e 
        itens de venda (registro C170), e persiste no banco de dados associado à 
        empresa identificada no arquivo ou à empresa selecionada.

        Args:
            file: Objeto de arquivo SPED a ser processado (FileStorage do Flask)
            empresa_selecionada_id: ID da empresa selecionada (opcional). Se fornecido,
                                   valida se o arquivo pertence a esta empresa.

        Returns:
            Tupla contendo:
                - bool: True se a importação foi bem-sucedida, False caso contrário
                - str: Mensagem descritiva do resultado da operação
                - Optional[int]: ID da empresa associada aos dados importados, ou None em caso de erro

        Raises:
            Exception: Em caso de erro fatal durante o processamento do arquivo
        """
        try:
            logger.info(f"Iniciando importação do arquivo SPED: {file.filename}")

            def parse_float(value: str) -> float:
                try:
                    return (
                        float(value.strip().replace(".", "").replace(",", "."))
                        if value.strip()
                        else 0.0
                    )
                except (ValueError, AttributeError):
                    return 0.0

            # Otimização: Processar o arquivo como um stream (linha por linha)
            file.seek(0)
            try:
                lines = TextIOWrapper(file, encoding="latin-1")
            except UnicodeDecodeError:
                file.seek(0)
                lines = TextIOWrapper(file, encoding="utf-8", errors="ignore")

            produtos_raw, vendas_raw, documentos_raw, erros, record_types = (
                [],
                [],
                [],
                [],
                Counter(),
            )
            info_documento = {}
            current_doc_fiscal = None

            # Dados da empresa do arquivo SPED (extraídos do registro 0000)
            empresa_sped = {
                "cnpj": None,
                "razao_social": None,
                "inscricao_estadual": None,
                "uf": None,
            }

            for num_linha, line in enumerate(lines, 1):
                try:
                    if not line.strip():
                        continue
                    fields = line.strip().split("|")
                    if len(fields) < 2:
                        continue

                    reg_type = fields[1]
                    record_types[reg_type] += 1

                    # Registro 0000 - Abertura do arquivo SPED (contém dados da empresa)
                    if reg_type == "0000":
                        if len(fields) >= 9:
                            # Campos do registro 0000:
                            # |0000|COD_VER|COD_FIN|DT_INI|DT_FIN|NOME|CNPJ|CPF|UF|IE|...
                            empresa_sped["razao_social"] = (
                                fields[6].strip()
                                if len(fields) > 6 and fields[6]
                                else "Empresa Desconhecida"
                            )
                            empresa_sped["cnpj"] = (
                                fields[7].strip()
                                if len(fields) > 7 and fields[7]
                                else None
                            )
                            empresa_sped["uf"] = (
                                fields[9].strip()
                                if len(fields) > 9 and fields[9]
                                else None
                            )
                            empresa_sped["inscricao_estadual"] = (
                                fields[10].strip()
                                if len(fields) > 10 and fields[10]
                                else None
                            )

                            logger.info(
                                f"Empresa do SPED: {empresa_sped['razao_social']} (CNPJ: {empresa_sped['cnpj']})"
                            )

                    elif reg_type == "C100":
                        # Reset info_documento para o novo documento
                        info_documento = {}
                        # Verifica se é um documento de saída e se o campo de data não está vazio
                        if len(fields) > 13 and fields[2] == "1" and fields[10].strip():
                            current_doc_fiscal = {
                                "num_documento": fields[8].strip(),
                                "serie": fields[7].strip() if fields[7] else "1",
                                "data": datetime.strptime(fields[10], "%d%m%Y").date(),
                                "valor_total": parse_float(fields[12]),
                                "ind_oper": fields[2].strip(),
                                "ind_pagamento": fields[13].strip(),
                            }
                            documentos_raw.append(current_doc_fiscal)
                            # Mantém info_documento para C170 que não têm essa informação
                            info_documento = {"data": current_doc_fiscal["data"]}
                        else:
                            current_doc_fiscal = None

                    elif reg_type == "0200":
                        if len(fields) < 9:
                            continue
                        produto = {
                            "codigo_item": fields[2].strip(),
                            "descricao_item": fields[3].strip(),
                            "unidade": fields[6].strip(),
                            "ncm": fields[8].strip(),
                        }
                        if (
                            produto["codigo_item"]
                            and produto["descricao_item"]
                            and produto["unidade"]
                        ):
                            produtos_raw.append(produto)

                    elif reg_type == "C170":
                        if not current_doc_fiscal:
                            continue  # Pula itens sem um documento de saída associado
                        if len(fields) < 8:
                            continue

                        quantidade = parse_float(fields[5])
                        if quantidade <= 0:
                            continue

                        valor_item = parse_float(fields[7])
                        valor_desconto = (
                            parse_float(fields[8]) if len(fields) > 8 else 0.0
                        )

                        venda = {
                            "num_documento": current_doc_fiscal["num_documento"],
                            "serie": current_doc_fiscal["serie"],
                            "data": current_doc_fiscal["data"],
                            "codigo_item": fields[3].strip(),
                            "quantidade": quantidade,
                            "valor_unitario": (valor_item / quantidade)
                            if quantidade != 0
                            else 0,
                            "valor_total": valor_item - valor_desconto,
                            "valor_desconto": valor_desconto,
                            "base_icms": parse_float(fields[13])
                            if len(fields) > 13
                            else 0.0,
                            "valor_icms": parse_float(fields[14])
                            if len(fields) > 14
                            else 0.0,
                            "aliquota_icms": parse_float(fields[15])
                            if len(fields) > 15
                            else 0.0,
                        }
                        if venda["codigo_item"]:
                            vendas_raw.append(venda)

                except Exception as e:
                    erros.append(f"Linha {num_linha} ({reg_type}): Erro - {e}")

            # Desduplicar registros lidos do arquivo
            produtos = list({p["codigo_item"]: p for p in produtos_raw}.values())
            documentos = list(
                {(d["num_documento"], d["serie"]): d for d in documentos_raw}.values()
            )
            vendas = list(
                {
                    (v["num_documento"], v["serie"], v["codigo_item"]): v
                    for v in vendas_raw
                }.values()
            )

            if not documentos and not vendas:
                return (
                    False,
                    "Nenhum documento fiscal de saída ou item de venda válido encontrado.",
                    None,
                )

            # Validar CNPJ do arquivo
            if not empresa_sped.get("cnpj"):
                return (
                    False,
                    "Não foi possível identificar o CNPJ da empresa no arquivo SPED (registro 0000).",
                    None,
                )

            with get_db() as session:
                try:
                    # Verificar/Criar empresa
                    empresa, is_new_empresa = get_or_create_empresa(
                        session,
                        cnpj=empresa_sped["cnpj"],
                        razao_social=empresa_sped["razao_social"],
                        inscricao_estadual=empresa_sped.get("inscricao_estadual"),
                        uf=empresa_sped.get("uf"),
                    )

                    empresa_id = empresa.id
                    empresa_msg = ""

                    if is_new_empresa:
                        empresa_msg = (
                            f"Nova empresa cadastrada: {empresa.razao_social}. "
                        )
                        logger.info(
                            f"AUDIT: Nova empresa cadastrada automaticamente: {empresa.razao_social} (CNPJ: {empresa.cnpj})"
                        )
                    else:
                        # Validar se a empresa do arquivo corresponde à selecionada
                        if (
                            empresa_selecionada_id
                            and empresa_id != empresa_selecionada_id
                        ):
                            empresa_selecionada = session.get(
                                Empresa, empresa_selecionada_id
                            )
                            return (
                                False,
                                f"O arquivo SPED pertence à empresa '{empresa.razao_social}' (CNPJ: {empresa.cnpj}), "
                                f"mas a empresa selecionada é '{empresa_selecionada.razao_social}' (CNPJ: {empresa_selecionada.cnpj}). "
                                f"Selecione a empresa correta ou nenhuma empresa para importar automaticamente.",
                                None,
                            )

                    # Contagem inicial para esta empresa
                    docs_antes = (
                        session.query(func.count(DocumentoFiscalSped.id))
                        .filter(DocumentoFiscalSped.empresa_id == empresa_id)
                        .scalar()
                    )
                    produtos_antes = (
                        session.query(func.count(ProdutoSped.id))
                        .filter(ProdutoSped.empresa_id == empresa_id)
                        .scalar()
                    )
                    vendas_antes = (
                        session.query(func.count(VendaSped.id))
                        .join(DocumentoFiscalSped)
                        .filter(DocumentoFiscalSped.empresa_id == empresa_id)
                        .scalar()
                    )

                    chunk_size = 500

                    # 1. Inserção de produtos com empresa_id
                    if produtos:
                        for produto in produtos:
                            produto["empresa_id"] = empresa_id

                        produto_chunk_size = 50
                        for i in range(0, len(produtos), produto_chunk_size):
                            chunk = produtos[i : i + produto_chunk_size]
                            stmt_produtos = (
                                insert(ProdutoSped)
                                .values(chunk)
                                .on_conflict_do_nothing(
                                    index_elements=["empresa_id", "codigo_item"]
                                )
                            )
                            session.execute(stmt_produtos)

                    # 2. Inserção de documentos fiscais com empresa_id
                    if documentos:
                        for doc in documentos:
                            doc["empresa_id"] = empresa_id

                        doc_chunk_size = 50
                        for i in range(0, len(documentos), doc_chunk_size):
                            chunk = documentos[i : i + doc_chunk_size]
                            stmt_docs = (
                                insert(DocumentoFiscalSped)
                                .values(chunk)
                                .on_conflict_do_nothing(
                                    index_elements=[
                                        "empresa_id",
                                        "num_documento",
                                        "serie",
                                    ]
                                )
                            )
                            session.execute(stmt_docs)

                    session.flush()

                    # 3. Mapear documentos e produtos para seus IDs
                    doc_map = {
                        (doc.num_documento, doc.serie): doc.id
                        for doc in session.query(
                            DocumentoFiscalSped.id,
                            DocumentoFiscalSped.num_documento,
                            DocumentoFiscalSped.serie,
                        )
                        .filter(DocumentoFiscalSped.empresa_id == empresa_id)
                        .all()
                    }

                    produto_map = {
                        prod.codigo_item: prod.id
                        for prod in session.query(
                            ProdutoSped.id,
                            ProdutoSped.codigo_item,
                        )
                        .filter(ProdutoSped.empresa_id == empresa_id)
                        .all()
                    }

                    # 4. Inserção de vendas com documento_id e produto_id
                    if vendas:
                        vendas_com_fk = []
                        for venda in vendas:
                            doc_id = doc_map.get(
                                (venda["num_documento"], venda["serie"])
                            )
                            produto_id = produto_map.get(venda["codigo_item"])

                            if doc_id and produto_id:
                                venda_corrigida = {
                                    "documento_id": doc_id,
                                    "produto_id": produto_id,
                                    "data": venda["data"],
                                    "quantidade": venda["quantidade"],
                                    "valor_unitario": venda["valor_unitario"],
                                    "valor_total": venda["valor_total"],
                                    "valor_desconto": venda["valor_desconto"],
                                    "base_icms": venda["base_icms"],
                                    "valor_icms": venda["valor_icms"],
                                    "aliquota_icms": venda["aliquota_icms"],
                                    "data_importacao": datetime.now().date(),
                                }
                                vendas_com_fk.append(venda_corrigida)

                        venda_chunk_size = 50
                        for i in range(0, len(vendas_com_fk), venda_chunk_size):
                            chunk = vendas_com_fk[i : i + venda_chunk_size]
                            stmt_vendas = (
                                insert(VendaSped)
                                .values(chunk)
                                .on_conflict_do_nothing(
                                    index_elements=["documento_id", "produto_id"]
                                )
                            )
                            session.execute(stmt_vendas)

                    session.commit()

                    # Contagem final
                    docs_depois = (
                        session.query(func.count(DocumentoFiscalSped.id))
                        .filter(DocumentoFiscalSped.empresa_id == empresa_id)
                        .scalar()
                    )
                    produtos_depois = (
                        session.query(func.count(ProdutoSped.id))
                        .filter(ProdutoSped.empresa_id == empresa_id)
                        .scalar()
                    )
                    vendas_depois = (
                        session.query(func.count(VendaSped.id))
                        .join(DocumentoFiscalSped)
                        .filter(DocumentoFiscalSped.empresa_id == empresa_id)
                        .scalar()
                    )

                    novos_docs = docs_depois - docs_antes
                    novos_produtos = produtos_depois - produtos_antes
                    novas_vendas = vendas_depois - vendas_antes

                    msg = f"{empresa_msg}{novos_docs} novos documentos, {novos_produtos} produtos e {novas_vendas} itens de venda importados para '{empresa.razao_social}'."
                    if erros:
                        msg += f" \nOcorreram {len(erros)} avisos/erros durante a importação (verifique os logs)."
                        logger.warning(f"Erros de importação: {erros}")
                    return True, msg, empresa_id

                except Exception as e:
                    session.rollback()
                    logger.error(
                        f"Erro ao salvar no banco de dados: {e}", exc_info=True
                    )
                    return False, f"Erro ao salvar no banco de dados: {e}", None

        except Exception as e:
            logger.exception("Erro fatal durante a importação")
            return False, f"Erro inesperado durante a importação: {e}", None

    @staticmethod
    def get_cfops(
        search_term: Optional[str] = None, empresa_id: Optional[int] = None
    ) -> List[Dict]:
        """Retorna a lista de CFOPs cadastrados para uma empresa."""
        try:
            with get_db() as session:
                query = session.query(Cfop)
                if empresa_id:
                    query = query.filter(Cfop.empresa_id == empresa_id)
                if search_term:
                    search = f"%{search_term}%"
                    query = query.filter(
                        or_(Cfop.cfop.ilike(search), Cfop.descricao.ilike(search))
                    )
                cfops = query.order_by(Cfop.cfop).all()
                result = [
                    {"id": c.id, "cfop": str(c.cfop), "descricao": c.descricao or ""}
                    for c in cfops
                ]
                return result
        except Exception as e:
            logger.error(f"Erro ao buscar CFOPs: {e}")
            raise

    @staticmethod
    def get_cfop_by_codigo(cfop_codigo: str) -> Optional[Dict]:
        """Retorna um único CFOP pelo seu código."""
        try:
            with get_db() as session:
                cfop = session.query(Cfop).filter_by(cfop=cfop_codigo).first()
                if cfop:
                    return {"cfop": str(cfop.cfop)}
                return None
        except Exception as e:
            logger.error(f"Erro ao buscar CFOP {cfop_codigo}: {e}")
            raise

    @staticmethod
    def add_cfop(cfop: str, empresa_id: Optional[int] = None) -> Tuple[bool, str]:
        """Adiciona um novo CFOP com validações de segurança."""
        try:
            # Validação de entrada
            cfop = validate_cfop(cfop)

            if not empresa_id:
                return False, "Empresa não selecionada."

            with get_db() as session:
                novo_cfop = Cfop(cfop=cfop, empresa_id=empresa_id)
                session.add(novo_cfop)
                session.commit()

                # Log de auditoria
                logger.info(
                    f"AUDIT: CFOP {cfop} adicionado com sucesso para empresa {empresa_id}"
                )
                return True, "CFOP adicionado com sucesso!"

        except ValidationError as e:
            logger.warning(f"Validação falhou ao adicionar CFOP: {str(e)}")
            return False, str(e)
        except IntegrityError:
            logger.warning(f"Tentativa de adicionar CFOP duplicado: {cfop}")
            return False, "CFOP já cadastrado."
        except Exception as e:
            logger.error(f"Erro ao adicionar CFOP {cfop}: {e}")
            return False, "Erro interno ao adicionar CFOP."

    @staticmethod
    def update_cfop(cfop_codigo: str, novo_cfop: str) -> Tuple[bool, str]:
        """Atualiza um CFOP existente."""

        try:
            with get_db() as session:
                # Verifica se o CFOP original existe
                cfop_obj = session.query(Cfop).filter_by(cfop=cfop_codigo).first()
                if not cfop_obj:
                    return False, "CFOP não encontrado."

                # Verifica se há acumuladores associados ao CFOP
                acumuladores_associados = (
                    session.query(Acumulador).filter_by(cfop=cfop_codigo).count()
                )

                if acumuladores_associados > 0:
                    return (
                        False,
                        f"Não é possível editar este CFOP pois existem {acumuladores_associados} acumulador(es) associado(s). Exclua os acumuladores primeiro.",
                    )

                # Verifica se há produtos associados através de acumuladores (verificação adicional de segurança)
                produtos_associados = (
                    session.query(ProdutoSped)
                    .join(Acumulador, ProdutoSped.acumulador_id == Acumulador.id)
                    .filter(Acumulador.cfop_id == cfop_obj.id)
                    .count()
                )

                if produtos_associados > 0:
                    return (
                        False,
                        f"Não é possível editar este CFOP pois existem {produtos_associados} produto(s) associado(s) através de acumuladores. Remova os produtos dos acumuladores primeiro.",
                    )

                # Verifica se o novo CFOP já existe (se for diferente do original)
                if novo_cfop != cfop_codigo:
                    existing_cfop = (
                        session.query(Cfop).filter_by(cfop=novo_cfop).first()
                    )
                    if existing_cfop:
                        return False, f"CFOP {novo_cfop} já existe."

                # Atualiza o código do CFOP
                cfop_obj.cfop = novo_cfop
                session.commit()
                logger.info(
                    f"CFOP {cfop_codigo} atualizado para {novo_cfop} com sucesso."
                )
                return True, "CFOP atualizado com sucesso!"
        except Exception as e:
            logger.error(f"Erro ao atualizar CFOP {cfop_codigo}: {e}")
            session.rollback()
            return False, "Erro interno ao atualizar CFOP."

    @staticmethod
    def delete_cfop(cfop: str) -> Tuple[bool, str]:
        """Deleta um CFOP se não estiver em uso."""
        try:
            with get_db() as session:
                cfop_obj = session.query(Cfop).filter_by(cfop=cfop).first()
                if not cfop_obj:
                    return False, "CFOP não encontrado."

                # Verifica se há acumuladores associados ao CFOP
                acumuladores_associados = (
                    session.query(Acumulador).filter_by(cfop_id=cfop_obj.id).count()
                )

                if acumuladores_associados > 0:
                    return (
                        False,
                        f"Não é possível excluir este CFOP pois existem {acumuladores_associados} acumulador(es) associado(s). Exclua os acumuladores primeiro.",
                    )

                # Verifica se há produtos associados através de acumuladores (verificação adicional de segurança)
                produtos_associados = (
                    session.query(ProdutoSped)
                    .join(Acumulador, ProdutoSped.acumulador_id == Acumulador.id)
                    .filter(Acumulador.cfop_id == cfop_obj.id)
                    .count()
                )

                if produtos_associados > 0:
                    return (
                        False,
                        f"Não é possível excluir este CFOP pois existem {produtos_associados} produto(s) associado(s) através de acumuladores. Remova os produtos dos acumuladores primeiro.",
                    )

                session.delete(cfop_obj)
                session.commit()
                logger.info(f"CFOP {cfop} deletado com sucesso.")
                return True, "CFOP deletado com sucesso!"
        except IntegrityError:
            return False, "Não é possível excluir. O CFOP está em uso."
        except Exception as e:
            logger.error(f"Erro ao deletar CFOP {cfop}: {e}")
            return False, "Erro interno ao deletar CFOP."

    @staticmethod
    def get_acumuladores(
        search_term: Optional[str] = None, empresa_id: Optional[int] = None
    ) -> List[Dict]:
        """Retorna a lista de Acumuladores cadastrados para uma empresa."""
        try:
            # Sanitiza termo de busca
            search_term = sanitize_search_term(search_term)

            with get_db() as session:
                query = session.query(Acumulador).options(
                    joinedload(Acumulador.cfop_rel)
                )
                if empresa_id:
                    query = query.filter(Acumulador.empresa_id == empresa_id)
                if search_term:
                    search = f"%{search_term}%"
                    query = query.filter(
                        or_(
                            Acumulador.codigo.ilike(search),
                            Acumulador.descricao.ilike(search),
                        )
                    )
                acumuladores = query.order_by(Acumulador.codigo).all()
                return [
                    {
                        "id": a.id,
                        "codigo": a.codigo,
                        "descricao": a.descricao,
                        "cfop": a.cfop_rel.cfop if a.cfop_rel else None,
                        "cfop_id": a.cfop_id,
                    }
                    for a in acumuladores
                ]
        except Exception as e:
            logger.error(f"Erro ao buscar Acumuladores: {e}")
            raise

    @staticmethod
    def get_acumulador_by_codigo(codigo: str) -> Optional[Dict]:
        """Retorna um único Acumulador pelo seu código."""
        try:
            with get_db() as session:
                acumulador = session.query(Acumulador).filter_by(codigo=codigo).first()
                if acumulador:
                    return {
                        "codigo": acumulador.codigo,
                        "descricao": acumulador.descricao,
                        "cfop": acumulador.cfop,
                    }
                return None
        except Exception as e:
            logger.error(f"Erro ao buscar Acumulador {codigo}: {e}")
            raise

    @staticmethod
    def add_acumulador(
        codigo: str, descricao: str, cfop: str, empresa_id: Optional[int] = None
    ) -> Tuple[bool, str]:
        """Adiciona um novo Acumulador com validações de segurança."""
        try:
            # Validações de entrada
            codigo = validate_codigo_acumulador(codigo)
            descricao = validate_descricao(descricao, "Descrição do acumulador")
            cfop = validate_cfop(cfop)

            if not empresa_id:
                return False, "Empresa não selecionada."

            with get_db() as session:
                # Verifica se o CFOP existe para a mesma empresa
                cfop_obj = (
                    session.query(Cfop)
                    .filter_by(cfop=cfop, empresa_id=empresa_id)
                    .first()
                )
                if not cfop_obj:
                    return False, "CFOP informado não existe para esta empresa."

                novo_acumulador = Acumulador(
                    codigo=codigo,
                    descricao=descricao,
                    cfop_id=cfop_obj.id,
                    empresa_id=empresa_id,
                )
                session.add(novo_acumulador)
                session.commit()

                # Log de auditoria
                logger.info(
                    f"AUDIT: Acumulador {codigo} adicionado com sucesso para empresa {empresa_id}"
                )
                return True, "Acumulador adicionado com sucesso!"

        except ValidationError as e:
            logger.warning(f"Validação falhou ao adicionar acumulador: {str(e)}")
            return False, str(e)
        except IntegrityError:
            logger.warning(f"Tentativa de adicionar Acumulador duplicado: {codigo}")
            return False, "Código de Acumulador já cadastrado."
        except Exception as e:
            logger.error(f"Erro ao adicionar Acumulador {codigo}: {e}")
            return False, "Erro interno ao adicionar Acumulador."

    @staticmethod
    def update_acumulador(codigo: str, descricao: str, cfop: str) -> Tuple[bool, str]:
        """Atualiza um Acumulador existente com validações de segurança."""
        try:
            # Validações de entrada
            descricao = validate_descricao(descricao, "Descrição do acumulador")
            cfop = validate_cfop(cfop)

            with get_db() as session:
                acumulador = session.query(Acumulador).filter_by(codigo=codigo).first()
                if not acumulador:
                    return False, "Acumulador não encontrado."
                if not session.query(Cfop).filter_by(cfop=cfop).first():
                    return False, "CFOP informado não existe."

                # Log de auditoria das mudanças
                logger.info(
                    f"AUDIT: Atualizando acumulador {codigo} - Descrição: '{acumulador.descricao}' -> '{descricao}', CFOP: '{acumulador.cfop}' -> '{cfop}'"
                )

                acumulador.descricao = descricao
                acumulador.cfop = cfop
                session.commit()

                logger.info(f"AUDIT: Acumulador {codigo} atualizado com sucesso")
                return True, "Acumulador atualizado com sucesso!"

        except ValidationError as e:
            logger.warning(
                f"Validação falhou ao atualizar acumulador {codigo}: {str(e)}"
            )
            return False, str(e)
        except Exception as e:
            logger.error(f"Erro ao atualizar Acumulador {codigo}: {e}")
            return False, "Erro interno ao atualizar Acumulador."

    @staticmethod
    def delete_acumulador(codigo: str) -> Tuple[bool, str]:
        """Deleta um Acumulador se não estiver em uso."""
        try:
            with get_db() as session:
                acumulador = session.query(Acumulador).filter_by(codigo=codigo).first()
                if not acumulador:
                    return False, "Acumulador não encontrado."

                # Verifica se o Acumulador está em uso por algum produto
                produtos_count = (
                    session.query(ProdutoSped)
                    .filter_by(acumulador_id=acumulador.id)
                    .count()
                )
                if produtos_count > 0:
                    return (
                        False,
                        f"Não é possível excluir. O Acumulador está em uso por {produtos_count} produto(s).",
                    )

                session.delete(acumulador)
                session.commit()
                logger.info(f"Acumulador {codigo} deletado com sucesso.")
                return True, "Acumulador deletado com sucesso!"
        except IntegrityError:
            return False, "Não é possível excluir. O Acumulador está em uso."
        except Exception as e:
            logger.error(f"Erro ao deletar Acumulador {codigo}: {e}")
            return False, "Erro interno ao deletar Acumulador."

    @staticmethod
    def update_produto_acumulador(
        codigo_produto: str, codigo_acumulador: str
    ) -> Tuple[bool, str]:
        """Atualiza o acumulador de um produto específico."""
        try:
            with get_db() as session:
                produto = (
                    session.query(ProdutoSped)
                    .filter_by(codigo_item=codigo_produto)
                    .first()
                )
                if not produto:
                    return False, "Produto não encontrado."

                if codigo_acumulador:
                    acumulador = (
                        session.query(Acumulador)
                        .filter_by(codigo=codigo_acumulador)
                        .first()
                    )
                    if not acumulador:
                        return False, "Acumulador não encontrado."

                produto.acumulador_id = acumulador.id if acumulador else None
                produto.data_alteracao = datetime.now().date()
                session.commit()
                logger.info(
                    f"Acumulador do produto {codigo_produto} atualizado para {codigo_acumulador}."
                )
                return True, "Acumulador do produto atualizado com sucesso!"
        except Exception as e:
            logger.error(
                f"Erro ao atualizar acumulador do produto {codigo_produto}: {e}"
            )
            return False, "Erro interno ao atualizar o acumulador do produto."

    @staticmethod
    def bulk_update_produto_acumulador(
        product_codes: List[str], acumulador_code: str
    ) -> Tuple[bool, str]:
        """Atualiza o acumulador para uma lista de produtos."""
        if not product_codes:
            return False, "Nenhum produto selecionado."
        if not acumulador_code:
            return False, "Nenhum acumulador selecionado."

        try:
            with get_db() as session:
                # Verifica se o acumulador existe e pega o ID
                acumulador = (
                    session.query(Acumulador).filter_by(codigo=acumulador_code).first()
                )
                if not acumulador:
                    return False, "Acumulador inválido."

                # Atualiza os produtos
                update_count = (
                    session.query(ProdutoSped)
                    .filter(ProdutoSped.codigo_item.in_(product_codes))
                    .update(
                        {
                            "acumulador_id": acumulador.id,
                            "data_alteracao": datetime.now().date(),
                        },
                        synchronize_session=False,
                    )
                )

                session.commit()
                return True, f"{update_count} produto(s) atualizado(s) com sucesso."
        except Exception as e:
            logger.error(f"Erro na atualização em massa de acumuladores: {e}")
            return False, "Erro interno ao atualizar produtos."

    @staticmethod
    def _get_paginated_query(
        session, base_query, page: int, per_page: int, order_by_clauses: list
    ) -> Tuple[List, int]:
        """
        Executa uma query paginada, conta o total de registros e retorna os resultados.

        Args:
            session: A sessão do SQLAlchemy.
            base_query: O objeto Query do SQLAlchemy com os filtros já aplicados.
            page: O número da página.
            per_page: Itens por página.
            order_by_clauses: Uma lista de cláusulas para ordenação.

        Returns:
            Uma tupla contendo a lista de itens da página e o total de itens.
        """
        try:
            total = base_query.count()
            items = (
                base_query.order_by(*order_by_clauses)
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
            return items, total
        except SQLAlchemyError as e:
            logger.error(f"Erro ao executar a query paginada: {str(e)}")
            return [], 0

    @staticmethod
    def get_competencias(empresa_id: Optional[int] = None) -> List[str]:
        """Retorna a lista de competências (meses/anos) disponíveis."""
        try:
            with get_db() as session:
                query = session.query(func.strftime("%Y-%m", VendaSped.data))

                if empresa_id:
                    query = query.join(
                        DocumentoFiscalSped,
                        VendaSped.documento_id == DocumentoFiscalSped.id,
                    ).filter(DocumentoFiscalSped.empresa_id == empresa_id)

                # Busca as competências distintas na tabela de vendas
                competencias = (
                    query.distinct()
                    .order_by(func.strftime("%Y-%m", VendaSped.data).desc())
                    .all()
                )
                # Converte os resultados para uma lista de strings
                return [str(comp[0]) for comp in competencias] if competencias else []
        except Exception as e:
            logger.error(f"Erro ao buscar competências: {e}")
            raise

    @staticmethod
    def get_produtos(
        filter_opt: Optional[str] = None,
        search_term: Optional[str] = None,
        page: int = 1,
        per_page: int = 50,
        empresa_id: Optional[int] = None,
    ) -> Tuple[List[Dict], int]:
        """
        Retorna produtos paginados com filtros opcionais e validações de segurança.

        Args:
            filter_opt: Opção de filtro para acumuladores (todos, cadastrados, naoCadastrados)
            search_term: Buscar por código, descrição ou NCM
            page: Número da página
            per_page: Itens por página
            empresa_id: ID da empresa para filtrar produtos
        """
        try:
            # Validações de entrada
            page, per_page = validate_pagination(page, per_page)
            search_term = sanitize_search_term(search_term)

            with get_db() as session:
                query = session.query(ProdutoSped)

                # Filtrar por empresa (obrigatório se fornecido)
                if empresa_id:
                    query = query.filter(ProdutoSped.empresa_id == empresa_id)

                if filter_opt == "cadastrados":
                    query = query.filter(ProdutoSped.acumulador_id.isnot(None))
                elif filter_opt == "naoCadastrados":
                    query = query.filter(ProdutoSped.acumulador_id.is_(None))

                if search_term:
                    search = f"%{search_term}%"
                    query = query.filter(
                        or_(
                            ProdutoSped.codigo_item.ilike(search),
                            ProdutoSped.descricao_item.ilike(search),
                            ProdutoSped.ncm.ilike(search),
                        )
                    )

                produtos, total = SpedService._get_paginated_query(
                    session, query, page, per_page, [ProdutoSped.codigo_item]
                )

                # Converte objetos SQLAlchemy para dicionários
                produtos_dict = [
                    {
                        "codigo_item": p.codigo_item,
                        "descricao_item": p.descricao_item,
                        "unidade": p.unidade,
                        "ncm": p.ncm,
                        "acumulador": p.acumulador_rel.codigo
                        if p.acumulador_rel
                        else None,
                        "aliquota_icms": p.aliquota_icms,
                        "data_cadastro": p.data_cadastro.isoformat()
                        if p.data_cadastro
                        else None,
                        "data_alteracao": p.data_alteracao.isoformat()
                        if p.data_alteracao
                        else None,
                    }
                    for p in produtos
                ]

                return produtos_dict, total

        except ValidationError as e:
            logger.warning(f"Validação falhou ao buscar produtos: {str(e)}")
            return [], 0

    @staticmethod
    def _calcular_valor_com_rateio(session, vendas_query):
        """
        Calcula o valor final de cada venda considerando o rateio proporcional das despesas da nota.

        Para cada item da nota:
        1. Valor líquido = valor_total (já considera descontos)
        2. Proporção do item = valor_total_item / soma_valores_itens_nota
        3. Despesas rateadas = (valor_total_nota - soma_valores_itens_nota) * proporção
        4. Valor final = valor_total_item + despesas_rateadas
        """
        vendas_com_rateio = []

        # Agrupa vendas por documento para calcular o rateio
        documentos_map = {}
        for venda in vendas_query:
            doc_id = venda.documento_id
            if doc_id not in documentos_map:
                documentos_map[doc_id] = {"documento": venda.documento_rel, "itens": []}
            documentos_map[doc_id]["itens"].append(venda)

        # Calcula o rateio para cada documento
        for doc_id, doc_data in documentos_map.items():
            documento = doc_data["documento"]
            itens = doc_data["itens"]

            # Soma total dos itens da nota
            soma_itens = sum(item.valor_total for item in itens)

            # Calcula despesas a ratear (diferença entre valor total da nota e soma dos itens)
            # Isso inclui frete, seguro, outras despesas, etc.
            despesas_totais = documento.valor_total - soma_itens

            # Rateia as despesas proporcionalmente para cada item
            for item in itens:
                if soma_itens > 0:
                    proporcao = item.valor_total / soma_itens
                    despesas_rateadas = despesas_totais * proporcao
                else:
                    despesas_rateadas = 0

                # Valor final = valor líquido do item + despesas rateadas
                valor_final = item.valor_total + despesas_rateadas

                vendas_com_rateio.append(
                    {
                        "venda": item,
                        "valor_liquido": item.valor_total,
                        "despesas_rateadas": despesas_rateadas,
                        "valor_final": valor_final,
                    }
                )

        return vendas_com_rateio

    @staticmethod
    def get_relatorio_vendas(
        competencia: Optional[str] = None, empresa_id: Optional[int] = None
    ) -> Dict:
        """Retorna o relatório de vendas agrupado por acumulador com detalhes por data."""
        try:
            # Valida competência
            competencia = validate_competencia(competencia)

            # Verifica se há produtos sem acumulador
            with get_db() as session:
                query_prod = session.query(ProdutoSped).filter(
                    ProdutoSped.acumulador_id.is_(None)
                )
                if empresa_id:
                    query_prod = query_prod.filter(ProdutoSped.empresa_id == empresa_id)

                produtos_sem_acumulador = query_prod.count()

                if produtos_sem_acumulador > 0:
                    raise ValueError(
                        f"Existem {produtos_sem_acumulador} produto(s) sem acumulador. Por favor, associe os acumuladores na aba 'Produtos' antes de gerar relatórios."
                    )

            with get_db() as session:
                # Busca todas as vendas com eager loading para evitar N+1 queries
                query = (
                    session.query(VendaSped)
                    .options(
                        joinedload(VendaSped.produto_rel).joinedload(
                            ProdutoSped.acumulador_rel
                        ),
                        joinedload(VendaSped.documento_rel),
                    )
                    .join(ProdutoSped, VendaSped.produto_id == ProdutoSped.id)
                    .join(Acumulador, ProdutoSped.acumulador_id == Acumulador.id)
                    .join(
                        DocumentoFiscalSped,
                        VendaSped.documento_id == DocumentoFiscalSped.id,
                    )
                )

                if empresa_id:
                    query = query.filter(DocumentoFiscalSped.empresa_id == empresa_id)

                if competencia:
                    query = query.filter(
                        func.strftime("%Y-%m", VendaSped.data) == competencia
                    )

                vendas = query.all()

                # Calcula valores com rateio
                vendas_com_rateio = SpedService._calcular_valor_com_rateio(
                    session, vendas
                )

                # Agrupa por acumulador
                acumuladores_data = {}

                for item in vendas_com_rateio:
                    venda = item["venda"]
                    valor_final = item["valor_final"]

                    # Busca o acumulador do produto
                    produto = venda.produto_rel
                    acumulador = produto.acumulador_rel

                    acumulador_codigo = acumulador.codigo
                    acumulador_descricao = acumulador.descricao
                    data_venda = venda.data.strftime("%d/%m/%Y")

                    # Inicializa acumulador se não existir
                    if acumulador_codigo not in acumuladores_data:
                        acumuladores_data[acumulador_codigo] = {
                            "codigo": acumulador_codigo,
                            "descricao": acumulador_descricao,
                            "total": 0,
                            "vendas_por_data": {},
                        }

                    # Soma no total do acumulador
                    acumuladores_data[acumulador_codigo]["total"] += valor_final

                    # Agrupa por data dentro do acumulador
                    if (
                        data_venda
                        not in acumuladores_data[acumulador_codigo]["vendas_por_data"]
                    ):
                        acumuladores_data[acumulador_codigo]["vendas_por_data"][
                            data_venda
                        ] = 0

                    acumuladores_data[acumulador_codigo]["vendas_por_data"][
                        data_venda
                    ] += valor_final

                # Converte para lista ordenada e organiza vendas por data
                acumuladores_list = []
                total_geral = 0

                for acumulador_codigo in sorted(acumuladores_data.keys()):
                    acumulador_data = acumuladores_data[acumulador_codigo]

                    # Ordena as vendas por data
                    vendas_ordenadas = []
                    for data, valor in acumulador_data["vendas_por_data"].items():
                        vendas_ordenadas.append({"data": data, "valor": valor})

                    # Ordena por data
                    vendas_ordenadas.sort(
                        key=lambda x: datetime.strptime(x["data"], "%d/%m/%Y")
                    )

                    acumuladores_list.append(
                        {
                            "codigo": acumulador_data["codigo"],
                            "descricao": acumulador_data["descricao"],
                            "total": acumulador_data["total"],
                            "vendas_por_data": vendas_ordenadas,
                        }
                    )

                    total_geral += acumulador_data["total"]

                return {"acumuladores": acumuladores_list, "total_geral": total_geral}

        except Exception as e:
            logger.warning(f"Não foi possível gerar relatório de vendas: {str(e)}")
            raise

    @staticmethod
    def get_relatorio_cfop(
        competencia: Optional[str] = None, empresa_id: Optional[int] = None
    ) -> List[Dict]:
        """Retorna o relatório de vendas por CFOP com rateio de despesas."""
        try:
            # Valida competência
            competencia = validate_competencia(competencia)
            logger.info(f"Gerando relatório CFOP para competência: {competencia}")

            # Verifica se há produtos sem acumulador (mesma lógica da aba acumuladores)
            with get_db() as session:
                query_prod = session.query(ProdutoSped).filter(
                    ProdutoSped.acumulador_id.is_(None)
                )
                if empresa_id:
                    query_prod = query_prod.filter(ProdutoSped.empresa_id == empresa_id)

                produtos_sem_acumulador = query_prod.count()
                logger.info(
                    f"Total de produtos sem acumulador: {produtos_sem_acumulador}"
                )

                if produtos_sem_acumulador > 0:
                    error_msg = f"Existem {produtos_sem_acumulador} produto(s) sem acumulador. Por favor, associe os acumuladores na aba 'Produtos' antes de gerar relatórios."
                    logger.warning(error_msg)
                    raise ValueError(error_msg)

            with get_db() as session:
                # Busca todas as vendas com seus relacionamentos usando joins explícitos
                query = (
                    session.query(
                        VendaSped, ProdutoSped, Acumulador, Cfop, DocumentoFiscalSped
                    )
                    .select_from(VendaSped)
                    .join(ProdutoSped, VendaSped.produto_id == ProdutoSped.id)
                    .join(Acumulador, ProdutoSped.acumulador_id == Acumulador.id)
                    .join(Cfop, Acumulador.cfop_id == Cfop.id)
                    .join(
                        DocumentoFiscalSped,
                        VendaSped.documento_id == DocumentoFiscalSped.id,
                    )
                )

                if empresa_id:
                    query = query.filter(DocumentoFiscalSped.empresa_id == empresa_id)

                if competencia:
                    query = query.filter(
                        func.strftime("%Y-%m", VendaSped.data) == competencia
                    )

                logger.info(
                    "Executando query para buscar vendas com relacionamentos..."
                )
                resultados = query.all()
                logger.info(
                    f"Encontradas {len(resultados)} vendas com relacionamentos válidos"
                )

                if not resultados:
                    logger.warning(
                        f"Nenhuma venda encontrada para a competência {competencia}"
                    )
                    return []

                # Converte os resultados para o formato esperado pela função de rateio
                vendas = []
                for venda, produto, acumulador, cfop, documento in resultados:
                    # Anexa os objetos relacionados à venda para compatibilidade
                    venda.produto_rel = produto
                    venda.documento_rel = documento
                    produto.acumulador_rel = acumulador
                    acumulador.cfop_rel = cfop
                    vendas.append(venda)

                logger.info(
                    f"Processando {len(vendas)} vendas para cálculo de rateio..."
                )

                # Calcula valores com rateio
                vendas_com_rateio = SpedService._calcular_valor_com_rateio(
                    session, vendas
                )

                # Agrupa por CFOP
                cfop_totais = {}
                vendas_processadas = 0
                vendas_com_erro = 0

                for item in vendas_com_rateio:
                    venda = item["venda"]
                    valor_final = item["valor_final"]

                    # Busca o CFOP através do acumulador de forma mais robusta
                    try:
                        produto = venda.produto_rel
                        if not produto or not produto.acumulador_id:
                            continue  # Pula produtos sem acumulador

                        acumulador = produto.acumulador_rel
                        if not acumulador:
                            continue  # Pula se não conseguir carregar o acumulador

                        cfop = acumulador.cfop_rel
                        if not cfop:
                            continue  # Pula se não conseguir carregar o CFOP

                        cfop_codigo = cfop.cfop
                        if cfop_codigo not in cfop_totais:
                            cfop_totais[cfop_codigo] = {"cfop": cfop_codigo, "total": 0}
                        cfop_totais[cfop_codigo]["total"] += valor_final
                        vendas_processadas += 1

                    except Exception as e:
                        logger.warning(
                            f"Erro ao processar venda {venda.id} para relatório CFOP: {e}"
                        )
                        vendas_com_erro += 1
                        continue

                logger.info(
                    f"Relatório CFOP processado: {vendas_processadas} vendas processadas, {vendas_com_erro} com erro"
                )
                logger.info(f"CFOPs encontrados: {list(cfop_totais.keys())}")

                resultado = [
                    {"cfop": item["cfop"], "total": float(item["total"])}
                    for item in cfop_totais.values()
                ]

                # Ordena por CFOP para consistência
                resultado.sort(key=lambda x: x["cfop"])

                logger.info(f"Retornando relatório com {len(resultado)} CFOPs")
                return resultado
        except Exception as e:
            logger.warning(f"Não foi possível gerar relatório de CFOP: {str(e)}")
            raise

    @staticmethod
    def get_vendas(
        competencia: Optional[str] = None, empresa_id: Optional[int] = None
    ) -> Dict:
        """
        Retorna um relatório de resumo de vendas (total, a vista, a prazo).

        Args:
            competencia: O mês/ano para filtrar o relatório.
            empresa_id: Filtra por empresa
        """
        try:
            # Valida competência
            competencia = validate_competencia(competencia)

            with get_db() as session:
                # Query base para documentos de saída
                query = session.query(DocumentoFiscalSped).filter(
                    DocumentoFiscalSped.ind_oper == "1"
                )

                if empresa_id:
                    query = query.filter(DocumentoFiscalSped.empresa_id == empresa_id)

                if competencia:
                    query = query.filter(
                        func.strftime("%Y-%m", DocumentoFiscalSped.data) == competencia
                    )

                # Usando subqueries para evitar o erro com `case` em algumas versões do SQLite/SQLAlchemy
                total_vendas_query = query.with_entities(
                    func.sum(DocumentoFiscalSped.valor_total)
                )
                vendas_a_vista_query = query.filter(
                    DocumentoFiscalSped.ind_pagamento == "0"
                ).with_entities(func.sum(DocumentoFiscalSped.valor_total))
                vendas_a_prazo_query = query.filter(
                    DocumentoFiscalSped.ind_pagamento == "1"
                ).with_entities(func.sum(DocumentoFiscalSped.valor_total))

                total_vendas = session.execute(total_vendas_query).scalar() or 0.0
                vendas_a_vista = session.execute(vendas_a_vista_query).scalar() or 0.0
                vendas_a_prazo = session.execute(vendas_a_prazo_query).scalar() or 0.0

                return {
                    "total_vendas": total_vendas,
                    "vendas_a_vista": vendas_a_vista,
                    "vendas_a_prazo": vendas_a_prazo,
                }
        except Exception as e:
            logger.error(f"Erro ao gerar relatório de vendas: {e}")
            raise
