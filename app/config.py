from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DOWNLOADS_DIR = DATA_DIR / "downloads"
PROCESSED_DIR = DATA_DIR / "processed"
DOSSIES_DIR = DATA_DIR / "dossies"
LOGS_DIR = BASE_DIR / "logs"
DB_PATH = DATA_DIR / "pid.db"
PLAYWRIGHT_USER_DATA_DIR = str(DATA_DIR / "browser_profile")

TRELLO_BOARD_URL: str = os.getenv("TRELLO_BOARD_URL", "")
TRELLO_LISTS: list[str] = [
    s.strip() for s in os.getenv("TRELLO_LISTS", "Novo PID,Em análise").split(",")
]

USE_TEXTRACT_FALLBACK: bool = os.getenv("USE_TEXTRACT_FALLBACK", "true").lower() == "true"
TEXTRACT_MIN_CONFIDENCE: float = float(os.getenv("TEXTRACT_MIN_CONFIDENCE", "0.75"))
TEXTRACT_MAX_PAGES_PER_MONTH: int = int(os.getenv("TEXTRACT_MAX_PAGES_PER_MONTH", "3000"))
TEXTRACT_DAILY_SOFT_LIMIT: int = int(os.getenv("TEXTRACT_DAILY_SOFT_LIMIT", "150"))

AWS_PROFILE: str | None = os.getenv("AWS_PROFILE") or None
AWS_DEFAULT_REGION: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

PORTAL_URL: str = os.getenv("PORTAL_URL", "")

# Mapeamento de campos para seletores CSS do Portal do Advogado.
# Ajuste os seletores após inspecionar o formulário real do portal.
PORTAL_FIELD_MAP: dict[str, str] = {
    "nome_completo": "#nome_completo",
    "cpf": "#cpf",
    "rg": "#rg",
    "data_nascimento": "#data_nascimento",
    "endereco": "#endereco",
    "cep": "#cep",
    "banco": "#banco",
    "agencia": "#agencia",
    "conta": "#conta",
    "tipo_conta": "#tipo_conta",
    "titularidade": "#titularidade",
}

ALL_FIELD_NAMES = list(PORTAL_FIELD_MAP.keys())


def ensure_dirs() -> None:
    for d in [
        DATA_DIR,
        DOWNLOADS_DIR,
        PROCESSED_DIR,
        DOSSIES_DIR,
        LOGS_DIR,
        Path(PLAYWRIGHT_USER_DATA_DIR),
    ]:
        d.mkdir(parents=True, exist_ok=True)
