import pytest
from pathlib import Path
from password_manager.vault import Vault

MASTER_PASSWORD = "test-master-password-123"


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "vault.db"


@pytest.fixture
def initialized_vault(db_path: Path):
    vault = Vault.initialize(MASTER_PASSWORD, db_path)
    yield vault
    vault.close()


@pytest.fixture
def seeded_vault(db_path: Path):
    vault = Vault.initialize(MASTER_PASSWORD, db_path)
    vault.add("github", "alice", "gh-secret")
    vault.add("gmail", "alice@example.com", "gm-secret")
    yield vault
    vault.close()
