"""OCR AWS Textract via Bytes — fallback quando Tesseract é insuficiente.

Arquivos permanecem locais; somente bytes temporários da página/imagem
são enviados para a AWS. Nenhum uso de S3.
"""
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import AWS_PROFILE, AWS_DEFAULT_REGION
from app.ocr.tesseract_engine import pdf_pages_as_png_bytes, image_as_png_bytes


def run(filepath: str) -> tuple[str, float, int]:
    """Executa OCR via Textract. Retorna (texto, confidence, n_paginas)."""
    ext = Path(filepath).suffix.lower()
    if ext == ".pdf":
        pages_bytes = pdf_pages_as_png_bytes(filepath)
    elif ext in (".png", ".jpg", ".jpeg"):
        pages_bytes = image_as_png_bytes(filepath)
    else:
        return "", 0.0, 0

    if not pages_bytes:
        return "", 0.0, 0

    client = _get_client()
    if client is None:
        return "", 0.0, 0

    all_text: list[str] = []
    all_conf: list[float] = []

    for png_bytes in pages_bytes:
        text, conf = _detect_page(client, png_bytes)
        all_text.append(text)
        all_conf.append(conf)

    combined = "\n\n".join(t for t in all_text if t)
    mean_conf = sum(all_conf) / len(all_conf) if all_conf else 0.0
    return combined, mean_conf, len(pages_bytes)


def _get_client() -> Optional[object]:
    """Cria cliente Textract preferência por AWS_PROFILE."""
    try:
        session = boto3.Session(
            profile_name=AWS_PROFILE or None,
            region_name=AWS_DEFAULT_REGION,
        )
        return session.client("textract")
    except Exception:
        return None


def _detect_page(client, png_bytes: bytes) -> tuple[str, float]:
    """Chama DetectDocumentText para uma única página em bytes."""
    try:
        response = client.detect_document_text(
            Document={"Bytes": png_bytes}
        )
    except (BotoCoreError, ClientError) as exc:
        import sys
        print(f"[textract_error] {exc}", file=sys.stderr)
        return "", 0.0

    lines: list[str] = []
    confs: list[float] = []
    for block in response.get("Blocks", []):
        if block.get("BlockType") == "LINE":
            text = block.get("Text", "").strip()
            conf = block.get("Confidence", 0.0)
            if text:
                lines.append(text)
                confs.append(conf / 100.0)

    text = "\n".join(lines)
    mean_conf = sum(confs) / len(confs) if confs else 0.0
    return text, mean_conf
