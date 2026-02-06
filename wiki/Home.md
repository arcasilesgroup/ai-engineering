# AI Engineering Framework

> Zero-dependency, AI-native framework for software engineering teams.

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Claude Code](https://img.shields.io/badge/Claude%20Code-Compatible-purple)

## What is this?

A collection of **markdown files** that AI coding agents (Claude Code, GitHub Copilot) read natively to enforce your team's standards, automate workflows, and maintain quality. No CLI, no build step, no dependencies.

## Quick Start

```bash
git clone https://github.com/arcasilesgroup/ai-engineering.git /tmp/ai-framework
/tmp/ai-framework/scripts/install.sh --name "MyProject" --stacks dotnet,typescript --cicd github --install-tools
```

[Full Installation Guide](Installation-Quick-Install)

## Features at a Glance

| Feature | Count | Examples |
|---------|-------|----------|
| **Skills** | 11 | `/ship`, `/review`, `/test`, `/assess` |
| **Agents** | 4 | verify-app, code-architect, oncall-guide |
| **Standards** | 10 | .NET, TypeScript, Python, Terraform |
| **Hooks** | 5 + 2 Git | auto-format, secret scan, vulnerability check |

## Navigation

### Learn

- [Getting Started](Getting-Started) - Install and configure in 5 minutes
- [Core Concepts](Core-Concepts-Overview) - Understand the philosophy

### Use

- [Skills](Skills-Overview) - Interactive workflows (`/ship`, `/review`, `/test`)
- [Agents](Agents-Overview) - Background workers (verify-app, code-architect)

### Reference

- [Standards](Standards-Overview) - Coding rules by stack
- [Hooks](Hooks-Overview) - Automation and safety guards

### Customize

- [Custom Skills](Customization-Custom-Skills) - Create team-specific workflows
- [Advanced](Advanced-Parallel-Work) - Power user features

## How It Works

```
CLAUDE.md (entry point)
    │
    ├── References standards/*.md for coding rules
    ├── References learnings/*.md for accumulated knowledge
    ├── Lists available skills in .claude/skills/
    ├── Lists available agents in .claude/agents/
    └── Hooks in .claude/hooks/ run automatically
          │
          ├── Skills: human-directed, multi-step workflows
          │   /ship → scan → commit → push
          │   /review → read standards → analyze → report
          │
          ├── Agents: autonomous, focused, background verification
          │   verify-app → build → test → lint → security → report
          │
          └── Hooks: automatic, event-driven guards
              auto-format → detect type → format
              block-dangerous → check command → allow/block
```

## Compatibility

| Tool | Support | Features |
|------|---------|----------|
| **Claude Code** | Full | Skills, agents, hooks, standards |
| **GitHub Copilot** | Standards | Via `.github/copilot-instructions.md` |
| **Cursor** | Partial | CLAUDE.md and standards |

## Quick Links

- [GitHub Repository](https://github.com/arcasilesgroup/ai-engineering)
- [Report an Issue](https://github.com/arcasilesgroup/ai-engineering/issues)
- [Contributing Guide](https://github.com/arcasilesgroup/ai-engineering/blob/main/CONTRIBUTING.md)
