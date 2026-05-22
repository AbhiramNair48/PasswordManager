import sqlite3

import pytest
from pathlib import Path

from password_manager.vault import (
    AuthenticationError,
    CredentialNotFoundError,
    Vault,
)

MASTER = "test-master-password-123"


# ------------------------------------------------------------------
# Initialization
# ------------------------------------------------------------------

def test_initialize_creates_vault(db_path):
    vault = Vault.initialize(MASTER, db_path)
    vault.close()
    vault2 = Vault.open(MASTER, db_path)
    vault2.close()


def test_initialize_twice_raises(db_path):
    v = Vault.initialize(MASTER, db_path)
    v.close()
    with pytest.raises(ValueError, match="already initialized"):
        Vault.initialize(MASTER, db_path)


# ------------------------------------------------------------------
# Authentication — tests written by hand (core security invariants)
# ------------------------------------------------------------------

def test_wrong_password_cannot_open_vault(db_path):
    """Core security guarantee: wrong master password must be rejected."""
    vault = Vault.initialize(MASTER, db_path)
    vault.close()
    with pytest.raises(AuthenticationError):
        Vault.open("definitely-wrong-password", db_path)


def test_plaintext_never_stored_in_db(db_path):
    """Encryption is applied on write, not just on read."""
    vault = Vault.initialize(MASTER, db_path)
    vault.add("github", "alice", "supersecret")
    vault.close()

    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT password FROM credentials").fetchall()
    conn.close()

    raw_values = [row[0] for row in rows]
    assert all("supersecret" not in v for v in raw_values), (
        "Plaintext password found in raw DB — encryption is not being applied on write"
    )


# ------------------------------------------------------------------
# add / get
# ------------------------------------------------------------------

def test_add_then_get_returns_plaintext(initialized_vault):
    initialized_vault.add("github", "alice", "my-secret")
    cred = initialized_vault.get("github")
    assert cred.service == "github"
    assert cred.username == "alice"
    assert cred.password == "my-secret"


def test_get_nonexistent_raises(initialized_vault):
    with pytest.raises(CredentialNotFoundError):
        initialized_vault.get("nonexistent-service")


def test_add_overwrites_existing(initialized_vault):
    initialized_vault.add("github", "alice", "old-password")
    initialized_vault.add("github", "alice2", "new-password")
    cred = initialized_vault.get("github")
    assert cred.username == "alice2"
    assert cred.password == "new-password"


# ------------------------------------------------------------------
# list
# ------------------------------------------------------------------

def test_list_empty_vault_returns_empty(initialized_vault):
    assert initialized_vault.list() == []


def test_list_returns_all_services(seeded_vault):
    entries = seeded_vault.list()
    services = [e["service"] for e in entries]
    assert "github" in services
    assert "gmail" in services


# ------------------------------------------------------------------
# delete
# ------------------------------------------------------------------

def test_delete_removes_entry(seeded_vault):
    assert seeded_vault.delete("github") is True
    with pytest.raises(CredentialNotFoundError):
        seeded_vault.get("github")


def test_delete_nonexistent_returns_false(initialized_vault):
    assert initialized_vault.delete("nonexistent") is False


# ------------------------------------------------------------------
# search
# ------------------------------------------------------------------

def test_search_returns_matching_services(seeded_vault):
    results = seeded_vault.search("git")
    services = [r["service"] for r in results]
    assert "github" in services
    assert "gmail" not in services


def test_search_is_case_insensitive(seeded_vault):
    results = seeded_vault.search("GITHUB")
    assert len(results) == 1
    assert results[0]["service"] == "github"


def test_search_no_match_returns_empty(seeded_vault):
    results = seeded_vault.search("zzz-no-match")
    assert results == []


# ------------------------------------------------------------------
# Cross-session persistence
# ------------------------------------------------------------------

def test_credential_persists_across_open(db_path):
    vault = Vault.initialize(MASTER, db_path)
    vault.add("github", "alice", "persist-me")
    vault.close()

    vault2 = Vault.open(MASTER, db_path)
    cred = vault2.get("github")
    vault2.close()
    assert cred.password == "persist-me"
