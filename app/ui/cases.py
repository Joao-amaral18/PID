"""Página de lista de casos com filtros."""
import streamlit as st

from app.database import list_cases

STATUS_COLORS = {
    "pendente": "🟡",
    "em_andamento": "🟠",
    "validado": "🟢",
    "preenchido": "🔵",
    "concluido": ✅",
}


def render() -> None:
    st.title("Casos PID")

    cases = list_cases()
    if not cases:
        st.info("Nenhum caso encontrado. Sincronize o Trello no Dashboard.")
        return

    # Filtros
    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("Buscar por título", placeholder="Digite...")
    with col2:
        status_filter = st.selectbox(
            "Status",
            ["Todos"] + list(STATUS_COLORS.keys()),
        )

    filtered = [
        c for c in cases
        if (not search or search.lower() in c.title.lower())
        and (status_filter == "Todos" or c.status == status_filter)
    ]

    st.caption(f"{len(filtered)} caso(s) encontrado(s)")

    for case in filtered:
        icon = STATUS_COLORS.get(case.status, "•")
        label = f"{icon} {case.title}"
        with st.expander(label, expanded=False):
            st.write(f"**Status:** `{case.status}`")
            if case.labels:
                st.write(f"**Etiquetas:** {', '.join(case.labels)}")
            if case.description:
                st.write(f"**Descrição:** {case.description[:300]}")
            if case.protocol:
                st.write(f"**Protocolo:** `{case.protocol}`")
            if st.button("Abrir Detalhes", key=f"open_{case.id}"):
                st.session_state["selected_case_id"] = case.id
                st.query_params["case_id"] = str(case.id)
                st.info("Vá para a página “Detalhe do Caso”.")
