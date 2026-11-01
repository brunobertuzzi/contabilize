# ==============================================================================
# CONTABILIZE - Multi-Stage Dockerfile (TypeScript Build + Python 3.12 Runtime)
# ==============================================================================

# ------------------------------------------------------------------------------
# Estágio 1: Build do Frontend (TypeScript & esbuild)
# ------------------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder

WORKDIR /app

# Copia manifestos de dependências do Node
COPY package.json package-lock.json* ./
RUN npm ci || npm install

# Copia código-fonte TypeScript e arquivos de configuração
COPY tsconfig.json build.js ./
COPY src/ ./src/
COPY static/ ./static/

# Compila o TypeScript para bundles JavaScript minificados
RUN npm run build

# ------------------------------------------------------------------------------
# Estágio 2: Ambiente de Execução Python
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runner

# Metadados e variáveis de ambiente
LABEL maintainer="Contabilize Team"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    FLASK_DEBUG=0

WORKDIR /app

# Instala dependências de sistema mínimas (curl para healthcheck e bibliotecas C)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Cria usuário não-privilegiado para execução segura
RUN useradd -m -u 1001 appuser

# Copia arquivos da aplicação
COPY . .

# Copia os assets JavaScript compilados no Estágio 1
COPY --from=frontend-builder /app/static/js/ /app/static/js/

# Cria e ajusta permissões dos diretórios de runtime
RUN mkdir -p /app/database /app/uploads \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

# Verificação de integridade do container
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Inicialização com Gunicorn (preload inicializa o app uma vez antes dos workers)
CMD ["gunicorn", "--preload", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120", "app:create_app()"]
