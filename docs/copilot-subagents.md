# Copilot Subagent Orchestration

How ai-engineering enables multi-agent orchestration in GitHub Copilot, achieving feature parity with Claude Code.

## How It Works

All agent definitions live in `.claude/` as the **canonical source**. The sync script (`scripts/sync_command_mirrors.py`) reads each canonical agent file, enriches it with Copilot-specific properties from the `AGENT_METADATA` dict, and writes the result to `.github/agents/*.agent.md`. These properties — `agents`, `handoffs`, `hooks` — are **only** injected into the GitHub Copilot surface; other mirrors (`.agents/`, templates) receive the base content without them.

The sync is deterministic: run `python scripts/sync_command_mirrors.py` to regenerate all mirrors, or `--check` to verify no drift exists.

## Copilot-Specific Properties

| Property | Purpose | Example |
|----------|---------|---------|
| `agents` | Allowlist of subagent names this agent can invoke | `[Build, Explorer, Verify]` |
| `handoffs` | Guided transitions between agents (buttons in VS Code) | `label: "✅ Verify Changes"` → Verify |
| `hooks` | Per-agent hooks scoped to this agent only | `PostToolUse: ruff format --quiet` |
| `agent` (tool) | Must be in the tools list to enable delegation | Added automatically by sync |

The sync script reads `copilot_agents`, `copilot_handoffs`, and `copilot_hooks` from each `AgentMeta` entry and writes them as YAML frontmatter in the generated `.agent.md` files.

## Agent Roles

| Agent | Role | Can Delegate To | Handoffs |
|-------|------|-----------------|----------|
| Autopilot | Multi-spec orchestrator | Build, Explorer, Verify, Plan, Guard | → Create PR |
| Build | Implementation (only write agent) | Guard, Explorer | → Verify Changes, → Review Changes |
| Plan | Spec decomposition | Explorer, Guard | → Dispatch Implementation → Autopilot |
| Review | Code review | Explorer | → Fix Issues → Build |
| Verify | Quality + security assessment | Explorer | — |
| Explorer | Codebase research (leaf) | — | — |
| Guard | Governance advisory (leaf) | — | — |
| Guide | Teaching & onboarding (leaf) | — | — |
| Simplifier | Code simplification (leaf) | — | — |

**Leaf agents** have no `agents` or `handoffs` — they execute and return results to the caller.

## Environment Capabilities

| Feature | VS Code | Copilot CLI | Coding Agent |
|---------|:-------:|:-----------:|:------------:|
| Subagent delegation (`agents`) | ✅ Native | ❌ Uses `task` tool | ✅ Auto-discovery |
| Handoffs (transition buttons) | ✅ Native | ❌ Not applicable | ⚠️ Unconfirmed |
| Per-agent hooks | ✅ Requires setting | ⚠️ Unconfirmed | ⚠️ Unconfirmed |
| Agent discovery from repo | ✅ | ✅ | ✅ |

## VS Code Usage

Select **@Autopilot** in VS Code chat to start an orchestrated session. It delegates automatically to Build, Explorer, Verify, Plan, and Guard based on the task.

After each agent response, handoff buttons appear in the chat:

- **@Plan** → `[▶ Dispatch Implementation]` → **@Autopilot**
- **@Build** → `[✅ Verify Changes]` or `[🔍 Review Changes]`
- **@Review** → `[🔧 Fix Issues]` → **@Build**

Per-agent hooks (e.g., auto-format after Build edits) require this VS Code setting:

```jsonc
// .vscode/settings.json (optional)
{ "chat.useCustomAgentHooks": true }
```

With hooks enabled, Build's `PostToolUse` hook runs `ruff format --quiet` after every file edit — keeping code formatted without manual intervention.

## Copilot CLI Usage

In Copilot CLI, agents are dispatched via the `task` tool rather than the `agents` property:

```
User: /ai-autopilot "Implement feature X"
CLI: → task(agent: "build", prompt: "Implement sub-spec 1...")
     → task(agent: "verify", prompt: "Verify implementation...")
     → task(agent: "explore", prompt: "Research dependencies...")
```

The `agents` and `handoffs` frontmatter properties are ignored in CLI mode — the CLI dispatches agents directly through tool calls. Agent discovery still works: the CLI reads `.github/agents/` from the repository.

## Coding Agent Usage

When Coding Agent processes a GitHub issue, it discovers agents from `.github/agents/` in the repository. The `agents` property enables it to delegate to specialized agents automatically — Autopilot can split work across Build, Verify, and Explorer just like in VS Code. Handoff buttons are not rendered in the cloud environment, but the delegation chain still functions.

## Handoff Chain

```
@Plan ──[▶ Dispatch]──▶ @Autopilot
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
         @Explorer      @Build        @Verify
                          │
                ┌─────────┼─────────┐
                ▼                   ▼
     [✅ Verify Changes]    [🔍 Review Changes]
           │                      │
           ▼                      ▼
        @Verify              @Review
                                │
                      [🔧 Fix Issues]
                                │
                                ▼
                             @Build
```

## Sync Architecture

```
.claude/ (CANONICAL SOURCE)
    │
    │  scripts/sync_command_mirrors.py
    │  + AGENT_METADATA (copilot_agents, copilot_handoffs, copilot_hooks)
    │
    ├──▶ .github/agents/*.agent.md   (with agents, handoffs, hooks)
    ├──▶ .agents/agents/ai-*.md      (without Copilot-specific props)
    └──▶ templates/                   (install templates)
```

**Rule**: changes always go to `.claude/` canonical sources. Never edit mirrors directly — they are overwritten on every sync run.

To add or modify orchestration properties, edit the `AGENT_METADATA` dict in `scripts/sync_command_mirrors.py` and re-run the sync.

## Comparison with Claude Code

| Aspect | Claude Code | GitHub Copilot |
|--------|-------------|----------------|
| Dispatch mechanism | `Agent(Build)` in agent instructions | `agents` property + `agent` tool |
| Handoffs | Not applicable (inline dispatch) | Native button transitions |
| Per-agent hooks | Global hooks in `.claude/settings.json` | Per-agent `hooks` in frontmatter |
| Context management | Fresh context per subagent dispatch | Fresh context via agent tool |
| Discovery | Reads `.claude/agents/` directly | Reads `.github/agents/` (synced mirror) |

Both environments achieve the same orchestration outcome — specialized agents with scoped permissions executing focused tasks — through different mechanisms.

## References

- [VS Code Custom Agents Docs](https://code.visualstudio.com/docs/copilot/customization/custom-agents)
- [returngis: Custom agents como subagents](https://www.returngis.net/2026/02/haz-que-tus-custom-agents-sean-subagents-de-github-copilot/)
- Decision: DEC-024 in `.ai-engineering/state/decision-store.json`