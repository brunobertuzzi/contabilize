# Contabilize

Aplicação desktop para importação, análise e gestão de dados fiscais do SPED (Sistema Público de Escrituração Digital), desenvolvida em Python com Flask e PyWebView, integrando back-end e interface gráfica em um único ambiente.

**Desenvolvido para simplificar a gestão contábil**

## Funcionalidades

- Interface gráfica web moderna com integração PyWebView
- Processamento e análise de arquivos SPED Fiscal
- Sistema de autenticação e autorização de usuários
- Relatórios de vendas e análise de CFOP
- Classificação automática de produtos por similaridade (Fuzzy Matching)
- Análise de inconsistências de produtos por NCM
- Gestão de acumuladores fiscais
- Implementação de middleware de segurança
- Funcionalidade automatizada de backup e restauração
- Validação de dados fiscais

## Stack Tecnológico

- Backend: Flask 3.1.1, SQLAlchemy 2.0.41
- Frontend: Bootstrap 5.3, JavaScript
- Interface: PyWebView 5.4
- Banco de dados: SQLite
- Segurança: Passlib, BCrypt, Flask-WTF
- Migrações: Alembic 1.13.1
- Testes: Pytest, Selenium

## Requisitos

- Python 3.8+
- Gerenciador de pacotes pip

## Instalação

```bash
git clone https://github.com/brunobertuzzi/contabilize.git
cd contabilize
pip install -r requirements.txt
python app.py
```

A aplicação abrirá em uma janela desktop. Configure o usuário administrador inicial na primeira execução.

## Estrutura do Projeto

```
contabilize/
├── app.py                 # Aplicação principal Flask
├── gui.py                 # Interface PyWebView
├── requirements.txt       # Dependências Python
├── scripts/               # Módulos principais
│   ├── config.py          # Configuração da aplicação
│   ├── database.py        # Modelos e conexão do banco
│   ├── sped.py            # Rotas e lógica SPED
│   ├── sped_service.py    # Serviços de processamento SPED
│   ├── product_analyzer.py# Análise de produtos por similaridade
│   ├── user_management.py # Sistema de gestão de usuários
│   ├── backup_restore.py  # Sistema de backup
│   ├── validators.py      # Validadores de dados fiscais
│   ├── initialization.py  # Inicialização do sistema
│   ├── auth_decorators.py # Decoradores de autenticação
│   └── security_middleware.py # Middleware de segurança
├── templates/             # Templates HTML
│   ├── index.html         # Dashboard principal
│   ├── sped.html          # Análise SPED
│   ├── settings.html      # Configurações do sistema
│   ├── login.html         # Tela de login
│   ├── setup_admin.html   # Configuração inicial do admin
│   ├── about.html         # Sobre o sistema
│   └── sidebar.html       # Componente de navegação
├── static/                # Arquivos estáticos
│   ├── js/                # Scripts JavaScript
│   └── css/               # Estilos CSS
├── uploads/               # Uploads de arquivos
├── backups/               # Backups do sistema
└── logs/                  # Logs da aplicação
```

## Uso

Execute a aplicação e configure o usuário administrador inicial. Importe arquivos SPED através da interface web para processamento e análise. Utilize a classificação automática para sugerir acumuladores aos produtos e analise inconsistências de NCM.

## Logging

Logs armazenados em `logs/app.log` com rotação automática (máximo 10MB, 5 arquivos de backup).