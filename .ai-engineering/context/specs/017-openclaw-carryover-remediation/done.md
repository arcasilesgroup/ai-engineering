---
spec: "017"
status: "completed"
started: "2026-02-23"
completed: "2026-02-23"
branch: "feat/openclaw-carryover-remediation"
---

# Done — Spec-017

## Delivered

- Expanded skill metadata contract and docs for `requires.anyBins`, `requires.env`, `requires.config`, and `os`.
- Added runtime skill diagnostics (`ai-eng skill status`) for eligibility and missing requirements.
- Added skill-frontmatter integrity category to validator runtime (7/7 categories).
- Added workflow sanity guardrails (`actionlint` + policy checks) and CI security parity (`gitleaks`, `semgrep`, `pip-audit`).
- Added cross-OS framework smoke matrix for install/doctor/gate/hook flows.
- Added pre-push duplication + 100% coverage threshold wiring.
- Added commit trailer injection (`Ai-Eng-Gate: passed`) plus CI verification step.
- Added hook hash persistence in install manifest and integrity verification path.
- Added integration test proving secret-containing commit is blocked by hooks.
- Added dedicated install smoke workflow for clean-environment install validation.
- Reconciled Spec-014 closure consistency across `spec.md`, `tasks.md`, and `done.md`.

## Verification Evidence

- `uv run pytest tests/unit/test_validator.py tests/unit/test_skills_status.py tests/unit/test_gates.py tests/unit/test_hooks.py tests/integration/test_hooks_git.py tests/unit/test_duplication.py -q`
- `uv run pytest tests/unit/test_command_workflows.py tests/unit/test_cli_errors.py tests/integration/test_cli_install_doctor.py -q`
- `uv run ruff check src/ tests/ scripts/`
- `uv run ty check src/ai_engineering`
- `uv run ai-eng validate` (PASS 7/7 categories)

## Trade-offs

- Commit trailer enforcement is implemented through commit-msg gate mutation + CI validation on PR commit range; this is robust for governed workflows but still depends on CI to detect local hook bypass.
- Duplication detection is lightweight window-based analysis to avoid introducing another external dependency in pre-push.
- Docs-only scoping is conservative; baseline security/integrity checks remain always-on.

## Deferred

- No additional deferred items recorded at close.
