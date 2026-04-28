# GitHub Copilot Instructions

Project instructions are canonical in `.ai-engineering/`.

## Source of Truth

- Config: `.ai-engineering/manifest.yml`
- Decisions: `.ai-engineering/state/decision-store.json`
- Contexts: `.ai-engineering/contexts/` (languages, frameworks, team)

## FIRST ACTION -- Mandatory

Your first action in every session MUST be to run `/ai-start`.
Do not respond to any user request until `/ai-start` completes.
`/ai-start` and other `/ai-*` entries are IDE slash commands, not `ai-eng` CLI subcommands.
Never translate `/ai-<name>` into `ai-eng <name>` unless the CLI reference explicitly documents that command.

## Plan/Execute Flow (Spec-as-Gate)

During `/ai-plan`:

1. **Analyze** -- read code, discover requirements, assess risk (read-only).
2. **Produce spec as text** -- write the full spec as markdown in the conversation.
3. **Persist via Write tool** -- write spec.md and plan.md directly to `specs/`.
4. **Commit** -- stage and commit the new files.
5. **STOP** -- present the result and wait for the user to invoke `/ai-dispatch`.

## Absolute Prohibitions

1. **NEVER** `--no-verify` on any git command.
2. **NEVER** skip/silence a failing gate -- fix root cause.
3. **NEVER** weaken gate severity.
4. **NEVER** push to protected branches (main, master).
5. **NEVER** dismiss security findings without `state/decision-store.json` risk acceptance.
6. **NEVER** add suppression comments to bypass static analysis or security scanners.

Gate failure: diagnose -> fix -> retry.

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

- Skills (46): `.github/skills/ai-<name>/SKILL.md`
- Agents (10): `.github/agents/<name>.agent.md`
- Quality: coverage 80%, duplication <=3%, cyclomatic <=10, cognitive <=15
- Security: zero medium+ findings, zero leaks, zero dependency vulns
