---
name: pr
description: Use when creating, submitting, or updating a pull request, or when ready for review. Trigger for "open a PR", "submit this for review", "I'm ready for review", "merge this into main", "draft PR", "update the PR".
effort: high
tier: core
capabilities: [tool_use]
---

# /ai-pr

Pull request creation, watch loop, fix CI to green. Devin-style PR
Checkpoint — second human approval gate after the spec.

## Process

1. **Run `/ai-commit` first** if there are uncommitted changes.
2. **Pre-push gates** (in parallel — 3 lanes):
   - Lane A: `verify` deterministic
   - Lane B: docs sync (`changelog`, `release-notes`, `api-docs`)
   - Lane C: pre-push security scans (semgrep, dep-audit)
3. **Open PR** via `gh pr create` with structured body from
   `.ai-engineering/specs/spec-NNN/spec.md`. Title follows Conventional
   Commits.
4. **Link work item** — board sync transitions to `in_review`.
5. **Watch loop** — capped at `max_iterations: 3`. Each iteration:
   - Read CI checks via `gh pr checks`
   - If failing: dispatch `builder` to fix, push, repeat
   - If green: notify and stop
6. **Notify on merge** — runs `/ai-cleanup` automatically.

## Hard limits

- `max_iterations: 3` for the watch loop (no unbounded loops).
- Cold path verifications stay async — they don't block merge unless
  release-gate failed.

## Risk acceptance flow

If a finding blocks merge but the team accepts the risk: `/ai-risk-accept`
records justification + owner + spec-ref + TTL by severity. Recorded in
`decision-store.json` and emitted to `framework-events.ndjson`.
