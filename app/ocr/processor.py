"""Orquestrador OCR: Tesseract local → Textract (fallback).

Arquivos permanecem locais. Quando Textract é acionado, apenas bytes
temporarios da página/imagem são enviados para a AWS — sem S3.
"""
from pathlib import Path

from app.config import (
    USE_TEXTRACT_FALLBACK,
    TEXTRACT_MIN_CONFIDENCE,
    TEXTRACT_MAX_PAGES_PER_MONTH,
    TEXTRACT_DAILY_SOFT_LIMIT,
)
from app.database import (
    get_textract_usage_today,
    get_textract_usage_month,
    record_ocr_usage,
    insert_log,
)
from app.ocr import tesseract_engine, textract_engine
from app.ocr.tesseract_engine import pdf_page_count


def process_document(
    filepath: str,
    document_id: int | None = None,
) -> tuple[str, float, str]:
    """
    Processa um documento e retorna (ocr_text, confidence, engine_usada).
    engine_usada: 'tesseract' | 'textract'
    """
    # 1. Tesseract local
    text, conf = tesseract_engine.run(filepath)
    record_ocr_usage("tesseract", _count_pages(filepath), document_id)

    if conf >= TEXTRACT_MIN_CONFIDENCE or not USE_TEXTRACT_FALLBACK:
        insert_log(
            None,
            "ocr_tesseract",
            f"{Path(filepath).name} conf={conf:.2f}",
        )
        return text, conf, "tesseract"

    # 2. Verificar limites de custo antes de chamar Textract
    n_pages = _count_pages(filepath)
    monthly = get_textract_usage_month()
    daily = get_textract_usage_today()

    if monthly + n_pages > TEXTRACT_MAX_PAGES_PER_MONTH:
        insert_log(
            None,
            "textract_blocked_monthly",
            f"limite mensal atingido ({monthly}/{TEXTRACT_MAX_PAGES_PER_MONTH})",
            "warning",
        )
        return text, conf, "tesseract"

    if daily + n_pages > TEXTRACT_DAILY_SOFT_LIMIT:
        insert_log(
            None,
            "textract_blocked_daily",
            f"soft limit diário atingido ({daily}/{TEXTRACT_DAILY_SOFT_LIMIT})",
            "warning",
        )
        return text, conf, "tesseract"

    # 3. Textract
    tx_text, tx_conf, tx_pages = textract_engine.run(filepath)

    if tx_text:
        record_ocr_usage("textract", tx_pages, document_id)
        insert_log(
            None,
            "ocr_textract",
            f"{Path(filepath).name} conf={tx_conf:.2f} pages={tx_pages}",
        )
        return tx_text, tx_conf, "textract"

    # Textract falhou silenciosamente — usa Tesseract mesmo assim
    insert_log(
        None,
        "textract_fallback_failed",
        f"{Path(filepath).name} — usando resultado Tesseract",
        "warning",
    )
    return text, conf, "tesseract"


def _count_pages(filepath: str) -> int:
    ext = Path(filepath).suffix.lower()
    if ext == ".pdf":
        return max(1, pdf_page_count(filepath))
    return 1
