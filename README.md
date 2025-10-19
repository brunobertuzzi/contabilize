# 📊 Contabilize

Aplicação desktop para importação, análise e gestão de dados fiscais do SPED (Sistema Público de Escrituração Digital), desenvolvida em Python com Flask e PyWebView, integrando back-end e interface gráfica em um único ambiente.

## 🚀 Características

- **Interface Gráfica Moderna**: Interface web responsiva com PyWebView
- **Processamento SPED**: Importação e análise de arquivos SPED Fiscal
- **Gestão de Usuários**: Sistema completo de autenticação e autorização
- **Relatórios Avançados**: Relatórios de vendas, CFOPs e análises fiscais
- **Segurança Robusta**: Implementação de melhores práticas de segurança
- **Backup Automático**: Sistema de backup e restauração de dados

## 🛠️ Tecnologias

- **Backend**: Flask 3.1.1 + SQLAlchemy 2.0.41
- **Frontend**: Bootstrap 5.3 + JavaScript
- **Interface**: PyWebView 5.4
- **Banco de Dados**: SQLite
- **Segurança**: Passlib + BCrypt
- **Testes**: Pytest + Selenium

## 📋 Pré-requisitos

- Python 3.8+
- pip (gerenciador de pacotes Python)

## ⚡ Instalação Rápida

1. **Clone o repositório**
```bash
git clone https://github.com/seu-usuario/contabilize.git
cd contabilize
```

2. **Instale as dependências**
```bash
pip install -r requirements.txt
```

3. **Execute a aplicação**
```bash
python app.py
```

4. **Acesse o sistema**
   - A aplicação abrirá automaticamente em uma janela desktop
   - Configure o primeiro usuário administrador no setup inicial

## 🏗️ Estrutura do Projeto

```
contabilize/
├── app.py                 # Aplicação principal Flask
├── gui.py                 # Interface gráfica PyWebView
├── requirements.txt       # Dependências Python
├── .gitignore            # Arquivos ignorados pelo Git
├── .secret_key           # Chave secreta da aplicação
├── database/             # Banco de dados SQLite
│   └── main.db
├── scripts/              # Módulos principais
│   ├── config.py         # Configurações da aplicação
│   ├── database.py       # Modelos e conexão do banco
│   ├── sped.py           # Rotas e lógica SPED
│   ├── sped_service.py   # Serviços de processamento SPED
│   ├── user_management.py # Gestão de usuários
│   ├── backup_restore.py # Sistema de backup
│   └── security_middleware.py # Middleware de segurança
├── templates/            # Templates HTML
│   ├── index.html
│   ├── login.html
│   ├── sped.html
│   └── settings.html
├── static/               # Arquivos estáticos
│   ├── css/
│   └── js/
├── uploads/              # Arquivos enviados
├── backups/              # Backups do sistema
└── logs/                 # Logs da aplicação
```

## 🔧 Configuração

### Configurações Principais

As configurações estão centralizadas em `scripts/config.py`:

- **Segurança**: Configurações de sessão, cookies e autenticação
- **Banco de Dados**: Configurações SQLite e SQLAlchemy
- **Logs**: Sistema de rotação de logs
- **Upload**: Limites e tipos de arquivo permitidos

## 📊 Funcionalidades

### 🔐 Sistema de Autenticação
- Login seguro com proteção contra força bruta
- Gestão de usuários e permissões
- Sessões seguras com timeout automático

### 📁 Processamento SPED
- Importação de arquivos SPED Fiscal
- Análise automática de produtos e CFOPs
- Gestão de acumuladores fiscais
- Relatórios de vendas por competência

### 📈 Relatórios
- **Relatório de Vendas**: Análise por período e acumulador
- **Relatório CFOP**: Breakdown por código fiscal
- **Análise de Produtos**: Gestão e categorização

### 🛡️ Segurança
- Headers de segurança HTTP
- Proteção CSRF
- Rate limiting em APIs
- Logs de auditoria completos

## 🚀 Uso

### Primeiro Acesso
1. Execute a aplicação
2. Configure o usuário administrador inicial
3. Faça login no sistema

### Importação SPED
1. Acesse a seção "SPED"
2. Clique em "Importar Arquivo"
3. Selecione seu arquivo SPED (.txt)
4. Aguarde o processamento

### Gestão de Usuários
1. Acesse "Configurações" (apenas administradores)
2. Adicione, edite ou remova usuários
3. Configure permissões de administrador

## 📦 Build e Deploy

## 🔒 Segurança

- ✅ Autenticação robusta com BCrypt
- ✅ Proteção contra ataques de força bruta
- ✅ Headers de segurança HTTP
- ✅ Validação de entrada rigorosa
- ✅ Logs de auditoria completos
- ✅ Sessões seguras com timeout

## 📝 Logs

Os logs são armazenados em `logs/app.log` com rotação automática:
- Máximo 10MB por arquivo
- Mantém 5 arquivos de backup
- Níveis: DEBUG, INFO, WARNING, ERROR

## 🔄 Backup

Sistema automático de backup:
- Backup do banco de dados
- Rotação automática (máximo 10 arquivos)
- Restauração via interface web

## 🆘 Suporte

- **Issues**: [GitHub Issues](https://github.com/seu-usuario/contabilize/issues)

## 📊 Status do Projeto

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Flask](https://img.shields.io/badge/flask-3.1.1-red.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)

---

**Desenvolvido com ❤️ para simplificar a gestão contábil**