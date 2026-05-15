"""Extração de campos por regex no texto OCR."""
import re
from typing import Optional

from app.models import Field


# Regex por campo
_PATTERNS: dict[str, str] = {
    "cpf": r'\d{3}\.?\d{3}\.?\d{3}[-\s]?\d{2}',
    "rg": r'\d{1,2}\.?\d{3}\.?\d{3}[-/]?[\dXx]',
    "data_nascimento": r'\b\d{2}[/\-\.]\d{2}[/\-\.]\d{4}\b',
    "cep": r'\b\d{5}[-\s]?\d{3}\b',
    "banco": (
        r'(?i)(?:banco|bank)\s+[\w\s]{2,30}|'
        r'(?i)(?:bradesco|itaú|itau|caixa|banco do brasil|santander|nubank|inter|c6 bank)'
    ),
    "agencia": r'(?i)agência[:\s]*([\d\-]{4,6})|ag[:\s#\.]*([\d\-]{4,6})',
    "conta": r'(?i)(?:conta|c\/c|c\/p)[:\s#\.]*([\d\-]{5,15})',
    "tipo_conta": r'(?i)(conta corrente|conta poupança|poupança|corrente)',
    "nome_completo": (
        r'(?i)(?:nome completo|nome do titular|titular|nome)[:\s]+'
        r'([A-ZÀ-Ü][a-zà-ü]+(?:\s+[A-ZÀ-Ü][a-zà-ü]+){1,6})'
    ),
    "titularidade": r'(?i)(titular(?:idade)?|beneficiário|beneficiario)',
}

# Campos cujo valor é capturado em grupo de captura
_GROUP_FIELDS = {"agencia", "conta", "nome_completo"}


def extract_fields(
    ocr_text: str,
    document_id: int,
    case_id: int,
) -> list[Field]:
    """Extrai campos do texto OCR. Inclui campo vazio para os não encontrados."""
    found: dict[str, list[tuple[str, float]]] = {k: [] for k in _PATTERNS}

    for field_name, pattern in _PATTERNS.items():
        for m in re.finditer(pattern, ocr_text, re.IGNORECASE | re.UNICODE):
            if field_name in _GROUP_FIELDS:
                value = next(
                    (g for g in m.groups() if g), m.group(0)
                ).strip()
            else:
                value = m.group(0).strip()

            if not value:
                continue

            # Valida CPF com checksum
            if field_name == "cpf" and not _cpf_valid(value):
                continue

            score = min(1.0, len(value) / 20)
            found[field_name].append((value, score))

    fields: list[Field] = []
    for field_name, matches in found.items():
        if not matches:
            # Campo não encontrado — inserir vazio para visibilidade na UI
            fields.append(
                Field(
                    case_id=case_id,
                    document_id=document_id,
                    field_name=field_name,
                    field_value="",
                    source="ocr",
                    score=0.0,
                    status="pendente",
                )
            )
        else:
            for value, score in matches:
                fields.append(
                    Field(
                        case_id=case_id,
                        document_id=document_id,
                        field_name=field_name,
                        field_value=value,
                        source="ocr",
                        score=score,
                        status="pendente",
                    )
                )

    return fields


def _cpf_valid(cpf_raw: str) -> bool:
    """Valida CPF pelo cálculo mod-11."""
    digits = re.sub(r'\D', '', cpf_raw)
    if len(digits) != 11 or len(set(digits)) == 1:
        return False

    def _check(d: str, n: int) -> bool:
        total = sum(int(d[i]) * (n - i) for i in range(n - 1))
        rem = (total * 10) % 11
        rem = 0 if rem == 10 else rem
        return rem == int(d[n - 1])

    return _check(digits, 10) and _check(digits, 11)
