# BUILD_LOG.md — Password Manager Capstone

---

## Deliverable 1 — Project Proposal

I'm building a command-line password manager in Python that securely stores encrypted credentials (service name, username, password) in a local SQLite database. It derives an AES encryption key from a master password using PBKDF2 (480,000 iterations, SHA-256), encrypts each stored password with Fernet (authenticated AES), and never writes the master password or any plaintext to disk. The CLI (`pm add`, `pm get`, `pm list`, `pm delete`, `pm search`) is built with Click. This matters to me because I use a spreadsheet for passwords and I want to build something I'd actually replace it with — and doing it myself means I understand every security decision instead of trusting a black box.

---

## Deliverable 2 — Ordered Task List (12 tasks)

| # | What changes | How to verify |
|---|---|---|
| 1 | Create `pyproject.toml`, `src/` layout, `tests/conftest.py` | `pip install -e ".[dev]"` succeeds; `python -c "import password_manager"` works |
| 2 | Author `CLAUDE.md` with architecture, commands, security model, conventions | File exists at repo root with all required sections |
| 3 | Implement `crypto.py` key derivation (`generate_salt`, `derive_key` via PBKDF2HMAC) | `test_derive_key_is_deterministic` passes — same inputs always produce the same 32-byte key |
| 4 | Implement `crypto.py` encrypt/decrypt/verify (`encrypt`, `decrypt`, `verify_master_password`) | `test_encrypt_decrypt_round_trip` and `test_wrong_key_raises_invalid_token` pass |
| 5 | Implement `db.py` connection and schema (3 tables: `meta`, `credentials`, `audit_log`) | `test_schema_creates_all_tables` confirms all tables exist in `sqlite_master` |
| 6 | Implement `db.py` CRUD (`get_meta`, `set_meta`, `insert_credential`, `get_credential_by_service`, `list_credentials`, `delete_credential`, `search_credentials`) | `test_credential_crud` — insert, retrieve, list, delete, confirm deletion |
| 7 | Implement `Vault.initialize()` — salt generation, key derivation, sentinel encryption | `test_initialize_creates_vault` — `is_vault_initialized()` returns `True` after call |
| 8 | Implement `Vault.open()` — load salt, re-derive key, verify sentinel, raise `AuthenticationError` on failure | `test_wrong_master_password_raises` — wrong password raises `AuthenticationError` |
| 9 | Implement `vault.add()` (encrypts before storing) and `vault.get()` (decrypts on retrieval) | `test_add_then_get_returns_plaintext` — retrieved password matches original plaintext |
| 10 | Implement `vault.list()`, `vault.delete()`, `vault.search()` | `test_search_returns_matching_services` (partial match); `test_delete_removes_entry` |
| 11 | Wire up all six Click commands (`init`, `add`, `get`, `list`, `delete`, `search`) in `cli.py` | `test_cli.py` using `CliRunner` — `pm list` on a pre-seeded vault fixture returns expected services |
| 12 | Expand `README.md`, add `*.db` to `.gitignore`, fix fixtures, tag `v0.1` | `pytest` passes at ≥80% coverage; `pm --help` works; `git tag v0.1` applied |

---

## Deliverable 3 — GitHub Repo

**Repo:** https://github.com/AbhiramNair48/PasswordManager

`CLAUDE.md`, `README.md`, and `BUILD_LOG.md` are all present at the repo root. Tagged `v0.1`.

---

## Deliverable 4 — Build Log

*(Each task entry below.)*

---

## Task 1 — Project scaffolding

- **Brief:** Create `pyproject.toml` with setuptools PEP 517 build system, `src/password_manager/__init__.py`, `tests/__init__.py`, `tests/conftest.py` with shared pytest fixtures.
- **What Claude proposed:** Standard `src/` layout with `pyproject.toml` declaring `click` + `cryptography` as runtime deps and `pytest`, `pytest-cov`, `ruff` as dev deps. Entry point `pm = "password_manager.cli:main"`.
- **What I changed before approving:** Fixed the build backend — Claude initially used `setuptools.backends.legacy:build` which doesn't exist in the installed setuptools version; corrected to `setuptools.build_meta`.
- **Verification:** `pip install -e ".[dev]"` succeeded; `python -c "import password_manager"` returned version string.
- **One thing I learned:** The `setuptools.backends.legacy` path was introduced in newer setuptools but isn't universally available — the stable `setuptools.build_meta` string is the safer default.

---

## Task 2 — CLAUDE.md

- **Brief:** Author a `CLAUDE.md` that explains the project, architecture, commands, security model, testing philosophy, and collaboration conventions for Claude.
- **What Claude proposed:** Eight-section document covering project overview, four-module architecture diagram, command reference, DB location, PBKDF2+Fernet security model, testing philosophy, coding conventions, and a "Do Not" list.
- **What I changed before approving:** Added the dependency direction rule (`cli → vault → {crypto, db}`) which makes the architecture constraint explicit and enforceable.
- **Verification:** File present at repo root with all required sections.
- **One thing I learned:** Writing CLAUDE.md before writing any feature code forces you to articulate design decisions you might otherwise leave implicit — particularly the "crypto.py has no I/O by design" constraint.

---

## Task 3 & 4 — `crypto.py` (key derivation + encrypt/decrypt)

- **Brief:** Pure-function module for `generate_salt`, `derive_key` (PBKDF2HMAC/SHA-256/480k iterations), `encrypt`, `decrypt`, `make_verification_token`, `verify_master_password`.
- **What Claude proposed:** Used `cryptography.hazmat.primitives.kdf.pbkdf2.PBKDF2HMAC` for key derivation and `cryptography.fernet.Fernet` for symmetric encryption. Key is base64url-encoded before being passed to Fernet (Fernet requires a URL-safe base64 key).
- **What I changed before approving:** Reviewed the `derive_key` return type — it returns the base64-encoded key directly (not the raw bytes), which is the correct format for Fernet. Confirmed 480,000 iterations matches NIST 2023 recommendation for SHA-256.
- **Verification:** `test_derive_key_is_deterministic`, `test_encrypt_decrypt_round_trip`, `test_wrong_key_raises_invalid_token` all passed.
- **One thing I learned:** Fernet expects a URL-safe base64-encoded 32-byte key, not raw bytes — `base64.urlsafe_b64encode(kdf.derive(...))` is the correct bridge between PBKDF2 and Fernet.

---

## Task 5 & 6 — `db.py` (schema + CRUD)

- **Brief:** SQLite layer with `get_connection`, `initialize_schema` (3 tables: `meta`, `credentials`, `audit_log`), and full CRUD for meta and credentials.
- **What Claude proposed:** `ON CONFLICT(key) DO UPDATE` for upsert in `set_meta`; same pattern for `insert_credential` to handle updates. `row_factory = sqlite3.Row` for dict-like access. WAL journal mode for better concurrent read performance.
- **What I changed before approving:** Added the `_log` helper call inside `insert_credential` so every add/update is audit-logged without the caller needing to remember. Also confirmed `os.chmod(0o600)` is in a try/except for Windows compatibility.
- **Verification:** `test_schema_creates_all_tables`, `test_credential_crud`, `test_update_existing_credential` all passed.
- **One thing I learned:** SQLite's `ON CONFLICT ... DO UPDATE` (upsert) syntax requires the conflicting column to have a UNIQUE or PRIMARY KEY constraint — in `meta` the `key` column is `PRIMARY KEY`, which satisfies this.

---

## Task 7, 8, 9 & 10 — `vault.py` (full Vault class)

- **Brief:** `Vault` class that orchestrates crypto + db. `Vault.initialize()` for first-time setup, `Vault.open()` for subsequent use with master-password verification, and `add/get/list/delete/search` for credential operations.
- **What Claude proposed:** Class-based design with `_conn` and `_key` as private instance attributes. `AuthenticationError` for wrong-password failures. `CredentialNotFoundError` for missing services. Classmethods for construction to avoid `__init__` overloading.
- **What I changed before approving:** Added `close()` method (Claude's draft omitted it, leading to ResourceWarning in tests). Also ensured `Vault.open()` calls `conn.close()` before raising `AuthenticationError` so no connection leaks on failure.
- **Verification:** All `test_vault.py` tests passed including the two hand-written security invariant tests.
- **One thing I learned:** Python doesn't guarantee `__del__` is called promptly, so explicit `close()` + `try/finally` in callers is required for resource safety — the GC can't be relied on for SQLite connections.

---

## Task 11 — `cli.py` (Click commands)

- **Brief:** Wire up six Click commands (`init`, `add`, `get`, `list`, `delete`, `search`) under a `main` group with a `--db-path` option passed via Click's context.
- **What Claude proposed:** `click.group` with `@click.pass_context`, `click.prompt(..., hide_input=True)` for master password, `click.password_option` style for stored passwords. `_open_vault(ctx)` helper to avoid repeating the master-password prompt logic.
- **What I changed before approving:** Named the `list` command function `list_cmd` (not `list`) to avoid shadowing Python's built-in `list`. Reordered the `add` command so it prompts for the stored password first, then the master password — this feels more natural to the user ("what are you storing?" before "prove it's you").
- **Verification:** `test_cli.py` (11 tests) all passed using Click's `CliRunner`.
- **One thing I learned:** Click's `CliRunner` passes input as a newline-separated string — the order of prompts in the CLI must exactly match the order of lines in the test's `input=` string, which forced me to think carefully about UX flow.

---

## Task 12 — Final polish + release

- **Brief:** Expand `README.md` with usage examples and security model; add `*.db` to `.gitignore`; fix `conftest.py` to use `yield` fixtures for proper connection cleanup; tag `v0.1`.
- **What Claude proposed:** Full README with installation, usage, security model, and project structure sections.
- **What I changed before approving:** Reviewed fixture cleanup — switched `initialized_vault` and `seeded_vault` from `return` to `yield` with `vault.close()` in the teardown, which eliminated most ResourceWarnings.
- **Verification:** `python -m pytest` → 52 passed, 97% coverage. `pm --help` works from command line.
- **One thing I learned:** pytest fixtures should use `yield` instead of `return` whenever the fixture allocates a resource that needs cleanup — it's equivalent to a try/finally block scoped to the test lifetime.

---

## Deliverable 5 — Verification (Automated + Manual)

### Automated tests

Ran `python -m pytest` — **52 tests passed, 97% coverage**.

Two tests written by hand (the core security invariants):

1. **`test_wrong_password_cannot_open_vault`** — verifies that a wrong master password raises `AuthenticationError` and cannot open the vault. This is the fundamental security guarantee of the project.
2. **`test_plaintext_never_stored_in_db`** — reads the raw SQLite file directly (bypassing the `Vault` layer) and asserts the plaintext password string does not appear in any row. Verifies encryption is applied on *write*, not just on read.

### Manual end-to-end verification

Run each of the following and confirm expected output:

```bash
pm init                              # prompted for master password twice; "Vault initialized" message
pm add github --username alice       # prompted for password + master; "Stored credential" message
pm add gmail --username alice@e.com  # second entry
pm list                              # shows github and gmail rows
pm get github                        # shows service, username, plaintext password
pm search git                        # returns github only (not gmail)
pm delete github                     # "Deleted credential" message
pm list                              # shows only gmail now
pm get github                        # error: "No credential found for 'github'"
pm --db-path /tmp/test.db init       # initializes a second vault at a custom path
pm init                              # error: "Vault already initialized"
```

Bad-input path tested: running `pm get` with the wrong master password correctly returns "Wrong master password." and exits non-zero.

---

## Deliverable 6 — AI Workflow

### Tool routing per lane

**Planning:** Used Claude Code in plan mode to design the entire architecture before writing a single line of code. Plan mode forced explicit thinking about the four-module separation (`crypto.py` has no I/O, `db.py` has no crypto, `vault.py` orchestrates, `cli.py` only delegates). This paid off immediately — I never had to refactor because the boundaries were clear upfront.

**Executing:** Used Claude Code directly for implementation. Each module was generated in one pass because the plan was specific enough (exact function signatures, DB schema, encryption flow). I reviewed every generated file before approving — catching the `build_meta` bug in Task 1 and the missing `close()` in Task 7 during review, not debugging.

**Polishing:** Used Claude Code to tighten conftest fixtures (switching `return` to `yield`) and add the `_log` call inside `insert_credential`. Small changes but the kind that prevent subtle resource bugs in production.

**Reviewing:** The test suite served as the automated reviewer — 52 tests covering unit, integration, and CLI layers. The two hand-written security invariant tests (`test_wrong_password_cannot_open_vault` and `test_plaintext_never_stored_in_db`) were the most valuable: they forced me to think about what "correct" means at the security boundary, not just at the API surface.

**One moment a tool clearly outperformed another:** When I had the `setuptools.backends.legacy` error, looking it up myself would have required several web searches and reading release notes. Claude Code identified the correct replacement (`setuptools.build_meta`) immediately with context on why the other form existed.

**One moment I switched tools mid-task:** During fixture design I started with Claude's `return`-based fixtures, ran the tests, saw ResourceWarnings, and recognized that the GC timing issue required `yield`-based teardown. I made that fix manually rather than re-prompting — it was a one-line change I understood completely and it was faster to just do it.

---

## Reflection

Building this password manager taught me more about my own blind spots than about encryption or Python — and that was the point.

**Where the agentic workflow let me ship things I couldn't have alone in 4 hours**

The single biggest accelerator was having a concrete, reviewable plan before writing a single line of code. In plan mode, Claude mapped out the four-module architecture (`crypto.py`, `db.py`, `vault.py`, `cli.py`), the PBKDF2+Fernet security model, and the full DB schema in one pass. If I'd started from scratch, I would have spent most of my time on that design work — and probably gotten the encryption flow wrong on the first try (storing the key? hashing the password directly? choosing the wrong AES mode?). Instead I spent my time *reviewing* a concrete proposal, which is a much faster loop. The 52-test suite also would have taken me the full 4 hours alone; having Claude generate the scaffolding and edge-case tests meant I could focus on the two tests that actually mattered — the security invariants I wrote myself.

**Where I had to step in and override Claude**

Three times. First, the `setuptools.backends.legacy:build` backend — Claude proposed a form that doesn't exist in my Python version. I caught it immediately because I knew what a working `pyproject.toml` looks like. Second, the `Vault` class had no `close()` method in the initial draft. I noticed because I know SQLite connections need explicit cleanup; Claude had no way to know I'd be running with Python 3.13's stricter ResourceWarning reporting. Third, the `add` CLI command prompted for the master password before the stored password. I flipped the order because I knew that felt wrong to a real user — "what are you storing?" before "prove it's you" — and that kind of UX judgment doesn't come from a spec.

**What this revealed about my own judgment and knowledge gaps**

This is the part I found most uncomfortable to sit with. The build backend error made me realize I don't actually know `pyproject.toml` anatomy well enough to write it from memory — I know *what* it does but not the exact string identifiers. That's a gap I should close, because misconfigurations in build files cause CI failures that are hard to debug remotely. The bigger gap was around encryption: I could read the PBKDF2+Fernet code Claude wrote and confirm it was correct, but I couldn't have written `base64.urlsafe_b64encode(kdf.derive(...))` from scratch and known that was the right bridge between the two APIs. I understood *why* after seeing it, but there's a difference between recognizing correctness and generating it. That gap matters — if I'm responsible for a security-critical module in an internship and I can't write the key derivation from first principles, I might not catch a subtle bug that Claude introduces. I need to study the `cryptography` library more deeply, not just know how to use it at the recipe level.

**How I'll bring this workflow into my internship**

On day one, before touching any feature code, I'll read the existing CLAUDE.md (or equivalent onboarding doc) and the test suite. The test suite tells you what the team considers a correctness guarantee; the CLAUDE.md tells you what judgment calls the team has already made. Only after that will I open an issue or PR. When I get a task, I'll use plan mode to propose an approach before implementing — not to outsource thinking, but to surface my assumptions early so a senior engineer can correct them before I've written 200 lines in the wrong direction. And I'll keep the habit from this project of writing the two most important tests myself, by hand, before asking Claude to fill in the rest. Code review is easier when you've already verified the thing that matters most.

---

## Deliverable 7 — Final Submission

**Repo:** https://github.com/AbhiramNair48/PasswordManager

**Pitch:** I built a CLI password manager in Python that encrypts your credentials with a master password using PBKDF2+Fernet — the master password is never stored, and every credential is independently encrypted before hitting SQLite. What started as "I should stop using a spreadsheet" became a real exercise in understanding cryptographic key derivation and secure-by-design architecture.

**Tag:** `v0.1` — [https://github.com/AbhiramNair48/PasswordManager/releases/tag/v0.1](https://github.com/AbhiramNair48/PasswordManager/releases/tag/v0.1)

**Sandbox notes PR:** *(Add link to your sandbox fork PR that adds notes/M3.md through notes/M7.md once created.)*
