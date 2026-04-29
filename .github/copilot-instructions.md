# GitHub Copilot Instructions — Copilot Overlay

> See [AGENTS.md](../AGENTS.md) for the canonical cross-IDE rules
> (Step 0, available skills, agents, and the hard rules that delegate
> to [CONSTITUTION.md](../CONSTITUTION.md)). Read those first; this
> file only adds GitHub-Copilot-specific specifics.

## Native Surface

- **Slash commands** — invoke skills via `/ai-<name>` in the GitHub
  Copilot agent surface (Copilot Chat, agent mode, or any
  Copilot-aware editor). Do not invent terminal equivalents that are
  not listed in the CLI reference.
- **Agent mode** — Copilot's autonomous edit/run/iterate loop is the
  intended driver for `/ai-dispatch`, `/ai-pr`, `/ai-run`, and the
  other agent skills documented in
  [AGENTS.md → Skills Available](../AGENTS.md#skills-available). The
  10-agent dispatch surface from
  [AGENTS.md → Agents Available](../AGENTS.md#agents-available)
  applies here exactly as it does in other IDEs.

## Agent Skills (Open Standard)

GitHub Copilot adopts the open Agent Skills format: a discoverable
package of instructions, optional resources, and metadata that
extends the agent's capabilities without modifying the host. Skills
in this framework follow the format and live under
`.github/skills/ai-<name>/SKILL.md` — one directory per skill, the
`SKILL.md` document inside, plus any sibling resources the skill
needs.

These mirror files are **generated**, never edited by hand. They
carry the `DO NOT EDIT` header and `linguist-generated=true`
attribute per Article V of the
[Constitution](../CONSTITUTION.md#article-v--single-source-of-truth);
the sync command listed in
[AGENTS.md → Skills Available](../AGENTS.md#skills-available)
regenerates the mirrors from their authoritative source. Manual
edits to `.github/skills/` are reverted on the next sync.

## Agent Hooks (VS Code v1.110+ Preview)

Copilot's per-agent hook surface (Preview in VS Code v1.110 and
later) lets the IDE host invoke shell commands at well-known
lifecycle points. The framework's wiring lives in
`.github/hooks/hooks.json` and registers commands at the events
Copilot exposes:

- `sessionStart`, `sessionEnd` — session boundary observability
  (skill telemetry, instinct extraction).
- `userPromptSubmitted` — emits the canonical `skill_invoked`
  telemetry event when the user issues a `/ai-*` command.
- `preToolUse` — pre-flight policy enforcement (deny-list, prompt
  hygiene checks) before a tool call reaches the host.
- `postToolUse` — emits `agent_dispatched` and `ide_hook` events
  after agent or tool invocation.
- `errorOccurred` — emits `framework_error` and `ide_hook` events
  when the host surfaces a failure.

Each hook entry declares both a `bash` and a `powershell` command
plus a `timeoutSec` budget so the same registry works on
macOS/Linux/WSL and native Windows.

Activating per-agent hooks requires the user setting
`chat.useCustomAgentHooks: true` in VS Code; without it Copilot
falls back to no-op behavior. The deny rules and the
hooks-registry file are tracked in source control — treat both as
read-only at the IDE layer.

## Agent Plugins (Extensions View)

Copilot exposes Agent Plugins through the VS Code Extensions view:
plugin bundles can register tools, prompts, and command surfaces
that Copilot agents can call. This framework does not bundle a
plugin today — the entire dispatch surface is delivered through
Agent Skills and Agent Hooks. If you install a third-party Agent
Plugin alongside this framework, prefer plugins whose tool
contracts can be filtered by the host's policy engine (see
[CONSTITUTION.md Article III](../CONSTITUTION.md#article-iii--dual-plane-security))
rather than ones that bypass the host.

## Hot-Path Discipline

Copilot agent mode fires hooks on every tool call and every commit,
so the local critical path must stay fast:

- **Pre-commit budget**: under 1 second wall-clock for the
  deterministic Layer-1 gate (lint, format check, secret scan on
  staged hunks only).
- **Pre-push budget**: under 5 seconds for the residual checks
  before the push pipeline takes over.
- Anything heavier (full test suite, dependency audit, governance
  evaluation) belongs in CI, not on the local hot path.

If a check exceeds budget, profile it and move work off the hot
path before adding new logic to the hook.

## Token Efficiency Tips

- Use Copilot's "New Conversation" / clear-context action when the
  current conversation no longer carries load-bearing state — agent
  mode keeps the full transcript in context until cleared.
- For deep codebase research, dispatch the `ai-explore` agent
  (read-only, fresh context) instead of having the main thread read
  the whole tree.
- Cite files with `startLine:endLine:filepath`; never paste large
  code blocks the user did not ask for.
- Treat `/ai-start` as the session bootstrap — it loads only what
  the current task needs and avoids re-reading already-loaded
  context.

## Observability

Telemetry is automatic. The hooks registered by
`.github/hooks/hooks.json` write canonical framework events to the
audit log under `.ai-engineering/state/` for the chain documented in
[AGENTS.md → Observability](../AGENTS.md#observability). Refer to
[AGENTS.md → Skills Available → `/ai-start`](../AGENTS.md#skills-available)
for the bootstrap that registers hooks. Session discovery and
transcript viewing are delegated to the separately installed
`agentsview` companion tool.
