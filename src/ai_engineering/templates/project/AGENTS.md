# AGENTS.md

Operational contract for AI agents. Consumed by GitHub Copilot, Claude Code, Gemini CLI, Codex, and other AI coding agents.

## Source of Truth

- Governance rules: `.ai-engineering/context/product/framework-contract.md`
- Product context: `.ai-engineering/context/product/product-contract.md`
- Contract: `.ai-engineering/manifest.yml`

## Session Start Protocol

Before non-trivial work:

1. **Read active spec** — `.ai-engineering/specs/_active.md` and linked spec/plan/tasks.
2. **Read decision store** — `.ai-engineering/state/decision-store.json`.
3. **Load checkpoint** — `ai-eng checkpoint load` for session recovery.
4. **Run cleanup** — sync repo (status, git pull, prune, branch cleanup).
5. **Verify tooling** — ruff, gitleaks, pytest, ty.

Mandatory. Skipping risks stale code, repeated decisions, or merge conflicts.

## Agent Behavior Mandates

1. **The `<think>` Protocol** — Before complex git operations, broad changes, or task conclusion: use internal reasoning to plan. Verify all context is discovered.
2. **Parallel Execution** — Batch independent operations into simultaneous tool calls. Never sequential when parallelizable.
3. **Context Efficiency** — Never re-read files already in context window.
4. **Code Citing** — Use `startLine:endLine:filepath` format. Never output code unless requested. Use `// ... existing code ...` for omissions.
5. **Proactive Memory** — Read/write `state/decision-store.json` to persist learnings and avoid repeated questions.
6. **Checkpoint on completion** — Save checkpoint after each task: `ai-eng checkpoint save`.
7. **No Suppression Comments** — Never add `# NOSONAR`, `# nosec`, `# type: ignore`, `# pragma: no cover`, `# noqa`, or equivalent to bypass static analysis or quality findings. Fix the root cause or escalate to the user with full context.

## On-Demand Context Loading

Before planning or creating specs: read `product-contract.md` §7 (roadmap, KPIs, blockers).
Before governance decisions: read `framework-contract.md` §2-3 (agentic model, ownership).
For skills/agents/CLI reference: read `product-contract.md` §2.2.
For commands/pipelines: read `framework-contract.md` §5.

## Platform Adaptors

Each LLM platform has adaptors that reference the canonical source of truth — never duplicate content.

| Platform | Skills Location | Count | Agents Location | Count |
|----------|----------------|-------|-----------------|-------|
| Claude Code | `.claude/skills/ai-*/SKILL.md` | 37 | `.claude/agents/ai-*.md` | 8 |
| GitHub Copilot | `.github/prompts/ai-*.prompt.md` | 34 | `.github/agents/*.agent.md` | 8 |
| Codex / Gemini | `.agents/skills/*/SKILL.md` | 34 | `.agents/agents/ai-*.md` | 8 |

## Automation Runbooks

Path: `.ai-engineering/runbooks/*.md` — 5 runbooks for operational procedures. Recurring automation is handled by GitHub Agentic Workflows (`.github/workflows/ai-eng-*.yml`).

| Runbook | Purpose | Trigger |
|---------|---------|---------|
| code-simplifier | Complexity reduction, dead code removal | `ai-eng-code-simplifier.yml` (Wed 5AM) |
| dependency-upgrade | Safe major version bump guide | Manual / Dependabot |
| governance-drift-repair | Mirror sync, expired decisions, counter accuracy | `ai-eng-governance-drift.yml` (Mon 4AM) |
| incident-response | P0-P3 structured incident handling | Manual |
| security-incident | Secret leak protocol, vulnerability disclosure | Manual |

## Absolute Prohibitions

1. **NEVER** `--no-verify` on any git command.
2. **NEVER** skip/silence a failing gate — fix root cause.
3. **NEVER** weaken gate severity.
4. **NEVER** modify hook scripts — hash-verified.
5. **NEVER** push to protected branches (main, master).
6. **NEVER** dismiss security findings without `state/decision-store.json` risk acceptance.
7. **NEVER** add suppression comments to bypass static analysis or security scanners. Fix the root cause.

Gate failure: diagnose → fix → retry. Use `ai-eng doctor --fix-tools` or `--fix-hooks`.

## Quick Reference

- Skills (34): `.agents/skills/<name>/SKILL.md` — slash commands: `/ai-<name>`
- Agents (8): `.agents/agents/ai-<name>.md`
- CLI: `ai-eng <command>` — deterministic tasks, zero AI tokens
- Quality: coverage 80%, duplication ≤3%, cyclomatic ≤10, cognitive ≤15
- Security: zero medium+ findings, zero leaks, zero dependency vulns
- Tooling: `uv` · `ruff` · `ty` · `pip-audit`
- Validation: `ruff`, `pytest`, `ty`, `gitleaks`, `semgrep`, `pip-audit`
