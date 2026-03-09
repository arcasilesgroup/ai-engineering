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

During `/ai:plan`, do NOT use file-writing tools to create spec files. Instead:

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
4. **STOP** — present the result and wait for the user to invoke `/ai:execute`.

## Quick Reference

- Skills (35): `.ai-engineering/skills/<name>/SKILL.md`
- Agents (7): `.ai-engineering/agents/<name>.md`
- Quality: coverage 80%, duplication ≤3%, cyclomatic ≤10, cognitive ≤15
- Security: zero medium+ findings, zero leaks, zero dependency vulns
