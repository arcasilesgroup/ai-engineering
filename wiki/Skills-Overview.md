# Skills Overview

> Interactive workflows invoked with `/skill-name` that run in your current session.

## What Are Skills?

Skills are multi-step workflows that you invoke interactively. Unlike agents (which run in the background), skills execute step-by-step with your input and feedback.

## Available Skills (23)

| Skill | Description | Auto-invocable |
|-------|-------------|:--------------:|
| `/commit-push` | Smart commit with secret scanning + push | No |
| `/commit-push-pr` | Full cycle: commit + push + PR | No |
| `/pr` | Create structured pull request | No |
| `/review` | Code review against standards | Yes |
| `/test` | Generate and run tests | Yes |
| `/fix` | Fix build, test, or lint errors | Yes |
| `/refactor` | Refactor with test verification | No |
| `/security-audit` | OWASP Top 10 security review | No |
| `/quality-gate` | Run quality gate checks | No |
| `/blast-radius` | Analyze impact of changes | Yes |
| `/deploy-check` | Pre-deployment verification | No |
| `/document` | Generate documentation | No |
| `/create-adr` | Create Architecture Decision Record | No |
| `/learn` | Record a learning for future sessions | Yes |
| `/validate` | Validate framework + platform detection | Yes |
| `/setup-project` | Initialize new project | No |
| `/add-endpoint` | Scaffold .NET API endpoint | No |
| `/add-component` | Scaffold React component | No |
| `/migrate-api` | Migrate API version | No |
| `/migrate-claude-md` | Migrate legacy CLAUDE.md to sectioned format | No |
| `/dotnet:add-provider` | Create .NET provider | No |
| `/dotnet:add-http-client` | Create typed HTTP client | No |
| `/dotnet:add-error-mapping` | Add error type + mapping | No |

## Auto-Invocable Skills

Skills marked "Auto-invocable" can be triggered automatically by Claude when appropriate. For example:
- `/review` runs after significant code changes
- `/test` runs when you ask Claude to verify tests
- `/fix` runs when Claude detects failing tests

## Skill Categories

### Git Workflow
- [/commit-push](Skills-Daily-Workflow#commit-push) - Stage, commit, and push with secret scanning
- [/commit-push-pr](Skills-Daily-Workflow#commit-push-pr) - Full cycle to PR
- [/pr](Skills-Daily-Workflow#pr) - Create pull requests

### Code Quality
- [/review](Skills-Code-Quality#review) - Code review
- [/test](Skills-Code-Quality#test) - Generate and run tests
- [/fix](Skills-Code-Quality#fix) - Fix errors
- [/refactor](Skills-Code-Quality#refactor) - Safe refactoring

### Security
- [/security-audit](Skills-Security#security-audit) - OWASP review
- [/quality-gate](Skills-Security#quality-gate) - Full quality check

### Documentation
- [/document](Skills-Documentation#document) - Generate docs
- [/create-adr](Skills-Documentation#create-adr) - Architecture decisions

### Setup
- [/validate](Skills-Daily-Workflow#validate) - Check installation
- [/setup-project](Installation-Quick-Install) - Initialize project
- [/learn](Skills-Documentation#learn) - Record learnings
- [/migrate-claude-md](Installation-Manual-Setup) - Migrate legacy CLAUDE.md

## How Skills Work

1. **You invoke:** Type `/skill-name` in Claude Code
2. **Skill loads:** Claude reads the skill definition from `.claude/skills/`
3. **Steps execute:** Claude follows the skill's process step-by-step
4. **You interact:** Provide input, approve actions, review results
5. **Completion:** Skill reports what was done

## Skill Anatomy

Each skill is a markdown file in `.claude/skills/`:

```markdown
---
description: One-line description
tools: [Bash, Read, Write, Edit]
autoInvocable: true|false
---

## Objective
What this skill does (one sentence).

## Process
1. Step one
2. Step two
3. Step three

## Success Criteria
How to know it worked.
```

## Finding Skills

List all available skills:
```
What skills are available?
```

Or look in `.claude/skills/` directory.

---
**See also:** [Daily Workflow](Skills-Daily-Workflow) | [Code Quality](Skills-Code-Quality) | [Custom Skills](Customization-Custom-Skills)
