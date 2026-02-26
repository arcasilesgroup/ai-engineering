---
spec: "024"
total: 32
completed: 11
last_session: "2026-02-26"
next_session: "Phase 2 — Platform Setup Implementations"
---

# Tasks — Sonar Scanner Integration & Platform Credential Onboarding

## Phase 0: Scaffold [S]

- [x] 0.1 Create spec directory `023-sonar-platform-onboarding/` with spec.md, plan.md, tasks.md
- [x] 0.2 Update `_active.md` to point to spec-024
- [x] 0.3 Record decisions D024-001 through D024-006 in `decision-store.json`
- [x] 0.4 Atomic commit: `spec-024: Phase 0 — scaffold spec files and activate`

## Phase 1: Foundation — Credentials Module [M]

- [x] 1.1 Add `keyring>=25.0,<26.0` to `pyproject.toml` dependencies
- [x] 1.2 Create `src/ai_engineering/credentials/__init__.py` with module docstring
- [x] 1.3 Create `src/ai_engineering/credentials/models.py` — Pydantic models: `CredentialRef`, `PlatformConfig`, `ToolsState`
- [x] 1.4 Create `src/ai_engineering/credentials/service.py` — `CredentialService` class: `store()`, `retrieve()`, `delete()`, `exists()`, `validate()` using `keyring`
- [x] 1.5 Create `src/ai_engineering/platforms/__init__.py` with module docstring
- [x] 1.6 Create `src/ai_engineering/platforms/detector.py` — `detect_platforms(root: Path) → list[str]` scanning for `.github/`, `azure-pipelines.yml`, `.azuredevops/`, `sonar-project.properties`
- [x] 1.7 Create `tests/unit/test_credentials.py` — unit tests for `CredentialService` (mock keyring backend)
- [x] 1.8 Create `tests/unit/test_platforms.py` — unit tests for `detect_platforms()` with various repo layouts
- [x] 1.9 Run `ruff check`, `ruff format --check`, `ty check` on new modules
- [x] 1.10 Atomic commit: `spec-024: Phase 1 — credentials module and platform detection`

## Phase 2: Platform Setup Implementations [L]

- [ ] 2.1 Create `src/ai_engineering/platforms/github.py` — `GitHubSetup` class: check `gh` CLI, verify auth, check scopes (`repo`, `workflow`, `read:org`), guide `gh auth login`
- [ ] 2.2 Create `src/ai_engineering/platforms/sonar.py` — `SonarSetup` class: prompt URL, open browser, prompt token (hidden), validate via `GET /api/authentication/validate`, store in keyring
- [ ] 2.3 Create `src/ai_engineering/platforms/azure_devops.py` — `AzureDevOpsSetup` class: prompt org URL, open browser, prompt PAT (hidden), validate via `GET /_apis/projects?api-version=7.0`, store in keyring
- [ ] 2.4 Define `tools.json` schema in `src/ai_engineering/credentials/models.py` — JSON schema for `{ "github": {...}, "sonar": {...}, "azure_devops": {...} }`
- [ ] 2.5 Create `src/ai_engineering/cli_commands/setup.py` — `setup_app` Typer group with `platforms`, `sonar`, `github`, `azure-devops` subcommands
- [ ] 2.6 Register `setup_app` in `src/ai_engineering/cli_factory.py` as `ai-eng setup`
- [ ] 2.7 Add post-install platform onboarding prompt to `install_cmd` in `cli_commands/core.py` (optional, skippable)
- [ ] 2.8 Create `tests/unit/test_setup_cli.py` — unit tests for CLI setup subcommands (mocked platform classes)
- [ ] 2.9 Add unit tests to `tests/unit/test_platforms.py` for GitHub, Sonar, Azure DevOps setup classes
- [ ] 2.10 Run quality checks: ruff, ty, pytest on new code
- [ ] 2.11 Atomic commit: `spec-024: Phase 2 — platform setup implementations`

## Phase 3: Sonar Gate Skill [M]

- [ ] 3.1 Create `.ai-engineering/skills/dev/sonar-gate/SKILL.md` — skill with frontmatter, procedure, output contract
- [ ] 3.2 Create `.ai-engineering/skills/dev/sonar-gate/scripts/sonar-pre-gate.sh` — Bash wrapper: check SONAR_TOKEN, run sonar-scanner, parse result
- [ ] 3.3 Create `.ai-engineering/skills/dev/sonar-gate/scripts/sonar-pre-gate.ps1` — PowerShell wrapper: check SONAR_TOKEN, run sonar-scanner, parse result
- [ ] 3.4 Create `.ai-engineering/skills/dev/sonar-gate/references/sonar-threshold-mapping.md` — quality contract ↔ Sonar property mapping
- [ ] 3.5 Create template mirrors for all 4 files in `src/ai_engineering/templates/.ai-engineering/skills/dev/sonar-gate/`
- [ ] 3.6 Create `tests/unit/test_sonar_gate.py` — unit tests for gate skip logic, threshold parsing, script argument generation
- [ ] 3.7 Atomic commit: `spec-024: Phase 3 — sonar gate skill and scripts`

## Phase 4: Integration — Existing Skills & Doctor [M]

- [ ] 4.1 Modify `install-check/SKILL.md` — add "Platform and Credentials" check section
- [ ] 4.2 Modify `audit-code/SKILL.md` — add optional Sonar gate step in procedure (with silent-skip logic)
- [ ] 4.3 Modify `release-gate/SKILL.md` — add "Sonar Quality Gate" as optional 8th dimension
- [ ] 4.4 Add `--check-platforms` flag to `doctor_cmd` in `cli_commands/core.py`
- [ ] 4.5 Add `check_platforms()` function to `doctor/service.py` — validate stored credentials via API
- [ ] 4.6 Create `tests/integration/test_platform_onboarding.py` — integration tests for full onboarding flow (mocked APIs, real filesystem)
- [ ] 4.7 Run full test suite and quality checks
- [ ] 4.8 Atomic commit: `spec-024: Phase 4 — integration with existing skills and doctor`

## Phase 5: Registration & Governance [S]

- [ ] 5.1 Add `sonar-gate` to all 6 instruction files under `### Dev Skills`
- [ ] 5.2 Update skill counts in `product-contract.md`
- [ ] 5.3 Create `.claude/commands/dev/sonar-gate.md` command wrapper + template mirror
- [ ] 5.4 Create `.github/prompts/dev-sonar-gate.prompt.md` Copilot prompt wrapper
- [ ] 5.5 Add `CHANGELOG.md` entry under `## [Unreleased] → ### Added`
- [ ] 5.6 Add cross-references: `sonar-gate` ↔ `audit-code`, `sonar-gate` ↔ `release-gate`, `sonar-gate` ↔ `install-check`
- [ ] 5.7 Atomic commit: `spec-024: Phase 5 — skill registration and governance`

## Phase 6: Verification & Close [S]

- [ ] 6.1 Run `ruff format --check src/ tests/` — PASS
- [ ] 6.2 Run `ruff check src/ tests/` — PASS
- [ ] 6.3 Run `ty check src/` — PASS
- [ ] 6.4 Run `pytest tests/ -v --cov` — ≥90% coverage
- [ ] 6.5 Run `gitleaks detect --no-banner` — 0 findings
- [ ] 6.6 Run `semgrep scan --config auto` — 0 medium+ findings
- [ ] 6.7 Run `pip-audit` — 0 known vulnerabilities
- [ ] 6.8 Run `govern:integrity-check` — 7/7 categories pass
- [ ] 6.9 Verify all 18 acceptance criteria from spec.md
- [ ] 6.10 Create `done.md` with summary, results, deferred items
- [ ] 6.11 Atomic commit: `spec-024: Phase 6 — verification and close`
