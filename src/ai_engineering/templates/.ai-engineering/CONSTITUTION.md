# CONSTITUTION

## Identity

[Project name] -- [1-2 sentences: what this project does and who it serves].

## Mission

1. [Primary goal -- what success looks like]
2. [Secondary goal]
3. [Tertiary goal, if applicable]

## Principles

### I. [Principle Name]

[Rule statement -- what must always be true. Why it matters.]

### II. [Principle Name]

[Rule statement -- what must always be true. Why it matters.]

### III. [Principle Name]

[Rule statement -- what must always be true. Why it matters.]

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
9. [Project-specific prohibition]

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

## Boundaries

### Framework-owned (do not modify without coordination)

- [List framework-managed files and directories]

### Team-owned (safe to customize)

- `.ai-engineering/contexts/team/**` -- team conventions and lessons
- `.ai-engineering/manifest.yml` (user configuration section only)

### Coordination-required changes

- [What changes require team notification or review]

## Governance

This document is the supreme governing authority for AI behavior in this project. It is loaded at Step 0 of every skill and agent invocation.

**Amendment process**: Changes to the CONSTITUTION require a pull request with explicit team review.

**Versioning**: MAJOR for principle removals. MINOR for new principles. PATCH for clarifications.

**Ownership**: TEAM_MANAGED. The framework will never overwrite this document during updates.

**Version**: 1.0.0 | **Ratified**: [YYYY-MM-DD] | **Last Amended**: [YYYY-MM-DD]
