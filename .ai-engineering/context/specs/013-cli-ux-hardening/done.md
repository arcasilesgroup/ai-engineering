---
spec: "013"
completed: "2026-02-11"
---

# Done — CLI UX Hardening

## Summary

Remediated 4 verify-app findings that degraded CLI user experience: raw tracebacks on invalid paths (F1), unvalidated stack/IDE names (F2), missing hook auto-install (F4), and noisy typer `[all]` dependency warning (F5). Finding F3 (PATH after install) accepted as expected behavior.

## Deliverables

| Finding | Fix | Files |
|---------|-----|-------|
| F5 — typer `[all]` warning | Remove `[all]` extra from dependency | `pyproject.toml`, `uv.lock` |
| F4 — hooks not auto-installed | Call `install_hooks()` in install orchestrator | `installer/service.py` |
| F1 — raw tracebacks | `_cli_error_boundary` decorator on all CLI commands | `cli_factory.py` |
| F2 — unvalidated names | `get_available_stacks()`/`get_available_ides()` + validation | `installer/operations.py` |
| F3 — PATH info | Accepted (D013-001) | No code change |

## Verification

- **Tests**: 427 passed, 0 failed, 85% coverage
- **Integrity**: Content integrity 6/6 passes
- **Acceptance criteria**: All 6 met

## Commits

1. `spec-013: Phase 0 — scaffold spec files and activate`
2. `spec-013: Phase 1 — remove typer[all] extra (F5)`
3. `spec-013: Phase 2 — auto-install hooks during install (F4)`
4. `spec-013: Phase 3 — centralized CLI error handler (F1)`
5. `spec-013: Phase 4 — stack and IDE name validation (F2)`
6. `spec-013: Phase 5 — verify and close`
