---
spec: "034"
total: 37
completed: 37
last_session: "2025-07-15"
next_session: "CLOSED"
---

# Tasks — Spec Lifecycle CLI + Closure Normalization

## Phase 0: Scaffold [S]

- [x] 0.1 Create spec branch `spec-034/spec-lifecycle-cli`
- [x] 0.2 Scaffold spec.md, plan.md, tasks.md
- [x] 0.3 Activate `_active.md`
- [x] 0.4 Commit scaffold

## Phase 1: Shared Parser + Closure Fix [M]

- [x] 1.1 Create `src/ai_engineering/lib/parsing.py` with `parse_frontmatter(text) -> dict` and `count_checkboxes(text) -> tuple[int, int]`
- [x] 1.2 Refactor `spec_reset.py:92-117` to import `parse_frontmatter` from `lib/parsing`
- [x] 1.3 Fix `spec_reset.py` closure logic: `done.md` mandatory — `completed==total` alone produces warning, not closure
- [x] 1.4 Refactor `sync_command_mirrors.py:156-170` to import `parse_frontmatter` from `lib/parsing`
- [x] 1.5 Create `tests/unit/test_parsing.py` — tests for `parse_frontmatter` and `count_checkboxes`
- [x] 1.6 Update `tests/unit/maintenance/test_spec_reset.py` — tests for new closure semantics (done.md mandatory)
- [x] 1.7 Run `ruff check` + `pytest -k "parsing or spec_reset"` — all pass

## Phase 2: Spec CLI Commands [L]

- [x] 2.1 Create `src/ai_engineering/cli_commands/spec_cmd.py` with Typer app
- [x] 2.2 Implement `verify` subcommand: count checkboxes via `lib/parsing`, auto-correct `total`/`completed` in frontmatter, validate status consistency, emit `spec_verified` signal
- [x] 2.3 Implement `catalog` subcommand: traverse `context/specs/archive/*/spec.md`, extract frontmatter, generate `_catalog.md` with table + tag index
- [x] 2.4 Implement `list` subcommand: read `_active.md`, display active specs with progress
- [x] 2.5 Implement `compact` subcommand: find specs older than threshold, remove spec/plan/tasks.md keeping done.md, support `--dry-run` and `--older-than`
- [x] 2.6 Register `spec_app` in `cli_factory.py` following `decision_app` pattern
- [x] 2.7 Create `tests/unit/test_spec_cmd.py` — tests for verify (drift detection, auto-fix, signal emission), catalog (generation, tag index), compact (age calc, dry-run, done.md preservation)
- [x] 2.8 Run `ruff check` + `pytest -k "spec_cmd"` — all pass

## Phase 3: Validator Fix + Decision Record [M]

- [x] 3.1 Fix `validator/categories/manifest_coherence.py:69` — update regex to handle unquoted values (`null`, `none`) and non-string activevalues
- [x] 3.2 Add `record` subcommand to `decisions_cmd.py`: accept id, scope, severity, spec_id; write to `decision-store.json`; emit `decision_recorded` signal
- [x] 3.3 Update `tests/unit/test_decisions_cmd.py` — tests for `record` subcommand
- [x] 3.4 Add test for manifest_coherence with `active: null` — no error
- [x] 3.5 Run `ruff check` + `pytest -k "decision or manifest_coherence"` — all pass

## Phase 4: Skill + Standards Updates [M]

- [x] 4.1 Update `.ai-engineering/skills/spec/SKILL.md` — enriched frontmatter scaffold (size, tags, branch, pipeline, decisions), dual-write protocol reference
- [x] 4.2 Update `.ai-engineering/skills/commit/SKILL.md` — add `ai-eng spec verify` invocation before commit
- [x] 4.3 Update `.ai-engineering/skills/pr/SKILL.md` — add `ai-eng spec verify` + `ai-eng spec catalog` at closure
- [x] 4.4 Update `.ai-engineering/skills/cleanup/SKILL.md` — add `ai-eng spec compact --dry-run` in cleanup flow
- [x] 4.5 Update `.ai-engineering/standards/framework/core.md` — document enriched frontmatter schema
- [x] 4.6 Update `.ai-engineering/context/product/product-contract.md` — sync figures with current state
- [x] 4.7 Run `python scripts/sync_command_mirrors.py` — sync all mirrors
- [x] 4.8 Run `ai-eng validate` — all categories pass

## Phase 5: Verification + Close [S]

- [x] 5.1 Run full test suite: `uv run pytest tests/` — all pass
- [x] 5.2 Run linting: `uv run ruff check src/ tests/` — clean
- [x] 5.3 Run type check: `uv run ty check src/` — clean
- [x] 5.4 Generate initial `_catalog.md` via `ai-eng spec catalog`
- [x] 5.5 Create `done.md`, update `_active.md`, create PR
