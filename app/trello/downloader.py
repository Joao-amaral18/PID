"""Download autenticado de anexos Trello usando cookies do Playwright."""
import re
from pathlib import Path
from typing import Optional

import requests

from app.config import DOWNLOADS_DIR
from app.database import insert_log


def download_attachments(
    cards: list[dict],
    playwright_cookies: list[dict],
) -> dict[str, list[str]]:
    """Baixa os anexos de cada card. Retorna {card_id: [filepath, ...]}."""
    session = _build_session(playwright_cookies)
    results: dict[str, list[str]] = {}

    for card in cards:
        card_id = card.get("card_id", "unknown")
        paths = _download_card_attachments(
            session, card_id, card.get("attachments", [])
        )
        results[card_id] = paths

    return results


def _build_session(cookies: list[dict]) -> requests.Session:
    session = requests.Session()
    for c in cookies:
        session.cookies.set(
            c["name"], c["value"], domain=c.get("domain", "trello.com")
        )
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; PID-Automation)"})
    return session


def _download_card_attachments(
    session: requests.Session,
    card_id: str,
    attachments: list[dict],
) -> list[str]:
    card_dir = DOWNLOADS_DIR / card_id
    card_dir.mkdir(parents=True, exist_ok=True)

    paths: list[str] = []
    for att in attachments:
        name = att.get("name", "attachment")
        url = att.get("url", "")
        if not url:
            continue

        filename = _safe_filename(name)
        dest = card_dir / filename

        if dest.exists():
            paths.append(str(dest))
            continue

        local_path = _fetch_file(session, url, dest)
        if local_path:
            paths.append(local_path)
            insert_log(None, "attachment_downloaded", f"{card_id}/{filename}")
        else:
            insert_log(None, "attachment_failed", f"{card_id}/{filename}", "warning")

    return paths


def _fetch_file(session: requests.Session, url: str, dest: Path) -> Optional[str]:
    try:
        with session.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return str(dest)
    except Exception as exc:
        import sys
        print(f"[download_error] {url}: {exc}", file=sys.stderr)
        return None


def _safe_filename(name: str) -> str:
    """Remove caracteres inválidos e limita o comprimento."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    return name[:200] if name else "attachment"
