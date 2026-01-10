"""
Módulo de Validação Simplificado
===============================

Contém validações essenciais para a aplicação.
"""

import html
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Exceção para erros de validação"""

    pass


def sanitize_input(text: Optional[str], max_length: Optional[int] = None, field_name: str = "Campo") -> Optional[str]:
    """Sanitiza entrada de texto básica."""
    if text is None:
        return None

    text = str(text).strip()
    if not text:
        return text

    if max_length and len(text) > max_length:
        raise ValidationError(f"{field_name} deve ter no máximo {max_length} caracteres")

    # Sanitização básica
    text = html.escape(text)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

    return text


def validate_codigo_acumulador(codigo: str) -> str:
    """Valida código de acumulador."""
    if not codigo:
        raise ValidationError("Código do acumulador é obrigatório")

    codigo = sanitize_input(codigo, max_length=20, field_name="Código do acumulador")

    if not re.match(r"^[A-Z0-9_]+$", codigo):
        raise ValidationError("Código deve conter apenas letras maiúsculas, números e underscore")

    if len(codigo) < 3:
        raise ValidationError("Código deve ter pelo menos 3 caracteres")

    return codigo


def validate_descricao(descricao: str, field_name: str = "Descrição") -> str:
    """Valida descrição."""
    if not descricao:
        raise ValidationError(f"{field_name} é obrigatória")

    descricao = sanitize_input(descricao, max_length=100, field_name=field_name)

    if len(descricao) < 3:
        raise ValidationError(f"{field_name} deve ter pelo menos 3 caracteres")

    return descricao


def validate_cfop(cfop: str) -> str:
    """Valida código CFOP."""
    if not cfop:
        raise ValidationError("CFOP é obrigatório")

    cfop = sanitize_input(cfop, max_length=4, field_name="CFOP")

    if not cfop.isdigit():
        raise ValidationError("CFOP deve conter apenas números")

    if len(cfop) != 4:
        raise ValidationError("CFOP deve ter exatamente 4 dígitos")

    if cfop[0] not in "1234567":
        raise ValidationError("CFOP deve começar com dígito de 1 a 7")

    return cfop


def validate_competencia(competencia: Optional[str]) -> Optional[str]:
    """Valida formato de competência (YYYY-MM)."""
    if not competencia:
        return None

    competencia = sanitize_input(competencia, max_length=7, field_name="Competência")

    if not re.match(r"^\d{4}-\d{2}$", competencia):
        raise ValidationError("Competência deve estar no formato YYYY-MM")

    try:
        ano, mes = competencia.split("-")
        ano, mes = int(ano), int(mes)

        if ano < 2000 or ano > 2050:
            raise ValidationError("Ano deve estar entre 2000 e 2050")

        if mes < 1 or mes > 12:
            raise ValidationError("Mês deve estar entre 01 e 12")

    except ValueError:
        raise ValidationError("Competência inválida")

    return competencia


def validate_pagination(page: int, per_page: int) -> tuple[int, int]:
    """Valida parâmetros de paginação."""
    if page < 1:
        page = 1
    if page > 999999:
        page = 999999

    if per_page < 0:
        per_page = 50
    elif per_page > 1000:
        per_page = 1000

    return page, per_page


def sanitize_search_term(search_term: Optional[str]) -> Optional[str]:
    """Sanitiza termo de busca."""
    if not search_term:
        return None

    search_term = sanitize_input(search_term, max_length=100, field_name="Termo de busca")

    # Remove caracteres perigosos básicos
    dangerous_sql = ["'", '"', ";", "--"]
    for dangerous in dangerous_sql:
        search_term = search_term.replace(dangerous, "")

    return search_term.strip() if search_term.strip() else None


def log_security_event(event_type: str, details: str, user_id: Optional[str] = None):
    """Registra eventos de segurança."""
    logger.warning(f"SECURITY_EVENT: {event_type} - User: {user_id or 'Unknown'} - Details: {details}")
