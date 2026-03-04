---
spec: "033"
approach: "serial-phases"
---

# Plan — 18-Dimension Audit Remediation

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `src/ai_engineering/doctor/models.py` | Shared types (`CheckResult`, `CheckStatus`, `DoctorReport`) extracted from `doctor/service.py` — breaks circular imports |
| `.gitattributes` | Line-ending enforcement for cross-OS reliability |
| `.github/workflows/maintenance.yml` | Weekly CI cron for `ai-eng maintenance all` |

### Modified Files

| File | Change |
|------|--------|
| `src/ai_engineering/commands/workflows.py` | Fix gitleaks: `detect` → `protect` (line 225) |
| `.ai-engineering/state/install-manifest.json` | frameworkVersion 0.1.0→0.2.0, schemaVersion 1.1→1.2, add missing fields |
| `.ai-engineering/state/ownership-map.json` | Add `.github/prompts/**`, `.github/agents/**`, `.claude/**`, `state/session-checkpoint.json` |
| `src/ai_engineering/state/defaults.py` | Update `_DEFAULT_OWNERSHIP_PATHS` to match |
| `README.md` | Update all v2 counts to v3 actuals (34 skills, 7 agents, 37 commands) |
| `GEMINI.md` | Update all v2 counts to v3 actuals + fix `/ai:` command syntax |
| `src/ai_engineering/templates/.ai-engineering/manifest.yml` | Sync with canonical (7 agents, 34 skills) |
| `src/ai_engineering/templates/.ai-engineering/README.md` | Sync with canonical (34 skills) |
| `src/ai_engineering/policy/gates.py` | Remove `__getattr__` backward-compat section (~65 LOC) |
| `src/ai_engineering/doctor/service.py` | Remove backward-compat wrapper functions (~80 LOC); move types to `doctor/models.py` |
| `src/ai_engineering/doctor/checks/*.py` | Update imports from `doctor.service` → `doctor.models` |
| `src/ai_engineering/doctor/checks/tools.py` | Delegate to `detector/readiness.py` instead of duplicating shutil.which + pip/uv |
| `src/ai_engineering/detector/readiness.py` | Export `is_tool_available()` and `try_install()` as public API |
| `src/ai_engineering/validator/_shared.py` | Rename `CheckStatus` → `IntegrityStatus` |
| `src/ai_engineering/validator/categories/*.py` | Update `CheckStatus` → `IntegrityStatus` imports |
| `src/ai_engineering/validator/service.py` | Update `CheckStatus` → `IntegrityStatus` imports |
| `.semgrep.yml` | Add SSRF detection rule |
| `src/ai_engineering/validator/categories/mirror_sync.py` | Add root-level file patterns (`manifest.yml`, `README.md`) to `_GOVERNANCE_MIRROR` |
| `src/ai_engineering/validator/_shared.py` | Update `_GOVERNANCE_MIRROR` tuple with root-level patterns |
| `src/ai_engineering/templates/project/.claude/settings.json` | Add Windows `.venv\Scripts\*` paths alongside Unix paths |
| `src/ai_engineering/doctor/checks/__init__.py` | Update imports if needed |
| Tests (multiple) | Update imports from `gates.__getattr__` to `policy.checks.*`; update `doctor.service._check_*` to `doctor.checks.*`; fill 6 stubs |

### Mirror Copies

| Canonical | Template |
|-----------|----------|
| `.ai-engineering/manifest.yml` | `src/ai_engineering/templates/.ai-engineering/manifest.yml` |
| `.ai-engineering/README.md` | `src/ai_engineering/templates/.ai-engineering/README.md` |

## Session Map

| Phase | Description | Size | Agent |
|-------|-------------|------|-------|
| 0 | Scaffold spec files and activate | S | plan |
| 1 | P0: Fix gitleaks + security hardening | S | build |
| 2 | P1: Version sync + state files | S | build |
| 3 | P1: Doc refresh (README, GEMINI, templates) | M | build |
| 4 | P2: Extract doctor/models.py + break circular imports | M | build |
| 5 | P2: Remove backward-compat shims (gates + doctor) | M | build |
| 6 | P2: Merge tool-availability primitives | S | build |
| 7 | P2: Validator rename + mirror_sync expansion | S | build |
| 8 | P2: Cross-OS hardening (.gitattributes, Windows paths) | S | build |
| 9 | P2: CI cron + semgrep SSRF rule | S | build |
| 10 | P2: Wire check_platforms + fill test stubs | M | build |
| 11 | Verification + done.md | S | build |

## Patterns

- One atomic commit per phase: `spec-033: Phase N — <description>`.
- Run `uv run ruff check . && uv run ruff format --check .` after each code change.
- Run `uv run pytest -m unit -x` after each phase to catch regressions early.
- Mirror sync: after updating canonical governance files, sync templates immediately in same phase.
- Test migration: when removing backward-compat imports, update ALL test files in the same commit.
