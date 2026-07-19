---
name: ai-docs
description: "Manages the documentation lifecycle: CHANGELOG, README, solution-intent architecture docs, external docs portals, and documentation quality gates. Auto-invoked by /ai-pr. Trigger for 'update the changelog', 'the README is stale', 'document this feature', 'docs portal needs updating', 'did we document all changes'. Not for blog or pitch content; use /ai-prose instead. Not for marketing collateral; use /ai-marketing instead."
effort: mid
argument-hint: "changelog|readme|solution-intent-init|solution-intent-sync|solution-intent-validate|docs-portal|docs-quality-gate"
tags: [documentation, architecture, governance]
---

# Documentation

Unified documentation lifecycle skill. Seven handlers manage changelogs, READMEs, solution intent documents, external docs portals, and doc quality verification.

## Workflow

Applies §10.4 DRY (docs mirror one canonical source; never duplicate or invent data) and §10.6 SDD (documentation follows the spec/decision record).

1. Detect handler from arguments (one of the 7 in the Routing Table).
2. Check gate — read `documentation.auto_update` flags from `.ai-engineering/manifest.yml`.
3. Execute the matching handler in `handlers/`.
4. Report a summary of actions taken.

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

No argument → display the routing table and ask which handler to use.

## Governance Notes

- **Visual priority**: diagrams > tables > text. Every solution intent section MUST have ≥1 Mermaid diagram or table; text accompanies but never substitutes.
- **TBD policy**: mark undefined/out-of-scope data explicitly as TBD. NEVER invent data.
- **Ownership**: `.ai-engineering/solution-intent.md` is project-managed. Sync updates data but never removes user-authored content; `ai-eng update` does not touch it.
- **Writing**: use `/ai-prose` patterns. Handlers define WHAT sections/data to gather; `/ai-prose` defines HOW to write them.

## Integration

Called by: `/ai-pr` (step 7, parallel subagent dispatch). Calls: `handlers/changelog.md`, `handlers/readme.md`, `handlers/solution-intent-*.md`, `handlers/docs-portal.md`, `handlers/docs-quality-gate.md`. Reads: `manifest.yml`, `.ai-engineering/solution-intent.md`, `decision-store.json`. See also: `/ai-prose` (prose content), `/ai-marketing` (outreach).

## References

- `.claude/skills/ai-pr/SKILL.md` — PR workflow that dispatches documentation subagents
- `.claude/skills/ai-prose/SKILL.md` — documentation writing patterns
- `.ai-engineering/manifest.yml` — documentation flags and portal config

## Examples

User: "did we document all the changes in this PR?"

```
/ai-docs docs-quality-gate
```

Diffs changed surfaces against documentation; flags un-documented public APIs or feature flags.

$ARGUMENTS
