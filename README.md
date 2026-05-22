# Password Manager

A command-line password manager that encrypts credentials locally using a master password. Built as a capstone for an AI engineering cohort.

## Features

- AES-128 encryption via Fernet (authenticated — tamper-evident)
- Master password derived via PBKDF2-HMAC-SHA256 (480,000 iterations) — never stored on disk
- SQLite storage at `~/.password_manager/vault.db`
- Six commands: `init`, `add`, `get`, `list`, `delete`, `search`
- 97% test coverage across 52 tests

## Installation

```bash
git clone https://github.com/AbhiramNair48/PasswordManager.git
cd PasswordManager
pip install -e ".[dev]"
```

## Usage

```bash
# Initialize a new vault (one-time setup)
pm init

# Store a credential
pm add github --username alice

# Retrieve a credential
pm get github

# List all services
pm list

# Search by keyword
pm search git

# Delete a credential
pm delete github

# Use a custom vault location
pm --db-path /path/to/vault.db list
```

## Security Model

1. Your master password is never stored. It is used to derive a 32-byte AES key via PBKDF2.
2. A random 16-byte salt is generated once and stored in the vault (salts are not secret).
3. A sentinel value is encrypted and stored so the app can verify the master password at startup.
4. Each password is independently Fernet-encrypted before being written to SQLite.
5. The vault database is created with `chmod 600` (owner read/write only).

## Running Tests

```bash
python -m pytest
```

## Project Structure

```
src/password_manager/
├── crypto.py   Pure key derivation + encrypt/decrypt (no I/O)
├── db.py       SQLite CRUD (no crypto)
├── vault.py    Orchestrates crypto + db (Vault class)
└── cli.py      Click commands (delegates to vault.py)
```

See [CLAUDE.md](CLAUDE.md) for architecture details and [BUILD_LOG.md](BUILD_LOG.md) for the development log.
