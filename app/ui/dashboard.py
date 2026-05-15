"""Página Dashboard: métricas gerais e sincronização com Trello."""
import threading
from typing import Any

import streamlit as st

from app.database import get_dashboard_stats, insert_log


@st.cache_data(ttl=30)
def _load_stats() -> dict[str, Any]:
    return get_dashboard_stats()


def render() -> None:
    st.title("Dashboard PID")

    stats = _load_stats()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Casos Totais", stats["total"])
    col2.metric("Docs Pendentes", stats["pending_docs"])
    col3.metric("Campos Pendentes", stats["pending_fields"])
    col4.metric("Textract Hoje", stats["textract_today"])
    col5.metric("Textract Mês", stats["textract_month"])

    if stats["by_status"]:
        st.subheader("Casos por Status")
        st.bar_chart(stats["by_status"])

    st.divider()
    st.subheader("Ações")

    sync_state = st.session_state.setdefault(
        "sync_state", {"running": False, "message": ""}
    )

    if sync_state["message"]:
        st.info(sync_state["message"])

    col_btn1, col_btn2 = st.columns([1, 3])
    with col_btn1:
        if st.button("Sincronizar Trello", disabled=sync_state["running"]):
            sync_state["running"] = True
            sync_state["message"] = "Sincronizando Trello..."
            thread = threading.Thread(target=_run_trello_sync, daemon=True)
            thread.start()
            st.rerun()

    with col_btn2:
        if st.button("Atualizar Métricas"):
            st.cache_data.clear()
            st.rerun()


def _run_trello_sync() -> None:
    """Executa sincronização Trello em thread separada."""
    from app.trello.scraper import scrape_board
    from app.trello.downloader import download_attachments
    from app.database import (
        insert_case, insert_document, update_document_ocr, insert_field,
        document_exists,
    )
    from app.ocr.processor import process_document
    from app.ocr.classifier import classify_document
    from app.ocr.extractor import extract_fields
    from app.models import Case, Document, Field

    sync = st.session_state.get("sync_state", {})
    try:
        cards = scrape_board()
        cookies = []
        for card in cards:
            c = Case(
                trello_card_id=card["card_id"],
                trello_card_url=card["card_url"],
                title=card["title"],
                description=card["description"],
                labels=card["labels"],
                checklists=card["checklists"],
                comments=card["comments"],
            )
            case_id = insert_case(c)
            if case_id is None:
                continue

            att_map = download_attachments([card], cookies)
            for fpath in att_map.get(card["card_id"], []):
                from pathlib import Path
                fname = Path(fpath).name
                if document_exists(case_id, fname):
                    continue

                doc = Document(case_id=case_id, filename=fname, filepath=fpath)
                doc_id = insert_document(doc)
                if doc_id is None:
                    continue

                ocr_text, conf, engine = process_document(fpath, doc_id)
                doc_type, _ = classify_document(ocr_text)
                update_document_ocr(doc_id, ocr_text, doc_type, conf)

                for f in extract_fields(ocr_text, doc_id, case_id):
                    insert_field(f)

        sync["message"] = f"Sincronização concluída: {len(cards)} cards processados."
        insert_log(None, "sync_complete", f"{len(cards)} cards")
    except Exception as exc:
        sync["message"] = f"Erro na sincronização: {exc}"
        insert_log(None, "sync_error", str(exc), "error")
    finally:
        sync["running"] = False
