---
name: ai-board
description: "Operates the project board (GitHub Projects v2 or Azure DevOps): discovers configuration after install (fields, state mappings, process templates) and syncs work-item state at lifecycle transitions. Trigger for 'set up the board', 'configure our ADO board', 'discover board fields', 'move this issue to in-review', 'update the board', 'mark as in progress', 'sync the work item state'. Two subcommands: `discover` (post-install configuration write) and `sync` (lifecycle state transitions). Auto-invoked via `sync` by /ai-brainstorm, /ai-build, and /ai-pr; fail-open. Not for backlog execution; use /ai-autopilot --backlog instead."
effort: cheap
argument-hint: "discover [--refresh] | sync <phase> <work-item-ref> [--comment text]"
tags: [board, discovery, sync, work-items, configuration]
---


# Board

Operates the project board (GitHub Projects v2 or Azure DevOps) through two subcommands — `discover` writes board config after install and `sync` transitions work-item state at lifecycle points. Use it to set up the board, discover fields, or move an issue between states (collapsed from separate skills in spec-127 D-127-10).

## Subcommands

| Subcommand | Detail file | Purpose |
| ---------- | ----------- | ------- |
| `discover` | [`discover.md`](discover.md) | Post-install discovery of board config (fields, state mappings, process templates) — writes atomically to `manifest.yml`. |
| `sync`     | [`sync.md`](sync.md)         | Lifecycle transitions (`refinement` → `ready` → `in_progress` → `in_review` → `done`). Auto-invoked by `/ai-brainstorm`, `/ai-build`, `/ai-pr`. Fail-open: never blocks the caller. |

```
/ai-board discover                 # one-time configuration discovery
/ai-board discover --refresh       # force re-discovery
/ai-board sync in_progress #45     # transition GitHub issue
/ai-board sync in_review AB#100    # transition Azure Boards work item
```

## Workflow

Principles: §10.1 KISS (subcommand dispatch, no provider rediscovery); §10.4 DRY (reuses `manifest.yml work_items` config, not per-skill routing).

1. **Load contexts.** Read `manifest.yml` `providers.stacks`; load `.ai-engineering/overrides/<stack>/conventions.md` per stack, `.ai-engineering/overrides/_shared/conventions.md`, and `.ai-engineering/team/*.md`.
2. **Detect subcommand** from the first positional argument.
3. `discover` → read [`discover.md`](discover.md), execute. Returns when manifest is updated atomically (aborts with no partial write on failure).
4. `sync` → read [`sync.md`](sync.md), execute. Returns the state-transition result; fail-open on auth, network, or missing-mapping errors.
5. **Neither** → print the subcommand table above and ask which mode.

## Examples

User: "move issue #123 to in-review on the board"

```
/ai-board sync in_review #123
```

Looks up the project item, applies the configured state transition, optionally posts a context comment. Fail-open if the provider CLI is not authenticated.

## Common Mistakes

- Treating `sync` failures as blockers — fail-open by design; callers log and proceed.
- Running `discover` unauthenticated — `gh auth status` or `az account show` must succeed first.

## Integration

Called by: user directly (both subcommands); `/ai-start` (suggests `discover` when config missing); `/ai-brainstorm`, `/ai-build`, `/ai-pr` (auto-invoke `sync` for lifecycle transitions). Reads + writes: `.ai-engineering/manifest.yml` `work_items` section. Pairs with: GitHub CLI (`gh`), Azure CLI (`az`). See also: `/ai-autopilot --backlog` (consumes the configured board to absorb backlog items).

$ARGUMENTS
