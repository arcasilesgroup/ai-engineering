# Skills Overview

> Interactive workflows invoked with `/skill-name` that run in your current session.

## What Are Skills?

Skills are multi-step workflows that you invoke interactively. Unlike agents (which run in the background), skills execute step-by-step with your input and feedback.

## Available Skills (11)

| Skill | Description | Auto-invocable |
|-------|-------------|:--------------:|
| `/ship` | Stage, commit, push, and optionally create PR (modes: default, `pr`, `pr-only`) | No |
| `/review` | Code review against project standards | Yes |
| `/test` | Generate tests and run the test suite | Yes |
| `/fix` | Fix failing tests, lint errors, or build issues | Yes |
| `/refactor` | Refactor code while preserving behavior with test verification | No |
| `/assess` | Security audit (OWASP Top 10) and/or blast radius analysis (modes: `security`, `impact`) | Yes |
| `/document` | Generate or update documentation for code | No |
| `/learn` | Record a new learning or pattern for future AI sessions | Yes |
| `/scaffold` | Scaffold code from templates for any stack (`dotnet endpoint`, `react`, etc.) | No |
| `/validate` | Validate framework installation, structure, and platform configuration | Yes |
| `/setup-project` | Initialize a new project with the framework | No |

## Auto-Invocable Skills

Skills marked "Auto-invocable" can be triggered automatically by Claude when appropriate. For example:
- `/review` runs after significant code changes
- `/test` runs when you ask Claude to verify tests
- `/fix` runs when Claude detects failing tests
- `/assess` runs when security-sensitive code is involved
- `/learn` runs when a reusable pattern or gotcha is discovered

## Skill Categories

### Inner Loop (Daily Use)
- [/ship](Skills-Daily-Workflow#ship) - Stage, commit, push, optionally create PR
- [/test](Skills-Code-Quality#test) - Generate and run tests
- [/fix](Skills-Code-Quality#fix) - Fix errors
- [/review](Skills-Code-Quality#review) - Code review

### Code Quality
- [/refactor](Skills-Code-Quality#refactor) - Safe refactoring with test verification
- [/assess](Skills-Security#assess) - Security audit and blast radius analysis

### Documentation
- [/document](Skills-Documentation#document) - Generate or update docs
- [/learn](Skills-Documentation#learn) - Record learnings

### Scaffolding
- [/scaffold](Skills-Documentation#scaffold) - Code generation from templates

### Framework
- [/validate](Skills-Daily-Workflow#validate) - Check installation
- [/setup-project](Installation-Quick-Install) - Initialize project

## How Skills Work

1. **You invoke:** Type `/skill-name` in Claude Code
2. **Skill loads:** Claude reads the skill definition from `.claude/skills/`
3. **Steps execute:** Claude follows the skill's process step-by-step
4. **You interact:** Provide input, approve actions, review results
5. **Completion:** Skill reports what was done

## Skill Anatomy

Each skill is a markdown file in `.claude/skills/{skill-name}/SKILL.md`:

```markdown
---
description: One-line description
disable-model-invocation: true  # Only if it should NOT be auto-invocable
---

## Context
What this skill does and when to use it.

## Inputs
$ARGUMENTS - What arguments the skill accepts.

## Steps
1. Step one
2. Step two
3. Step three

## Verification
How to know it worked.
```

## Finding Skills

List all available skills:
```
What skills are available?
```

Or look in `.claude/skills/` directory.

---
**See also:** [Daily Workflow](Skills-Daily-Workflow) | [Code Quality](Skills-Code-Quality) | [Security](Skills-Security) | [Custom Skills](Customization-Custom-Skills)
