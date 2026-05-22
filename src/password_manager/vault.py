from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import crypto, db

__all__ = ["Vault", "AuthenticationError", "CredentialNotFoundError"]

_DEFAULT_DB = Path.home() / ".password_manager" / "vault.db"


class AuthenticationError(Exception):
    pass


class CredentialNotFoundError(Exception):
    pass


@dataclass
class Credential:
    service: str
    username: str
    password: str


class Vault:
    def __init__(self, conn: sqlite3.Connection, key: bytes) -> None:
        self._conn = conn
        self._key = key

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def initialize(
        cls, master_password: str, db_path: Path = _DEFAULT_DB
    ) -> "Vault":
        conn = db.get_connection(db_path)
        db.initialize_schema(conn)
        if db.is_vault_initialized(conn):
            raise ValueError("Vault already initialized. Use Vault.open() instead.")
        salt = crypto.generate_salt()
        key = crypto.derive_key(master_password, salt)
        token = crypto.make_verification_token(key)
        db.set_meta(conn, "salt", salt.hex())
        db.set_meta(conn, "verification_token", token)
        return cls(conn, key)

    @classmethod
    def open(cls, master_password: str, db_path: Path = _DEFAULT_DB) -> "Vault":
        conn = db.get_connection(db_path)
        db.initialize_schema(conn)
        if not db.is_vault_initialized(conn):
            raise ValueError("Vault not initialized. Run `pm init` first.")
        salt_hex = db.get_meta(conn, "salt")
        if salt_hex is None:
            raise AuthenticationError("Vault metadata is corrupt (missing salt).")
        salt = bytes.fromhex(salt_hex)
        key = crypto.derive_key(master_password, salt)
        token = db.get_meta(conn, "verification_token")
        if not crypto.verify_master_password(token, key):
            conn.close()
            raise AuthenticationError("Wrong master password.")
        return cls(conn, key)

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------
    # Credential operations
    # ------------------------------------------------------------------

    def add(self, service: str, username: str, password: str) -> None:
        encrypted = crypto.encrypt(password, self._key)
        db.insert_credential(self._conn, service, username, encrypted)

    def get(self, service: str) -> Credential:
        row = db.get_credential_by_service(self._conn, service)
        if row is None:
            raise CredentialNotFoundError(f"No credential found for '{service}'.")
        db._log(self._conn, "get", service)
        self._conn.commit()
        return Credential(
            service=row["service"],
            username=row["username"],
            password=crypto.decrypt(row["password"], self._key),
        )

    def list(self) -> list[dict]:
        rows = db.list_credentials(self._conn)
        return [
            {"service": r["service"], "username": r["username"], "created_at": r["created_at"]}
            for r in rows
        ]

    def delete(self, service: str) -> bool:
        return db.delete_credential(self._conn, service)

    def search(self, query: str) -> list[dict]:
        rows = db.search_credentials(self._conn, query)
        return [
            {"service": r["service"], "username": r["username"], "created_at": r["created_at"]}
            for r in rows
        ]
