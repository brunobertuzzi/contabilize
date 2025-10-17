"""
Middleware de Segurança Simplificado
===================================

Implementa funcionalidades básicas de segurança necessárias para a aplicação.
"""

import logging
from functools import wraps
from collections import defaultdict, deque
from datetime import datetime, timedelta
from flask import request, jsonify, current_app
from flask_login import current_user

logger = logging.getLogger(__name__)

# Armazenamento simples para rate limiting
rate_limit_storage = defaultdict(lambda: deque())

def rate_limit(max_requests: int = 60, window_minutes: int = 1):
    """
    Decorator para implementar rate limiting básico.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
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
                return jsonify({
                    'success': False,
                    'error': 'Muitas requisições. Tente novamente em alguns minutos.'
                }), 429
            
            client_requests.append(now)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def apply_security_headers(response):
    """Aplica cabeçalhos de segurança básicos."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    if current_app.debug:
        response.headers['Content-Security-Policy'] = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob:; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net data:; "
            "img-src 'self' data: https://cdn.jsdelivr.net blob:; "
            "connect-src 'self';"
        )
    
    response.headers.pop('Server', None)
    return response

def secure_api_endpoint(max_requests: int = 60, window_minutes: int = 1):
    """Decorator que aplica rate limiting."""
    return rate_limit(max_requests, window_minutes)