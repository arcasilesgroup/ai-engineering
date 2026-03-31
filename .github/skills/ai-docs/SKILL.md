---
name: ai-docs
description: "Use for documentation lifecycle: updating CHANGELOG.md, refreshing README files, scaffolding or syncing solution intent architecture docs, pushing to external docs portals, and verifying documentation coverage. Also invoked automatically by /ai-pr. Trigger for 'update the changelog', 'the README is stale', 'document this feature', 'docs portal needs updating', 'did we document all changes'."
effort: high
argument-hint: "changelog|readme|solution-intent-init|solution-intent-sync|solution-intent-validate|docs-portal|docs-quality-gate"
mode: agent
tags: [documentation, architecture, governance]
---



# Documentation

## Purpose

Unified documentation skill covering the full project documentation lifecycle. Seven handlers manage changelogs, READMEs, solution intent documents, external documentation portals, and documentation quality verification.

## When to Use

- Changelog needs updating after code changes -> `changelog`
- README files need updating to reflect project state -> `readme`
- New project needs a solution intent document -> `solution-intent-init`
- Architectural changes require solution intent sync -> `solution-intent-sync`
- Pre-release or periodic health check on solution intent -> `solution-intent-validate`
- External documentation portal needs updating -> `docs-portal`
- Verify all documentation outputs cover semantic changes -> `docs-quality-gate`
- Automatically invoked by `/ai-pr` via parallel subagent dispatch

## Process

1. **Detect handler** from arguments: one of the 7 handlers listed below
2. **Check gate** -- read `documentation.auto_update` flags from `.ai-engineering/manifest.yml`
3. **Execute handler** -- follow the matching handler in `handlers/`
4. **Report** -- present summary of actions taken

## Routing Table

| Argument | Handler | Gate Flag |
|----------|---------|-----------|
| `changelog` | `handlers/changelog.md` | `documentation.auto_update.changelog` |
| `readme` | `handlers/readme.md` | `documentation.auto_update.readme` |
| `solution-intent-init` | `handlers/solution-intent-init.md` | none (manual invocation) |
| `solution-intent-sync` | `handlers/solution-intent-sync.md` | `documentation.auto_update.solution_intent` |
| `solution-intent-validate` | `handlers/solution-intent-validate.md` | none (read-only) |
| `docs-portal` | `handlers/docs-portal.md` | `documentation.external_portal.enabled` |
| `docs-quality-gate` | `handlers/docs-quality-gate.md` | none (always runs when dispatched) |

If no argument is provided, display the routing table above and ask the user which handler to use.

## Quick Reference

```
/ai-docs changelog                # update CHANGELOG.md from semantic diff
/ai-docs readme                   # diff-aware README updates
/ai-docs solution-intent-init     # scaffold docs/solution-intent.md
/ai-docs solution-intent-sync     # diff-aware sync from project state
/ai-docs solution-intent-validate # completeness and freshness scorecard
/ai-docs docs-portal              # update external documentation portal
/ai-docs docs-quality-gate        # verify doc coverage of all changes
```

## Integration

- **Called by**: `/ai-pr` (step 6.5) via parallel subagent dispatch
- **Calls**: `handlers/changelog.md`, `handlers/readme.md`, `handlers/solution-intent-init.md`, `handlers/solution-intent-sync.md`, `handlers/solution-intent-validate.md`, `handlers/docs-portal.md`, `handlers/docs-quality-gate.md`
- **Reads**: `.ai-engineering/manifest.yml` (auto_update flags, external_portal config), `docs/solution-intent.md`, `.ai-engineering/state/decision-store.json`
- **NOT** `/ai-write` -- for prose content (blog posts, pitch decks) use `/ai-write` instead

## Governance Notes

**Visual priority**: diagrams > tables > text. Every solution intent section MUST have at least one Mermaid diagram or table. Text accompanies but does not substitute visual representation.

**TBD policy**: if a section's data is not defined, implemented, or in scope, mark it explicitly as TBD. NEVER invent data.

**Ownership**: `docs/solution-intent.md` is project-managed. Sync updates data but never removes user-authored content. `ai-eng update` does not touch this file.

**Writing**: use `/ai-write` patterns for document generation. Handlers define WHAT sections and data to gather; `/ai-write` defines HOW to write them.

## References

- `.github/skills/ai-pr/SKILL.md` -- PR workflow that dispatches documentation subagents
- `.github/skills/ai-write/SKILL.md` -- documentation writing patterns
- `.ai-engineering/manifest.yml` -- documentation flags and portal config
$ARGUMENTS
