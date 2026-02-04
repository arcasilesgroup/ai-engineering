# Module 0: Introduction

## What is the AI Engineering Framework?

The AI Engineering Framework is a **zero-dependency, AI-native development framework** that gives software teams everything they need to work effectively with AI coding agents like Claude Code and GitHub Copilot.

It's not a library, not a CLI tool, not a package to install. It's a collection of **markdown files** that AI agents read natively — standards, commands, agents, learnings, and CI/CD templates.

## Why Does This Exist?

AI coding agents are powerful but inconsistent without structure. They:
- Don't know your project's conventions unless told
- Generate code that doesn't match your patterns
- Miss security checks, quality gates, and testing requirements
- Can't learn from past mistakes across sessions

This framework solves these problems by providing:

| Problem | Solution |
|---------|----------|
| Inconsistent code style | `standards/*.md` — Stack-specific coding standards |
| No security checks | `security-scanner` agent + `/security-audit` command |
| Missing tests | `/test` command + `test-runner` agent |
| No quality gates | `/quality-gate` command + SonarQube integration |
| Lost knowledge | `learnings/*.md` — Accumulated patterns and gotchas |
| Manual workflows | `/commit`, `/pr`, `/review` — Automated inner-loop |

## Philosophy

1. **Zero dependencies**: No Python, no npm, no CLI. Just markdown + YAML.
2. **Files ARE the format**: Every file is directly consumed by Claude Code or GitHub Copilot. No compilation, no sync.
3. **AI-native**: Written in markdown because LLMs process markdown natively.
4. **Flat structure**: Maximum 3 levels deep. AI agents navigate flat structures faster.
5. **Convention over configuration**: File existence = registration. No registries.

## What You'll Learn

| Module | Topic |
|--------|-------|
| 01 | Installation — Get the framework into your project |
| 02 | First Commands — `/commit`, `/pr`, `/review`, `/test` |
| 03 | Standards & Learnings — How AI follows your rules |
| 04 | Agents — Background verification workers |
| 05 | Quality Gates — SonarQube, Snyk, secret scanning |
| 06 | CI/CD Integration — GitHub Actions + Azure Pipelines |
| 07 | Customization — Add stacks, commands, agents |
| 08 | Advanced Workflows — Parallel Claudes, plan mode, hooks |

## Prerequisites

- **Claude Code** installed ([claude.ai/claude-code](https://claude.ai/claude-code))
- OR **GitHub Copilot** with Chat enabled
- A project repository (any stack: .NET, TypeScript, Python, Terraform)
- Basic familiarity with Git and your IDE

## Next

→ [Module 1: Installation](01-installation.md)
