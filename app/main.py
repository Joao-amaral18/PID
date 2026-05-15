"""Entry point do sistema PID Automation.

Executar com: streamlit run app/main.py
"""
import streamlit as st

from app.config import ensure_dirs
from app.database import run_migrations
from app.ui import dashboard, cases, case_detail, documents, fields, logs, export

# Inicialização única no startup
ensure_dirs()
run_migrations()

st.set_page_config(
    page_title="PID Automation — Samarco",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGES: dict[str, callable] = {
    "Dashboard": dashboard.render,
    "Casos": cases.render,
    "Detalhe do Caso": case_detail.render,
    "Validação de Documentos": documents.render,
    "Campos Extraídos": fields.render,
    "Logs": logs.render,
    "Exportar Dossiê": export.render,
}

with st.sidebar:
    st.title("PID Automation")
    st.caption("Samarco — Automação de Cadastro PID")
    st.divider()
    page = st.radio("Navegação", list(PAGES.keys()))
    st.divider()
    st.caption("⚠️ O envio final no portal é sempre manual.")

PAGES[page]()
