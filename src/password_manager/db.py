import sqlite3
import os
from pathlib import Path
from typing import Optional

__all__ = [
    "get_connection",
    "initialize_schema",
    "is_vault_initialized",
    "get_meta",
    "set_meta",
    "insert_credential",
    "get_credential_by_service",
    "list_credentials",
    "delete_credential",
    "search_credentials",
]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS credentials (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    service    TEXT NOT NULL,
    username   TEXT NOT NULL,
    password   TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_service ON credentials(service);

CREATE TABLE IF NOT EXISTS audit_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    operation TEXT NOT NULL,
    service   TEXT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def get_connection(db_path: Path) -> sqlite3.Connection:
    db_path = Path(db_path).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not db_path.exists()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    if is_new:
        try:
            os.chmod(db_path, 0o600)
        except NotImplementedError:
            pass  # Windows does not support chmod
    return conn


def initialize_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()


def is_vault_initialized(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT value FROM meta WHERE key = 'verification_token'"
    ).fetchone()
    return row is not None


# --- meta table ---

def get_meta(conn: sqlite3.Connection, key: str) -> Optional[str]:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()


# --- credentials table ---

def insert_credential(
    conn: sqlite3.Connection,
    service: str,
    username: str,
    encrypted_password: str,
) -> None:
    existing = get_credential_by_service(conn, service)
    if existing:
        conn.execute(
            "UPDATE credentials SET username = ?, password = ?, updated_at = datetime('now') "
            "WHERE service = ?",
            (username, encrypted_password, service),
        )
    else:
        conn.execute(
            "INSERT INTO credentials (service, username, password) VALUES (?, ?, ?)",
            (service, username, encrypted_password),
        )
    _log(conn, "add", service)
    conn.commit()


def get_credential_by_service(
    conn: sqlite3.Connection, service: str
) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM credentials WHERE service = ?", (service,)
    ).fetchone()


def list_credentials(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT service, username, created_at FROM credentials ORDER BY service"
    ).fetchall()


def delete_credential(conn: sqlite3.Connection, service: str) -> bool:
    cursor = conn.execute(
        "DELETE FROM credentials WHERE service = ?", (service,)
    )
    deleted = cursor.rowcount > 0
    if deleted:
        _log(conn, "delete", service)
    conn.commit()
    return deleted


def search_credentials(conn: sqlite3.Connection, query: str) -> list[sqlite3.Row]:
    pattern = f"%{query.lower()}%"
    return conn.execute(
        "SELECT service, username, created_at FROM credentials "
        "WHERE lower(service) LIKE ? ORDER BY service",
        (pattern,),
    ).fetchall()


def _log(conn: sqlite3.Connection, operation: str, service: Optional[str]) -> None:
    conn.execute(
        "INSERT INTO audit_log (operation, service) VALUES (?, ?)",
        (operation, service),
    )
