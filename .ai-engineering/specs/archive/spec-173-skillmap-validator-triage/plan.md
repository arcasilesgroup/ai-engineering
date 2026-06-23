---
title: "Plan — spec-173 Skill-Map validator triage: fix review-validator color"
spec: spec-173
slug: skillmap-validator-triage
status: approved
pipeline: trivial
execution_route:
  version: 1
  spec: spec-173
  executor: build
  automation: build
  concern_count: 1
  estimated_files: 8
  reason: "Single-concern, mechanical frontmatter value change (color magenta->pink) on one canonical agent, propagated to 7 mirror/template twins via ai-eng dev sync. No code logic, no schema, no API."
  safe_next_command: "/ai-build"
safe_next_command: "/ai-build"
---

# Plan — spec-173: fix review-validator color (magenta → pink)

## Architecture

Pattern: `ad-hoc` (config/frontmatter change, no code structure). One canonical
edit fans out to mirrors + install templates through the existing
`scripts/sync_mirrors/core.py` pipeline (`ai-eng dev sync`). No new modules, no
logic, no tests of behavior — the gate is a deterministic grep assertion that
all 8 copies carry `color: pink` and none carry `magenta`.

Source of truth: `.claude/agents/review-validator.md` (canonical). Regenerated
by `dev sync`: `.codex/agents/internal/`, `.github/agents/internal/`,
`.agents/agents/internal/`, and the four `src/ai_engineering/templates/project/...`
twins.

## Phases

### Phase 1 — Edit canonical

- [x] T-1 — Change review-validator agent color magenta → pink (canonical)
  - Agent: build
  - Files: `.claude/agents/review-validator.md:5`
  - Principles applied: §10.1 KISS (smallest correct change), §10.4 DRY (edit canonical only; mirrors are generated)
  - Patch (deterministic):
    ```diff
    --- a/.claude/agents/review-validator.md
    +++ b/.claude/agents/review-validator.md
    @@ -2,7 +2,7 @@
     name: review-validator
     description: "Adversarial validation agent. Receives ONLY the YAML finding block (no reasoning chain) and reads the code fresh to attempt disproof. Dispatched by ai-review after all specialists complete."
     model: opus
    -color: magenta
    +color: pink
     tools: [Read, Glob, Grep, Bash]
    ```
  - Gate: `grep '^color: pink' .claude/agents/review-validator.md` returns the line; no `magenta` remains in the file.

### Phase 2 — Propagate to mirrors + templates

- [x] T-2 — Regenerate mirror + template twins via dev sync
  - Agent: build
  - Files: `.codex/agents/internal/review-validator.md`, `.github/agents/internal/review-validator.md`, `.agents/agents/internal/review-validator.md`, `src/ai_engineering/templates/project/.claude/agents/review-validator.md`, `src/ai_engineering/templates/project/.codex/agents/internal/review-validator.md`, `src/ai_engineering/templates/project/.agents/agents/internal/review-validator.md`, `src/ai_engineering/templates/project/agents/internal/review-validator.md`
  - Principles applied: §10.4 DRY (single canonical source propagated by generator), §10.6 SDD (mirror/template parity is the standing contract)
  - Patch (deterministic): N/A — run the generator, do not hand-edit:
    ```
    ai-eng dev sync
    ```
  - Gate: `dev sync` exits clean (no residual drift); all 7 generated copies now show `color: pink`. Contingency: if `dev sync` does not cover the internal `review-validator` twins, hand-apply the same one-line patch to any copy still showing `magenta`, then re-run the assertion in T-3.

### Phase 3 — Verify parity

- [x] T-3 — Assert zero magenta, full pink across all 8 copies
  - Agent: verify
  - Files: all 8 `review-validator.md` copies (read-only)
  - Principles applied: §10.5 TDD (verification gate stands in for behavior tests on a config change), §10.7 Clean Code
  - Gate: `! grep -rl '^color: magenta' . --include='review-validator.md'` (no file matches) AND every `review-validator.md` copy matches `^color: pink`. Optionally re-run `sm check --json` and confirm the `review-validator` `frontmatter-invalid` color finding is gone (sm is one-off; not required to pass CI).

## Gate Criteria (plan-level)

- All 8 `review-validator.md` copies carry `color: pink`; none carry `magenta`.
- `ai-eng dev sync` clean — no uncommitted mirror/template drift.
- No file other than the `review-validator.md` set changed (Non-Goals honored:
  no effort-taxonomy, name-pair, or reference edits; no sm config added).

## Quality Outcome

All three tasks complete; single quality round, no remediation pass needed.

- **T-1/T-2/T-3 deterministic gate: PASS.** All 8 `review-validator.md` copies
  carry `color: pink`; `grep` for `^color: magenta` matches zero files.
  `ai-eng dev sync` reported "Mirrors synced" with no residual drift.
- **Scope held (Non-Goals).** Changeset touches only the 8 `review-validator.md`
  files plus spec artifacts (spec.md, plan.md, spec-173.json, brief). No
  effort-taxonomy, name-pair, reference, or sm-config changes. `dev sync` caused
  no collateral mirror edits (README capability catalog already current).
- **Excluded from delivery:** `.ai-engineering/observations/observations.yml` was
  already modified before this session (unrelated) — must NOT be committed here.
- **Review depth:** full ai-verify/ai-review swarm is disproportionate for a
  generated-config single-value change; the deterministic parity gate is the
  verification. No code logic, no secrets surface (color literal), no test
  behavior to exercise.

## Notes

- No TDD RED/GREEN code pair: this is a generated-config value change, not
  behavior. The deterministic grep gate (T-3) is the verification.
- No hooks-manifest regen: agent frontmatter is not pinned in
  `hooks-manifest.json` (that pins hook scripts only).
- Out of scope per spec-173 Non-Goals: sm's effort/name-collision/reference
  false positives are left intact by decision.
