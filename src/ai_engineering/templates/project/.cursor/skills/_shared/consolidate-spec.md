# Shared Handler: --consolidate-spec

## Purpose

Delete a finalised spec file, append a canonical row to `_history.md`, and leave the canonical `spec.md` slot ready for the next iteration. Exposed by `/ai-branch-cleanup`, `/ai-pr`, and `/ai-brainstorm` as the `--consolidate-spec` action.

Single source of truth for the explicit post-merge consolidation flow (DRY §10.4). The load-bearing call lives in `.ai-engineering/scripts/spec_lifecycle.py mark_shipped`; bulk catch-up of already-SHIPPED sidecars lives in `.ai-engineering/scripts/spec_lifecycle.py consolidate_shipped`. This handler is the thin orchestration layer.

## CLI surface

`--consolidate-spec <spec-id|slug>` -- accepted by any of the three callers:

- `/ai-branch-cleanup --consolidate-spec <slug>` -- manual hygiene.
- `/ai-pr --consolidate-spec` -- auto-invoked after merge (the existing post-merge `mark_shipped` call is the same handler under the hood).
- `/ai-brainstorm --consolidate-spec <slug>` -- when resetting the canonical slot before a new brainstorm.

## Procedure

1. **Resolve the spec record.** Validate the spec id / slug resolves to a record under `.ai-engineering/state/specs/<slug>.json`. If no record is found, log a warning and STOP (the operator likely passed a stale slug).
2. **Check status.** Confirm the spec status is SHIPPED. If not:
   - Interactive mode: ask the operator for confirmation before mutating.
   - Non-interactive mode: refuse and escalate.
3. **Invoke spec lifecycle.** Run `python .ai-engineering/scripts/spec_lifecycle.py mark_shipped <spec-id> <pr> <branch>` -- this is the single load-bearing call for one spec. It walks DRAFT → APPROVED → IN_PROGRESS → SHIPPED when needed; if the sidecar is already SHIPPED it re-materializes/upserts the canonical 7-col `_history.md` row instead of duplicating it. For bulk catch-up, run `python .ai-engineering/scripts/spec_lifecycle.py consolidate_shipped`. **Fail-open**: log a warning on non-zero exit; do not block the caller.
4. **Clear the canonical slot.** Reset `.ai-engineering/specs/spec.md` to its placeholder (`# No active spec`).
5. **Clear the active plan.** Reset `.ai-engineering/specs/plan.md` to its placeholder (`# No active plan`).
6. **Emit telemetry.** Emit a `framework_operation` event with kind `spec_consolidated`, fields `{spec_id, slug, pr, branch}`.

## Failure Modes

| Condition | Action |
|-----------|--------|
| `spec_lifecycle.py` missing or non-zero exit | Log warn, continue (fail-open). Spec records may be stale until the script is restored. |
| Record not SHIPPED | Refuse and escalate -- do not pretend the record is closed. |
| `_history.md` write fails | Log warn; do not block the calling skill. |
| Slug not found | Log warn, STOP. Recommend `ls .ai-engineering/state/specs/` to the operator. |

## Callers

- `/ai-branch-cleanup --consolidate-spec <slug>` -- manual hygiene from the cleanup surface.
- `/ai-pr --consolidate-spec` -- auto-invoked post-merge (replaces the inline `mark_shipped` block; same call site).
- `/ai-brainstorm --consolidate-spec <slug>` -- Step 0a fast-path when resetting the canonical slot before a new brainstorm.

## Behavioral Negatives

- **Do NOT** re-implement the `_history.md` row format here; the canonical 7-col schema lives in `spec_lifecycle.py`.
- **Do NOT** mark non-SHIPPED records SHIPPED. Status integrity is enforced upstream.
- **Do NOT** block the caller on a fail-open script error -- log and continue.
