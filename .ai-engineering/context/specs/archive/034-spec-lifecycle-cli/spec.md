---
id: "034"
slug: "spec-lifecycle-cli"
status: "in-progress"
created: "2026-03-04"
---

# Spec 034 — Spec Lifecycle CLI + Closure Normalization

## Problem

Six critical misalignments and six persistent pain points degrade spec lifecycle reliability:

1. **Closure semantics inconsistent** — `spec_reset.py` considers a spec complete when `done.md` exists OR `completed==total`. The `done.md` MUST be mandatory; `completed==total` is necessary but not sufficient.
2. **Validator assumes single-pointer** — `manifest_coherence.py:69` uses regex `r'^active:\s*"([^"]+)"'` that only reads a quoted string. Fails on `active: null` (unquoted). Must be updated for multi-active (Spec C follow-up).
3. **`decisions_cmd.py` lacks `record`** — Only has `list` and `expire-check`. No subcommand for dual-write.
4. **Double parser** — `spec_reset.py:92-117` and `sync_command_mirrors.py:156-170` have nearly identical frontmatter parsers. Consolidate in `lib/parsing.py`.
5. **`_active.md` still single-pointer** — Current format: `active: null` (string, not list). Blocks parallel work (addressed in Spec C follow-up).
6. **`product-contract.md` with stale figures** — Document drifted from real state.

Pain points: frontmatter counter drift (proven wrong in specs 022, 025), decision store empty after 33 specs, no automatic verification, specs not searchable.

## Solution

Implement the **Precondition** (closure normalization + shared parser) and **Spec A** (CLI commands + enriched frontmatter) from the Architecture Evolution Plan v3.1:

1. **Shared parser** — Extract `lib/parsing.py` with `parse_frontmatter()` consumed by `spec_reset`, `sync_command_mirrors`, and new CLI commands.
2. **Closure fix** — `done.md` mandatory for closure; `completed==total` is a warning, not a trigger.
3. **`ai-eng spec verify`** — Deterministic CLI command: count checkboxes, auto-correct frontmatter counters, validate status consistency, emit `spec_verified` signal.
4. **`ai-eng spec catalog`** — Generate `_catalog.md` from all spec frontmatter with table + tag index.
5. **`ai-eng spec list`** — Show active specs with progress.
6. **`ai-eng spec compact`** — Archive old specs by removing spec/plan/tasks.md, keeping only done.md.
7. **Enriched frontmatter** — Add `size`, `tags`, `branch`, `pipeline`, `decisions` fields to spec scaffold.
8. **Validator fix** — Handle unquoted `active:` values, prepare for multi-active.
9. **Decision `record` subcommand** — Enable dual-write protocol.
10. **Signal emission** — `spec_verified`, `spec_created`, `spec_closed` events for observability.

## Scope

### In Scope

- Create `src/ai_engineering/lib/parsing.py` — shared frontmatter parser
- Refactor `spec_reset.py` — use shared parser, fix closure semantics (done.md mandatory)
- Refactor `sync_command_mirrors.py` — use shared parser
- Create `src/ai_engineering/cli_commands/spec_cmd.py` — `verify`, `catalog`, `list`, `compact` subcommands
- Register `spec` Typer subgroup in `cli_factory.py`
- Fix `validator/categories/manifest_coherence.py` — handle unquoted `active:` values
- Add `record` subcommand to `decisions_cmd.py`
- Update `skills/spec/SKILL.md` — enriched frontmatter scaffold, dual-write protocol
- Update `skills/commit/SKILL.md` — invoke `ai-eng spec verify`
- Update `skills/pr/SKILL.md` — invoke `ai-eng spec verify` + `ai-eng spec catalog`
- Update `skills/cleanup/SKILL.md` — invoke `ai-eng spec compact --dry-run`
- Update `standards/framework/core.md` — document enriched frontmatter
- Generate `context/specs/_catalog.md`
- Unit + integration tests for all new code
- Signal emission for spec lifecycle events
- Update `product-contract.md` — sync with current state

### Out of Scope

- Multi-active `_active.md` migration (Spec C — follow-up spec 035)
- Size S single-file format (Spec B — follow-up spec 036)
- Historical decision migration script (Spec D — follow-up spec 037)
- Checkpoint multi-active awareness (Spec C)

## Acceptance Criteria

1. `spec_reset` does NOT close specs without `done.md` — `completed==total` alone produces a warning.
2. `lib/parsing.py` exists and is the sole frontmatter parser used by `spec_reset`, `sync_command_mirrors`, and `spec_cmd`.
3. `ai-eng spec verify` auto-corrects `total`/`completed` counters in `tasks.md` frontmatter from checkbox counts.
4. `ai-eng spec verify` emits `spec_verified` signal via `ai-eng signals emit`.
5. `ai-eng spec catalog` generates `_catalog.md` with 33+ entries including id, slug, status, tags, created.
6. `ai-eng spec list` displays active specs with progress percentage.
7. `ai-eng spec compact --dry-run` lists archive candidates older than threshold.
8. `ai-eng decision record` writes to `decision-store.json` with required fields (id, scope, severity).
9. `validator/categories/manifest_coherence.py` handles `active: null` without error.
10. All existing tests pass; new tests cover all new functionality.
11. `ruff check`, `ruff format --check`, `uv run pytest` all pass.
12. `ai-eng validate` passes all categories.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D-034-001 | Consolidate parsers in `lib/parsing.py` | Two nearly identical frontmatter parsers cause maintenance burden and inconsistency risk |
| D-034-002 | `done.md` mandatory for closure | Prevents premature closure — `completed==total` is computed state; `done.md` is human verification |
| D-034-003 | Use Typer subgroup pattern from `decision_app` | Consistent CLI architecture; proven pattern in `cli_factory.py` |
| D-034-004 | Emit signals from CLI commands | Feeds observe dashboards (team throughput, AI decision continuity, DORA lead time) at zero token cost |
| D-034-005 | Enriched frontmatter is additive | New fields (size, tags, pipeline, branch, decisions) are optional — backward-compatible with 33 archived specs |
| D-034-006 | Compact preserves only `done.md` | `done.md` already contains summary, decisions, metrics, and learnings; full files recoverable via `git checkout` |
