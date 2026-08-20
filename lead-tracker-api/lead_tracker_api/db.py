"""SQLite persistence layer for the Lead Tracker API.

A tiny dependency-free data-access module. The schema is created on first import
so the service is fully functional with no external database.
"""
import sqlite3
from typing import List, Optional

from .models import Lead

_SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL,
    email     TEXT NOT NULL,
    company   TEXT,
    budget    REAL,
    source    TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    return conn


def insert_lead(db_path: str, lead: Lead) -> Lead:
    with _connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO leads (name, email, company, budget, source) "
            "VALUES (?, ?, ?, ?, ?)",
            (lead.name, lead.email, lead.company, lead.budget, lead.source),
        )
        new_id = cur.lastrowid
    assert new_id is not None
    return Lead(
        id=new_id,
        name=lead.name,
        email=lead.email,
        company=lead.company,
        budget=lead.budget,
        source=lead.source,
    )


def get_lead(db_path: str, lead_id: int) -> Optional[Lead]:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    return Lead.from_row(row) if row else None


def list_leads(db_path: str, limit: int = 100, company: Optional[str] = None) -> List[Lead]:
    with _connect(db_path) as conn:
        if company:
            rows = conn.execute(
                "SELECT * FROM leads WHERE company LIKE ? ORDER BY id DESC LIMIT ?",
                (f"%{company}%", limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM leads ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
    return [Lead.from_row(r) for r in rows]


def count_leads(db_path: str) -> int:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM leads").fetchone()
    return int(row["c"])
