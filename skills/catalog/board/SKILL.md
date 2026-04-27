---
name: board
description: Use when working with the issue tracker — discover provider, sync state on phase transitions, read current status, or map specs to issues. Trigger for "what's the status", "move this ticket", "link this to Jira", "where is this tracked". Subcommands discover, sync, status, map. Fail-open semantics.
effort: medium
tier: core
capabilities: [tool_use]
governance:
  blocking: false
---

# /ai-board

Unified board interface across Jira, Linear, GitHub Issues, Azure
Boards. Fail-open: if the board provider is unreachable, the workflow
continues; the gap is logged for later reconciliation.

## When to use

- New spec needs a tracking issue
- Phase transition (spec → plan → impl → review → release) needs the
  ticket moved
- "What's the status of X?" — read current state
- Mapping audit — confirm every spec has an issue and vice versa

## Subcommands

### `discover`

Detects the active board provider from project config:
- `.ai-engineering/manifest.toml` → `[board]` section
- Repo metadata (Jira URL in README, Linear team ID, GitHub Issues)
- IDE plugins (Linear / Jira extensions installed)

Outputs the detected provider + auth method + default project key.

### `sync <phase> <ref>`

Transitions a work item to the state matching the SDLC phase:

| Phase | Target state |
|-------|--------------|
| `spec` | `Backlog → Spec In Progress` |
| `plan` | `Spec In Progress → Planned` |
| `impl` | `Planned → In Progress` |
| `review` | `In Progress → In Review` |
| `release` | `In Review → Done` |
| `incident` | `Any → Reopened` |

Idempotent: rerunning `sync impl <ref>` when already In Progress is a
no-op.

### `status`

Reads the current state, assignee, comments since last poll. Does NOT
write. Used by other skills (`/ai-pr`, `/ai-release-gate`) to display
context.

### `map`

Cross-references `.ai-engineering/specs/spec-NNN-*.md` ↔ board issues.
Output:
- specs without an issue (gap)
- issues without a spec (orphan)
- mismatched titles / states

## Process

1. **`discover`** if no provider cached.
2. **Auth via IDE host first** (subscription piggyback), fallback to
   personal access token.
3. **Run subcommand** with idempotent semantics.
4. **Emit telemetry** — `board.synced`, `board.gap_detected`.
5. **Fail-open** — if the provider is unreachable, log
   `board.sync_skipped` and continue. Other skills do not block on
   board errors.

## Hard rules

- NEVER block a workflow on board reachability — fail-open and log.
- NEVER overwrite issue body content; append a comment instead.
- Every transition includes a comment with spec ref + commit SHA.
- Auth tokens are scoped read+transition only; never grant admin.
- Map detects drift but does not auto-fix — surface to user.

## Common mistakes

- Treating board sync as a hard gate (it's intentionally fail-open)
- Letting orphan issues / gap specs accumulate without periodic `map`
- Writing into issue bodies instead of comments (loses history)
- Forgetting to discover after switching providers
- Broad-scope auth tokens (admin not needed for sync)
