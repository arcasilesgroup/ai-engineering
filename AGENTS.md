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
| Claude Code | `.claude/skills/ai-*/SKILL.md` | 41 | `.claude/agents/ai-*.md` | 8 |
| GitHub Copilot | `.github/prompts/ai-*.prompt.md` | 38 | `.github/agents/*.agent.md` | 8 |
| Codex / Gemini | `.agents/skills/*/SKILL.md` | 38 | `.agents/agents/ai-*.md` | 8 |

## Agents (8)

Path: IDE-specific (`.claude/agents/ai-<name>.md`, `.github/agents/<name>.agent.md`, `.agents/agents/ai-<name>.md`)

| Agent | Role | Purpose | Scope |
|-------|------|---------|-------|
| plan | Architect | Planning pipeline, spec creation, architecture design — stops before execution | read-write |
| build | Engineer | ONLY code writer, multi-stack implementation across 20 stacks | read-write |
| verify | Analyst | 7-mode scanning: governance, security, quality, performance, a11y, feature-gap, architecture | read-write (work items only) |
| guard | Guardian | Proactive governance advisory, drift detection, shift-left enforcement | read-only + state |
| guide | Mentor | Teaching, onboarding, architecture tours, decision archaeology | read-only |
| operate | SRE | Runbook execution, incident response, operational health monitoring | read-write |
| explorer | Context Gatherer | Deep codebase research, context discovery before other agents act | read-only |
| simplifier | Code Cleaner | Guard clauses, extract methods, flatten nesting, reduce complexity | read-write |

## Skills (38)

Path: IDE-specific (`.claude/skills/ai-<name>/SKILL.md`, `.github/prompts/ai-<name>.prompt.md`, `.agents/skills/<name>/SKILL.md`)

| Skills (alphabetical) |
|-----------------------|
| accessibility, api, architecture, changelog, cleanup, code, commit, contract, dashboard, debug, discover, dispatch, document, evolve, explain, gap, governance, guard, infra, lifecycle, migrate, onboard, ops, performance, pipeline, plan, pr, quality, refactor, release, risk, schema, security, simplify, spec, standards, test, triage |

## Automation Runbooks

Path: `.ai-engineering/runbooks/*.md` — 5 runbooks for operational procedures. Recurring automation is handled by GitHub Agentic Workflows (`.github/workflows/ai-eng-*.yml`).

| Runbook | Purpose | Trigger |
|---------|---------|---------|
| code-simplifier | Complexity reduction, dead code removal | `ai-eng-code-simplifier.yml` (Wed 5AM) |
| dependency-upgrade | Safe major version bump guide | Manual / Dependabot |
| governance-drift-repair | Mirror sync, expired decisions, counter accuracy | `ai-eng-governance-drift.yml` (Mon 4AM) |
| incident-response | P0-P3 structured incident handling | Manual |
| security-incident | Secret leak protocol, vulnerability disclosure | Manual |

## Lifecycle

Discovery → Architecture → Planning → Guard (advisory) → Implementation → Verify → Operate → Feedback.

## Command Contract

- `/ai-plan` → planning pipeline (classify → discover → risk → spec → execution plan → STOP)
- `/ai-dispatch` → read approved plan, dispatch agents, coordinate, report
- `/ai-commit` → stage + commit + push
- `/ai-commit --only` → stage + commit
- `/ai-pr` → stage + commit + push + PR + auto-complete (`--auto --squash --delete-branch`)
- `/ai-pr --only` → create PR; warn if unpushed, propose auto-push

## Absolute Prohibitions

1. **NEVER** `--no-verify` on any git command.
2. **NEVER** skip/silence a failing gate — fix root cause.
3. **NEVER** weaken gate severity.
4. **NEVER** modify hook scripts — hash-verified.
5. **NEVER** push to protected branches (main, master).
6. **NEVER** dismiss security findings without `state/decision-store.json` risk acceptance.
7. **NEVER** add suppression comments to bypass static analysis or security scanners. Fix the root cause.

Gate failure: diagnose → fix → retry. Use `ai-eng doctor --fix-tools` or `--fix-hooks`.

## Progressive Disclosure

Three-level loading: **Metadata** (always, ~50 tok/skill) → **Body** (on-demand) → **Resources** (on-demand).

Session start loads ONLY: `_active.md` → `spec.md` → `tasks.md` → `decision-store.json`. Do NOT pre-load skills or agents.

| Level | Budget |
|-------|--------|
| Session start | ~500 tokens |
| Single skill | ~2,050 tokens |
| Agent + 2 skills | ~3,200 tokens |
| Platform audit (7 dim) | ~10,500 tokens |

Schema: `.ai-engineering/standards/framework/skills-schema.md`. Organization: flat (no categories).

## Quick Reference

- Skills (38): `.claude/skills/ai-<name>/SKILL.md` — slash commands: `/ai-<name>`
- Agents (8): `.claude/agents/ai-<name>.md`
- CLI: `ai-eng <command>` — deterministic tasks, zero AI tokens
- Quality: coverage 80%, duplication ≤3%, cyclomatic ≤10, cognitive ≤15
- Security: zero medium+ findings, zero leaks, zero dependency vulns
- Tooling: `uv` · `ruff` · `ty` · `pip-audit`
- Validation: `ruff`, `pytest`, `ty`, `gitleaks`, `semgrep`, `pip-audit`
