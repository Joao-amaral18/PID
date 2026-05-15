import json
import sqlite3
from datetime import datetime, date
from typing import Optional

from app.config import DB_PATH
from app.models import Case, Document, Field, Log


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def run_migrations() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS pid_cases (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                trello_card_id      TEXT UNIQUE,
                trello_card_url     TEXT,
                title               TEXT NOT NULL,
                description         TEXT DEFAULT '',
                labels              TEXT DEFAULT '[]',
                checklists          TEXT DEFAULT '[]',
                comments            TEXT DEFAULT '[]',
                status              TEXT DEFAULT 'pendente',
                protocol            TEXT,
                portal_evidence_path TEXT,
                created_at          TEXT DEFAULT (datetime('now')),
                updated_at          TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS pid_documents (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id             INTEGER NOT NULL REFERENCES pid_cases(id),
                filename            TEXT NOT NULL,
                filepath            TEXT NOT NULL,
                doc_type            TEXT DEFAULT 'outros',
                ocr_text            TEXT DEFAULT '',
                confidence_score    REAL DEFAULT 0.0,
                validation_status   TEXT DEFAULT 'pendente',
                origin              TEXT DEFAULT 'trello_attachment',
                created_at          TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS pid_fields (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id             INTEGER NOT NULL REFERENCES pid_cases(id),
                document_id         INTEGER REFERENCES pid_documents(id),
                field_name          TEXT NOT NULL,
                field_value         TEXT DEFAULT '',
                source              TEXT DEFAULT 'ocr',
                score               REAL DEFAULT 0.0,
                status              TEXT DEFAULT 'pendente',
                created_at          TEXT DEFAULT (datetime('now')),
                updated_at          TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS pid_logs (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id             INTEGER REFERENCES pid_cases(id),
                action              TEXT NOT NULL,
                details             TEXT DEFAULT '',
                level               TEXT DEFAULT 'info',
                created_at          TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS ocr_usage (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                engine              TEXT NOT NULL,
                pages               INTEGER NOT NULL,
                document_id         INTEGER,
                created_at          TEXT DEFAULT (datetime('now'))
            );
        """)


# ── Cases ────────────────────────────────────────────────────────────────────

def insert_case(case: Case) -> Optional[int]:
    with get_connection() as conn:
        try:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO pid_cases
                    (trello_card_id, trello_card_url, title, description,
                     labels, checklists, comments, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case.trello_card_id,
                    case.trello_card_url,
                    case.title,
                    case.description,
                    json.dumps(case.labels, ensure_ascii=False),
                    json.dumps(case.checklists, ensure_ascii=False),
                    json.dumps(case.comments, ensure_ascii=False),
                    case.status,
                ),
            )
            if cur.lastrowid:
                return cur.lastrowid
            row = conn.execute(
                "SELECT id FROM pid_cases WHERE trello_card_id = ?",
                (case.trello_card_id,),
            ).fetchone()
            return row["id"] if row else None
        except Exception:
            return None


def get_case(case_id: int) -> Optional[Case]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM pid_cases WHERE id = ?", (case_id,)
        ).fetchone()
        return _row_to_case(row) if row else None


def list_cases() -> list[Case]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM pid_cases ORDER BY created_at DESC"
        ).fetchall()
        return [_row_to_case(r) for r in rows]


def update_case_status(case_id: int, status: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE pid_cases SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (status, case_id),
        )


def update_case_protocol(
    case_id: int, protocol: str, evidence_path: str
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE pid_cases
            SET protocol = ?, portal_evidence_path = ?, status = 'preenchido',
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (protocol, evidence_path, case_id),
        )


def _row_to_case(row: sqlite3.Row) -> Case:
    return Case(
        id=row["id"],
        trello_card_id=row["trello_card_id"] or "",
        trello_card_url=row["trello_card_url"] or "",
        title=row["title"],
        description=row["description"] or "",
        labels=json.loads(row["labels"] or "[]"),
        checklists=json.loads(row["checklists"] or "[]"),
        comments=json.loads(row["comments"] or "[]"),
        status=row["status"],
        protocol=row["protocol"],
        portal_evidence_path=row["portal_evidence_path"],
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )


# ── Documents ────────────────────────────────────────────────────────────────

def insert_document(doc: Document) -> Optional[int]:
    with get_connection() as conn:
        try:
            cur = conn.execute(
                """
                INSERT INTO pid_documents
                    (case_id, filename, filepath, doc_type, ocr_text,
                     confidence_score, validation_status, origin)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc.case_id,
                    doc.filename,
                    doc.filepath,
                    doc.doc_type,
                    doc.ocr_text,
                    doc.confidence_score,
                    doc.validation_status,
                    doc.origin,
                ),
            )
            return cur.lastrowid
        except Exception:
            return None


def get_document(doc_id: int) -> Optional[Document]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM pid_documents WHERE id = ?", (doc_id,)
        ).fetchone()
        return _row_to_document(row) if row else None


def list_documents_for_case(case_id: int) -> list[Document]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM pid_documents WHERE case_id = ? ORDER BY created_at",
            (case_id,),
        ).fetchall()
        return [_row_to_document(r) for r in rows]


def update_document_ocr(
    doc_id: int, ocr_text: str, doc_type: str, confidence: float
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE pid_documents
            SET ocr_text = ?, doc_type = ?, confidence_score = ?
            WHERE id = ?
            """,
            (ocr_text, doc_type, confidence, doc_id),
        )


def update_document_status(doc_id: int, status: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE pid_documents SET validation_status = ? WHERE id = ?",
            (status, doc_id),
        )


def document_exists(case_id: int, filename: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM pid_documents WHERE case_id = ? AND filename = ?",
            (case_id, filename),
        ).fetchone()
        return row is not None


def _row_to_document(row: sqlite3.Row) -> Document:
    return Document(
        id=row["id"],
        case_id=row["case_id"],
        filename=row["filename"],
        filepath=row["filepath"],
        doc_type=row["doc_type"],
        ocr_text=row["ocr_text"] or "",
        confidence_score=row["confidence_score"],
        validation_status=row["validation_status"],
        origin=row["origin"],
        created_at=_parse_dt(row["created_at"]),
    )


# ── Fields ───────────────────────────────────────────────────────────────────

def insert_field(f: Field) -> Optional[int]:
    with get_connection() as conn:
        try:
            cur = conn.execute(
                """
                INSERT INTO pid_fields
                    (case_id, document_id, field_name, field_value,
                     source, score, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f.case_id,
                    f.document_id,
                    f.field_name,
                    f.field_value,
                    f.source,
                    f.score,
                    f.status,
                ),
            )
            return cur.lastrowid
        except Exception:
            return None


def list_fields_for_case(case_id: int) -> list[Field]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM pid_fields WHERE case_id = ? ORDER BY field_name, created_at",
            (case_id,),
        ).fetchall()
        return [_row_to_field(r) for r in rows]


def update_field(
    field_id: int,
    field_value: str,
    status: str,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE pid_fields
            SET field_value = ?, status = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (field_value, status, field_id),
        )


def approve_all_fields(case_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE pid_fields
            SET status = 'aprovado', updated_at = datetime('now')
            WHERE case_id = ? AND status = 'pendente'
            """,
            (case_id,),
        )


def _row_to_field(row: sqlite3.Row) -> Field:
    return Field(
        id=row["id"],
        case_id=row["case_id"],
        document_id=row["document_id"],
        field_name=row["field_name"],
        field_value=row["field_value"] or "",
        source=row["source"],
        score=row["score"],
        status=row["status"],
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )


# ── Logs ─────────────────────────────────────────────────────────────────────

def insert_log(
    case_id: Optional[int],
    action: str,
    details: str = "",
    level: str = "info",
) -> None:
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO pid_logs (case_id, action, details, level)
                VALUES (?, ?, ?, ?)
                """,
                (case_id, action, details, level),
            )
    except Exception as exc:
        import sys
        print(f"[log_error] {exc}", file=sys.stderr)


def list_logs(
    case_id: Optional[int] = None,
    level: Optional[str] = None,
    limit: int = 200,
) -> list[Log]:
    with get_connection() as conn:
        conditions = []
        params: list = []
        if case_id is not None:
            conditions.append("case_id = ?")
            params.append(case_id)
        if level:
            conditions.append("level = ?")
            params.append(level)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)
        rows = conn.execute(
            f"SELECT * FROM pid_logs {where} ORDER BY created_at DESC LIMIT ?",
            params,
        ).fetchall()
        return [_row_to_log(r) for r in rows]


def _row_to_log(row: sqlite3.Row) -> Log:
    return Log(
        id=row["id"],
        case_id=row["case_id"],
        action=row["action"],
        details=row["details"] or "",
        level=row["level"],
        created_at=_parse_dt(row["created_at"]),
    )


# ── OCR Usage ────────────────────────────────────────────────────────────────

def record_ocr_usage(engine: str, pages: int, document_id: Optional[int] = None) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO ocr_usage (engine, pages, document_id) VALUES (?, ?, ?)",
            (engine, pages, document_id),
        )


def get_textract_usage_today() -> int:
    today = date.today().isoformat()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(pages), 0)
            FROM ocr_usage
            WHERE engine = 'textract'
              AND date(created_at) = ?
            """,
            (today,),
        ).fetchone()
        return int(row[0])


def get_textract_usage_month() -> int:
    month = datetime.now().strftime("%Y-%m")
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(pages), 0)
            FROM ocr_usage
            WHERE engine = 'textract'
              AND strftime('%Y-%m', created_at) = ?
            """,
            (month,),
        ).fetchone()
        return int(row[0])


def get_dashboard_stats() -> dict:
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM pid_cases").fetchone()[0]
        by_status = conn.execute(
            "SELECT status, COUNT(*) as n FROM pid_cases GROUP BY status"
        ).fetchall()
        pending_docs = conn.execute(
            "SELECT COUNT(*) FROM pid_documents WHERE validation_status = 'pendente'"
        ).fetchone()[0]
        pending_fields = conn.execute(
            "SELECT COUNT(*) FROM pid_fields WHERE status = 'pendente'"
        ).fetchone()[0]
        textract_today = get_textract_usage_today()
        textract_month = get_textract_usage_month()
        return {
            "total": total,
            "by_status": {r["status"]: r["n"] for r in by_status},
            "pending_docs": pending_docs,
            "pending_fields": pending_fields,
            "textract_today": textract_today,
            "textract_month": textract_month,
        }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
