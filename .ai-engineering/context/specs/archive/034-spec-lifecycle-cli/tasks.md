---
spec: "034"
total: 32
completed: 0
last_session: "2026-03-04"
next_session: "Phase 0 — Scaffold"
---

# Tasks — Spec Lifecycle CLI + Closure Normalization

## Phase 0: Scaffold [S]

- [ ] 0.1 Create spec branch `spec-034/spec-lifecycle-cli`
- [ ] 0.2 Scaffold spec.md, plan.md, tasks.md
- [ ] 0.3 Activate `_active.md`
- [ ] 0.4 Commit scaffold

## Phase 1: Shared Parser + Closure Fix [M]

- [ ] 1.1 Create `src/ai_engineering/lib/parsing.py` with `parse_frontmatter(text) -> dict` and `count_checkboxes(text) -> tuple[int, int]`
- [ ] 1.2 Refactor `spec_reset.py:92-117` to import `parse_frontmatter` from `lib/parsing`
- [ ] 1.3 Fix `spec_reset.py` closure logic: `done.md` mandatory — `completed==total` alone produces warning, not closure
- [ ] 1.4 Refactor `sync_command_mirrors.py:156-170` to import `parse_frontmatter` from `lib/parsing`
- [ ] 1.5 Create `tests/unit/test_parsing.py` — tests for `parse_frontmatter` and `count_checkboxes`
- [ ] 1.6 Update `tests/unit/maintenance/test_spec_reset.py` — tests for new closure semantics (done.md mandatory)
- [ ] 1.7 Run `ruff check` + `pytest -k "parsing or spec_reset"` — all pass

## Phase 2: Spec CLI Commands [L]

- [ ] 2.1 Create `src/ai_engineering/cli_commands/spec_cmd.py` with Typer app
- [ ] 2.2 Implement `verify` subcommand: count checkboxes via `lib/parsing`, auto-correct `total`/`completed` in frontmatter, validate status consistency, emit `spec_verified` signal
- [ ] 2.3 Implement `catalog` subcommand: traverse `context/specs/archive/*/spec.md`, extract frontmatter, generate `_catalog.md` with table + tag index
- [ ] 2.4 Implement `list` subcommand: read `_active.md`, display active specs with progress
- [ ] 2.5 Implement `compact` subcommand: find specs older than threshold, remove spec/plan/tasks.md keeping done.md, support `--dry-run` and `--older-than`
- [ ] 2.6 Register `spec_app` in `cli_factory.py` following `decision_app` pattern
- [ ] 2.7 Create `tests/unit/test_spec_cmd.py` — tests for verify (drift detection, auto-fix, signal emission), catalog (generation, tag index), compact (age calc, dry-run, done.md preservation)
- [ ] 2.8 Run `ruff check` + `pytest -k "spec_cmd"` — all pass

## Phase 3: Validator Fix + Decision Record [M]

- [ ] 3.1 Fix `validator/categories/manifest_coherence.py:69` — update regex to handle unquoted values (`null`, `none`) and non-string activevalues
- [ ] 3.2 Add `record` subcommand to `decisions_cmd.py`: accept id, scope, severity, spec_id; write to `decision-store.json`; emit `decision_recorded` signal
- [ ] 3.3 Update `tests/unit/test_decisions_cmd.py` — tests for `record` subcommand
- [ ] 3.4 Add test for manifest_coherence with `active: null` — no error
- [ ] 3.5 Run `ruff check` + `pytest -k "decision or manifest_coherence"` — all pass

## Phase 4: Skill + Standards Updates [M]

- [ ] 4.1 Update `.ai-engineering/skills/spec/SKILL.md` — enriched frontmatter scaffold (size, tags, branch, pipeline, decisions), dual-write protocol reference
- [ ] 4.2 Update `.ai-engineering/skills/commit/SKILL.md` — add `ai-eng spec verify` invocation before commit
- [ ] 4.3 Update `.ai-engineering/skills/pr/SKILL.md` — add `ai-eng spec verify` + `ai-eng spec catalog` at closure
- [ ] 4.4 Update `.ai-engineering/skills/cleanup/SKILL.md` — add `ai-eng spec compact --dry-run` in cleanup flow
- [ ] 4.5 Update `.ai-engineering/standards/framework/core.md` — document enriched frontmatter schema
- [ ] 4.6 Update `.ai-engineering/context/product/product-contract.md` — sync figures with current state
- [ ] 4.7 Run `python scripts/sync_command_mirrors.py` — sync all mirrors
- [ ] 4.8 Run `ai-eng validate` — all categories pass

## Phase 5: Verification + Close [S]

- [ ] 5.1 Run full test suite: `uv run pytest tests/` — all pass
- [ ] 5.2 Run linting: `uv run ruff check src/ tests/` — clean
- [ ] 5.3 Run type check: `uv run ty check src/` — clean
- [ ] 5.4 Generate initial `_catalog.md` via `ai-eng spec catalog`
- [ ] 5.5 Create `done.md`, update `_active.md`, create PR
