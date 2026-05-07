# GitHub Copilot Instructions

> See [AGENTS.md](../AGENTS.md) for canonical cross-IDE rules
> (Step 0, skills, agents, hard rules, quality gates, observability,
> source of truth). Non-negotiable rules in
> [CONSTITUTION.md](../CONSTITUTION.md). Read those first.

## FIRST ACTION — Mandatory

Run `/ai-start` first in every session. `/ai-*` are IDE slash
commands, not `ai-eng` CLI subcommands.

## Hooks Wiring (Copilot-specific)

Hook config in `.github/hooks/hooks.json`. Canonical script in
`.ai-engineering/scripts/hooks/` via bash/PowerShell adapter.

| Cross-IDE primitive        | Copilot event |
|----------------------------|---------------|
| Progressive disclosure     | `userPromptSubmitted` |
| Tool offload + loop detect | `postToolUse` |
| Checkpoint + Ralph Loop    | `sessionEnd` |
| Deny-list enforcement      | `preToolUse` |
| Error capture              | `errorOccurred` |

PreCompact / PostCompact not surfaced by Copilot; snapshot
primitive degrades gracefully.

## Observability

See [AGENTS.md → Observability](../AGENTS.md#observability) for the
canonical telemetry posture and audit chain wiring. Copilot-specific
hook events are listed in the table above.
