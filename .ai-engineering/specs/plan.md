# Plan: spec-101 First-Run Experience Hardening

## Pipeline: full
## Phases: 4
## Tasks: 11 (build: 11, verify: 0, guard: 0)

### Phase 1: Provider-Scoped Tooling And Provider Truth
**Gate**: GitHub-first install/provider flows stop reporting or auto-installing Azure tooling, and provider surfaces read from `ai_providers.enabled`.
- [x] T-1.1: Add regression tests for provider-scoped install/readiness tool selection and provider CLI truth sources (agent: build)
- [x] T-1.2: Refactor readiness/tool helpers to separate provider-required tooling from stack-required tooling without changing unrelated stacks (agent: build)
- [x] T-1.3: Update installer operational phases so only the active VCS provider is auto-installed or surfaced as a manual step (agent: build)
- [x] T-1.4: Switch provider CLI output and related install/provider summaries to `ai_providers.enabled` and `ai_providers.primary` (agent: build)

### Phase 2: Hook Runtime Boundary Hardening
**Gate**: Framework-managed Copilot helper hooks execute through a shared framework runtime contract instead of arbitrary `python` / `python3` resolution on PATH.
- [x] T-2.1: Add regression tests that simulate hostile host `python` / `python3` resolution for Copilot hook helpers and doctor hook diagnostics (agent: build)
- [x] T-2.2: Introduce a shared framework-runtime launcher contract for hook helpers on Bash and PowerShell (agent: build)
- [x] T-2.3: Refactor Copilot hook wrappers to use the shared launcher and remove direct helper execution through raw `python` / `python3` lookups (agent: build)
- [x] T-2.4: Update doctor hook diagnostics and remediation messaging to validate the new runtime contract instead of a generic `python3` PATH check (agent: build)

### Phase 3: First-Run UX And Docs Parity
**Gate**: Install output, doctor guidance, onboarding docs, and generated instruction files converge on `ai-eng doctor -> /ai-start` and advertise only real doctor remediation commands.
- [x] T-3.1: Update install CLI next-step guidance and first-run summaries to point users through `ai-eng doctor` and `/ai-start` (agent: build)
- [x] T-3.2: Update README, GETTING_STARTED, CLI reference, solution-intent, and generated instruction/docs surfaces to remove stale `/ai-brainstorm`-first and `--fix-tools` / `--fix-hooks` guidance (agent: build)
- [x] T-3.3: Add regression coverage for first-run command guidance and doctor remediation messaging across CLI and documentation-facing tests (agent: build)

### Phase 4: Evidence Convergence
**Gate**: Targeted installer/provider/hooks/doctor suites pass locally before the full repository verification run.
- [x] T-4.1: Run targeted unit and integration suites covering installer, provider, doctor, hooks, and first-run CLI behavior; fix regressions until green (agent: build)

## Review
- Implemented provider-scoped readiness and operational tooling so GitHub-first installs no longer surface Azure CLI unless Azure DevOps is the configured VCS.
- Added a shared Copilot hook runtime launcher for Bash and PowerShell and switched framework-owned hook wrappers to that launcher.
- Hardened `doctor` messaging so fix guidance is capability-based and first-run output consistently points to `ai-eng doctor -> /ai-start`.
- Updated top-level onboarding docs to align with the same first-run sequence and removed stale `--fix-tools` / `--fix-hooks` guidance.
- Verification evidence:
  - `uv run pytest tests/unit/test_installer_tools.py tests/unit/test_provider_cli.py tests/unit/test_readiness.py tests/unit/test_installer.py tests/unit/test_doctor_phases_hooks.py tests/integration/test_install_operational_flows.py tests/integration/test_provider_commands.py tests/integration/test_readiness_integration.py tests/integration/test_framework_hook_emitters.py tests/integration/test_cli_command_modules.py tests/integration/test_cli_install_doctor.py tests/e2e/test_install_pipeline.py -q`
  - `uv run ruff check src/ tests/`
  - `uv run ruff format --check src/ tests/`
  - `uv run ty check src/`
  - `uv run pytest tests/unit tests/integration tests/e2e -n auto --dist worksteal --cov=src/ai_engineering --cov-report=term-missing --cov-report=xml:/tmp/coverage.xml --cov-fail-under=80`
  - `gitleaks detect --source . --config .gitleaks.toml --no-banner --redact --no-git`
  - `semgrep --config .semgrep.yml --error --json .`
  - `uv run pip-audit`
- Note: `gitleaks detect` against full git history still reports two historical false positives from commit `077ea12` in paths no longer present in the working tree. The current tree and this change set are clean under `--no-git`.
