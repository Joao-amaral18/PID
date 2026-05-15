"""Página visualizadora de logs do sistema."""
import streamlit as st

from app.database import list_logs


def render() -> None:
    st.title("Logs do Sistema")

    col1, col2, col3 = st.columns(3)
    with col1:
        level_filter = st.selectbox(
            "Nível", ["Todos", "info", "warning", "error"]
        )
    with col2:
        limit = st.number_input("Limite", min_value=10, max_value=1000, value=200)
    with col3:
        st.write("")
        refresh = st.button("Atualizar")

    level = None if level_filter == "Todos" else level_filter
    logs = list_logs(level=level, limit=int(limit))

    if not logs:
        st.info("Nenhum log encontrado.")
        return

    data = [
        {
            "Data": str(log.created_at)[:19] if log.created_at else "",
            "Nível": log.level,
            "Ação": log.action,
            "Caso ID": log.case_id or "",
            "Detalhes": log.details,
        }
        for log in logs
    ]

    def _row_color(row):
        if row["Nível"] == "error":
            return ["background-color: #ffcccc"] * len(row)
        if row["Nível"] == "warning":
            return ["background-color: #fff3cc"] * len(row)
        return [""] * len(row)

    import pandas as pd
    df = pd.DataFrame(data)
    st.dataframe(
        df.style.apply(_row_color, axis=1),
        use_container_width=True,
    )
