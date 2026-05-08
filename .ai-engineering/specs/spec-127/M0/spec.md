---
id: sub-001
parent: spec-127
milestone: M0
title: "Foundations + spec lifecycle + voice updates"
status: planning
files:
  - .ai-engineering/scripts/spec_lifecycle.py
  - tests/unit/specs/test_spec_lifecycle.py
  - tests/unit/docs/test_canonical_docs_consistency.py
  - .ai-engineering/specs/_history.md
  - .claude/skills/ai-brainstorm/SKILL.md
  - .claude/skills/ai-pr/SKILL.md
  - .claude/skills/ai-cleanup/SKILL.md
  - AGENTS.md
  - CLAUDE.md
depends_on: []
---

# Sub-Spec 001: M0 — Foundations + spec lifecycle + voice updates

## Scope

Ship the spec lifecycle automation script (`spec_lifecycle.py`) with idempotent
state transitions (`start_new`, `mark_shipped`, `archive`, `sweep`, `status`),
wire it into `/ai-brainstorm`, `/ai-pr`, and `/ai-cleanup --specs`. Update
`_history.md` to the 7-column layout (ID, Title, Status, Created, Shipped, PR,
Branch) preserving backward-compat read of legacy 6-col rows. Rewrite AGENTS.md
to ≤80 lines (Boris+Karpathy voice, two-file state pattern, 46 skills + 23
agents post-rename) and CLAUDE.md (hot-path-first reorder, governance hooks
section enumerating `skill_lint`, `test_layer_isolation`, eval gate, perf
budgets). Verify via `tests/unit/docs/test_canonical_docs_consistency.py`.

## Exploration

### Scope summary

M0 ships the deterministic spec-lifecycle FSM + lifecycle-aware history table +
voice-rewritten root governance docs. Five integration points: one new script,
two new test modules, one history projection, three SKILL.md wire-ins, two doc
rewrites.

### Current-state evidence

**Lifecycle script — does not exist.** `find . -name spec_lifecycle.py` → 0
results. Greenfield (stdlib only, <500ms budget per umbrella plan).

**Locking primitive — exists, reuse it.**
`.ai-engineering/scripts/hooks/_lib/locking.py` exposes `artifact_lock(project_root,
artifact_name)` (cross-platform fcntl/msvcrt advisory lock). Brief §15.2
mandates reuse. Decision: import in place — no relocation in M0.

**`_history.md` — currently 5 columns, NOT 6.** File: 336 lines, header
`| ID | Title | Status | Created | Branch |`. Plan must read N ∈ {5, 6, 7}
and write canonical 7-col `(ID, Title, Status, Created, Shipped, PR, Branch)`
per brief §15.4. Existing rows have `Status` populated; map to FSM states.
Idempotent insertion after header separator; free-form retro sections below
`---` preserved verbatim.

**AGENTS.md — 73 lines today** (≤80 target met by removal). Skill count line 29
"Skills (50)" → "46". Agent count line 40 "Agents (10)" → "23" (verify via
`manifest.yml`). Voice → CAPS imperatives + bold openers + arrow notation per
brief §18.1. Two-file state pattern: surface `plan.md` + `LESSONS.md`.

**CLAUDE.md — 239 lines; reorder, not full rewrite.** Brief §18.3: hot-path
discipline → Step 0 → tooling rules. Required new section "Governance hooks"
enumerating `skill_lint`, `test_layer_isolation`, eval regression gate,
`tests/perf/test_hot_path_budgets.py`. Voice → imperative-bold.

**SKILL.md wire-in points.**
- `ai-brainstorm/SKILL.md` (71 lines): insert step 1.0 (`start_new` call,
  fail-open) before evidence sweep. ~3 lines.
- `ai-pr/SKILL.md` (135 lines): replace step 11's manual `_history.md` row
  append with `mark_shipped` post-merge (step 16, after `state == MERGED`).
  ~5 lines.
- `ai-cleanup/SKILL.md` (91 lines): add Phase 3 `--specs` invoking `sweep()`;
  extend Quick Reference + frontmatter. ~10 lines.

**Test scaffolding — directories exist, target files do not.**
- `tests/unit/specs/` exists with 4 unrelated tests; no `test_spec_lifecycle.py`.
- `tests/unit/docs/` exists with `test_skill_references_exist.py`; no
  `test_canonical_docs_consistency.py`.

**State sidecar.** `.ai-engineering/state/spec-lifecycle.json` per brief §15.2.
Directory exists; no FSM file yet. `framework_event` NDJSON observability:
brief §15.2 references `_lib/observability.append_framework_event`. Confirm in
T-2.2.b; fallback is direct NDJSON append with `artifact_lock` guard.

### Integration points (touch surface)

| File | Action | Risk |
|---|---|---|
| `.ai-engineering/scripts/spec_lifecycle.py` | NEW (~250 LOC, stdlib) | Low |
| `tests/unit/specs/test_spec_lifecycle.py` | NEW (RED first) | None |
| `tests/unit/docs/test_canonical_docs_consistency.py` | NEW (RED first) | None |
| `.ai-engineering/specs/_history.md` | Migrate 5→7 col + preserve legacy | Medium |
| `.claude/skills/ai-brainstorm/SKILL.md` | Insert `start_new` call | Low |
| `.claude/skills/ai-pr/SKILL.md` | Replace manual row append | Medium |
| `.claude/skills/ai-cleanup/SKILL.md` | Add `--specs` phase | Low |
| `AGENTS.md` | Rewrite ≤80 lines | Medium |
| `CLAUDE.md` | Reorder + Governance hooks section | Low |

### Blockers / open decisions

1. **Final agent count** — confirm via `manifest.yml` before AGENTS.md commit.
2. **Locking module path** — import in place (no relocation).
3. **observability.append_framework_event** — existence not confirmed; fallback
   direct NDJSON append.

### TDD pairing

- T-2.1 (RED) → T-2.2 (GREEN, lifecycle script)
- T-2.5 (RED) → T-2.6/T-2.7 (GREEN, AGENTS.md + CLAUDE.md)

### Hot-path budget

All `spec_lifecycle.py` atomic ops <500ms (asserted in
`tests/unit/specs/test_spec_lifecycle.py` perf case).
