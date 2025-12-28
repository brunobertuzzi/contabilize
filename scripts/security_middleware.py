"""
Middleware de Segurança Simplificado
===================================

Implementa funcionalidades básicas de segurança necessárias para a aplicação.
"""

import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from functools import wraps
from threading import Lock

from flask import current_app, jsonify, request
from flask_login import current_user

logger = logging.getLogger(__name__)

# Armazenamento simples para rate limiting com limpeza periódica
rate_limit_storage = defaultdict(lambda: deque())
_cleanup_lock = Lock()
_last_cleanup = time.time()


def _cleanup_old_entries():
    """Remove entradas antigas do rate_limit_storage para evitar memory leak."""
    global _last_cleanup
    now = time.time()

    # Limpa a cada 5 minutos
    if now - _last_cleanup < 300:
        return

    with _cleanup_lock:
        # Double-check após adquirir o lock
        if now - _last_cleanup < 300:
            return

        cutoff = datetime.now() - timedelta(hours=1)
        keys_to_delete = []

        for key in list(rate_limit_storage.keys()):
            # Remove entradas antigas da deque
            while rate_limit_storage[key] and rate_limit_storage[key][0] < cutoff:
                rate_limit_storage[key].popleft()
            # Marca para remoção se vazia
            if not rate_limit_storage[key]:
                keys_to_delete.append(key)

        # Remove chaves vazias
        for key in keys_to_delete:
            del rate_limit_storage[key]

        _last_cleanup = now
        if keys_to_delete:
            logger.debug(
                f"Rate limit cleanup: {len(keys_to_delete)} entradas removidas"
            )


def rate_limit(max_requests: int = 60, window_minutes: int = 1):
    """
    Decorator para implementar rate limiting básico.
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Limpa entradas antigas periodicamente
            _cleanup_old_entries()

            client_id = request.remote_addr
            if current_user.is_authenticated:
                client_id += f"_user_{current_user.id}"

            now = datetime.now()
            window_start = now - timedelta(minutes=window_minutes)

            # Remove requisições antigas
            client_requests = rate_limit_storage[client_id]
            while client_requests and client_requests[0] < window_start:
                client_requests.popleft()

            # Verifica limite
            if len(client_requests) >= max_requests:
                logger.warning(f"Rate limit exceeded for {client_id}")
                return jsonify(
                    {
                        "success": False,
                        "error": "Muitas requisições. Tente novamente em alguns minutos.",
                    }
                ), 429

            client_requests.append(now)
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def apply_security_headers(response):
    """Aplica cabeçalhos de segurança em todas as respostas."""
    # Headers de segurança básicos (sempre aplicados)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Content Security Policy - diferenciada por ambiente
    if current_app.debug:
        # CSP mais permissiva para desenvolvimento
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob:; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net data:; "
            "img-src 'self' data: https://cdn.jsdelivr.net blob:; "
            "connect-src 'self';"
        )
    else:
        # CSP mais restritiva para produção
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            "img-src 'self' data: blob:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self';"
        )
        # HSTS apenas em produção
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    # Remove header do servidor
    response.headers.pop("Server", None)
    return response


def secure_api_endpoint(max_requests: int = 60, window_minutes: int = 1):
    """Decorator que aplica rate limiting."""
    return rate_limit(max_requests, window_minutes)
