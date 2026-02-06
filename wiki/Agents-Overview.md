# Agents Overview

> Background workers that verify, scan, and report autonomously.

## What Are Agents?

Agents are autonomous verification workers that run in the background. Unlike skills (which you interact with step-by-step), agents run independently and return results when done.

## Skills vs Agents

| Aspect | Skills | Agents |
|--------|--------|--------|
| Invocation | `/skill-name` | Claude dispatches them |
| Interaction | Interactive, step-by-step | Autonomous, fire-and-forget |
| Purpose | Multi-step workflows | Single-purpose verification |
| Examples | `/ship`, `/review`, `/test` | verify-app, code-architect |

## Available Agents (4)

| Agent | Purpose | Tools |
|-------|---------|-------|
| [verify-app](Agents-verify-app) | Build + test + lint + security in one pass | Bash, Read, Glob, Grep |
| [code-architect](Agents-code-architect) | Design before implementing | Read, Glob, Grep |
| [oncall-guide](Agents-oncall-guide) | Production incident debugging | Read, Glob, Grep, Bash |
| [code-simplifier](Agents-code-simplifier) | Reduce complexity | Read, Write, Bash |
| Custom agents | Your team's agents | Varies |

## How to Use Agents

### Dispatch an Agent

Ask Claude to run an agent:

```
Run the verify-app agent to check if everything compiles and tests pass.
```

```
Use the code-architect agent to design the caching layer before I implement it.
```

### Run Agents in Parallel

One of the most powerful patterns — run multiple agents simultaneously:

```
Run the verify-app and code-architect agents in parallel.
```

Claude dispatches both as background tasks and reports combined results.

## Agent Anatomy

Each agent is a markdown file in `.claude/agents/`:

```markdown
---
description: One-line description
tools: [Bash, Read, Glob]
---

## Objective
What this agent does (one sentence).

## Process
1. Step one
2. Step two
3. Step three

## Success Criteria
How to know it worked.

## Constraints
What NOT to do.
```

### Key Design Principles

- **Objective:** One clear purpose. An agent does ONE thing well.
- **Process:** Step-by-step instructions (usually 3-5 steps).
- **Constraints:** Most agents are read-only — they report, don't modify.

## When to Use Agents

| Scenario | Agent |
|----------|-------|
| Before PR | verify-app |
| Planning new feature | code-architect |
| Production incident | oncall-guide |
| High complexity code | code-simplifier |

## Agent Location

Agents are stored in `.claude/agents/`:

```
.claude/
└── agents/
    ├── verify-app.md
    ├── code-architect.md
    ├── oncall-guide.md
    ├── code-simplifier.md
    └── custom/              # Team custom agents
        └── deploy-checker.md
```

---
**See also:** [verify-app](Agents-verify-app) | [code-architect](Agents-code-architect) | [oncall-guide](Agents-oncall-guide) | [code-simplifier](Agents-code-simplifier) | [Custom Agents](Customization-Custom-Agents)
