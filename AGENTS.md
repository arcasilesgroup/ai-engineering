# AGENTS.md

Operational contract for AI agents. Consumed by GitHub Copilot, Claude Code, Gemini CLI, Codex, and other AI coding agents.

## Source of Truth

- Governance rules: `.ai-engineering/context/product/framework-contract.md`
- Product context: `.ai-engineering/context/product/product-contract.md`
- Contract: `.ai-engineering/manifest.yml`

## Session Start Protocol

Before non-trivial work:

1. **Read active spec** — `.ai-engineering/context/specs/_active.md` and linked spec/plan/tasks.
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

## On-Demand Context Loading

Before planning or creating specs: read `product-contract.md` §7 (roadmap, KPIs, blockers).
Before governance decisions: read `framework-contract.md` §2-3 (agentic model, ownership).
For skills/agents/CLI reference: read `product-contract.md` §2.2.
For commands/pipelines: read `framework-contract.md` §5.

## Platform Adaptors

Each LLM platform has adaptors that reference the canonical source of truth — never duplicate content.

| Platform | Adaptor Path | Count |
|----------|-------------|-------|
| Claude Code | `.claude/commands/ai/*.md` | 37 |
| GitHub Copilot | `.github/prompts/ai-*.prompt.md` + `.github/agents/*.agent.md` | 38 + 7 |
| Codex / Gemini | `.agents/skills/*/SKILL.md` | 41 |

## Automation Runbooks

Path: `.ai-engineering/runbooks/*.md` — 13 platform-agnostic runbooks for recurring automation tasks. Copy-paste any runbook prompt into Codex, Devin, cron + CLI, or GitHub Actions with AI.

| Layer | Runbooks | Schedule |
|-------|----------|----------|
| Scanner | scheduled-scan, dep-check, feature-scanner, perf-scanner, wiring-scanner, issue-validate | Daily/Weekly |
| Triage | daily-triage, stale-issues | Daily |
| Executor | executor, ci-fixer | Hourly/30min |
| Reporting | weekly-report, changelog-gen, pr-review | Weekly/4h |

## Quick Reference

- Skills (35): `.ai-engineering/skills/<name>/SKILL.md` — slash commands: `/ai:<name>`
- Agents (7): `.ai-engineering/agents/<name>.md`
- CLI: `ai-eng <command>` — deterministic tasks, zero AI tokens
- Quality: coverage 80%, duplication ≤3%, cyclomatic ≤10, cognitive ≤15
- Security: zero medium+ findings, zero leaks, zero dependency vulns
- Tooling: `uv` · `ruff` · `ty` · `pip-audit`
- Validation: `ruff`, `pytest`, `ty`, `gitleaks`, `semgrep`, `pip-audit`
