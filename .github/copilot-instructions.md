# GitHub Copilot Instructions

Project instructions are canonical in `.ai-engineering/`.

## Source of Truth

- Governance rules: `.ai-engineering/context/product/framework-contract.md`
- Product context: `.ai-engineering/context/product/product-contract.md`

## Session Start Protocol

Before non-trivial work:

1. **Read active spec** — `.ai-engineering/context/specs/_active.md` and linked spec/plan/tasks.
2. **Read decision store** — `.ai-engineering/state/decision-store.json`.
3. **Run cleanup** — sync repo (status, git pull, prune, branch cleanup).
4. **Verify tooling** — ruff, gitleaks, pytest, ty.

## Plan/Execute Flow (Spec-as-Gate)

During `/ai-plan`, do NOT use file-writing tools to create spec files. Instead:

1. **Analyze** — read code, discover requirements, assess risk (read-only).
2. **Produce spec as text** — write the full spec as markdown in the conversation.
3. **Persist via CLI** — pipe the spec to `ai-eng spec save`:
   ```bash
   cat <<'EOF' | ai-eng spec save --title "Feature Name" --pipeline standard --size M
   # Feature Name
   ## Problem
   ...
   EOF
   ```
4. **STOP** — present the result and wait for the user to invoke `/ai-execute`.

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
- `post_tool_call` hook emits `skill_invoked` events automatically
- `session_end` hook emits `session_end` events automatically
- All events → `.ai-engineering/state/audit-log.ndjson`
- Dashboards: `ai-eng observe [engineer|team|ai|dora|health]`

## Quick Reference

- Skills (34): `.github/prompts/ai-<name>.prompt.md`
- Agents (8): `.github/agents/<name>.agent.md`
- Quality: coverage 80%, duplication ≤3%, cyclomatic ≤10, cognitive ≤15
- Security: zero medium+ findings, zero leaks, zero dependency vulns
