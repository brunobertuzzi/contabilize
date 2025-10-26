# Contabilize

Aplicação desktop para importação, análise e gestão de dados fiscais do SPED (Sistema Público de Escrituração Digital), desenvolvida em Python com Flask e PyWebView, integrando back-end e interface gráfica em um único ambiente.

**Desenvolvido para simplificar a gestão contábil**

## Funcionalidades

- Interface gráfica web com integração PyWebView
- Processamento e análise de arquivos SPED Fiscal
- Sistema de autenticação e autorização de usuários
- Relatórios de vendas e análise de CFOP
- Implementação de middleware de segurança
- Funcionalidade automatizada de backup e restauração

## Stack Tecnológico

- Backend: Flask 3.1.1, SQLAlchemy 2.0.41
- Frontend: Bootstrap 5.3, JavaScript
- Interface: PyWebView 5.4
- Banco de dados: SQLite
- Segurança: Passlib, BCrypt
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
│   ├── user_management.py # Sistema de gestão de usuários
│   ├── backup_restore.py  # Sistema de backup
│   └── security_middleware.py # Middleware de segurança
├── templates/             # Templates HTML
├── static/                # Arquivos estáticos
├── uploads/               # Uploads de arquivos
├── backups/               # Backups do sistema
└── logs/                  # Logs da aplicação
```

## Uso

Execute a aplicação e configure o usuário administrador inicial. Importe arquivos SPED através da interface web para processamento e análise.

## Logging

Logs armazenados em `logs/app.log` com rotação automática (máximo 10MB, 5 arquivos de backup).