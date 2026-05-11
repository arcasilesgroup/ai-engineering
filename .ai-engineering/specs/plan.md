---
spec: spec-132
title: spec-132 — CLI UX & Architecture Overhaul (single-PR full-brief delivery)
pipeline: autopilot
phases: 6
sub-specs: 7
status: shipped-pending-pr-merge
---

# Plan — spec-132 CLI UX Overhaul (aggregate of spec-128/129/131/132 in PR #509)

> Per spec-131 D-131-13, the deep plan lives per-sub-spec under
> `.ai-engineering/runtime/autopilot/sub-NNN/plan.md`. This file is
> the aggregate index that captures wave outcomes after the
> autopilot pipeline completed. Wave 1-4 commits are in-tree; the
> Phase 5 closure sweep landed a follow-up commit after operator
> review identified blockers + criticals + highs. PR #509 carries
> the full delivery.

## Sub-spec waves shipped

- **Wave 1** (cc8e73d5) — sub-001 + sub-007: markdown canon reset
  (CANONICAL.md template, byte-equivalent mirrors) and spec-lint
  validator landing.
- **Wave 2** (f6143c7d) — sub-002 + sub-004 + sub-006: single quality
  loop, hooks robustness (no-verify shlex matcher, sub-agent
  positive allow-list, trusted-script lane), naming alignment.
- **Wave 3** (8280d1e6) — sub-005: docs evangelism + cross-IDE audit
  extension for Antigravity.
- **Wave 4** (3dd13073) — sub-003: model dispatch economics (effort
  vocabulary cheap/mid/high + model_tier haiku/sonnet/opus across
  every SKILL.md frontmatter; docs/model-dispatch-policy.md SSOT).

## Phase 5 closure sweep

Operator quality-loop on the full Wave-1..4 changeset surfaced
8 blockers + 5 criticals + 4 highs + 2 review-highs + 1 guard-concern.
Operator chose Option A: surgical fix sweep. The single closure
commit on top of Wave 4 covers:

- B1 — refactor `apply_effort_model_tier.py` to drop the
  `# noqa: E402` suppression via `importlib.import_module`.
- B2 — copy `no-verify-guard.py` into the templates tree; align the
  template `settings.json` PreToolUse + deny-rule shape; sync
  `prompt-injection-guard.py` byte-equivalence.
- B3 — rotate plan.md to the per-sub-spec index pattern (this file).
- B4 — refresh `tool_capabilities` state.db projection via
  `write_framework_capabilities` (47 skills + 9 agents + 56 cards).
- B5 — document the `settings.json` shlex-matcher deviation as a
  risk-accept in CHANGELOG (option-a: narrow globs + runtime hook).
- C1 — recalibrate 10+ consumer tests to the new spec-131 contract
  (CONSTITUTION project-identity-only, 4-verb chain,
  `.gemini/GEMINI.md` deletion, byte-equivalent mirror contract,
  TDD migration to CANONICAL.md §10.5).
- C2 — elevate `ai-mcp-audit` to `effort: high` / `model_tier: opus`
  per spec-107 D-107-08 (security skill).
- H1 — fix 18 ruff errors (no `# noqa`; refactor each).
- H2 — trim `ai-autopilot/SKILL.md` to ≤120 lines via
  `references/examples.md` progressive disclosure.
- Review-H1 — remove `cat` from the sub-agent positive allow-list;
  add regression tests.
- Review-H2 — fix scaffold-skill.sh frontmatter to `effort: mid` +
  `model_tier: sonnet` across all 8 mirror+template copies.
- Guard-Concern — correct CHANGELOG Wave-2 wording so trusted-script
  lane status reflects reality (mechanism shipped; session_bootstrap
  enrolment deferred).
- Guard-Warn — clarify phase-quality.md retry-clause: dispatch-level
  operational retry is distinct from a quality-finding retry, which
  Non-Goal #13 forbids.

## Acceptance

`uv run pytest tests/` runs green after the closure sweep. The
4 mirror surfaces (AGENTS.md / CLAUDE.md / GEMINI.md /
copilot-instructions.md) are byte-equivalent per spec-131 D-131-04.
The 4-verb chain (`/ai-brainstorm → /ai-plan → /ai-build → /ai-pr`)
appears verbatim in every mirror. `python -m spec_lint --check
.ai-engineering/specs/spec.md` reports 0 blockers. PR #509 is the
delivery vehicle.
