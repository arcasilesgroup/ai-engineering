# Plan: spec-056 Enterprise Artifact Feed & Manifest Reorganization

## Pipeline: standard
## Phases: 3
## Tasks: 9 (build: 7, verify: 2)

### Phase 1: Configuration files
**Gate**: manifest.yml reorganized, pyproject.toml has feed section, dependabot.yml has registries example.

- [x] T-1.1: Reorganize `manifest.yml` — move user-configurable sections above `# === USER CONFIGURATION ===` separator, framework-managed sections below `# === FRAMEWORK MANAGED ===` separator. Add `artifact_feeds` pointer. Preserve all existing content, only reorder and add separators + pointer. (agent: build)
- [x] T-1.2: Add commented `[[tool.uv.index]]` section to `pyproject.toml` — insert after `[dependency-groups]` (line 27), before `[project.scripts]` (line 28). Include instructions for Azure Artifacts, JFrog, Nexus with keyring auth and CI env var fallback. (agent: build)
- [x] T-1.3: Add commented `registries` example to `.github/dependabot.yml` — add block at top of file (after `version: 2`) explaining distribution lock incompatibility and how to configure registries. (agent: build)

### Phase 2: Doctor checks (TDD)
**Gate**: All 4 feed checks implemented, registered in service.py, all tests pass.

- [x] T-2.1: Write failing tests for feed doctor checks in `tests/unit/test_doctor_feeds.py`. Test cases: (1) no feed configured = no checks emitted, (2) private feed without PyPI + clean uv.lock = OK, (3) private feed without PyPI + pypi.org in uv.lock = FAIL, (4) private feed WITH PyPI = WARN mixed sources, (5) keyring not found = FAIL, (6) keyring no backend = WARN, (7) keyring no credential = WARN, (8) CI environment = skip keyring, (9) uv.lock missing = WARN, (10) uv.lock stale = WARN. Follow existing test_doctor.py patterns (pytest.mark.unit, AAA pattern). (agent: build)
- [x] T-2.2: Implement `src/ai_engineering/doctor/checks/feeds.py` — 4 check functions: `check_feed_lock_leak`, `check_feed_mixed_sources`, `check_feed_keyring`, `check_feed_lock_freshness`. Wrapped by a single `check_feeds(target, report)` entry point matching doctor convention. Parse `pyproject.toml` with tomllib to detect `[[tool.uv.index]]` entries. Parse `uv.lock` as text to grep for pypi.org registry. Use `shutil.which("keyring")` for CLI detection. Check `os.environ` for CI detection. Note: `CheckStatus` has no SKIP — use OK with descriptive message for skip scenarios. Blocked by T-2.1. DO NOT modify test files from T-2.1. (agent: build)
- [x] T-2.3: Register feeds checks in `src/ai_engineering/doctor/service.py` — import `check_feeds` from `checks.feeds`, add call in `diagnose()` after `check_operational_readiness`. Also update `checks/__init__.py` to export `check_feeds`. (agent: build, blocked by T-2.2)

### Phase 3: Verification
**Gate**: All existing tests pass, new tests pass, ruff clean, no regressions.

- [x] T-3.1: Run full test suite `uv run pytest tests/ -x` to verify no regressions. (agent: verify)
- [x] T-3.2: Run `uv run ruff check src/ai_engineering/doctor/checks/feeds.py tests/unit/test_doctor_feeds.py` and `uv run ty check src/ai_engineering/doctor/checks/feeds.py`. Fix any lint/type issues. (agent: build)
- [x] T-3.3: Validate acceptance criteria — verify each criterion from spec against actual files. (agent: verify)
