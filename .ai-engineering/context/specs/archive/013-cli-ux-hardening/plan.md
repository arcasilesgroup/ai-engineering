---
spec: "013"
approach: "serial-phases"
---

# Plan — CLI UX Hardening

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `tests/unit/test_cli_errors.py` | Unit tests for centralized error handling |

### Modified Files

| File | Change |
|------|--------|
| `pyproject.toml` | Remove `[all]` extra from typer dependency (F5) |
| `src/ai_engineering/installer/service.py` | Add `install_hooks()` call at end of `install()` (F4) |
| `src/ai_engineering/cli_factory.py` | Add centralized error handler for path errors (F1) |
| `src/ai_engineering/cli_commands/stack_ide.py` | Add stack/IDE name validation (F2) |
| `src/ai_engineering/installer/operations.py` | Add `get_available_stacks()` helper (F2) |
| `tests/e2e/test_install_clean.py` | Assert hooks present after install (F4) |
| `tests/integration/test_cli_install_doctor.py` | Add stack validation test cases (F2) |

### Mirror Copies

None — all changes are in source code and tests, not governance content.

## Session Map

| Phase | Size | Description |
|-------|------|-------------|
| 0 | S | Scaffold spec files + activate |
| 1 | S | F5 — remove typer `[all]` extra, update lockfile |
| 2 | S | F4 — auto-install hooks in installer service |
| 3 | M | F1 — centralized error handler in cli_factory |
| 4 | M | F2 — stack/IDE name validation |
| 5 | S | Close — full test suite, integrity check, done.md |

## Patterns

- **Error handling**: Use Typer's error callback mechanism in the app factory to catch and format exceptions before they reach the user.
- **Validation**: Use the existing stack definitions (from operations.py or standards directory scanning) to build the allowed-values list dynamically.
- **Hook install**: Reuse the existing hook installation logic already present in the doctor flow.
- **Testing**: Follow existing test patterns — `unittest.mock` for unit tests, subprocess-based for e2e.
