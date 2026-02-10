# Spec 001: AI-Engineering Framework — Rewrite from Scratch

## Problem

The current codebase has 24 fully implemented Python modules and 51 tests, but:

1. **No governance content for AI agents** — 0 agent definitions, 0 workflow skills, 0 SWE skills, 0 quality skills, 0 stack instructions. AI assistants operate without context.
2. **Legacy context/ structure** — `backlog/` (7 files + archive/) and `delivery/` (8 files + evidence/) are enterprise theater that the AI doesn't need to write code.
3. **Redundant product docs** — `vision.md`, `roadmap.md`, `rebuild-rollout-charter.md`, `framework-adoption-map.md` duplicate what's already in `framework-contract.md`.
4. **No product-contract.md** — No document tells the AI what the project IS, who it's for, what rules to follow.
5. **No CI/CD** — No GitHub Actions workflows for automated testing.
6. **No stack instructions** — `.github/instructions/` directory doesn't exist. Copilot has no path-specific guidance.
7. **Code was written without AI governance** — Python modules were built before skills/agents/standards existed. The code works but wasn't shaped by the framework's own rules.

## Solution

Complete rewrite in 3 mega-phases with **dogfooding from the first commit**:

- **Mega-Phase A (Content-First)**: Create ALL governance content (18 skills, 8 agents, 3 stack instructions, updated standards, context architecture migration) BEFORE touching any Python code. This ensures Copilot operates at 100% context during the entire Python rewrite.
- **Mega-Phase B (Python Rewrite)**: Delete all 24 Python modules and 51 tests. Rewrite from scratch following the new standards, guided by the skills and agents created in Phase A.
- **Mega-Phase C (Mirror + CI + E2E)**: Sync templates mirror, create CI/CD workflows, run E2E validation, close the spec.

## Scope

### In Scope

- Context architecture migration (backlog/ → specs/, delivery/ → specs/done.md)
- Product-contract.md creation (project-managed, dogfooding)
- Framework-contract.md consolidation (absorb vision.md + roadmap.md)
- 18 skills: 3 workflows + 12 SWE + 1 prompt-engineer + 1 python-mastery + 2 quality
- 8 agents: principal-engineer, debugger, architect, quality-auditor, security-reviewer, codebase-mapper, code-simplifier, verify-app
- 3 stack instructions: python, testing, markdown
- Complete Python rewrite: state, installer, hooks, doctor, updater, detector, policy, skills, maintenance, commands, CLI
- Templates mirror sync
- CI/CD workflows (GitHub Actions)
- E2E tests

### Out of Scope

- Azure DevOps support (Phase 2 per roadmap)
- `.claude/settings.json` (future Claude Code phase)
- Additional stack instructions beyond Python (TypeScript, Go, Java — future)
- Remote skills sync implementation improvements
- Nextra documentation site

## Acceptance Criteria

- [ ] `uv sync && uv run pytest tests/ -v --cov=ai_engineering` → >80% coverage
- [ ] `uv run ruff check src/ && uv run ruff format --check src/` → 0 issues
- [ ] `uv run ty check src/` → 0 errors
- [ ] `uv run pip-audit` → 0 vulnerabilities
- [ ] `uv build` → `py3-none-any` wheel
- [ ] Install on clean venv → `ai version`, `ai doctor`, `ai install` work
- [ ] Copilot reads agents/ and skills/ → executes `/commit`, `/pr` correctly
- [ ] Hooks enforce: commit with secret → blocked, push without tests → blocked
- [ ] All 18 skills exist and are referenced from instruction files
- [ ] All 8 agents exist and are referenced from AGENTS.md and CLAUDE.md
- [ ] context/ only contains: product/, specs/, learnings.md
- [ ] CI passes on Python 3.11/3.12/3.13 × Ubuntu/Windows/macOS

## Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | **Content-first, Python-second** | Mega-Phase A creates all governance content BEFORE touching Python. Guarantees Copilot has 100% context when rewriting code. |
| D2 | **Delete all Python and rewrite from scratch** | All 24 modules and 51 tests deleted and rewritten following new standards/agents/skills. Clean slate, no legacy drift. |
| D3 | **Ultra-granular tasks** | 1 file = 1 task = 1 atomic commit. Copilot can do session recovery via `_active.md` → `tasks.md`. |
| D4 | **Branch `rewrite/v2`** | Isolated from main. Merge only after full E2E passes. |
| D5 | **All skills + agents from the start** | 18 skills + 8 agents + 3 instructions created in Mega-Phase A, not a partial MVP. |
| D6 | **specs/ replaces backlog/ + delivery/** | Each spec has WHAT/HOW/DO/DONE. No done.md = pending. With done.md = completed. |
| D7 | **Python mastery skill** | Consolidates 12 Python domains (performance, testing, packaging, design patterns, code style, project structure, error handling, anti-patterns, type safety, observability, resilience) into one comprehensive skill. |
| D8 | **Prompt engineer skill** | Advanced prompting frameworks (RTF, CoT, RISEN, RODES, etc.) adapted for ai-engineering context. |
| D9 | **Product-contract.md** | Project-managed document that tells AI what the project IS. Framework-contract.md tells what the framework IS. Separation of concerns. |
| D10 | **No CLI for lifecycle** | `/commit`, `/pr`, `/acho` are skills the AI reads, not CLI commands. Python = install/update/doctor/stack/ide only. |
| D11 | **Phase-branch multi-agent strategy** | Parallel phases use `rewrite/v2-phase-N` branches. Serial phases work directly on `rewrite/v2`. Prevents cross-agent conflicts and enables true parallel execution. |
| D12 | **Phase gate protocol** | Every phase must pass a gate (tasks [x], quality checks, decisions recorded) before dependent phases can start. Prevents half-implemented phases from propagating. |
| D13 | **Session Map with agent slots** | Each session is pre-assigned to an agent slot with explicit scope, size, and dependencies. Eliminates task contention and enables session recovery by any agent. |
| D14 | **Agentic model is framework-core** | Multi-agent coordination (branch strategy, session maps, phase gates, agent contracts) is not spec-specific — it is a first-class framework capability defined in `framework-contract.md` and `standards/framework/core.md`. Future specs inherit this model. |
