# Contabilize — Sistema de Gestão Fiscal SPED

Aplicação desktop para importação, análise e gestão de dados fiscais do SPED (Sistema Público de Escrituração Digital). Desenvolvida em **Python** com **Flask** e interface gráfica via **PyWebView**.

---

## Funcionalidades

### Autenticação
- Login seguro com controle de tentativas.
- Bloqueio temporário após 5 falhas consecutivas (15 minutos).
- Controle de acesso por nível (administrador e usuário).
- Sessões com cookies HTTPOnly.

### SPED Fiscal
- Importação de arquivos `.txt` do SPED Fiscal.  
- Gestão de produtos e agrupamento por categorias fiscais.  
- Controle de CFOPs e acumuladores.  
- Relatórios de vendas, acumuladores e CFOPs.  
- Filtros avançados por produto, acumulador e competência.

### Administração
- Backup e restauração automática do banco de dados.  
- Gerenciamento completo de usuários (CRUD).  
- Logs de auditoria e monitoramento de operações.  
- Configurações de segurança e middleware de validação.

### Segurança
- Validação e sanitização de entradas.  
- Proteção contra SQL Injection.  
- Headers de segurança (CSP, HSTS, X-Frame-Options).  
- Rate limiting em endpoints sensíveis.  
- Registro de eventos de segurança.

---

## Instalação e Configuração

### Requisitos
- Python 3.8+
- pip (gerenciador de pacotes)

### Passos

1. **Clone o repositório**
   ```bash
   git clone <url-do-repositorio>
   cd contabilize
   ```

2. **Instale as dependências**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure as variáveis de ambiente**
   Crie um arquivo `.env` na raiz:
   ```env
   SECRET_KEY=sua_chave_secreta
   FLASK_DEBUG=0
   DEFAULT_ADMIN_USERNAME=admin
   DEFAULT_ADMIN_PASSWORD=sua_senha
   LOG_LEVEL=INFO
   ```

4. **Execute o sistema**
   ```bash
   python app.py
   ```

---

## Configuração do Usuário Administrador

**Via `.env` (recomendado):**
```env
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=sua_senha
```

**Ou via código (`scripts/config.py`):**
```python
DEFAULT_ADMIN_USERNAME = os.environ.get('DEFAULT_ADMIN_USERNAME', 'admin')
DEFAULT_ADMIN_PASSWORD = os.environ.get('DEFAULT_ADMIN_PASSWORD')
```

**Importante:**
- Altere as credenciais padrão antes do uso em produção.  
- Utilize senhas fortes.  
- O administrador é criado automaticamente na primeira execução.

---

## Estrutura do Projeto

```
contabilize/
├── app.py
├── gui.py
├── requirements.txt
├── scripts/
│   ├── auth_decorators.py
│   ├── backup_restore.py
│   ├── config.py
│   ├── database.py
│   ├── initialization.py
│   ├── security_middleware.py
│   ├── sped.py
│   ├── sped_service.py
│   ├── user_management.py
│   └── validators.py
├── templates/
├── static/js/
├── database/
├── backups/
├── logs/
└── uploads/
```

---

## Banco de Dados

SQLite com tabelas principais:
- `users` — Usuários.  
- `documento_fiscal_sped` — Documentos fiscais.  
- `produtos_sped` — Produtos cadastrados.  
- `vendas_sped` — Itens de venda.  
- `acumuladores` — Agrupadores de produtos.  
- `cfops` — Códigos fiscais.

---

## Uso

### Primeiro acesso
1. Execute `python app.py`.  
2. Faça login com as credenciais de administrador.  
3. Crie novos usuários em “Configurações”.

### Importar SPED
1. Vá em “SPED Fiscal”.  
2. Escolha o arquivo `.txt`.  
3. Clique em “Importar”.

### Acumuladores
1. Acesse “Produtos > Acumuladores”.  
2. Crie acumuladores e associe produtos.

### Relatórios
1. Acesse “Relatórios”.  
2. Selecione a competência desejada.  
3. Visualize vendas, acumuladores ou CFOPs.

---

## Configurações Avançadas

### Backup
- Geração automática de backups.  
- Limite configurável de 10 arquivos.  
- Diretório: `backups/`.

### Logs
- Arquivos rotativos (10 MB, até 5 backups).  
- Diretório: `logs/`.

### Segurança
- Sessões expiram em 12 horas.  
- Limite de requisições configurável.  
- Validação rigorosa em todas as entradas.

---

## Desenvolvimento

**Modo debug:**
```bash
FLASK_DEBUG=1
python app.py
```

**Testes:**
```bash
pytest
```

---

## Logs e Auditoria

Registro detalhado de:
- Tentativas de login.  
- Operações CRUD.  
- Eventos de segurança.  
- Erros e exceções.

---

## Considerações de Segurança

1. Alterar credenciais padrão.  
2. Utilizar HTTPS em produção.  
3. Realizar backups regulares.  
4. Monitorar logs de segurança.  
5. Atualizar dependências.

---

## Suporte

- Abra uma issue no repositório.  
- Verifique os logs em `logs/app.log`.  
- Consulte a documentação do projeto.

**Desenvolvido para facilitar a vida dos contadores**