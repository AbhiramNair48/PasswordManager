# CLAUDE.md — Password Manager

## Project Overview

A command-line password manager that stores credentials (service name, username, password) in a local encrypted SQLite database. The master password is never stored — it is used to derive an AES encryption key via PBKDF2, and each stored password is independently encrypted with Fernet (AES-128-CBC + HMAC-SHA256). The CLI is built with Click and exposes five commands: `pm init`, `pm add`, `pm get`, `pm list`, `pm delete`, `pm search`. Built as a capstone for an AI engineering cohort.

## Architecture

Four modules with strict separation of concerns:

```
crypto.py   Pure functions only — key derivation, encrypt, decrypt. No I/O, no DB.
db.py       All SQLite I/O. No crypto. Returns raw rows; never touches the key.
vault.py    Orchestrates crypto + db. Vault class holds conn + key in memory.
cli.py      Click commands only. Delegates entirely to vault.py. No business logic here.
```

Data flow: `cli.py` prompts for master password → `vault.py` opens vault (derives key, verifies) → `vault.py` calls `crypto.py` to encrypt/decrypt → `vault.py` calls `db.py` to read/write.

## Commands

```bash
pip install -e ".[dev]"      # install for development
pytest                        # run full test suite with coverage
python -m pytest              # alternative if pytest not on PATH
pm --help                     # list available CLI commands
pm init                       # initialize a new vault (prompts for master password)
pm add <service>              # store a credential
pm get <service>              # retrieve and display a credential
pm list                       # list all stored services
pm delete <service>           # remove a credential
pm search <query>             # search services by keyword
ruff check src/ tests/        # lint
ruff format src/ tests/       # format
```

## DB Location

Default: `~/.password_manager/vault.db`. File is created with `chmod 600` (owner read/write only).
Override with: `pm --db-path /path/to/vault.db <command>`

**Never commit `.db` files.** The `.gitignore` already excludes `*.db`.

## Security Model

1. **Key derivation:** `PBKDF2HMAC(SHA-256, 480,000 iterations, 16-byte random salt)` → 32-byte key. The salt is stored in plaintext in the `meta` table (salts are not secret).
2. **Vault verification:** A known sentinel (`"vault-ok"`) is Fernet-encrypted with the derived key and stored in `meta` as `verification_token`. On each open, re-derive the key and attempt to decrypt the sentinel — `InvalidToken` means wrong password.
3. **Per-credential encryption:** Each password is independently Fernet-encrypted before the DB write. Fernet ciphertext embeds its own IV and HMAC; no additional columns needed.
4. **Master password in memory only:** The derived key lives only in the `Vault` instance for the duration of one CLI invocation. It is never written to disk.

## Testing Philosophy

- `tests/conftest.py` provides `db_path`, `initialized_vault`, and `seeded_vault` fixtures backed by pytest's `tmp_path`. Tests never touch `~/.password_manager`.
- `test_crypto.py` — unit tests for pure crypto functions (no DB).
- `test_db.py` — unit tests for DB layer using an in-memory or `tmp_path` SQLite file.
- `test_vault.py` — integration tests for the full encrypt→store→retrieve→decrypt path.
- `test_cli.py` — CLI tests using Click's `CliRunner`.

## Conventions

- Type hints on all function signatures.
- No global state. The `Vault` class holds all runtime state.
- Small, focused functions. If a function does two things, split it.
- `crypto.py` must never import from `db.py` or `vault.py` (dependency direction: cli → vault → {crypto, db}).
- Raise `AuthenticationError` (defined in `vault.py`) for wrong-password failures, not bare exceptions.

## Do Not

- Do not modify tests to make them pass — fix the implementation instead.
- Do not lower PBKDF2 iteration count for performance. Use fixtures with a pre-derived key in tests if speed is needed.
- Do not accept the master password as a positional CLI argument (it would appear in shell history). Always use `click.password_option()` or `click.prompt(..., hide_input=True)`.
- Do not add new dependencies without asking first.
- Do not write the master password or plaintext credentials to any log, print statement, or file.

## Capstone Artifacts

- [BUILD_LOG.md](BUILD_LOG.md) — per-task build log and AI workflow documentation
