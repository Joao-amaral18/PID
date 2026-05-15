"""Bot Playwright para preenchimento assistido no Portal do Advogado Samarco.

O bot preenche o formulário PID com dados validados e PARA antes do envio
final — a submissão é sempre manual. Após envio, o operador registra o
protocolo e o sistema salva screenshot como evidência.
"""
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright, Page, BrowserContext

from app.config import (
    PORTAL_URL,
    PORTAL_FIELD_MAP,
    PLAYWRIGHT_USER_DATA_DIR,
    DOSSIES_DIR,
)
from app.database import insert_log, update_case_protocol
from app.models import Case, Field


class PortalBot:
    """Contexto de automação do portal. Use como context manager."""

    def __init__(self):
        self._playwright = None
        self._ctx: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    def __enter__(self) -> "PortalBot":
        self._playwright = sync_playwright().start()
        self._ctx = self._playwright.chromium.launch_persistent_context(
            PLAYWRIGHT_USER_DATA_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            locale="pt-BR",
        )
        self._page = self._ctx.new_page()
        return self

    def __exit__(self, *_):
        if self._ctx:
            try:
                self._ctx.close()
            except Exception:
                pass
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass

    # ── Público ───────────────────────────────────────────────────────────────

    def open_portal(self) -> None:
        """Abre o portal. Aguarda login por certificado digital (manual)."""
        if not PORTAL_URL:
            raise ValueError("PORTAL_URL não configurado no .env")

        self._page.goto(PORTAL_URL, wait_until="networkidle", timeout=60_000)
        self._inject_wait_message()

        # Aguarda o usuário completar a autenticação via certificado
        self._page.wait_for_selector(
            "#portal-main, .main-content, #dashboard, nav.main-nav",
            timeout=300_000,
        )
        insert_log(None, "portal_opened", "Portal do Advogado aberto", "info")

    def fill_pid_form(self, case: Case, fields: list[Field]) -> list[str]:
        """
        Preenche o formulário PID com os campos aprovados/corrigidos.
        Retorna lista de campos preenchidos com sucesso.
        NUNCA submete o formulário — para antes do botão de envio.
        """
        approved_values = {
            f.field_name: f.field_value
            for f in fields
            if f.status in ("aprovado", "corrigido") and f.field_value
        }

        filled: list[str] = []
        for field_name, selector in PORTAL_FIELD_MAP.items():
            value = approved_values.get(field_name, "")
            if not value:
                continue
            if self._fill_field(selector, value, field_name, case.id):
                filled.append(field_name)

        insert_log(
            case.id,
            "portal_form_filled",
            f"{len(filled)}/{len(PORTAL_FIELD_MAP)} campos preenchidos",
        )
        return filled

    def record_protocol(
        self,
        case_id: int,
        protocol: str,
    ) -> str:
        """Salva screenshot como evidência e registra protocolo no banco."""
        screenshot_path = str(
            DOSSIES_DIR / f"evidence_{case_id}_{protocol}.png"
        )
        try:
            self._page.screenshot(path=screenshot_path, full_page=True)
        except Exception:
            screenshot_path = ""

        update_case_protocol(case_id, protocol, screenshot_path)
        insert_log(
            case_id,
            "protocol_recorded",
            f"Protocolo: {protocol}",
            "info",
        )
        return screenshot_path

    # ── Privado ───────────────────────────────────────────────────────────────

    def _fill_field(
        self,
        selector: str,
        value: str,
        field_name: str,
        case_id: Optional[int],
    ) -> bool:
        try:
            el = self._page.locator(selector).first
            el.scroll_into_view_if_needed()
            el.fill(value)
            insert_log(case_id, "field_filled", f"{field_name}={value}")
            return True
        except Exception as exc:
            insert_log(
                case_id,
                "field_fill_error",
                f"{field_name}: {exc}",
                "warning",
            )
            return False

    def _inject_wait_message(self) -> None:
        """Exibe mensagem na tela do browser orientando o usuário."""
        try:
            self._page.evaluate(
                """
                () => {
                    const el = document.createElement('div');
                    el.id = '_pid_portal_msg';
                    el.style = 'position:fixed;top:0;left:0;width:100%;'
                               + 'background:#1a73e8;color:#fff;font-size:16px;'
                               + 'padding:10px 16px;z-index:99999;';
                    el.innerText = 'PID Automation: aguardando autenticação por certificado digital...';
                    document.body.prepend(el);
                }
                """
            )
        except Exception:
            pass
