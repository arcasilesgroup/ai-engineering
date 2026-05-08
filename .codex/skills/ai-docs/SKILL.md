---
name: ai-docs
description: "Manages the documentation lifecycle: CHANGELOG, README, solution-intent architecture docs, external docs portals, and documentation quality gates. Auto-invoked by /ai-pr. Trigger for 'update the changelog', 'the README is stale', 'document this feature', 'docs portal needs updating', 'did we document all changes'. Not for blog or pitch content; use /ai-write instead. Not for marketing collateral; use /ai-gtm instead."
effort: high
argument-hint: "changelog|readme|solution-intent-init|solution-intent-sync|solution-intent-validate|docs-portal|docs-quality-gate"
tags: [documentation, architecture, governance]
mirror_family: codex-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-docs/SKILL.md
edit_policy: generated-do-not-edit
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

| Argument                   | Handler                                | Gate Flag                                   |
| -------------------------- | -------------------------------------- | ------------------------------------------- |
| `changelog`                | `handlers/changelog.md`                | `documentation.auto_update.changelog`       |
| `readme`                   | `handlers/readme.md`                   | `documentation.auto_update.readme`          |
| `solution-intent-init`     | `handlers/solution-intent-init.md`     | none (manual invocation)                    |
| `solution-intent-sync`     | `handlers/solution-intent-sync.md`     | `documentation.auto_update.solution_intent` |
| `solution-intent-validate` | `handlers/solution-intent-validate.md` | none (read-only)                            |
| `docs-portal`              | `handlers/docs-portal.md`              | `documentation.external_portal.enabled`     |
| `docs-quality-gate`        | `handlers/docs-quality-gate.md`        | none (always runs when dispatched)          |

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

## Examples

### Example 1 — sync the changelog before a release

User: "update the changelog with everything since v1.2"

```
/ai-docs changelog
```

Reads recent commits + closed PRs since the last tagged release, drafts a Keep-a-Changelog formatted entry, opens for review.

### Example 2 — verify doc coverage before merge

User: "did we document all the changes in this PR?"

```
/ai-docs docs-quality-gate
```

Diffs changed surfaces against documentation; flags un-documented public APIs or feature flags.

## Integration

Called by: `/ai-pr` (step 7, parallel subagent dispatch). Calls: `handlers/changelog.md`, `handlers/readme.md`, `handlers/solution-intent-*.md`, `handlers/docs-portal.md`, `handlers/docs-quality-gate.md`. Reads: `manifest.yml`, `docs/solution-intent.md`, `state.db.decisions`. See also: `/ai-write` (prose content), `/ai-gtm` (outreach).

## Governance Notes

**Visual priority**: diagrams > tables > text. Every solution intent section MUST have at least one Mermaid diagram or table. Text accompanies but does not substitute visual representation.

**TBD policy**: if a section's data is not defined, implemented, or in scope, mark it explicitly as TBD. NEVER invent data.

**Ownership**: `docs/solution-intent.md` is project-managed. Sync updates data but never removes user-authored content. `ai-eng update` does not touch this file.

**Writing**: use `/ai-write` patterns for document generation. Handlers define WHAT sections and data to gather; `/ai-write` defines HOW to write them.

## References

- `.codex/skills/ai-pr/SKILL.md` -- PR workflow that dispatches documentation subagents
- `.codex/skills/ai-write/SKILL.md` -- documentation writing patterns
- `.ai-engineering/manifest.yml` -- documentation flags and portal config
  $ARGUMENTS
