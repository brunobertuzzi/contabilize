# Contabilize

Aplicação web profissional para importação, processamento e conciliação de arquivos SPED Fiscal (EFD ICMS/IPI), desenvolvida em Python com Flask, SQLAlchemy, suporte a PostgreSQL e SQLite, conteinerização Docker e frontend moderno em TypeScript.

## Funcionalidades

- Processamento e importação de arquivos SPED Fiscal (registros 0000, 0200, C100 e C170)
- Suporte a múltiplos bancos de dados (**PostgreSQL** para produção corporativa ou **SQLite** para uso local)
- Isolamento de dados por empresa (multi-tenancy por CNPJ)
- Sugestão e classificação de produtos por similaridade (fuzzy matching)
- Análise de inconsistências cadastrais por NCM
- Relatórios de vendas e consolidação por competência fiscal
- Gestão de CFOPs e acumuladores fiscais
- Controle de usuários com autenticação e níveis de acesso (RBAC)
- Sistema de backup e restauração do banco de dados
- Interface web responsiva conteinerizada via Docker ou executável localmente

## Tecnologias

- **Backend:** Python 3.10+, Flask 3.1, SQLAlchemy 2.0, Gunicorn (WSGI)
- **Banco de Dados:** PostgreSQL 16 (produção/container) & SQLite 3 (local)
- **Frontend:** TypeScript, esbuild, Bootstrap 5.3 & JavaScript (ES2020)
- **Containerização:** Docker & Docker Compose (Multi-stage build)

## Requisitos

- Python 3.10 ou superior (para execução local)
- Gerenciador de pacotes pip
- Node.js 18+ e npm (para compilação TypeScript)
- *Recomendado:* Docker e Docker Compose (para subir a stack completa com PostgreSQL com 1 comando)

---

## Como Executar

### Opção 1: Via Docker Compose (Stack Completa com PostgreSQL)

A forma mais rápida e recomendada para rodar o projeto em produção ou desenvolvimento:

1. Clone o repositório e acesse a pasta:
```bash
git clone https://github.com/seu-usuario/contabilize.git
cd contabilize
```

2. Inicie a aplicação com Docker Compose:
```bash
docker compose up --build
```

O Docker construirá o frontend com TypeScript, configurará o PostgreSQL 16 com volume persistente e iniciará o servidor Gunicorn. Acesse em seu navegador em **http://localhost:5000**.

Para parar os containers:
```bash
docker compose down
```

---

### Opção 2: Execução Local (Python + SQLite ou PostgreSQL)

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/contabilize.git
cd contabilize
```

2. Crie e ative um ambiente virtual:
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

3. Instale as dependências Python:
```bash
pip install -r requirements.txt
```

4. Instale as dependências Frontend e compile o TypeScript:
```bash
npm install
npm run build
```

> Durante o desenvolvimento do frontend, você pode usar `npm run watch` para recompilar os arquivos TypeScript automaticamente.

5. Configure o arquivo de ambiente:
```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```
*(Por padrão, se `DATABASE_URL` não for especificado no `.env`, o sistema usa SQLite local em `database/main.db`. Caso queira apontar para um PostgreSQL externo, basta preencher a variável `DATABASE_URL`)*.

6. Inicie o servidor da aplicação:
```bash
python app.py
```

Ou com Gunicorn em ambientes Linux:
```bash
gunicorn "app:create_app()" --bind 0.0.0.0:5000 --workers 2 --threads 4
```

Acesse em seu navegador em **http://localhost:5000**. No primeiro acesso, o sistema solicitará o cadastro do usuário administrador inicial em `/setup-admin`.

---

## Estrutura do Projeto

```
contabilize/
├── Dockerfile              # Imagem Docker multi-stage (Node TypeScript + Python Gunicorn)
├── docker-compose.yml      # Orquestração de serviços (Web Flask + PostgreSQL 16)
├── .dockerignore           # Arquivos ignorados no contexto de build do Docker
├── .env.example            # Modelo de variáveis de ambiente
├── app.py                  # Ponto de entrada da aplicação Web
├── requirements.txt        # Dependências Python essenciais (Flask, SQLAlchemy, psycopg2, Gunicorn)
├── package.json            # Dependências e scripts TypeScript/Frontend
├── tsconfig.json           # Configuração do compilador TypeScript
├── build.js                # Script de bundling esbuild
├── database/               # Armazenamento do banco local SQLite (main.db)
├── uploads/                # Diretório para upload de arquivos SPED
├── src/                    # Código-fonte Frontend em TypeScript
│   ├── main.ts             # Lógica global da aplicação (sidebar, modais, UI)
│   ├── sped.ts             # Workbench fiscal SPED e conciliação
│   └── types/              # Interfaces e tipagem estrita do domínio fiscal
│       ├── common.ts       # Tipos comuns e respostas de API
│       ├── globals.d.ts    # Declarações para Bootstrap, Chart.js e Window
│       ├── index.ts        # Barrel export dos tipos
│       └── sped.ts         # Modelos de dados SPED (CFOP, Acumulador, Produto, etc.)
├── scripts/                # Lógica de negócio e serviços Python
│   ├── auth_decorators.py  # Decoradores de controle de acesso
│   ├── backup_restore.py   # Backup e restauração do banco
│   ├── config.py           # Configurações gerais (PostgreSQL / SQLite, segurança, logs)
│   ├── database.py         # Modelos ORM, conexão multiplataforma e helpers SQL
│   ├── empresa_service.py  # Gestão de empresas e multi-tenancy
│   ├── initialization.py   # Inicialização e validação de administrador
│   ├── product_analyzer.py # Análise e similaridade de produtos
│   ├── security_middleware.py # Headers de segurança e controle de requisições
│   ├── sped.py             # Rotas e endpoints da API SPED
│   ├── sped_service.py     # Processamento e conciliação de arquivos SPED
│   ├── user_management.py  # Gerenciamento de usuários
│   └── validators.py       # Validação de dados fiscais
├── static/                 # Arquivos estáticos servidos pelo Flask
│   ├── css/                # Folhas de estilo
│   └── js/                 # Bundles JavaScript compilados e sourcemaps
└── templates/              # Templates HTML (Jinja2)
    ├── about.html          # Informações do sistema
    ├── error.html          # Página de erro
    ├── index.html          # Painel principal
    ├── login.html          # Tela de autenticação
    ├── settings.html       # Configurações do sistema
    ├── setup_admin.html    # Cadastro inicial de administrador
    ├── sidebar.html        # Menu lateral
    ├── sped.html           # Workbench de conciliação SPED
    └── topbar.html         # Barra superior com empresa ativa
```

## Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.
