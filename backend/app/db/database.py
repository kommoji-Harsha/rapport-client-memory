"""
SQLite database management for clients, responses, and feedback logs.
"""

import os
import sqlite3
import uuid

from pydantic import BaseModel


def get_default_db_path() -> str:
    return os.environ.get("SQLITE_DB_PATH", "data/rapport.db")


class ClientDBModel(BaseModel):
    id: str
    name: str
    industry: str
    primary_contact: str
    quirks: str
    created_at: str


class FeedbackRecord(BaseModel):
    response_id: str
    outcome: str  # went_well | pushback
    notes: str | None = None
    created_at: str | None = None


class ResponseLogRecord(BaseModel):
    id: str
    client_id: str
    incoming_text: str
    memory_enabled: bool
    draft_reply: str
    model_used: str
    created_at: str


def get_db_connection(db_path: str | None = None) -> sqlite3.Connection:
    target_path = db_path or get_default_db_path()
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | None = None) -> None:
    """Initialize SQLite database tables."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS clients (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            industry TEXT NOT NULL,
            primary_contact TEXT NOT NULL,
            quirks TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS response_logs (
            id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL,
            incoming_text TEXT NOT NULL,
            memory_enabled INTEGER NOT NULL,
            draft_reply TEXT NOT NULL,
            model_used TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(client_id) REFERENCES clients(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback (
            response_id TEXT PRIMARY KEY,
            outcome TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def create_or_update_client(
    client: ClientDBModel, db_path: str | None = None
) -> ClientDBModel:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO clients (id, name, industry, primary_contact, quirks, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            industry=excluded.industry,
            primary_contact=excluded.primary_contact,
            quirks=excluded.quirks
        """,
        (
            client.id,
            client.name,
            client.industry,
            client.primary_contact,
            client.quirks,
            client.created_at,
        ),
    )
    conn.commit()
    conn.close()
    return client


def list_clients(db_path: str | None = None) -> list[ClientDBModel]:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, industry, primary_contact, quirks, created_at FROM clients"
    )
    rows = cursor.fetchall()
    conn.close()

    return [
        ClientDBModel(
            id=row["id"],
            name=row["name"],
            industry=row["industry"],
            primary_contact=row["primary_contact"],
            quirks=row["quirks"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def get_client(client_id: str, db_path: str | None = None) -> ClientDBModel | None:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, industry, primary_contact, quirks, created_at FROM clients WHERE id = ?",
        (client_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return ClientDBModel(
        id=row["id"],
        name=row["name"],
        industry=row["industry"],
        primary_contact=row["primary_contact"],
        quirks=row["quirks"],
        created_at=row["created_at"],
    )


def log_response(
    client_id: str,
    incoming_text: str,
    memory_enabled: bool,
    draft_reply: str,
    model_used: str,
    response_id: str | None = None,
    created_at: str | None = None,
    db_path: str | None = None,
) -> str:
    res_id = response_id or f"resp-{uuid.uuid4().hex[:10]}"
    timestamp = created_at or "2025-01-01T00:00:00Z"

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO response_logs
        (id, client_id, incoming_text, memory_enabled, draft_reply, model_used, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            res_id,
            client_id,
            incoming_text,
            1 if memory_enabled else 0,
            draft_reply,
            model_used,
            timestamp,
        ),
    )
    conn.commit()
    conn.close()
    return res_id


def save_feedback(
    response_id: str,
    outcome: str,
    notes: str | None = None,
    created_at: str | None = None,
    db_path: str | None = None,
) -> FeedbackRecord:
    """Save feedback outcome idempotently."""
    timestamp = created_at or "2025-01-01T00:00:00Z"
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO feedback (response_id, outcome, notes, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(response_id) DO UPDATE SET
            outcome=excluded.outcome,
            notes=excluded.notes
        """,
        (response_id, outcome, notes, timestamp),
    )
    conn.commit()
    conn.close()

    return FeedbackRecord(
        response_id=response_id,
        outcome=outcome,
        notes=notes,
        created_at=timestamp,
    )


def get_feedback(response_id: str, db_path: str | None = None) -> FeedbackRecord | None:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT response_id, outcome, notes, created_at FROM feedback WHERE response_id = ?",
        (response_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return FeedbackRecord(
        response_id=row["response_id"],
        outcome=row["outcome"],
        notes=row["notes"],
        created_at=row["created_at"],
    )
