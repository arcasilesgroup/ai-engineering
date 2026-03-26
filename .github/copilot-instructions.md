# GitHub Copilot Instructions

Project instructions are canonical in `.ai-engineering/`.

## Source of Truth

- Config: `.ai-engineering/manifest.yml`
- Decisions: `.ai-engineering/state/decision-store.json`
- Contexts: `.ai-engineering/contexts/` (languages, frameworks, team)

## Session Start Protocol

Before non-trivial work:

1. **Read active spec** — `.ai-engineering/specs/spec.md` and `.ai-engineering/specs/plan.md`.
2. **Read decision store** — `.ai-engineering/state/decision-store.json`.
3. **Read project identity** — `.ai-engineering/contexts/project-identity.md` (if it exists).
4. **Load contexts** — read `.ai-engineering/contexts/languages/{lang}.md`, `frameworks/{fw}.md`, and `team/*.md` for each detected stack before writing code.
5. **Run cleanup** — sync repo (status, git pull, prune, branch cleanup).
6. **Verify tooling** — ruff, gitleaks, pytest, ty.

## Plan/Execute Flow (Spec-as-Gate)

During `/ai-plan`:

1. **Analyze** — read code, discover requirements, assess risk (read-only).
2. **Produce spec as text** — write the full spec as markdown in the conversation.
3. **Persist via Write tool** — write spec.md and plan.md directly to `specs/`.
4. **Commit** — stage and commit the new files.
5. **STOP** — present the result and wait for the user to invoke `/ai-dispatch`.

## Absolute Prohibitions

1. **NEVER** `--no-verify` on any git command.
2. **NEVER** skip/silence a failing gate — fix root cause.
3. **NEVER** weaken gate severity.
4. **NEVER** push to protected branches (main, master).
5. **NEVER** dismiss security findings without `state/decision-store.json` risk acceptance.
6. **NEVER** add suppression comments to bypass static analysis or security scanners.

Gate failure: diagnose → fix → retry.

## Observability

Telemetry is **automatic via hooks** — configured in `.github/hooks/hooks.json`.
- `sessionStart` hook emits `session_start` events on session initialization
- `sessionEnd` hook emits `session_end` events on session close
- `userPromptSubmitted` hook emits `skill_invoked` events on `/ai-*` commands
- `preToolUse` hook enforces deny-list (blocks dangerous operations)
- `postToolUse` hook emits `agent_dispatched` events on agent use
- `errorOccurred` hook emits `error_occurred` events on failures
- All events → `.ai-engineering/state/audit-log.ndjson`
- Dashboards: `ai-eng observe [engineer|team|ai|dora|health]`

## Subagent Orchestration

Orchestrator agents can delegate tasks to specialized subagents via the `agent` tool:

| Orchestrator | Delegates To | Handoffs |
|-------------|-------------|----------|
| Autopilot | Build, Explorer, Verify, Plan, Guard | → Create PR |
| Build | Guard, Explorer | → Verify, → Review |
| Plan | Explorer, Guard | → Autopilot |
| Review | Explorer | → Build |
| Verify | Explorer | — |

Leaf agents (Explorer, Guard, Guide, Simplifier) cannot delegate — they are terminal nodes.

Handoffs provide guided transitions between agents in VS Code (buttons after responses).
Per-agent hooks (e.g., auto-format in Build) require `chat.useCustomAgentHooks: true`.

## Quick Reference

- Skills (38): `.github/skills/ai-<name>/SKILL.md`
- Agents (9): `.github/agents/<name>.agent.md`
- Quality: coverage 80%, duplication ≤3%, cyclomatic ≤10, cognitive ≤15
- Security: zero medium+ findings, zero leaks, zero dependency vulns
