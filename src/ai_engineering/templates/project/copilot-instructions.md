# GitHub Copilot Instructions

Project instructions are canonical in `.ai-engineering/`.

> See [AGENTS.md](../AGENTS.md) for the canonical cross-IDE rules (Step 0, available skills, agents, and the hard rules that delegate to [CONSTITUTION.md](../CONSTITUTION.md)). Read those first; this file only adds Copilot-specific specifics.

## Source of Truth

- Config: `.ai-engineering/manifest.yml`
- Decisions: `.ai-engineering/state/decision-store.json`
- Contexts: `.ai-engineering/contexts/` (languages, frameworks, team)

## FIRST ACTION -- Mandatory

Your first action in every session MUST be to run `/ai-start`.
Do not respond to any user request until `/ai-start` completes.
`/ai-start` and other `/ai-*` entries are IDE slash commands, not `ai-eng` CLI subcommands.
Never translate `/ai-<name>` into `ai-eng <name>` unless the CLI reference explicitly documents that command.

Cross-IDE workflow rules, including the spec-gated `/ai-brainstorm` -> `/ai-plan` -> `/ai-dispatch` flow, live in [AGENTS.md](../AGENTS.md).

## Hard Rules

The non-negotiable rules live in [CONSTITUTION.md](../CONSTITUTION.md), summarised in [AGENTS.md](../AGENTS.md). Do not restate them here — read those first. Gate failure: diagnose -> fix -> retry.

## Observability

Telemetry is **automatic via hooks** -- configured in `.github/hooks/hooks.json`.
- `userPromptSubmitted` hook emits `skill_invoked` events on `/ai-*` commands
- `preToolUse` hook enforces deny-list (blocks dangerous operations)
- `postToolUse` hook emits `agent_dispatched` and `ide_hook` events on agent use
- `errorOccurred` hook emits `framework_error` and `ide_hook` events on failures
- Hook, gate, governance, security, and quality outcomes flow to `.ai-engineering/state/framework-events.ndjson`
- Registered skills, agents, contexts, and hooks are catalogued in `.ai-engineering/state/framework-capabilities.json`
- Session discovery and transcript viewing are delegated to separately installed `agentsview`

## Subagent Orchestration

Orchestrator agents can delegate tasks to specialized subagents via the `agent` tool:

| Orchestrator | Delegates To | Handoffs |
|-------------|-------------|----------|
| Build | Guard, ai-explore | -> Verify, -> Review |
| Plan | ai-explore, Guard | -> Autopilot |
| Review | ai-explore | -> Build |
| Verify | ai-explore | -> Build |
| Autopilot | Build, ai-explore, Verify, Plan, Guard | -> agent |
| Run | Build, ai-explore, Verify, Review, Guard | -- |

Leaf agents (Guard, Guide, Simplifier, ai-explore) cannot delegate -- they are terminal nodes.

Handoffs provide guided transitions between agents in VS Code (buttons after responses).
Per-agent hooks (e.g., auto-format in Build) require `chat.useCustomAgentHooks: true`.

## Quick Reference

- Skills (51): `.github/skills/ai-<name>/SKILL.md`
- Agents (11): `.github/agents/<name>.agent.md`
- Quality: coverage 80%, duplication <=3%, cyclomatic <=10, cognitive <=15
- Security: zero medium+ findings, zero leaks, zero dependency vulns
