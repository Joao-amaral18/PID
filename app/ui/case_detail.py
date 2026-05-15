"""Página de detalhe do caso com abas: Documentos, Campos, Portal, Logs."""
import streamlit as st
import pandas as pd

from app.database import (
    get_case, list_documents_for_case, list_fields_for_case,
    list_logs, update_field, approve_all_fields, update_case_status,
    insert_log,
)
from app.validation.validator import validate_field


def render() -> None:
    case_id = _resolve_case_id()
    if not case_id:
        st.warning("Selecione um caso na página “Casos”.")
        return

    case = get_case(case_id)
    if not case:
        st.error(f"Caso {case_id} não encontrado.")
        return

    st.title(f"Caso: {case.title}")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(f"ID Trello: `{case.trello_card_id}` | Status: `{case.status}`")
    with col2:
        if case.labels:
            st.write(" ".join(f"`{l}`" for l in case.labels))

    if case.description:
        with st.expander("Descrição"):
            st.write(case.description)

    tab_docs, tab_fields, tab_portal, tab_logs = st.tabs(
        ["Documentos", "Campos", "Portal", "Logs"]
    )

    with tab_docs:
        _render_documents_tab(case_id)

    with tab_fields:
        _render_fields_tab(case_id)

    with tab_portal:
        _render_portal_tab(case)

    with tab_logs:
        _render_logs_tab(case_id)


def _resolve_case_id() -> int | None:
    if "selected_case_id" in st.session_state:
        return st.session_state["selected_case_id"]
    param = st.query_params.get("case_id")
    if param:
        try:
            cid = int(param)
            st.session_state["selected_case_id"] = cid
            return cid
        except ValueError:
            pass
    return None


def _render_documents_tab(case_id: int) -> None:
    from app.ui.documents import render_for_case
    render_for_case(case_id)


def _render_fields_tab(case_id: int) -> None:
    fields = list_fields_for_case(case_id)
    if not fields:
        st.info("Nenhum campo extraído ainda.")
        return

    data = [
        {
            "id": f.id,
            "Campo": f.field_name,
            "Valor": f.field_value,
            "Fonte": f.source,
            "Score": round(f.score, 2),
            "Status": f.status,
        }
        for f in fields
    ]
    df = pd.DataFrame(data)

    # Destacar conflitos: mesmo campo com múltiplos valores não aprovados
    field_counts = df.groupby("Campo")["Valor"].nunique()
    conflict_fields = set(field_counts[field_counts > 1].index)

    st.caption(
        f"{len(fields)} campos | Conflitos detectados: {len(conflict_fields)}"
    )
    if conflict_fields:
        st.warning(f"Campos com valores conflitantes: {', '.join(conflict_fields)}")

    edited = st.data_editor(
        df.drop(columns=["id"]),
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "Status": st.column_config.SelectboxColumn(
                options=["pendente", "aprovado", "corrigido"]
            ),
        },
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Salvar Alterações"):
            _save_edited_fields(fields, df, edited)
            st.success("Campos salvos.")
            st.rerun()
    with col2:
        if st.button("Aprovar Todos"):
            approve_all_fields(case_id)
            insert_log(case_id, "fields_approved_all", "Todos os campos aprovados")
            st.success("Todos os campos aprovados.")
            st.rerun()


def _save_edited_fields(
    original_fields,
    original_df: pd.DataFrame,
    edited_df: pd.DataFrame,
) -> None:
    for i, (orig_row, edit_row) in enumerate(
        zip(original_df.itertuples(), edited_df.itertuples())
    ):
        field = original_fields[i]
        new_value = str(edit_row.Valor)
        new_status = str(edit_row.Status)

        value_changed = new_value != (field.field_value or "")
        status_changed = new_status != field.status

        if value_changed or status_changed:
            # Se o valor mudou manualmente, promove a status corrigido
            if value_changed and new_status == "pendente":
                new_status = "corrigido"
            ok, err = validate_field(field.field_name, new_value)
            if not ok:
                st.warning(f"{field.field_name}: {err}")
            update_field(field.id, new_value, new_status)


def _render_portal_tab(case) -> None:
    st.subheader("Preenchimento no Portal do Advogado")
    st.info(
        "⚠️ O robô preenche o formulário e **para antes do envio**. "
        "A submissão final é sempre manual."
    )

    if st.button("Abrir Portal e Preencher"):
        fields = list_fields_for_case(case.id)
        approved = [f for f in fields if f.status in ("aprovado", "corrigido")]
        if not approved:
            st.warning("Aprove os campos antes de preencher o portal.")
            return

        from app.portal.portal_bot import PortalBot
        with st.spinner("Abrindo portal..."):
            try:
                with PortalBot() as bot:
                    bot.open_portal()
                    filled = bot.fill_pid_form(case, fields)
                    st.success(
                        f"Formulário preenchido: {len(filled)} campos. "
                        "Revise no browser e submeta manualmente."
                    )

                    st.divider()
                    st.subheader("Registrar Protocolo")
                    protocol = st.text_input(
                        "Número do protocolo recebido após envio"
                    )
                    if st.button("Registrar") and protocol:
                        evidence = bot.record_protocol(case.id, protocol)
                        update_case_status(case.id, "preenchido")
                        st.success(f"Protocolo {protocol} registrado.")
                        if evidence:
                            st.image(evidence, caption="Evidência de envio")
            except Exception as exc:
                st.error(f"Erro no portal: {exc}")
                insert_log(case.id, "portal_error", str(exc), "error")


def _render_logs_tab(case_id: int) -> None:
    logs = list_logs(case_id=case_id, limit=100)
    if not logs:
        st.info("Sem logs para este caso.")
        return
    data = [
        {
            "Data": str(log.created_at)[:19] if log.created_at else "",
            "Nivel": log.level,
            "Ação": log.action,
            "Detalhes": log.details,
        }
        for log in logs
    ]
    st.dataframe(data, use_container_width=True)
