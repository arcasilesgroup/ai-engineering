# Module 4: Agents

## Overview

Agents are background workers that verify, scan, and report. Unlike commands (which you invoke and interact with), agents run autonomously and return results.

---

## Commands vs Agents

| Aspect | Commands | Agents |
|--------|----------|--------|
| Invocation | `/command-name` | Claude dispatches them |
| Interaction | Interactive, step-by-step | Autonomous, fire-and-forget |
| Purpose | Multi-step workflows | Single-purpose verification |
| Examples | `/commit`, `/review`, `/test` | `build-validator`, `security-scanner` |

---

## Available Agents

| Agent | What It Does |
|-------|-------------|
| `build-validator` | Runs build + tests, reports pass/fail |
| `test-runner` | Runs tests with coverage metrics |
| `security-scanner` | Scans for secrets, vulnerabilities, OWASP issues |
| `quality-checker` | Validates code against quality gate thresholds |
| `doc-generator` | Updates documentation from code changes |
| `code-simplifier` | Reduces complexity in recently changed code |

---

## How to Use Agents

### In Claude Code

Ask Claude to dispatch an agent:

```
Run the build-validator agent to check if everything compiles and tests pass.
```

```
Use the security-scanner agent to check for any vulnerabilities in the codebase.
```

Claude reads the agent definition from `.claude/agents/` and executes it.

### Running Multiple Agents in Parallel

One of the most powerful patterns — run multiple agents simultaneously:

```
Run the build-validator and security-scanner agents in parallel.
```

Claude dispatches both agents as background tasks and reports their combined results.

---

## Agent Anatomy

Each agent is a markdown file in `.claude/agents/` with this structure:

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

- **Objective**: One clear purpose. An agent does ONE thing well.
- **Process**: Step-by-step instructions (usually 3-5 steps).
- **Constraints**: Agents should NOT modify code (except `code-simplifier`). They report.

---

## Exercise 1: Run the Build Validator

```
Dispatch the build-validator agent.
```

Expected output: Build status, test count, pass/fail.

## Exercise 2: Run the Security Scanner

```
Dispatch the security-scanner agent.
```

Expected output: Findings by severity (Critical/High/Medium/Low).

## Exercise 3: Run Agents in Parallel

```
Run build-validator and quality-checker in parallel.
```

Both run simultaneously. Claude reports when both complete.

---

## Key Takeaways

- Agents are autonomous verification workers.
- They run in the background and report results.
- Running multiple agents in parallel is a key productivity pattern.
- Most agents are read-only — they don't modify code.

## Next

→ [Module 5: Quality Gates](05-quality-gates.md)
