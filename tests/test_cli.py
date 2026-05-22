import pytest
from click.testing import CliRunner
from pathlib import Path

from password_manager.cli import main
from password_manager.vault import Vault

MASTER = "test-master-password-123"


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def vault_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "vault.db"
    vault = Vault.initialize(MASTER, db_path)
    vault.add("github", "alice", "gh-secret")
    vault.add("gmail", "alice@example.com", "gm-secret")
    vault.close()
    return db_path


def _invoke(runner, args, input_text=None):
    return runner.invoke(main, args, input=input_text, catch_exceptions=False)


# ------------------------------------------------------------------
# pm init
# ------------------------------------------------------------------

def test_init_creates_vault(runner, tmp_path):
    db_path = tmp_path / "new.db"
    result = _invoke(runner, ["--db-path", str(db_path), "init"], f"{MASTER}\n{MASTER}\n")
    assert result.exit_code == 0
    assert "initialized" in result.output.lower()


def test_init_already_initialized_errors(runner, vault_db):
    result = _invoke(runner, ["--db-path", str(vault_db), "init"], f"{MASTER}\n{MASTER}\n")
    assert result.exit_code != 0


# ------------------------------------------------------------------
# pm list
# ------------------------------------------------------------------

def test_list_shows_services(runner, vault_db):
    result = _invoke(runner, ["--db-path", str(vault_db), "list"], f"{MASTER}\n")
    assert result.exit_code == 0
    assert "github" in result.output
    assert "gmail" in result.output


def test_list_wrong_password_fails(runner, vault_db):
    result = runner.invoke(main, ["--db-path", str(vault_db), "list"], input="wrong\n")
    assert result.exit_code != 0


# ------------------------------------------------------------------
# pm get
# ------------------------------------------------------------------

def test_get_shows_credential(runner, vault_db):
    result = _invoke(runner, ["--db-path", str(vault_db), "get", "github"], f"{MASTER}\n")
    assert result.exit_code == 0
    assert "alice" in result.output
    assert "gh-secret" in result.output


def test_get_missing_service_errors(runner, vault_db):
    result = runner.invoke(
        main, ["--db-path", str(vault_db), "get", "nonexistent"], input=f"{MASTER}\n"
    )
    assert result.exit_code != 0


# ------------------------------------------------------------------
# pm add
# ------------------------------------------------------------------

def test_add_new_credential(runner, vault_db):
    result = _invoke(
        runner,
        ["--db-path", str(vault_db), "add", "twitter", "--username", "bob"],
        f"tw-secret\ntw-secret\n{MASTER}\n",
    )
    assert result.exit_code == 0
    assert "twitter" in result.output


# ------------------------------------------------------------------
# pm delete
# ------------------------------------------------------------------

def test_delete_credential(runner, vault_db):
    result = _invoke(runner, ["--db-path", str(vault_db), "delete", "github"], f"{MASTER}\n")
    assert result.exit_code == 0
    assert "deleted" in result.output.lower()


def test_delete_nonexistent_errors(runner, vault_db):
    result = runner.invoke(
        main, ["--db-path", str(vault_db), "delete", "nonexistent"], input=f"{MASTER}\n"
    )
    assert result.exit_code != 0


# ------------------------------------------------------------------
# pm search
# ------------------------------------------------------------------

def test_search_returns_matches(runner, vault_db):
    result = _invoke(runner, ["--db-path", str(vault_db), "search", "git"], f"{MASTER}\n")
    assert result.exit_code == 0
    assert "github" in result.output
    assert "gmail" not in result.output


def test_search_no_results(runner, vault_db):
    result = _invoke(runner, ["--db-path", str(vault_db), "search", "zzz-nomatch"], f"{MASTER}\n")
    assert result.exit_code == 0
    assert "no services" in result.output.lower()
