---
spec: spec-181
title: ai-pr small-model robustness
status: approved
execution_route:
  version: 1
  spec: spec-181
  executor: build
  automation: assisted
  concern_count: 1
  estimated_files: 5
  reason: "Single-concern prose restructure of one SKILL.md + deterministic mirror regen + read-only verify. No multi-stack decomposition, no source/script change."
  safe_next_command: "/ai-build"
---

# Plan — ai-pr small-model robustness

## Architecture

Pattern: **ad-hoc** (documentation/skill-surface edit — no runtime module).
The canonical file is `.claude/skills/ai-pr/SKILL.md`; the `.codex/`,
`.agents/`, `.github/` (+ cursor/opencode/antigravity) surfaces are
byte-equivalent regenerations written by `ai-eng dev sync` — never hand-edited
(Surface Axiom A1). All four edits land in the single canonical file in one
pass; mirrors regenerate; verify confirms budget + parity + the preserved
cross-skill `Step 9` anchor.

Pipeline: **standard**. TDD RED/GREEN pairing is **N/A** — this is prose, not
code; the existing `test_skill_line_budget` + `test_surface_parity` gates are
the executable contract, asserted in T-3.

## Phase 1 — Restructure (canonical SKILL.md)

- [x] T-1 — Restructure `ai-pr/SKILL.md` for small-model legibility (4 edits, one pass)
- Agent: build
- Files: .claude/skills/ai-pr/SKILL.md
- Principles applied: §10.7 Clean Code (each step = one action), §10.1 KISS (one canonical gate description)
- Patch (deterministic): none — prose judgment. Apply the four edits to distinct regions of the file:
  1. **Decision preamble (D-181-04)** — insert a short block immediately before
     `### Steps 0-6` that resolves three flags ONCE: `draft?` (invoked with
     `--draft`), `existing_pr?` (a PR already exists for the branch),
     `placeholder_spec?` (`spec.md` is the `# No active spec` placeholder).
     State that downstream steps read these resolved flags, not re-decide inline.
  2. **Pre-push gate dedup (D-181-02)** — keep `### 9. Pre-push gate` as the ONE
     canonical full description (it is the anchor `ai-build/handlers/deliver.md`
     cites). Rewrite Step 7 Lane 3 to a pointer: "Lane 3 — pre-push gate:
     dispatched concurrently here; full description in Step 9." Do NOT duplicate
     the `ai-eng gate run …` command text in both places.
  3. **Drop dead pointer step (D-181-03)** — delete the standalone `### 8.
     Instinct consolidation` (body is only "See Step 2"); ensure Step 2 already
     fully owns instinct consolidation. Leave Step 9's number intact (external
     cite); the 7→9 sequence is acceptable, OR relabel the removed slot only if
     it stays line-neutral and breaks no external cite.
  4. **Terminal self-verify block (D-181-01)** — append a final block after Step
     16 (and after the `--only/--draft` note) titled e.g. `### Self-verify
     (terminal)`. It re-reads `spec.md` + `plan.md` and asserts: placeholders
     present (SKIP when `draft?`), docs files staged, PR number exists,
     `_history.md` has the `spec-NNN` row. Any failed assertion → STOP loud.
- Gate: `## Process` retains all step headers; `grep -c '### 9\. Pre-push' = 1`;
  no standalone `### 8.` instinct step; self-verify block present;
  `wc -l .claude/skills/ai-pr/SKILL.md` ≤ 180.

## Phase 2 — Propagate + verify

- [x] T-2 — Regenerate cross-IDE mirrors from the edited canonical
- Agent: build
- Files: .codex/, .agents/, .github/ (+ cursor/opencode/antigravity surfaces)
- Principles applied: §10.4 DRY (mirrors are generated, never hand-authored)
- Patch (deterministic):
  ```sh
  ai-eng dev sync
  ```
- Gate: `pytest tests/architecture/test_surface_parity.py -q` green; mirror diff
  is byte-equivalent regen only (no manual edits).

- [x] T-3 — Verify budget, parity, cross-ref integrity, spec lint
- Agent: verify
- Files: tests/unit/test_skill_line_budget.py, tests/architecture/test_surface_parity.py
- Principles applied: §10.5 TDD (existing gates are the executable contract for a prose change)
- Patch (deterministic): none — read-only verification:
  ```sh
  pytest tests/unit/test_skill_line_budget.py tests/architecture/test_surface_parity.py -q
  grep -n "Step 9" .claude/skills/ai-build/handlers/deliver.md   # still resolves to ai-pr pre-push gate
  PYTHONPATH=tools python -m spec_lint --check .ai-engineering/specs/spec.md
  ```
- Gate: both pytest targets pass; `deliver.md` Step 9 references still valid
  (Step 9 label preserved in ai-pr SKILL.md); spec_lint BLOCKERS limited to the
  expected placeholder `plan_frontmatter_missing` (cleared once this plan is
  the active plan.md with frontmatter — i.e. now).

## Quality Outcome

**Verdict: PASS** (single fail-loud round, one bounded remediation pass spent).

Verify (deterministic, all green):
- `test_skill_line_budget` — ai-pr 156 ≤ 180; combined 414 ≤ 414.
- `test_surface_parity` — 11 regenerated surfaces byte-equivalent.
- `tests/unit/docs` + `tests/unit/config` — 127 passed (no count/catalog gate tripped).
- `spec_lint` — 0 BLOCKERS, 0 ADVISORIES.
- Cross-ref: `ai-build/handlers/deliver.md:37,120` "Step 9" still resolves (label preserved).

Review (1 adversarial agent on the diff):
- Confirmed: self-verify asserts directly catch the PR #190 skip class; preamble
  consistent with every downstream conditional (14b draft-skip, 11 placeholder,
  14 existing-PR extend, 16 draft-skip); no dangling pointers; 7→9 gap by design.
- LOW finding (fixed): Step 17 wording could be misread as skipping the
  docs-staging assert under `placeholder_spec?`. Reworded to **Always** (docs +
  PR) vs **Unless draft?/placeholder_spec?** (spec + history). Line-neutral.

Residual risk: combined budget at exactly **414/414** (zero margin) — passes
deterministically in CI; an in-loop CI fix touching the 3 skill files would
trip it (spec R4 dogfood). No blocker/critical/high open.
