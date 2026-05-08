---
name: ai-board
description: "Operates the project board (GitHub Projects v2 or Azure DevOps): discovers configuration after install (fields, state mappings, process templates) and syncs work-item state at lifecycle transitions. Trigger for 'set up the board', 'configure our ADO board', 'discover board fields', 'move this issue to in-review', 'update the board', 'mark as in progress', 'sync the work item state'. Two subcommands: `discover` (post-install configuration write) and `sync` (lifecycle state transitions). Auto-invoked via `sync` by /ai-brainstorm, /ai-build, and /ai-pr; fail-open. Not for backlog execution; use /ai-autopilot --backlog instead."
effort: high
argument-hint: "discover [--refresh] | sync <phase> <work-item-ref> [--comment text]"
tags: [board, discovery, sync, work-items, configuration]
---


# Board

## Quick start

```
/ai-board discover                       # one-time configuration discovery
/ai-board discover --refresh             # force re-discovery
/ai-board sync in_progress #45           # transition GitHub issue
/ai-board sync in_review AB#100          # transition Azure Boards work item
```

## Subcommands

`/ai-board` carries two subcommands that previously lived as separate skills (`/ai-board discover` and `/ai-board sync` — collapsed in spec-127 D-127-10 to a single skill with subcommand routing).

| Subcommand | Detail file | Purpose |
| ---------- | ----------- | ------- |
| `discover` | [`discover.md`](discover.md) | Post-install discovery of board configuration (fields, state mappings, process templates) — writes atomically to `manifest.yml`. |
| `sync`     | [`sync.md`](sync.md)         | Lifecycle state transitions on the project board (`refinement` → `ready` → `in_progress` → `in_review` → `done`). Auto-invoked by `/ai-brainstorm`, `/ai-build`, and `/ai-pr`. Fail-open: never blocks the calling workflow. |

## Workflow

The skill body owns the user-facing routing contract. Detail files own the per-subcommand procedure. Step 0 (load contexts): per `.ai-engineering/contexts/stack-context.md`.

1. Detect subcommand from the first positional argument.
2. If `discover`: read [`discover.md`](discover.md) and execute. Returns when manifest is updated atomically (or aborts with no partial write on failure).
3. If `sync`: read [`sync.md`](sync.md) and execute. Returns the configured state transition result; fail-open on auth, network, or missing-mapping errors.
4. If neither: print the subcommand table above and ask the user which mode to use.

## When to Use

- After initial framework install (`ai-eng install`) — run `/ai-board discover`.
- When board configuration changes (new project, new fields) — run `/ai-board discover --refresh`.
- At lifecycle transitions — run `/ai-board sync <phase> <ref>` (or rely on auto-invocation from `/ai-brainstorm`, `/ai-build`, `/ai-pr`).
- Suggested by `/ai-start` when board config is missing.

## Examples

### Example 1 — first-time discovery on GitHub project

User: "configure board sync for our GitHub Projects v2 board"

```
/ai-board discover
```

Detects the active Projects v2 board, queries Status field options, infers mapping from canonical phases (refinement/ready/in_progress/in_review/done), writes the config block atomically into `manifest.yml`.

### Example 2 — manual transition to in-review

User: "move issue #123 to in-review on the board"

```
/ai-board sync in_review #123
```

Looks up the project item, applies the configured state transition, optionally posts a comment with context. Fail-open if provider CLI is not authenticated.

## Common Mistakes

- Calling `/ai-board` without a subcommand — the skill needs `discover` or `sync` to dispatch.
- Treating `sync` failures as blockers — the subcommand is fail-open by design; calling skills should log and proceed.
- Running `discover` without authentication — `gh auth status` or `az account show` must succeed first.

## Integration

Called by: user directly (both subcommands); `/ai-start` (suggests `discover` when config missing); `/ai-brainstorm`, `/ai-build`, `/ai-pr` (auto-invoke `sync` for lifecycle transitions). Reads + writes: `.ai-engineering/manifest.yml` `work_items` section. Pairs with: GitHub CLI (`gh`), Azure CLI (`az`). See also: `/ai-autopilot --backlog` (consumes the configured board to absorb backlog items).

$ARGUMENTS
