from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Case:
    id: Optional[int] = None
    trello_card_id: str = ""
    trello_card_url: str = ""
    title: str = ""
    description: str = ""
    labels: list[str] = field(default_factory=list)
    checklists: list[dict] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)
    status: str = "pendente"
    protocol: Optional[str] = None
    portal_evidence_path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Document:
    id: Optional[int] = None
    case_id: int = 0
    filename: str = ""
    filepath: str = ""
    doc_type: str = "outros"
    ocr_text: str = ""
    confidence_score: float = 0.0
    validation_status: str = "pendente"
    origin: str = "trello_attachment"
    created_at: Optional[datetime] = None


@dataclass
class Field:
    id: Optional[int] = None
    case_id: int = 0
    document_id: Optional[int] = None
    field_name: str = ""
    field_value: str = ""
    source: str = "ocr"
    score: float = 0.0
    status: str = "pendente"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Log:
    id: Optional[int] = None
    case_id: Optional[int] = None
    action: str = ""
    details: str = ""
    level: str = "info"
    created_at: Optional[datetime] = None
