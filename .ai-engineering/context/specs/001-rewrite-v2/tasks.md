---
total: 86
completed: 76
last_session: S15
next_session: S16
---

# Tasks: AI-Engineering Framework — Rewrite from Scratch

> **Agentic execution**: Each phase has an assigned session (SN) and agent slot.
> See `plan.md` → Session Map for full coordination model.
> Parallel phases use phase branches; serial phases work on `rewrite/v2` directly.

## Mega-Phase A: Governance Foundation (Content-First)

### Phase 0: Branch + Scaffold — `S0 · Agent-1 · ✓ COMPLETE`

- [x] **Task 0.1**: Create branch `rewrite/v2` from `origin/main`
- [x] **Task 0.2**: Create `.ai-engineering/context/specs/_active.md` — pointer to active spec `001-rewrite-v2`
- [x] **Task 0.3**: Create `specs/001-rewrite-v2/` with `spec.md`, `plan.md`, `tasks.md`

### Phase 1: Context Architecture Migration — `S1 · Agent-1 · rewrite/v2 · ✓ COMPLETE`

- [x] **Task 1.1**: Absorb `context/product/vision.md` into `framework-contract.md` — add Personas and Success Metrics sections
- [x] **Task 1.2**: Absorb `context/product/roadmap.md` into `framework-contract.md` — add Roadmap Overview and Release Model section
- [x] **Task 1.3**: Create `context/product/product-contract.md` — project living document for ai-engineering itself (dogfooding). Sections: Project Identity (name, repo, owner, status), Product Goals (current phase objectives, success criteria), Release Status (current version, next milestone, blockers), Active Spec (pointer to `specs/_active.md`), KPIs (install adoption, quality gate pass rate, agent coverage), Stakeholders, Decision Log Summary (pointer to `state/decision-store.json`)
- [x] **Task 1.4**: Delete redundant files: `vision.md`, `roadmap.md`, `rebuild-rollout-charter.md`, `framework-adoption-map.md`
- [x] **Task 1.4b**: Delete orphan planning prompts: `context/product/plan-aiEngineeringRewrite.prompt.md`, `context/product/plan-context-architecture.prompt.md` — content fully absorbed by `specs/001-rewrite-v2/`
- [x] **Task 1.5**: Delete `context/backlog/` directory entirely (absorbed by specs/)
- [x] **Task 1.6**: Delete `context/delivery/` directory entirely (absorbed by specs/done.md)
- [x] **Task 1.7**: Update `manifest.yml`, `.github/copilot-instructions.md`, `AGENTS.md`, `CLAUDE.md` — **remove references to deleted files only** (`backlog/`, `delivery/`, `vision.md`, `roadmap.md`, prompt files). Add `agents/**` to `framework_managed` in manifest. Do NOT add comprehensive content references — that is Phase 7's scope (Tasks 7.4, 7.6, 7.7)

### Phase 2: Standards Review — `S2 · Agent-1 · rewrite/v2 · ✓ COMPLETE`

- [x] **Task 2.1**: Review/update `standards/framework/core.md` — align with framework-contract.md v2, ensure it references skills and agents
- [x] **Task 2.2**: Review/update `standards/framework/stacks/python.md` — align with new tooling baseline
- [x] **Task 2.3**: Review/update quality standards (`quality/core.md`, `quality/python.md`, `quality/sonarlint.md`) — **define the quality contract** (thresholds, metrics, gate structure). Quality skills in Phase 5 will implement this contract. No back-alignment pass needed

### Phase 3: Skills — Workflows — `S3 · Agent-1 · rewrite/v2 · ✓ COMPLETE`

- [x] **Task 3.1**: Create `skills/workflows/commit.md` — `/commit` flow: stage + format + lint + gitleaks + commit + push
- [x] **Task 3.2**: Create `skills/workflows/pr.md` — `/pr` flow: stage + commit + push + create PR + auto-complete (`--auto --squash --delete-branch`)
- [x] **Task 3.3**: Create `skills/workflows/acho.md` — `/acho` alias + `/acho pr` variant

### Phase 4: Skills — SWE — `S4 · Agent-2 (4.1-4.10) · S5 · Agent-3 (4.11-4.12) · rewrite/v2 · ✓ COMPLETE`

- [x] **Task 4.1**: Create `skills/swe/debug.md`
- [x] **Task 4.2**: Create `skills/swe/refactor.md`
- [x] **Task 4.3**: Create `skills/swe/code-review.md`
- [x] **Task 4.4**: Create `skills/swe/test-strategy.md`
- [x] **Task 4.5**: Create `skills/swe/architecture-analysis.md`
- [x] **Task 4.6**: Create `skills/swe/pr-creation.md`
- [x] **Task 4.7**: Create `skills/swe/dependency-update.md`
- [x] **Task 4.8**: Create `skills/swe/performance-analysis.md`
- [x] **Task 4.9**: Create `skills/swe/security-review.md`
- [x] **Task 4.10**: Create `skills/swe/migration.md`
- [x] **Task 4.11**: Create `skills/swe/prompt-engineer.md`
- [x] **Task 4.12**: Create `skills/swe/python-mastery.md`

> **Note**: Tasks 4.11 and 4.12 are L-sized (3-5x typical skill). Each requires a dedicated agent session with extended context. Assign to Session S5 separately from the other 10 SWE skills.

### Phase 5: Skills — Quality — `S6 · Agent-4 · rewrite/v2 · ✓ COMPLETE`

- [x] **Task 5.1**: Create `skills/quality/audit-code.md` — SonarQube-like quality gate: coverage ≥80%, duplication ≤3%, no blocker/critical, complexity, maintainability
- [x] **Task 5.2**: Create `skills/quality/audit-report.md` — report template with PASS/FAIL verdict and metrics

### Phase 6: Agents — `S6 · Agent-4 · rewrite/v2 · ✓ COMPLETE`

- [x] **Task 6.1**: Create `agents/principal-engineer.md` — reviews as principal: patterns, edge cases, naming, tests, performance, mentoring improvements
- [x] **Task 6.2**: Create `agents/debugger.md` — systematic diagnosis with persistent state tracking
- [x] **Task 6.3**: Create `agents/architect.md` — architecture analysis: dependencies, boundaries, trade-offs, scaling
- [x] **Task 6.4**: Create `agents/quality-auditor.md` — executes quality gate reading standards, generates report
- [x] **Task 6.5**: Create `agents/security-reviewer.md` — OWASP, secrets, dependency vulnerabilities, auth flaws
- [x] **Task 6.6**: Create `agents/codebase-mapper.md` — maps brownfield codebase: stack, architecture, conventions, tech debt
- [x] **Task 6.7**: Create `agents/code-simplifier.md` — reduces complexity, cyclomatic complexity, readability. Reconnaissance of existing patterns before simplifying
- [x] **Task 6.8**: Create `agents/verify-app.md` — E2E single-pass finisher: build, test, lint, security, quality, product vision, goals, contract, verification

### Phase 7: Stack Instructions + Copilot Integration — `S7 · Agent-1 · rewrite/v2 · ✓ COMPLETE`

- [x] **Task 7.1**: Create `.github/instructions/python.instructions.md` — `applyTo: "**/*.py"`, build/run/test/style/security for Python with uv, ruff, ty, pytest, pip-audit
- [x] **Task 7.2**: Create `.github/instructions/testing.instructions.md` — `applyTo: "**/tests/**"`, pytest conventions, fixtures, coverage
- [x] **Task 7.3**: Create `.github/instructions/markdown.instructions.md` — `applyTo: "**/*.md"`, governance documentation conventions
- [x] **Task 7.4**: Update `.github/copilot-instructions.md` — reference skills, agents, product-contract.md, specs/
- [x] **Task 7.5**: Update `.github/copilot/code-generation.md` + `code-review.md` + `test-generation.md` + `commit-message.md` — align with quality standards and agents
- [x] **Task 7.6**: Update `AGENTS.md` — entry point connecting skills/, agents/, specs/
- [x] **Task 7.7**: Update `CLAUDE.md` — entry point for Claude Code with same references

---

**Checkpoint: Mega-Phase A complete. From here on, Copilot has 100% context.**

---

## Mega-Phase B: Python Rewrite from Scratch

### Phase 8: Python Scaffold — `S8 · Agent-1 · rewrite/v2 · ✓ COMPLETE`

- [x] **Task 8.1**: Delete all modules in `src/ai_engineering/` (keep `__init__.py`, `__version__.py`)
- [x] **Task 8.2**: Delete all tests in `tests/` (keep `__init__.py`, empty `conftest.py`)
- [x] **Task 8.3**: Update `pyproject.toml` — entry points only `ai install/update/doctor/stack/ide/version`, verify deps
- [x] **Task 8.4**: Create `.gitleaks.toml` — base secret detection rules
- [x] **Task 8.5**: Create `.semgrep.yml` — OWASP base ruleset

### Phase 9: State Layer — `S9 · Agent-1 · rewrite/v2 · ✓ COMPLETE`

- [x] **Task 9.1**: Create `src/ai_engineering/state/models.py` — Pydantic schemas: `InstallManifest`, `OwnershipMap`, `DecisionStore`, `AuditEntry`, `SourcesLock`
- [x] **Task 9.2**: Create `src/ai_engineering/state/io.py` — JSON/NDJSON read/write with stable formatting and timestamps
- [x] **Task 9.3**: Create `src/ai_engineering/state/defaults.py` — default payloads for bootstrapping
- [x] **Task 9.4**: Create `src/ai_engineering/state/decision_logic.py` — decision reuse with SHA-256 context hash
- [x] **Task 9.5**: Create `tests/unit/test_state.py` — tests for models, io, defaults, decision logic

### Phase 10: Installer — `S10 · Agent-1 · rewrite/v2 · ✓ COMPLETE`

- [x] **Task 10.1**: Create `src/ai_engineering/installer/service.py` — `install()`: creates complete `.ai-engineering/` from templates
- [x] **Task 10.2**: Create `src/ai_engineering/installer/templates.py` — template discovery by stack/IDE, create-only semantics
- [x] **Task 10.3**: Create `src/ai_engineering/installer/operations.py` — `add_stack`, `remove_stack`, `add_ide`, `remove_ide`, `list_status`
- [x] **Task 10.4**: Create `tests/unit/test_installer.py` — install on empty repo, existing repo, add/remove operations

### Phase 11: Hooks — `S11 · Agent-1 · rewrite/v2 · ✓ COMPLETE`

- [x] **Task 11.1**: Create `src/ai_engineering/hooks/manager.py` — generates cross-OS scripts (Bash + PowerShell), installs in `.git/hooks/`, detects conflicts (husky, lefthook)
- [x] **Task 11.2**: Create `tests/unit/test_hooks.py` — hook generation, conflict detection
- [x] **Task 11.3**: Create `tests/integration/test_hooks_git.py` — hooks with real `git init`

### Phase 12: Doctor — `S12 · Agent-3 · rewrite/v2 · ✓ COMPLETE`

- [x] **Task 12.1**: Create `src/ai_engineering/doctor/service.py` — validates: layout, state, hooks, tools, `gh` auth, branch policy. Supports `--fix-hooks`, `--fix-tools`
- [x] **Task 12.2**: Create `tests/unit/test_doctor.py` — remediation paths, JSON output

### Phase 13: Updater — `S13 · Agent-4 · rewrite/v2 · ✓ COMPLETE`

- [x] **Task 13.1**: Create `src/ai_engineering/updater/service.py` — dry-run by default, ownership-safe, only framework/system-managed paths
- [x] **Task 13.2**: Create `tests/unit/test_updater.py` — ownership safety, dry-run vs apply

### Phase 14: Detector + Policy — `S14 · Agent-5 · rewrite/v2 · ✓ COMPLETE`

- [x] **Task 14.1**: Create `src/ai_engineering/detector/readiness.py` — detect `gh`, `az`, Python tools (ruff, ty, gitleaks, semgrep, pip-audit), auto-remediation
- [x] **Task 14.2**: Create `src/ai_engineering/policy/gates.py` — pre-commit/commit-msg/pre-push checks, protected branch blocking, auto-remediation for missing tools
- [x] **Task 14.3**: Create `tests/unit/test_gates.py` — gate checks, branch blocking, remediation

### Phase 15: Skills + Maintenance — `S15 · Agent-6 · rewrite/v2 · ✓ COMPLETE`

- [x] **Task 15.1**: Create `src/ai_engineering/skills/service.py` — sources sync, allowlist, checksums, offline fallback, cache
- [x] **Task 15.2**: Create `src/ai_engineering/maintenance/report.py` — report generation, PR creation, staleness analysis
- [x] **Task 15.3**: Create `tests/unit/test_skills_maintenance.py` — sync, offline, allowlist, report, PR

### Phase 16: Commands + Workflows — `S16 · Agent-1 · rewrite/v2`

- [ ] **Task 16.1**: Create `src/ai_engineering/commands/workflows.py` — `run_commit_workflow`, `run_pr_workflow`, `run_pr_only_workflow`, decision-store integration, audit logging
- [ ] **Task 16.2**: Create `tests/unit/test_workflows.py` — branch blocking, PR modes, auto-complete

### Phase 17: CLI — `S16 · Agent-1 · rewrite/v2`

- [ ] **Task 17.1**: Create `src/ai_engineering/cli.py` + `cli_factory.py` + `paths.py` — Typer app with entry points
- [ ] **Task 17.2**: Create CLI commands: `cli_commands/core.py` (install, update, doctor, version) + `stack_ide.py` + `gate.py` + `skills.py` + `maintenance.py` (no `workflow.py` — D10: lifecycle commands are skills-only)
- [ ] **Task 17.3**: Create `tests/integration/test_cli.py` — CliRunner: install, doctor, update, stack, ide, gates, workflows

---

## Mega-Phase C: Mirror + CI + E2E

### Phase 18: Templates Mirror — `S17 · Agent-1 · rewrite/v2`

- [ ] **Task 18.1**: Sync `.ai-engineering/` canonical → `src/ai_engineering/templates/.ai-engineering/` (exclude state/, context/specs/ high-churn)
- [ ] **Task 18.2**: Sync `.github/`, `AGENTS.md`, `CLAUDE.md` → `src/ai_engineering/templates/project/`

### Phase 19: CI/CD — `S18 · Agent-1 · rewrite/v2`

- [ ] **Task 19.1**: Create `.github/workflows/ci.yml` — Python 3.11/3.12/3.13 × Ubuntu/Windows/macOS matrix. Steps: ruff check → ruff format --check → ty check src → pytest --cov → pip-audit → uv build
- [ ] **Task 19.2**: Create `.github/workflows/release.yml` — semantic versioning, publish to PyPI on tag
- [ ] **Task 19.3**: Create `tests/conftest.py` — shared fixtures for the entire test suite

### Phase 20: E2E + Closure — `S19 · Agent-1 · rewrite/v2`

- [ ] **Task 20.1**: Create `tests/e2e/test_install_clean.py` — install on empty repo replicates full structure
- [ ] **Task 20.2**: Create `tests/e2e/test_install_existing.py` — install on repo with code preserves team/project content
- [ ] **Task 20.3**: Create `specs/001-rewrite-v2/done.md` — closure summary, quality gate result, decisions made, learnings
