import pytest
from pathlib import Path

from password_manager import db


@pytest.fixture
def conn(tmp_path: Path):
    c = db.get_connection(tmp_path / "test.db")
    db.initialize_schema(c)
    yield c
    c.close()


def test_schema_creates_all_tables(conn):
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert {"meta", "credentials", "audit_log"}.issubset(tables)


def test_is_vault_initialized_false_when_empty(conn):
    assert db.is_vault_initialized(conn) is False


def test_is_vault_initialized_true_after_token_set(conn):
    db.set_meta(conn, "verification_token", "token-value")
    assert db.is_vault_initialized(conn) is True


def test_meta_roundtrip(conn):
    db.set_meta(conn, "my-key", "my-value")
    assert db.get_meta(conn, "my-key") == "my-value"


def test_meta_missing_key_returns_none(conn):
    assert db.get_meta(conn, "nonexistent") is None


def test_meta_overwrite(conn):
    db.set_meta(conn, "key", "v1")
    db.set_meta(conn, "key", "v2")
    assert db.get_meta(conn, "key") == "v2"


def test_credential_insert_and_retrieve(conn):
    db.insert_credential(conn, "github", "alice", "enc-pw")
    row = db.get_credential_by_service(conn, "github")
    assert row is not None
    assert row["service"] == "github"
    assert row["username"] == "alice"
    assert row["password"] == "enc-pw"


def test_credential_not_found_returns_none(conn):
    assert db.get_credential_by_service(conn, "missing") is None


def test_list_credentials_empty(conn):
    assert db.list_credentials(conn) == []


def test_list_credentials_returns_all(conn):
    db.insert_credential(conn, "github", "alice", "enc1")
    db.insert_credential(conn, "gmail", "bob", "enc2")
    rows = db.list_credentials(conn)
    services = [r["service"] for r in rows]
    assert "github" in services
    assert "gmail" in services


def test_delete_credential(conn):
    db.insert_credential(conn, "github", "alice", "enc-pw")
    deleted = db.delete_credential(conn, "github")
    assert deleted is True
    assert db.get_credential_by_service(conn, "github") is None


def test_delete_nonexistent_returns_false(conn):
    assert db.delete_credential(conn, "nonexistent") is False


def test_search_credentials_partial_match(conn):
    db.insert_credential(conn, "github", "alice", "enc1")
    db.insert_credential(conn, "gitlab", "bob", "enc2")
    db.insert_credential(conn, "gmail", "carol", "enc3")
    results = db.search_credentials(conn, "git")
    services = [r["service"] for r in results]
    assert "github" in services
    assert "gitlab" in services
    assert "gmail" not in services


def test_search_credentials_case_insensitive(conn):
    db.insert_credential(conn, "GitHub", "alice", "enc1")
    results = db.search_credentials(conn, "GITHUB")
    assert len(results) == 1


def test_update_existing_credential(conn):
    db.insert_credential(conn, "github", "alice", "old-enc")
    db.insert_credential(conn, "github", "alice2", "new-enc")
    row = db.get_credential_by_service(conn, "github")
    assert row["username"] == "alice2"
    assert row["password"] == "new-enc"
    # Should still be only one row
    all_rows = db.list_credentials(conn)
    assert len(all_rows) == 1
