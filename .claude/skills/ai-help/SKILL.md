---
name: ai-help
description: "Surfaces the canonical seven-step chain, the 46-skill registry, and a matchback lookup that suggests the new name when an operator types a legacy slash command. Trigger for 'help', 'what skills do I have', 'what slash commands exist', '/ai-canvas didn't work', 'where did /ai-dispatch go', 'list all skills', 'what changed'. Read-only: prints guidance to stdout. Not for skill creation; use /ai-create instead. Not for skill tuning; use /ai-skill-tune instead."
effort: low
argument-hint: "[skill-name or legacy-slash-command]"
tags: [meta, help, discovery, matchback]
---

# Help

## Quick start

```
/ai-help                       # canonical seven-step chain + skill index
/ai-help /ai-dispatch          # matchback: legacy → new name
/ai-help ai-build              # show one skill's quick-start lines
```

## Workflow

`/ai-help` is the discovery surface. It does three things:

1. Print the canonical seven-step chain verbatim:
   `/ai-brainstorm → /ai-plan → /ai-build → /ai-verify → /ai-review → /ai-commit → /ai-pr`
2. Optional argument: a skill name (`ai-build`) or a legacy slash command (`/ai-dispatch`). When the argument is a legacy name, suggest the new name via the matchback table below; otherwise read `.claude/skills/<name>/SKILL.md` and print its first 12 lines.
3. Defer to `.ai-engineering/manifest.yml` `skills.registry` for the full skill list — never invent skills not present on disk.

## When to Use

- A new contributor types `/ai-help` to discover the surface.
- An operator types a legacy slash command after the spec-127 D-127-04 rename (e.g. `/ai-dispatch`) and wants the new name.
- Before reaching for `/ai-create`, confirm the skill doesn't already exist.

## Matchback

Per D-127-04, no alias dispatcher exists for renamed skills — the new name is the only name. This table is the *only* migration aid. When an operator types a legacy form, suggest the new name with a one-line reason and STOP.

```yaml
matchback:
  /ai-dispatch:        "use /ai-build (D-127-11 canonical implementation gateway)"
  /ai-canvas:          "use /ai-visual (D-127-05 broader visual category framing)"
  /ai-market:          "use /ai-gtm (clearer go-to-market framing)"
  /ai-mcp-sentinel:    "use /ai-mcp-audit (verb-noun naming, audit is the action)"
  /ai-entropy-gc:      "use /ai-simplify-sweep (no metaphor; sweep == repeated simplify)"
  /ai-instinct:        "use /ai-observe (verb-noun; what the skill actually does)"
  /ai-skill-evolve:    "use /ai-skill-tune (tune is the operation; evolve overpromised)"
  /ai-platform-audit:  "use /ai-ide-audit (we audit IDE wiring, not platforms)"
  /ai-run:             "use /ai-autopilot --backlog --source <github|ado|local> (D-127-12 single autonomous wrapper)"
  /ai-board-discover:  "use /ai-board discover (subcommand merger, D-127-10)"
  /ai-board-sync:      "use /ai-board sync (subcommand merger, D-127-10)"
  /ai-release-gate:    "use /ai-verify --release (mode flag merger, D-127-10)"
```

## Examples

### Example 1 — operator types a legacy command

User: "I tried `/ai-dispatch` and it didn't work, what's the new name?"

```
/ai-help /ai-dispatch
```

Reads the matchback table, prints `use /ai-build (D-127-11 canonical implementation gateway)`, and stops.

### Example 2 — discover the canonical chain

User: "what's the standard workflow?"

```
/ai-help
```

Prints `/ai-brainstorm → /ai-plan → /ai-build → /ai-verify → /ai-review → /ai-commit → /ai-pr` and links to `.ai-engineering/manifest.yml` for the full registry.

## Common Mistakes

- Inventing a skill that isn't on disk — always read `manifest.yml` first.
- Using the matchback table to alias-route execution — the table is *advisory only*; the new name is the only name (D-127-04).
- Suggesting `/ai-help` when the user wants context exploration — use `/ai-explore` or `/ai-explain` for that.

## Integration

Called by: user directly. Reads: `.ai-engineering/manifest.yml` `skills.registry`, `.claude/skills/<name>/SKILL.md` (frontmatter only). Read-only: never modifies code. See also: `/ai-explain` (deep concept walkthrough), `/ai-guide` (architecture tours), `/ai-create` (new skill scaffolding).

$ARGUMENTS
