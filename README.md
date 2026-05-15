# PID Automation — Sistema de Automação de Cadastro Samarco

Sistema local em Python para automação do fluxo operacional de cadastro de casos PID (Programa de Indenização Direta) Samarco.

## Visão Geral

```
Trello (Playwright) → Download de Anexos → OCR (Tesseract / Textract) → Extração de Campos → Validação Humana (Streamlit) → Preenchimento no Portal do Advogado (Playwright)
```

## Pré-requisitos

- Python 3.11+
- Tesseract OCR ≥ 4.0 com pacote de idioma português
- Conta AWS com permissão `textract:DetectDocumentText` (opcional, usado como fallback)
- Acesso ao Trello (sem API key — login via browser)
- Acesso ao Portal do Advogado Samarco

## Instalação

```bash
# 1. Clonar repositório e criar ambiente virtual
git clone <repo-url>
cd pid-automation
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Instalar dependências Python
pip install -r requirements.txt

# 3. Instalar navegador Playwright
playwright install chromium

# 4. Instalar Tesseract (Ubuntu/Debian)
sudo apt-get install tesseract-ocr tesseract-ocr-por

# macOS (Homebrew)
# brew install tesseract tesseract-lang
```

## Configuração

```bash
# 1. Copiar arquivo de exemplo
cp .env.example .env

# 2. Editar .env com seus valores
nano .env
```

Variáveis obrigatórias:
- `TRELLO_BOARD_URL` — URL do board Trello (ex: `https://trello.com/b/ABC123/nome-board`)
- `PORTAL_URL` — URL do Portal do Advogado Samarco

Variáveis opcionais (Textract fallback):
```bash
# Configurar perfil AWS CLI
aws configure --profile pid-local
# Informar: Access Key ID, Secret Key, região us-east-1
```

Política IAM mínima necessária:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["textract:DetectDocumentText"],
    "Resource": "*"
  }]
}
```

## Execução

```bash
streamlit run app/main.py
```

O sistema abrirá em `http://localhost:8501`.

## Fluxo Operacional

1. **Dashboard** → Clique em "Sincronizar Trello"
   - Um browser se abre; faça login no Trello se solicitado
   - Cards das listas configuradas são baixados junto com os anexos
   - OCR é executado automaticamente

2. **Casos** → Selecione um caso para revisar

3. **Detalhe do Caso** → Aba "Campos"
   - Revise os campos extraídos pelo OCR
   - Corrija valores incorretos diretamente na tabela
   - Clique "Aprovar Todos" quando satisfeito

4. **Detalhe do Caso** → Aba "Portal"
   - Clique "Abrir Portal e Preencher"
   - Um browser abre o Portal do Advogado
   - Faça autenticação via certificado digital (manual)
   - O sistema preenche os campos automaticamente
   - **O envio final é sempre manual** — revise e submeta você mesmo
   - Registre o protocolo recebido no campo indicado

5. **Exportar Dossiê** → Gere e baixe o PDF do caso

## Monitoramento de Custo Textract

O Textract é usado apenas como fallback quando o Tesseract local retorna baixa confiança (< 75%).
Free tier AWS: 1.000 páginas/mês para `DetectDocumentText`.

```bash
# Ver uso total por engine
sqlite3 data/pid.db "SELECT engine, SUM(pages) AS pages FROM ocr_usage GROUP BY engine;"

# Ver uso Textract no mês atual
sqlite3 data/pid.db "SELECT SUM(pages) FROM ocr_usage WHERE engine='textract' AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now');"
```

## Verificação do Ambiente

```bash
# Testar importações
python -c "import streamlit, pytesseract, cv2, fitz, PIL, boto3, dotenv; from playwright.sync_api import sync_playwright; print('OK')"

# Testar Tesseract
tesseract --version

# Inicializar banco
python -c "from app.database import run_migrations; run_migrations(); print('Banco OK')"
sqlite3 data/pid.db ".tables"
# Esperado: ocr_usage  pid_cases  pid_documents  pid_fields  pid_logs
```

## Estrutura do Projeto

```
pid-automation/
├── app/
│   ├── main.py               # Entry point Streamlit
│   ├── config.py             # Configuração centralizada
│   ├── database.py           # SQLite CRUD
│   ├── models.py             # Dataclasses
│   ├── trello/               # Scraper Trello (Playwright)
│   ├── ocr/                  # Pipeline OCR
│   ├── portal/               # Bot Portal do Advogado
│   ├── validation/           # Regras de validação
│   └── ui/                   # Páginas Streamlit
├── data/                     # Dados locais (não commitados)
├── logs/                     # Logs de operação
├── .env.example
├── requirements.txt
└── README.md
```
