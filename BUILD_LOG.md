# BUILD_LOG.md — Password Manager Capstone

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

## AI Workflow

### Tool routing per lane

**Planning:** Used Claude Code in plan mode to design the entire architecture before writing a single line of code. Plan mode forced explicit thinking about the four-module separation (`crypto.py` has no I/O, `db.py` has no crypto, `vault.py` orchestrates, `cli.py` only delegates). This paid off immediately — I never had to refactor because the boundaries were clear upfront.

**Executing:** Used Claude Code directly for implementation. Each module was generated in one pass because the plan was specific enough (exact function signatures, DB schema, encryption flow). I reviewed every generated file before approving — catching the `build_meta` bug in Task 1 and the missing `close()` in Task 7 during review, not debugging.

**Polishing:** Used Claude Code to tighten conftest fixtures (switching `return` to `yield`) and add the `_log` call inside `insert_credential`. Small changes but the kind that prevent subtle resource bugs in production.

**Reviewing:** The test suite served as the automated reviewer — 52 tests covering unit, integration, and CLI layers. The two hand-written security invariant tests (`test_wrong_password_cannot_open_vault` and `test_plaintext_never_stored_in_db`) were the most valuable: they forced me to think about what "correct" means at the security boundary, not just at the API surface.

**One moment a tool clearly outperformed another:** When I had the `setuptools.backends.legacy` error, looking it up myself would have required several web searches and reading release notes. Claude Code identified the correct replacement (`setuptools.build_meta`) immediately with context on why the other form existed.

**One moment I switched tools mid-task:** During fixture design I started with Claude's `return`-based fixtures, ran the tests, saw ResourceWarnings, and recognized that the GC timing issue required `yield`-based teardown. I made that fix manually rather than re-prompting — it was a one-line change I understood completely and it was faster to just do it.

---

## Reflection

*(To be written after manual end-to-end testing — minimum 300 words covering: where agentic workflow accelerated delivery, where I overrode Claude, what this revealed about my own knowledge gaps, and how I'll bring this workflow into an internship.)*
