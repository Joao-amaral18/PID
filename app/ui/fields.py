"""Página de gestão de campos extraídos."""
import streamlit as st
import pandas as pd

from app.database import list_cases, list_fields_for_case, update_field, approve_all_fields
from app.validation.validator import validate_field


def render() -> None:
    st.title("Campos Extraídos")

    cases = list_cases()
    if not cases:
        st.info("Nenhum caso disponível.")
        return

    case_options = {c.title: c.id for c in cases}
    selected_title = st.selectbox("Selecionar caso", list(case_options.keys()))
    case_id = case_options[selected_title]

    fields = list_fields_for_case(case_id)
    if not fields:
        st.info("Nenhum campo extraído para este caso.")
        return

    data = [
        {
            "id": f.id,
            "Campo": f.field_name,
            "Valor": f.field_value,
            "Score": round(f.score, 2),
            "Status": f.status,
            "Fonte": f.source,
        }
        for f in fields
    ]
    df = pd.DataFrame(data)

    edited = st.data_editor(
        df.drop(columns=["id"]),
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "Status": st.column_config.SelectboxColumn(
                options=["pendente", "aprovado", "corrigido"]
            ),
            "Score": st.column_config.NumberColumn(format="%.2f"),
        },
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Salvar"):
            errors = []
            for i, field in enumerate(fields):
                new_val = str(edited.iloc[i]["Valor"])
                new_status = str(edited.iloc[i]["Status"])
                if new_val != (field.field_value or "") or new_status != field.status:
                    ok, err = validate_field(field.field_name, new_val)
                    if not ok:
                        errors.append(f"{field.field_name}: {err}")
                    if new_val != field.field_value and new_status == "pendente":
                        new_status = "corrigido"
                    update_field(field.id, new_val, new_status)
            if errors:
                for e in errors:
                    st.warning(e)
            else:
                st.success("Campos salvos.")
            st.rerun()
    with col2:
        if st.button("Aprovar Todos"):
            approve_all_fields(case_id)
            st.success("Todos os campos aprovados.")
            st.rerun()
