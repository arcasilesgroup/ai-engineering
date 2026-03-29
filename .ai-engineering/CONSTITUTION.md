# CONSTITUTION

## Identity

ai-engineering is an open-source governance framework that turns any repository into a governed AI workspace. Content-first: policies, skills, agents, runbooks, specs, and state live in versioned files inside the repo. The CLI installs the framework, keeps IDE mirrors in sync, and enforces quality/security gates before code leaves the machine.

Built for regulated enterprises (banking, finance, investment, healthcare) where governance, audit trails, decision traceability, and compliance evidence are mandatory requirements.

## Mission

1. **Zero-trust AI governance** -- every AI action in a codebase is bounded by explicit, auditable rules that the team controls.
2. **IDE-agnostic consistency** -- the same skills, agents, and gates work identically across Claude Code, GitHub Copilot, Gemini CLI, and OpenAI Codex.
3. **Compliance by default** -- quality gates, secret scanning, and dependency auditing run automatically; no developer action required to be compliant.

## Principles

### I. Content Over Code

Policies, skills, agents, and quality standards are Markdown and YAML files versioned alongside the code -- not runtime logic hidden in libraries. Any team member can read, review, and amend governance rules through a pull request.

### II. Gate Integrity

Quality gate thresholds are non-negotiable baselines. They exist to protect the team from shipping defects, not to be tuned down when they become inconvenient. Weakening a gate requires the full protocol: impact warning, remediation patch, explicit risk acceptance, and audit trail.

### III. Single Source of Truth

Every concept has exactly one canonical location. Skills live in IDE skill directories. State lives in `.ai-engineering/state/`. Decisions live in `decision-store.json`. Duplicating information across locations creates drift -- always reference, never copy.

### IV. Simplicity First

The right solution is the simplest one that fully solves the problem. No speculative abstractions, no premature generalization, no clever code. Three similar lines are better than a premature helper. When in doubt, delete.

### V. Verify Before Done

No task is complete without proof it works. Run the tests, run the linter, check the output. "It should work" is not evidence. Diff behavior against main when relevant. Ask: "Would a staff engineer approve this?"

### VI. Fix Root Causes

Workarounds, suppression comments, and temporary patches are prohibited. When a gate fails, diagnose why and fix the underlying issue. When a test is flaky, fix the test. When a linter complains, fix the code.

### VII. Cross-Platform by Default

All generated code, scripts, and paths must work on Windows, macOS, and Linux. Use platform-agnostic idioms. No OS-specific assumptions without explicit fallbacks.

### VIII. Autonomous Execution

When given an approved plan, execute it fully without unnecessary interruptions or confirmations. Report results, not intentions. Fix bugs encountered along the way and mention them in the commit.

## Prohibitions

The AI must NEVER:

1. Use `--no-verify` on any git command.
2. Skip or silence a failing gate -- fix the root cause.
3. Weaken gate severity or coverage thresholds without the full protocol.
4. Modify hook scripts -- they are hash-verified.
5. Push to protected branches (main, master).
6. Dismiss security findings without a risk acceptance in `state/decision-store.json`.
7. Disable or modify `.claude/settings.json` deny rules.
8. Add suppression comments (`# noqa`, `# nosec`, `# type: ignore`, `# pragma: no cover`, `# NOSONAR`, `// nolint`) to bypass quality gates.
9. Write machine-specific paths in committed files -- use `$HOME`, `$(which ...)`, or relative paths.
10. Create new abstractions without analyzing if they're needed and what value they add.

## Quality Gates

| Gate | Threshold |
|------|-----------|
| Test coverage | >= 80% |
| Code duplication | <= 3% |
| Cyclomatic complexity | <= 10 per function |
| Cognitive complexity | <= 15 per function |
| Blocker/critical issues | 0 |
| Security findings (medium+) | 0 |
| Secret leaks | 0 |
| Dependency vulnerabilities | 0 |

Tooling: `ruff` + `ty` (lint/format), `pytest` (test), `gitleaks` (secrets), `pip-audit` (deps).

Gate failure: diagnose, fix, retry. Use `ai-eng doctor --fix` or `ai-eng doctor --fix --phase <name>`.

## Boundaries

### Framework-owned (do not modify without coordination)

- `.claude/skills/**`, `.claude/agents/**` -- skill and agent definitions
- `.ai-engineering/**` -- manifest, state, contexts, specs
- `.github/agents/**`, `.github/skills/**`, `.github/hooks/**` -- Copilot mirrors
- `.codex/**`, `.gemini/**` -- other IDE mirrors
- Hook scripts -- hash-verified, never modified directly

### Team-owned (safe to customize)

- `.ai-engineering/contexts/team/**` -- team conventions and lessons
- `.ai-engineering/manifest.yml` (user configuration section only)

### Coordination-required changes

- Gate thresholds -- require risk acceptance in `state/decision-store.json`
- Manifest schema -- affects all IDEs and downstream mirrors
- Skill/agent contracts -- consumed by multiple IDE providers
- PyPI package interface -- public API for `ai-eng` CLI

## Governance

This document is the supreme governing authority for AI behavior in this project. It is loaded at Step 0 of every skill and agent invocation.

**Amendment process**: Changes to the CONSTITUTION require a pull request with explicit team review. No automated process may modify this document.

**Versioning**: Semantic versioning. MAJOR for principle removals or redefinitions. MINOR for new principles or expanded guidance. PATCH for clarifications and wording.

**Ownership**: TEAM_MANAGED. The framework will never overwrite this document during updates.

**Version**: 1.0.0 | **Ratified**: 2026-03-29 | **Last Amended**: 2026-03-29
