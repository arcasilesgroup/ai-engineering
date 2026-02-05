# Core Concepts Overview

> Understand the philosophy and architecture of the AI Engineering Framework.

## What Is This?

The AI Engineering Framework is a **zero-dependency, AI-native development framework** that gives software teams everything they need to work effectively with AI coding agents like Claude Code and GitHub Copilot.

It's not a library, not a CLI tool, not a package to install. It's a collection of **markdown files** that AI agents read natively.

## The Problem It Solves

AI coding agents are powerful but inconsistent without structure. They:
- Don't know your project's conventions unless told
- Generate code that doesn't match your patterns
- Miss security checks, quality gates, and testing requirements
- Can't learn from past mistakes across sessions

## The Solution

| Problem | Solution |
|---------|----------|
| Inconsistent code style | `standards/*.md` — Stack-specific coding standards |
| No security checks | `verify-app` agent + `/security-audit` skill |
| Missing tests | `/test` skill + test verification |
| No quality gates | `/quality-gate` skill + SonarQube integration |
| Lost knowledge | `learnings/*.md` — Accumulated patterns and gotchas |
| Manual workflows | `/commit-push`, `/pr`, `/review` — Automated skills |
| Unsafe operations | `.claude/hooks/` — Auto-format, block dangerous commands |

## Philosophy

1. **Zero dependencies**: No Python, no npm, no CLI. Just markdown + YAML. Optional shell hooks for auto-formatting and safety.

2. **Files ARE the format**: Every file is directly consumed by Claude Code or GitHub Copilot. No compilation, no sync.

3. **AI-native**: Written in markdown because LLMs process markdown natively.

4. **Flat structure**: Maximum 3 levels deep. AI agents navigate flat structures faster.

5. **Convention over configuration**: File existence = registration. No registries.

6. **Multi-platform**: Auto-detects GitHub or Azure DevOps and adapts accordingly.

## The Framework at a Glance

| Component | Count | Purpose |
|-----------|-------|---------|
| **Skills** | 23 | Interactive workflows (`/commit-push`, `/review`, `/test`) |
| **Agents** | 5 | Background verification workers |
| **Standards** | 10 | Stack-specific coding rules |
| **Hooks** | 5 + 2 Git | Auto-format, safety guards, secret scan |
| **CI/CD Templates** | 2 platforms | GitHub Actions + Azure Pipelines |

## Next Steps

- [CLAUDE.md](Core-Concepts-CLAUDE-md) - How the main entry point works
- [Three-Layer Architecture](Core-Concepts-Three-Layer-Architecture) - Framework, Team, Personal layers
- [Production Reliability](Core-Concepts-Production-Reliability) - The Boris Cherny workflow

---
**See also:** [Getting Started](Getting-Started) | [Skills Overview](Skills-Overview)
