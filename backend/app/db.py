"""Lightweight stdlib sqlite3 database for clients and response logs."""

import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DB_PATH_ENV = os.environ.get("DATABASE_PATH", "rapport.db")


class Database:
    """SQLite database manager for Rapport backend."""

    def __init__(self, db_path: str = DB_PATH_ENV) -> None:
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self, clients_seed_path: Path | None = None) -> None:
        """Create tables if they do not exist and seed initial clients if empty."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS clients (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    contact_name TEXT,
                    contact_email TEXT,
                    industry TEXT,
                    primary_quirk TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS responses (
                    response_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    incoming_text TEXT NOT NULL,
                    memory_enabled BOOLEAN NOT NULL,
                    draft_reply TEXT NOT NULL,
                    client_brief_json TEXT NOT NULL,
                    risk_flags_json TEXT NOT NULL,
                    memory_used_json TEXT NOT NULL,
                    warnings_json TEXT NOT NULL,
                    model_used TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (client_id) REFERENCES clients (id)
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    response_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (response_id) REFERENCES responses (response_id)
                );
                """
            )
            conn.commit()

        # Seed initial clients if database table is empty
        if clients_seed_path and clients_seed_path.exists():
            self._seed_clients_from_json(clients_seed_path)

    def _seed_clients_from_json(self, json_path: Path) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM clients;")
            count = cursor.fetchone()[0]
            if count == 0:
                logger.info("Seeding SQLite clients table from %s", json_path)
                with open(json_path, encoding="utf-8") as f:
                    clients_data = json.load(f)
                for c in clients_data:
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO clients (id, name, contact_name, contact_email, industry, primary_quirk)
                        VALUES (?, ?, ?, ?, ?, ?);
                        """,
                        (
                            c["id"],
                            c["name"],
                            c.get("contact_name", ""),
                            c.get("contact_email", ""),
                            c.get("industry", ""),
                            c.get("primary_quirk", ""),
                        ),
                    )
                conn.commit()

    def get_clients(self) -> list[dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, contact_name, contact_email, industry, primary_quirk FROM clients ORDER BY name ASC;")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_client(self, client_id: str) -> dict[str, Any] | None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, contact_name, contact_email, industry, primary_quirk FROM clients WHERE id = ?;", (client_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_client(
        self,
        client_id: str,
        name: str,
        contact_name: str = "",
        contact_email: str = "",
        industry: str = "",
        primary_quirk: str = "",
    ) -> dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO clients (id, name, contact_name, contact_email, industry, primary_quirk)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (client_id, name, contact_name, contact_email, industry, primary_quirk),
            )
            conn.commit()
        return {
            "id": client_id,
            "name": name,
            "contact_name": contact_name,
            "contact_email": contact_email,
            "industry": industry,
            "primary_quirk": primary_quirk,
        }

    def save_response(self, resp_data: dict[str, Any]) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO responses (
                    response_id, client_id, incoming_text, memory_enabled,
                    draft_reply, client_brief_json, risk_flags_json,
                    memory_used_json, warnings_json, model_used
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    resp_data["response_id"],
                    resp_data["client_id"],
                    resp_data["incoming_text"],
                    resp_data["memory_enabled"],
                    resp_data["draft_reply"],
                    json.dumps(resp_data.get("client_brief", [])),
                    json.dumps(resp_data.get("risk_flags", [])),
                    json.dumps(resp_data.get("memory_used", [])),
                    json.dumps(resp_data.get("warnings", [])),
                    resp_data["model_used"],
                ),
            )
            conn.commit()

    def get_response(self, response_id: str) -> dict[str, Any] | None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM responses WHERE response_id = ?;", (response_id,))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            res["client_brief"] = json.loads(res["client_brief_json"])
            res["risk_flags"] = json.loads(res["risk_flags_json"])
            res["memory_used"] = json.loads(res["memory_used_json"])
            res["warnings"] = json.loads(res["warnings_json"])
            return res

    def save_feedback(self, response_id: str, client_id: str, outcome: str, notes: str | None = None) -> dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO feedback (response_id, client_id, outcome, notes)
                VALUES (?, ?, ?, ?);
                """,
                (response_id, client_id, outcome, notes or ""),
            )
            conn.commit()
        return {
            "response_id": response_id,
            "client_id": client_id,
            "outcome": outcome,
            "notes": notes,
        }

    def get_feedback(self, response_id: str) -> dict[str, Any] | None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM feedback WHERE response_id = ?;", (response_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
