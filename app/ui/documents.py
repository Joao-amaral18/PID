"""Página de validação de documentos."""
from pathlib import Path

import streamlit as st

from app.database import list_documents_for_case, update_document_status, insert_log


def render() -> None:
    st.title("Validação de Documentos")

    case_id = st.session_state.get("selected_case_id")
    if not case_id:
        st.warning("Selecione um caso na página “Casos”.")
        return

    render_for_case(case_id)


def render_for_case(case_id: int) -> None:
    """Renderiza lista de documentos para um caso específico."""
    documents = list_documents_for_case(case_id)
    if not documents:
        st.info("Nenhum documento baixado para este caso.")
        return

    for doc in documents:
        with st.expander(
            f"📄 {doc.filename} | {doc.doc_type} | {doc.validation_status}",
            expanded=False,
        ):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.caption(f"Confiança OCR: {doc.confidence_score:.0%}")
                st.caption(f"Origem: {doc.origin}")
            with col2:
                if st.button("Aprovar", key=f"approve_{doc.id}"):
                    update_document_status(doc.id, "aprovado")
                    insert_log(
                        case_id, "doc_approved", doc.filename
                    )
                    st.success("Aprovado")
                    st.rerun()
            with col3:
                if st.button("Rejeitar", key=f"reject_{doc.id}"):
                    update_document_status(doc.id, "rejeitado")
                    insert_log(
                        case_id, "doc_rejected", doc.filename, "warning"
                    )
                    st.warning("Rejeitado")
                    st.rerun()

            if doc.ocr_text:
                with st.expander("Ver texto OCR"):
                    st.text_area(
                        "",
                        doc.ocr_text[:3000],
                        height=200,
                        key=f"ocr_{doc.id}",
                        disabled=True,
                    )

            # Pré-visualização se imagem
            fpath = Path(doc.filepath)
            if fpath.exists() and fpath.suffix.lower() in (".png", ".jpg", ".jpeg"):
                st.image(str(fpath), width=400)
