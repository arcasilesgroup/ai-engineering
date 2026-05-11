# Skills + Agents Excellence — Phase C (Deferred Bundle)

> **Status**: Draft placeholder — opened at PR-#509 merge time per spec-129
> §Risks "Deferred items rot in backlog" mitigation.
> **Predecessors**: `.ai-engineering/specs/archive/spec-129-pragmatic.md`
> (when archived after merge), original brief at
> `.ai-engineering/specs/drafts/skills-agents-excellence-refactor.md`.
> **Suggested spec id**: `spec-130` (numerically follows spec-129).
> **Suggested branch**: `spec-130/skills-excellence-phase-c`.

---

## Why this bundle exists

Spec-129 cut M6 (eval harness) and the items that depend on it (M3
SKILL.md length cuts, §22 pair-length cuts, M2 Grade A uplift, CSO
optimization passes via `/ai-prompt`). Reason: without an eval corpus
that detects triggering regressions, any description-level rewrite is
hope-driven. Building the corpus is the gate that unlocks everything
else.

This draft is the placeholder so the deferred work is tracked rather
than lost when spec-129 lands.

---

## Deferred items

### 1. M6 eval harness — eval corpus build

**Scope**: write `evals/<skill>.jsonl` for each of the 47 skills with at
least 8 should-trigger + 8 near-miss cases (original brief §3 conformance
bar set 16; spec-129 §Open Questions Q2 recommends 8 + iterate as the
MVP). Total: ~376 cases minimum (47 × 8) for MVP, or ~752 cases for the
brief-compliant 16.

**Estimated effort**: 46 h focal at the MVP size, or ~150 h at full
brief compliance. Each case requires "prompt user-realistic + skill
expected + rationale".

**Gate**: `tests/integration/test_eval_regression_gate.py` already
exists. Activate it once the corpus is in place. CI must run the gate
on every PR touching `.claude/skills/**`.

**Open question** (from spec-129): MVP 8/skill or full 16/skill?

### 2. M3 SKILL.md length cuts

**Scope**: 24 SKILL.md files currently exceed the 120-line internal
ceiling. Move "always-needed" content (Quick start, Workflow summary,
top-level decision matrix) to stay inline; move detailed reference,
code blocks, full schemas to `references/<topic>.md` with TOC.

Top 5 violators (lines):
- `ai-observe` (193)
- `ai-eval` (180)
- `ai-slides` (169)
- `ai-security` (163)
- `ai-media` (162)

**Gate**: requires the M6 eval corpus to detect triggering regressions
after the cuts. The skill-lint tool already enforces the 120-line rule
for new skills; the deferred work applies it retroactively.

### 3. §22 skill+agent pair-length cuts

**Scope**: five skill+agent pairs duplicate phase narrative across two
files. Targets: extract phase logic to `handlers/phase-*.md`; keep
identity in agent, trigger in skill.

Current vs target:
- `ai-autopilot` skill 128/agent 107 → 120/60
- `ai-verify` skill 127/agent 41 → 120/50
- `ai-plan` agent 86 → 50
- `ai-guide` agent 73 → 50
- `ai-review` already in compliance

Total savings: ~295 lines DRY.

**Gate**: `skill_lint/checks/pair_aware.py` already exists. Currently
runs in warn mode; switch to enforce after M6 corpus + a baseline
re-eval confirms no regression.

### 4. M2 Grade A description uplift

**Scope**: optimize the description field of the bottom-10 confusion-
prone skills (per original brief §2.4: `ai-entropy-gc` (now
`ai-simplify-sweep`), `ai-instinct` (now `ai-observe`), `ai-mcp-sentinel`
(now `ai-mcp-audit`), `ai-canvas` (now consolidated into `ai-visual`),
`ai-eval`, `ai-run` (deleted), `ai-platform-audit` (now `ai-ide-audit`),
`ai-governance`, `ai-skill-evolve` (now `ai-skill-tune`),
`ai-constitution`).

Run `/ai-prompt --skill <name>` over each. Commit the optimized
description back. Eval-gate the change.

**Gate**: M6 corpus required.

### 5. Pre-commit hook integration verification

**Scope**: spec-129 §Open Questions Q3 — confirm `skill_lint --check` is
actually wired into `.git/hooks/pre-commit` on contributor machines, not
just shipped. If missing, wire it. ~1 h effort.

Independent of M6 — can ship in any PR.

### 6. `_history.md` 7-col format migration

**Scope**: spec-129 §Open Questions Q4 — the spec-128 row was written
in the old format. One-time migration to the 7-col layout (ID, Title,
Status, Created, Shipped, PR, Branch).

Independent of M6 — can ship in any PR.

---

## Sequencing recommendation

1. **First**: Q5 + Q6 (pre-commit wiring + `_history.md` migration) —
   independent, ~2 h total, cleans up loose ends.
2. **Second**: M6 MVP (8/skill, ~46 h focal) — unlocks everything else.
3. **Third**: §22 pair-length cuts (~4 h) — guarded by M6 regression
   detector.
4. **Fourth**: M3 SKILL.md cuts (~8 h) — same guard.
5. **Fifth**: M2 Grade A uplift on bottom-10 only — same guard.

Each step opens a separate spec under `.ai-engineering/specs/` so the
PR surface stays reviewable.

---

## North Star preservation

The original brief §0 axes must continue to drive decisions:

1. Names self-describe.
2. Descriptions trigger on natural utterances.
3. One canonical path per intent.
4. Token-cheap by default.
5. Cohesive flow.
6. Hexagonal harness.
7. Speed-neutral.
8. Self-improving.

Spec-129 shipped axes 6 and 7 fully. This bundle closes axes 4
(token-cheap) and 8 (self-improving) once the eval corpus exists.
