# GEMINI.md — Gemini CLI Overlay

> See [AGENTS.md](./AGENTS.md) for the canonical cross-IDE rules (Step 0,
> available skills, agents, and the hard rules that delegate to
> [CONSTITUTION.md](./CONSTITUTION.md)). Read those first; this file
> only adds Gemini-CLI-specific specifics.

## Native Surface

- **Slash commands** — invoke skills via `/ai-<name>` in the Gemini CLI
  agent surface. Do not invent terminal equivalents that are not listed
  in the CLI reference.
- **Skill mirrors** — Gemini CLI loads skill mirrors from `.gemini/skills/`
  (project scope) and `~/.gemini/skills/` (user scope). These mirrors are
  generated, never edited by hand; the authoritative skill definition is
  the path referenced from
  [AGENTS.md → Skills Available](./AGENTS.md#skills-available). See
  Article V of [CONSTITUTION.md](./CONSTITUTION.md) for the SSOT contract.
- **Agent mirrors** — agent mirrors live under `.gemini/agents/`. The
  dispatch surface is the 10 first-class agents listed in
  [AGENTS.md → Agents Available](./AGENTS.md#agents-available); each runs
  in its own context window.

## Settings & Hook Wiring

Gemini CLI reads its hook configuration from `.gemini/settings.json` with
two-tier precedence: the user-scope file at `~/.gemini/settings.json` is
loaded first and the project-scope `.gemini/settings.json` is merged on
top, so project-level entries override user defaults. The framework's
audit chain depends on the project file remaining authoritative for hook
declarations and deny rules — both are tracked in source control.

The framework registers hooks across the 11 lifecycle events Gemini CLI
exposes:

- `SessionStart`, `SessionEnd` — session boundary observability.
- `BeforeAgent`, `AfterAgent` — skill invocation telemetry and instinct
  extraction.
- `BeforeTool`, `AfterTool` — prompt-injection guard, MCP health check,
  strategic-compact, and auto-format wiring.
- `BeforeToolSelection` — pre-flight guidance before the model chooses a
  tool.
- `BeforeModel`, `AfterModel` — model-call envelopes for cost and trace
  capture.
- `PreCompress` — context-window compression hook.
- `Notification` — user-facing notification routing.

Hook commands receive `AIENG_HOOK_ENGINE=gemini` as an environment signal
so the shared hook scripts under `.ai-engineering/scripts/hooks/` can
adapt their I/O envelope without duplicating logic per IDE.

## Stdin/Stdout JSON Contract

Gemini CLI hooks communicate with the host through a strict JSON envelope
on stdin and stdout — plain text or partial JSON is rejected. Every hook
script in `.ai-engineering/scripts/hooks/` therefore:

- Reads the full stdin payload, parses it as JSON, and never logs to
  stdout in non-JSON form (diagnostics go to stderr).
- Emits a single JSON object on stdout with the documented Gemini CLI
  fields (e.g. `decision`, `reason`, `output`) plus the framework's own
  metadata for the local audit chain.
- Returns a non-zero exit code only when the hook itself fails; policy
  decisions are encoded in the JSON body so Gemini CLI can route them
  deterministically.

This contract is the reason the framework cannot share the IDE-host log
stream for hook output — the audit trail flows to the framework events
file instead (see Observability below).

## Hot-Path Discipline

Gemini CLI fires hooks on every tool call and every commit, so the local
critical path must stay fast:

- **Pre-commit budget**: under 1 second wall-clock for the deterministic
  Layer-1 gate (lint, format check, secret scan on staged hunks only).
- **Pre-push budget**: under 5 seconds for the residual checks before the
  push pipeline takes over.
- Anything heavier (full test suite, dependency audit, governance
  evaluation) belongs in CI, not on the local hot path.

If a check exceeds budget, profile it and move work off the hot path
before adding new logic to the hook.

## Token Efficiency Tips

- Use Gemini CLI's `/clear` (or its session-reset equivalent) when
  context is no longer load-bearing instead of letting the conversation
  balloon.
- For deep codebase research, dispatch the `ai-explore` agent (read-only,
  fresh context) instead of having the main thread read the whole tree.
- Cite files with `startLine:endLine:filepath`; never paste large code
  blocks the user did not ask for.
- Treat `/ai-start` as the session bootstrap — it loads only what the
  current task needs and avoids re-reading already-loaded context.

## Observability

Telemetry is automatic. The hook chain registered by the project's
`.gemini/settings.json` writes canonical framework events to
`.ai-engineering/state/framework-events.ndjson` for the audit chain.
Refer to
[AGENTS.md → Skills Available → `/ai-start`](./AGENTS.md#skills-available)
for the bootstrap that registers hooks. Session discovery and transcript
viewing are delegated to the separately installed `agentsview` companion
tool.
