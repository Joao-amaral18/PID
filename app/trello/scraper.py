"""Playwright scraper para boards Trello sem uso de API."""
import time
from typing import Optional

from playwright.sync_api import sync_playwright, Page, BrowserContext

from app.config import TRELLO_BOARD_URL, TRELLO_LISTS, PLAYWRIGHT_USER_DATA_DIR
from app.database import insert_log


def scrape_board() -> list[dict]:
    """Rastreia o board Trello e retorna lista de dicts por card."""
    if not TRELLO_BOARD_URL:
        raise ValueError("TRELLO_BOARD_URL não configurado no .env")

    results: list[dict] = []
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PLAYWRIGHT_USER_DATA_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            locale="pt-BR",
        )
        page = ctx.new_page()
        try:
            page.goto(TRELLO_BOARD_URL, wait_until="networkidle", timeout=60_000)
            _ensure_logged_in(page)

            for list_name in TRELLO_LISTS:
                cards = _extract_list(page, list_name)
                results.extend(cards)
                insert_log(None, "trello_list_scraped", f"{list_name}: {len(cards)} cards")
        finally:
            ctx.close()

    return results


def _ensure_logged_in(page: Page) -> None:
    """Se landing em página de login, aguarda o usuário autenticar."""
    if "login" in page.url.lower() or "auth" in page.url.lower():
        page.evaluate(
            """() => {
                const el = document.createElement('div');
                el.id = '_pid_msg';
                el.style = 'position:fixed;top:0;left:0;width:100%;background:#1a73e8;'
                           + 'color:#fff;font-size:18px;padding:12px;z-index:99999';
                el.innerText = 'PID Automation: faça login no Trello para continuar.';
                document.body.appendChild(el);
            }"""
        )
        page.wait_for_url("**/b/**", timeout=300_000)
        time.sleep(2)


def _extract_list(page: Page, list_name: str) -> list[dict]:
    """Localiza uma lista pelo nome e extrai todos os cards."""
    # Tenta encontrar o cabeçalho da lista
    header = page.locator(
        f'[data-testid="list-header"] span:has-text("{list_name}")'
    ).first
    if not header.is_visible(timeout=5_000):
        insert_log(None, "trello_list_not_found", list_name, "warning")
        return []

    # Sobe para o container da lista
    list_wrapper = header.locator(
        "xpath=ancestor::*[contains(@class,'list-wrapper') or "
        "@data-testid='list' or contains(@class,'list js')]" 
    ).first

    _scroll_list_to_bottom(page, list_wrapper)

    card_links = list_wrapper.locator(
        '[data-testid="trello-card"], a.list-card'
    ).all()

    cards = []
    for card_el in card_links:
        card_data = _open_card_and_extract(page, card_el)
        if card_data:
            cards.append(card_data)

    return cards


def _scroll_list_to_bottom(page: Page, list_el) -> None:
    """Rola a lista para garantir que todos os cards lazy sejam carregados."""
    prev_count = -1
    for _ in range(20):
        count = list_el.locator('[data-testid="trello-card"], a.list-card').count()
        if count == prev_count:
            break
        prev_count = count
        page.evaluate(
            "el => el.scrollTop = el.scrollHeight",
            list_el.element_handle(),
        )
        time.sleep(0.5)


def _open_card_and_extract(page: Page, card_el) -> Optional[dict]:
    """Clica no card, extrai dados do modal e retorna dict."""
    for attempt in range(3):
        try:
            href = card_el.get_attribute("href") or ""
            card_el.click()
            page.wait_for_selector(
                '[data-testid="card-back"], .card-detail-window',
                timeout=10_000,
            )
            data = _extract_card_modal(page, href)
            _close_modal(page)
            return data
        except Exception as exc:
            insert_log(
                None,
                "trello_card_open_error",
                f"tentativa {attempt + 1}: {exc}",
                "warning",
            )
            if attempt < 2:
                page.keyboard.press("Escape")
                time.sleep(1)
    return None


def _extract_card_modal(page: Page, card_url: str) -> dict:
    """Lê os campos do modal do card aberto."""
    # Título
    title = (
        page.locator('[data-testid="card-back-title"], .card-detail-title').first
        .inner_text(timeout=5_000).strip()
    )

    # ID do card extraido da URL
    card_id = _extract_card_id(page.url, card_url)

    # Descrição
    try:
        description = (
            page.locator('[data-testid="card-back-description"], .card-detail-desc')
            .first.inner_text(timeout=3_000).strip()
        )
    except Exception:
        description = ""

    # Etiquetas
    labels: list[str] = []
    try:
        label_els = page.locator(
            '[data-testid="card-label"], .card-label'
        ).all()
        labels = [el.inner_text(timeout=2_000).strip() for el in label_els]
    except Exception:
        pass

    # Checklists
    checklists: list[dict] = []
    try:
        cl_sections = page.locator(
            '[data-testid="checklist"], .checklist'
        ).all()
        for section in cl_sections:
            cl_name = section.locator(
                '[data-testid="checklist-title"], .checklist-title'
            ).first.inner_text(timeout=2_000).strip()
            items = [
                el.inner_text(timeout=1_000).strip()
                for el in section.locator(
                    '[data-testid="checklist-item"], .checklist-item'
                ).all()
            ]
            checklists.append({"name": cl_name, "items": items})
    except Exception:
        pass

    # Comentários
    comments: list[str] = []
    try:
        comment_els = page.locator(
            '[data-testid="activity-item"], .phenom-desc'
        ).all()
        comments = [el.inner_text(timeout=1_000).strip() for el in comment_els]
    except Exception:
        pass

    # Anexos
    attachments: list[dict] = []
    try:
        att_els = page.locator(
            '[data-testid="attachment-thumbnail"], .attachment-thumbnail'
        ).all()
        for att in att_els:
            try:
                name_el = att.locator(
                    '[data-testid="attachment-name"], .attachment-name'
                ).first
                url_el = att.locator("a").first
                att_name = name_el.inner_text(timeout=1_000).strip()
                att_url = url_el.get_attribute("href") or ""
                if att_name and att_url:
                    attachments.append({"name": att_name, "url": att_url})
            except Exception:
                pass
    except Exception:
        pass

    return {
        "card_id": card_id,
        "card_url": page.url,
        "title": title,
        "description": description,
        "labels": [l for l in labels if l],
        "checklists": checklists,
        "comments": [c for c in comments if c],
        "attachments": attachments,
    }


def _close_modal(page: Page) -> None:
    page.keyboard.press("Escape")
    time.sleep(0.3)


def _extract_card_id(current_url: str, fallback_href: str) -> str:
    """Extrai o ID alfanumérico do card da URL."""
    for url in (current_url, fallback_href):
        parts = url.rstrip("/").split("/")
        for part in reversed(parts):
            if part and len(part) >= 8:
                return part[:24]
    return fallback_href or current_url
