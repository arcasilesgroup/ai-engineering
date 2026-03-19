# AGENTS.md

Multi-IDE instruction file. Consumed by GitHub Copilot, Codex, Gemini CLI, and other AI coding assistants.
For Claude Code-specific behavior, see `CLAUDE.md`.

## Source of Truth

Config: `.ai-engineering/manifest.yml`. Governance: `.ai-engineering/context/product/framework-contract.md`.
Product context: `.ai-engineering/context/product/product-contract.md`.

## Before You Start

1. Read the active spec: `.ai-engineering/context/specs/_active.md` and linked plan/tasks.
2. Read the decision store: `.ai-engineering/state/decision-store.json`.
3. Load checkpoint if resuming: `ai-eng checkpoint load`.
4. Verify tooling is available: ruff, gitleaks, pytest, ty.

## Agent Selection

| Task | Agent | Invoke |
|------|-------|--------|
| Planning, specs, architecture | plan | `/ai-brainstorm` |
| Writing/editing code | build | `/ai-dispatch` (after plan) |
| Quality + security scanning | verify | `/ai-verify` |
| Governance, compliance | guard | `/ai-governance` |
| Code review (parallel agents) | review | `/ai-review` |
| Deep codebase research | explore | direct dispatch |
| Onboarding, teaching | guide | `/ai-guide` |
| Simplify/refactor code | simplify | `/ai-simplify` |

## Platform Mirrors

Each IDE has its own skill and agent files. Same content, platform-native format.

| Platform | Skills | Agents |
|----------|--------|--------|
| Claude Code | `.claude/skills/ai-*/SKILL.md` | `.claude/agents/ai-*.md` |
| GitHub Copilot | `.github/prompts/ai-*.prompt.md` | `.github/agents/*.agent.md` |
| Codex / Gemini | `.agents/skills/*/SKILL.md` | `.agents/agents/ai-*.md` |

## Skills (34)

Grouped by workflow phase. Invoke as `/ai-<name>`.

**Plan:** plan, spec, architecture, contract, schema
**Build:** code, api, infra, pipeline, migrate, refactor, simplify
**Test:** test, debug, gap, performance, accessibility
**Ship:** commit, pr, release, lifecycle
**Observe:** dashboard, ops, triage, integrity, evolve
**Govern:** governance, guard, security, verify, quality
**Learn:** document, explain, dispatch, cleanup

## Quality Gates

| Metric | Threshold |
|--------|-----------|
| Test coverage | >= 80% |
| Code duplication | <= 3% |
| Cyclomatic complexity | <= 10 per function |
| Cognitive complexity | <= 15 per function |
| Blocker/critical issues | 0 |
| Security findings (medium+) | 0 |
| Secret leaks | 0 |
| Dependency vulnerabilities | 0 |

Tooling: `ruff` + `ty` (lint/format), `pytest` (test), `gitleaks` (secrets), `pip-audit` (deps).

## Don't

See `CLAUDE.md` section "Don't" for the full prohibitions list. The three hardest rules:

1. **NEVER** `--no-verify` on any git command.
2. **NEVER** skip or silence a failing gate -- fix the root cause.
3. **NEVER** add suppression comments to bypass static analysis or security scanners.

Gate failure: diagnose, fix, retry. Use `ai-eng doctor --fix-tools` or `--fix-hooks`.
