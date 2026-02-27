# AGENTS.md

## Purpose

Operational contract for AI agents working in this repository.
This file is automatically consumed by GitHub Copilot (agent mode), Claude Code, Codex, and other AI coding agents that read repository-root instruction files.

## Canonical Governance Source

- `.ai-engineering/` is the single source of truth for governance and context.
- Agents must treat `.ai-engineering/manifest.yml` and `.ai-engineering/context/**` as authoritative.

## Session Start Protocol

Before any non-trivial implementation work:

1. **Read active spec** — `.ai-engineering/context/specs/_active.md` and linked spec/plan/tasks files.
2. **Read decision store** — `.ai-engineering/state/decision-store.json` to avoid re-asking decided questions.
3. **Run pre-implementation** — sync the repository (git pull, prune, cleanup, create feature branch).
4. **Verify tooling** — confirm ruff, gitleaks, pytest, ty are available.

This protocol is mandatory. Skipping it risks working on stale code, repeating decided questions, or creating merge conflicts.

## Agent Behavior Mandates

Top-tier autonomous operation requires strict adherence to these behavioral patterns:

1. **The `<think>` Protocol** — Before performing complex git operations, making broad architectural changes, or concluding a task, you MUST use your internal scratchpad or reasoning process to plan. Do not guess; verify you have discovered all necessary context.
2. **Parallel Execution** — ALWAYS batch multiple, independent operations (e.g., searching for 3 different files, or running 3 independent linters) into simultaneous tool calls. Never make sequential tool calls when they can be combined. Maximize efficiency.
3. **Context Efficiency** — NEVER use tools to read files that are already fully visible in your current context window. Only read files if you genuinely need the contents. 
4. **Code Citing Rules** — When citing existing code, use the exact `startLine:endLine:filepath` format. NEVER output code to the user unless explicitly requested. NEVER omit spans of pre-existing code without using the `// ... existing code ...` comment to indicate their absence.
5. **Proactive Memory Usage** — Liberally read from and write to `.ai-engineering/state/decision-store.json` to persist learnings and avoid repeating questions.

## Required References

Read these before any non-trivial work:

- `.ai-engineering/context/product/framework-contract.md` — framework identity, personas, roadmap.
- `.ai-engineering/context/product/product-contract.md` — project goals, KPIs, release status.
- `.ai-engineering/standards/framework/core.md` — governance structure, ownership, lifecycle, skills/agents model.
- `.ai-engineering/standards/framework/stacks/python.md` — Python stack contract, code patterns, testing patterns.
- `.ai-engineering/standards/team/core.md` — team-specific standards.
- `.ai-engineering/context/specs/_active.md` — pointer to active spec.

## Skills

50 procedural skills in `.ai-engineering/skills/<category>/<name>/SKILL.md`.
Categories: `workflows`, `dev`, `review`, `quality`, `govern`, `docs`.
Discover via `ls .ai-engineering/skills/*/` and SKILL.md frontmatter.

## Agents

19 agent personas in `.ai-engineering/agents/<name>.md`.
Discover via `ls .ai-engineering/agents/`.

## Slash Commands & Copilot Integration

All skills and agents are available as Claude Code slash commands (`.claude/commands/`), Copilot prompts (`.github/prompts/`), and Copilot agents (`.github/agents/`). Mirrors managed by `scripts/sync_command_mirrors.py`.

## Lifecycle Enforcement

Every non-trivial change follows:

1. Discovery
2. Architecture
3. Planning
4. Implementation
5. Review
6. Verification
7. Testing
8. Iteration

## Ownership Model

- Framework-managed: `.ai-engineering/standards/framework/**`
- Team-managed: `.ai-engineering/standards/team/**`
- Project-managed: `.ai-engineering/context/**`
- System-managed: `.ai-engineering/state/*.json`, `.ai-engineering/state/*.ndjson`

Agents must never overwrite team-managed or project-managed content during framework update flows.

- Cross-OS enforcement: all gates must pass on Ubuntu, Windows, and macOS.
- **Context Constraints**: NEVER read files already provided in the useful context or previously read files unless they have been modified externally.
- **Assumption Constraints**: NEVER assume a library or utility is available. Always verify via `package.json`, `requirements.txt`, etc., or by searching the codebase.

## Quality Contract

- Coverage: 90%.
- Duplication ≤ 3%.
- Cyclomatic complexity ≤ 10.
- Cognitive complexity ≤ 15.
- No blocker/critical issues.
- Quality gate pass rate: 100% on all governed operations.

## Security Contract

- Security scan pass rate: 100% — zero medium/high/critical findings.
- Secret detection: zero leaks (blocker severity).
- Dependency vulnerabilities: zero known (blocker severity).
- SAST findings (medium+): zero — remediate or risk-accept.
- Tamper resistance: hook hash verification + `--no-verify` bypass detection mandatory.
- Cross-OS enforcement: all gates must pass on Ubuntu, Windows, and macOS.

## Command Contract

- `/commit` -> stage + commit + push current branch
- `/commit --only` -> stage + commit
- `/pr` -> stage + commit + push + create PR + enable auto-complete (`--auto --squash --delete-branch`)
- `/pr --only` -> create PR; if branch is unpushed, warn and propose auto-push; continue via selected mode if declined
- `/acho` -> stage + commit + push current branch
- `/acho pr` -> stage + commit + push + create PR + enable auto-complete (`--auto --squash --delete-branch`)

## Decision and Audit Rules

- Risk acceptance decisions must be written to `.ai-engineering/state/decision-store.json`.
- Governance events must be appended to `.ai-engineering/state/audit-log.ndjson`.
- Agents must check decision store before prompting for the same risk decision.

## Tooling Baseline

- Python runtime/package tooling: `uv`
- Lint/format: `ruff`
- Type checking: `ty`
- Dependency vulnerability check: `pip-audit`

## Working Agreement for This Repository

- Keep changes small and verifiable.
- Follow active spec via `.ai-engineering/context/specs/_active.md`.
- Include rationale, expected gain, and potential impact in governance document updates.
