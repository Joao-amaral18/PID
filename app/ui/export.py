"""Página de exportação de dossiê em PDF."""
import io
from pathlib import Path

import fitz
import streamlit as st
from PIL import Image

from app.database import list_cases, get_case, list_documents_for_case, list_fields_for_case, list_logs


def render() -> None:
    st.title("Exportar Dossiê")

    cases = list_cases()
    if not cases:
        st.info("Nenhum caso disponível.")
        return

    case_options = {c.title: c.id for c in cases}
    selected_title = st.selectbox("Selecionar caso", list(case_options.keys()))
    case_id = case_options[selected_title]

    approved_only = st.checkbox(
        "Incluir apenas documentos aprovados", value=True
    )

    if st.button("Gerar Dossiê PDF"):
        with st.spinner("Gerando PDF..."):
            try:
                pdf_bytes = _build_dossier(case_id, approved_only)
                case = get_case(case_id)
                filename = f"dossie_{case_id}_{case.title[:30]}.pdf".replace(" ", "_")
                st.download_button(
                    label="Baixar PDF",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                )
                st.success("Dossiê gerado com sucesso.")
            except Exception as exc:
                st.error(f"Erro ao gerar dossiê: {exc}")


def _build_dossier(case_id: int, approved_only: bool) -> bytes:
    case = get_case(case_id)
    fields = list_fields_for_case(case_id)
    documents = list_documents_for_case(case_id)
    logs = list_logs(case_id=case_id, limit=50)

    if approved_only:
        documents = [d for d in documents if d.validation_status == "aprovado"]

    doc = fitz.open()

    # Página 1: Sumário do caso
    page = doc.new_page(width=595, height=842)
    _write_text(page, "DOSSIÊ PID — SAMARCO", 50, 50, fontsize=18, bold=True)
    _write_text(page, case.title, 50, 85, fontsize=13)
    _write_text(page, f"Status: {case.status}", 50, 110, fontsize=10)
    if case.protocol:
        _write_text(page, f"Protocolo: {case.protocol}", 50, 125, fontsize=10)
    _write_text(page, f"ID Trello: {case.trello_card_id}", 50, 140, fontsize=9)

    # Campos
    y = 170
    _write_text(page, "CAMPOS EXTRAÍDOS", 50, y, fontsize=12, bold=True)
    y += 20
    approved_fields = [
        f for f in fields if f.status in ("aprovado", "corrigido")
    ]
    for f in approved_fields:
        line = f"{f.field_name}: {f.field_value}"
        _write_text(page, line, 60, y, fontsize=9)
        y += 14
        if y > 800:
            page = doc.new_page(width=595, height=842)
            y = 50

    # Logs recentes
    if logs:
        y += 10
        _write_text(page, "LOGS RECENTES", 50, y, fontsize=12, bold=True)
        y += 18
        for log in logs[:20]:
            line = f"[{log.level}] {log.action}: {log.details[:80]}"
            _write_text(page, line, 60, y, fontsize=8)
            y += 12
            if y > 800:
                page = doc.new_page(width=595, height=842)
                y = 50

    # Páginas de documentos
    for document in documents:
        fpath = Path(document.filepath)
        if not fpath.exists():
            continue

        ext = fpath.suffix.lower()
        if ext in (".png", ".jpg", ".jpeg"):
            _insert_image_page(doc, document, str(fpath))
        elif ext == ".pdf":
            _insert_pdf_pages(doc, document, str(fpath))

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def _write_text(
    page: fitz.Page,
    text: str,
    x: float,
    y: float,
    fontsize: int = 10,
    bold: bool = False,
) -> None:
    font = "helv" if not bold else "helvB"
    page.insert_text(
        fitz.Point(x, y), text, fontsize=fontsize, fontname=font
    )


def _insert_image_page(doc: fitz.Document, document, filepath: str) -> None:
    page = doc.new_page(width=595, height=842)
    _write_text(
        page,
        f"Documento: {document.filename} | Tipo: {document.doc_type}",
        50, 30, fontsize=9,
    )
    rect = fitz.Rect(50, 50, 545, 780)
    page.insert_image(rect, filename=filepath)


def _insert_pdf_pages(doc: fitz.Document, document, filepath: str) -> None:
    try:
        src = fitz.open(filepath)
        for src_page in src:
            mat = fitz.Matrix(0.8, 0.8)
            pix = src_page.get_pixmap(matrix=mat)
            page = doc.new_page(width=pix.w, height=pix.h)
            page.insert_image(fitz.Rect(0, 0, pix.w, pix.h), pixmap=pix)
        src.close()
    except Exception:
        pass
