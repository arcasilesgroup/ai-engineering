---
spec: "033"
total: 48
completed: 0
last_session: "2026-03-04"
next_session: "Phase 1 — P0 security fix"
---

# Tasks — 18-Dimension Audit Remediation

## Phase 0: Scaffold [S]

- [ ] 0.1 Create spec branch `spec-033/audit-remediation`
- [ ] 0.2 Scaffold spec.md, plan.md, tasks.md
- [ ] 0.3 Activate `_active.md`
- [ ] 0.4 Commit scaffold

## Phase 1: P0 — Security Fix [S]

- [ ] 1.1 Fix `workflows.py:225`: change `gitleaks detect --staged` to `gitleaks protect --staged`
- [ ] 1.2 Add/update test in `test_command_workflows.py` verifying correct gitleaks subcommand
- [ ] 1.3 Add SSRF semgrep rule to `.semgrep.yml`
- [ ] 1.4 Run `ruff check` + `ruff format --check` + `pytest -m unit -x`

## Phase 2: P1 — Version Sync + State Files [S]

- [ ] 2.1 Update `install-manifest.json`: `frameworkVersion` 0.1.0→0.2.0
- [ ] 2.2 Update `install-manifest.json`: `schemaVersion` 1.1→1.2; add missing fields (`aiProviders`, `cicd`, `branchPolicy`, `operationalReadiness`, `release`)
- [ ] 2.3 Update `state/defaults.py` `_DEFAULT_OWNERSHIP_PATHS`: add `.github/prompts/**`, `.github/agents/**`, `.claude/**`, `state/session-checkpoint.json`
- [ ] 2.4 Regenerate `ownership-map.json` to include new paths
- [ ] 2.5 Fix `decision-store.json` key: `schema_version` → `schemaVersion` (camelCase consistency)
- [ ] 2.6 Run tests to verify state files load correctly

## Phase 3: P1 — Doc Refresh [M]

- [ ] 3.1 Update `README.md`: skill count 47→34, agent count 6→7, agent table to v3 roster, slash command count 53→37, copilot counts, remove v2 skill list
- [ ] 3.2 Update `GEMINI.md`: skill count 47→34, agent count 6→7, agent table to v3, command syntax `ai-commit`→`/ai:commit`, token budgets
- [ ] 3.3 Sync template `manifest.yml` with canonical (7 agents, 34 skills, execute agent)
- [ ] 3.4 Sync template `README.md` with canonical (34 skills, plan/ directory)
- [ ] 3.5 Update `governance/SKILL.md`: fix CLI references (`ai-eng integrity`→`ai-eng validate --category`)
- [ ] 3.6 Run `ai-eng validate` to verify mirror sync passes

## Phase 4: P2 — Extract doctor/models.py [M]

- [ ] 4.1 Create `src/ai_engineering/doctor/models.py` with `CheckResult`, `CheckStatus`, `DoctorReport` extracted from `doctor/service.py`
- [ ] 4.2 Update `doctor/service.py` to import from `doctor/models.py`
- [ ] 4.3 Update all `doctor/checks/*.py` to import from `doctor.models` instead of `doctor.service`
- [ ] 4.4 Update `doctor/checks/__init__.py` if needed
- [ ] 4.5 Run tests to verify no import regressions

## Phase 5: P2 — Remove Backward-Compat Shims [M]

- [ ] 5.1 Migrate `test_gates.py` imports from `gates.__getattr__` names to `policy.checks.*` direct imports
- [ ] 5.2 Migrate `test_gates_integration.py` imports similarly
- [ ] 5.3 Remove `__getattr__` section from `policy/gates.py` (~65 LOC)
- [ ] 5.4 Migrate `test_doctor*.py` patches from `doctor.service._check_*` to `doctor.checks.*` direct patches
- [ ] 5.5 Remove backward-compat wrapper functions from `doctor/service.py` (~80 LOC)
- [ ] 5.6 Remove re-exported constants (`_REQUIRED_DIRS`, `_TOOLS`, etc.) from `doctor/service.py`
- [ ] 5.7 Run full test suite to verify no regressions

## Phase 6: P2 — Merge Tool-Availability Primitives [S]

- [ ] 6.1 Export `is_tool_available()` and `try_install()` as public functions in `detector/readiness.py`
- [ ] 6.2 Refactor `doctor/checks/tools.py` to delegate to `detector.readiness` instead of duplicating `shutil.which` + pip/uv logic
- [ ] 6.3 Update tests that mock `doctor.checks.tools.is_tool_available` to use new import paths
- [ ] 6.4 Run tests

## Phase 7: P2 — Validator Rename + Mirror Sync Expansion [S]

- [ ] 7.1 Rename `CheckStatus` → `IntegrityStatus` in `validator/_shared.py`
- [ ] 7.2 Update all `validator/categories/*.py` imports
- [ ] 7.3 Update `validator/service.py` imports
- [ ] 7.4 Add `manifest.yml` and `README.md` root-level patterns to `_GOVERNANCE_MIRROR` in `validator/_shared.py`
- [ ] 7.5 Run `ai-eng validate` to verify expanded mirror sync works

## Phase 8: P2 — Cross-OS Hardening [S]

- [ ] 8.1 Create `.gitattributes` with LF enforcement for `*.sh`, `*.py`, `*.yml`, `*.yaml`, `*.md`, `*.json`
- [ ] 8.2 Update `templates/project/.claude/settings.json`: add `.venv\Scripts\*` paths for Windows alongside `.venv/bin/*`
- [ ] 8.3 Run tests

## Phase 9: P2 — CI Cron + SSRF Rule [S]

- [ ] 9.1 Create `.github/workflows/maintenance.yml` with weekly cron schedule running `ai-eng maintenance all`
- [ ] 9.2 Verify SSRF rule added in Phase 1 covers `requests.get($URL)` patterns
- [ ] 9.3 Run CI lint check on new workflow file

## Phase 10: P2 — Wire check_platforms + Fill Test Stubs [M]

- [ ] 10.1 Add `--check-platforms` flag to `diagnose()` in `doctor/service.py`; wire `check_platforms()` when flag is set
- [ ] 10.2 Fill test stub: `test_version_check_fail_when_deprecated` in `test_doctor_integration.py`
- [ ] 10.3 Fill test stub: `test_returns_false_on_all_failures` in `test_readiness_integration.py`
- [ ] 10.4 Fill test stub: `test_project_template_root_missing_raises` in `test_installer_integration.py`
- [ ] 10.5 Fill test stub: `test_skills_cli_branches` in `test_cli_command_modules.py`
- [ ] 10.6 Fill test stub: `test_returns_python_when_manifest_empty_stacks` in `test_gates_integration.py`
- [ ] 10.7 Fill test stub: `test_pr_creation_returns_false_on_failure` in `test_skills_integration.py`
- [ ] 10.8 Run full test suite

## Phase 11: Verification + Close [S]

- [ ] 11.1 Run `uv run ruff check . && uv run ruff format --check .`
- [ ] 11.2 Run `uv run pytest -m unit` — all pass
- [ ] 11.3 Run `uv run pytest -m integration` — all pass
- [ ] 11.4 Run `uv run ai-eng validate` — all categories pass
- [ ] 11.5 Verify all 17 acceptance criteria from spec.md
- [ ] 11.6 Create done.md
