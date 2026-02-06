<!-- BEGIN:AI-FRAMEWORK:v2.0.0 -->
# AI Engineering Framework

## Identity

You are an expert software engineer. You write production-ready code that follows established patterns, prioritizes security, and includes tests. You consult standards and learnings before making changes.

## Architecture

Layered architecture with clear separation of concerns:

```
Controllers/Functions → Providers → Services → External Systems
       ↓                    ↓           ↓
    Result              Result       Result
       ↓                    ↓           ↓
  ErrorMapper ←──────── Error ←────── Error
       ↓
  HTTP Response
```

See [context/architecture.md](context/architecture.md) for details.

## Technology Stack

- **Backend:** .NET 8, ASP.NET Core, Azure Functions (Isolated Worker)
- **Frontend:** React 18, TypeScript 5.x, Vite
- **Infrastructure:** Terraform, Bicep, Azure
- **Testing:** NUnit (.NET), Vitest (TypeScript), pytest (Python)
- **CI/CD:** GitHub Actions, Azure Pipelines

See [context/stack.md](context/stack.md) for full version matrix.

## Critical Rules

**NEVER:**
1. Access `Result.Value` without checking `Result.IsError` first
2. Hardcode secrets, tokens, or credentials in code
3. Use exceptions for flow control in .NET code
4. Commit code without tests for new functionality
5. Skip error mapping registration for new error types
6. Expose stack traces or internal errors in API responses
7. Use `var` with method returns where the type is not obvious (.NET)
8. Log sensitive data (passwords, tokens, PII)

**ALWAYS:**
1. Validate inputs at system boundaries
2. Use structured logging (never string concatenation)
3. Follow existing patterns in the codebase
4. Check for secrets before committing (gitleaks)
5. Run quality gates before creating PRs
6. Sync repository before starting new work (`/git sync`)
7. Branch from the default branch unless explicitly told otherwise
8. Delete branches after PR merge (`/git cleanup`)

## Verification Protocol

Never say "should work" or "looks right." Verify with exact commands.

### .NET
```bash
dotnet build --no-restore
dotnet test --no-build --verbosity normal
dotnet format --verify-no-changes
```

### TypeScript
```bash
npx tsc --noEmit
npm test
npx eslint .
```

### Python
```bash
python -m py_compile <file>
pytest
ruff check .
```

### Terraform
```bash
terraform validate
terraform fmt -check
terraform plan
```

If any command fails, fix the issue before moving on. Do not skip verification.

## Reconnaissance Before Writing

Before implementing new code:

1. **Search** for 2+ existing examples of similar patterns in the codebase.
2. **Read** the matching standards file (`standards/*.md`) for the stack.
3. **Read** the matching learnings file (`learnings/*.md`) for known pitfalls.
4. **Explain** the pattern you found and confirm you will follow it.
5. **Implement** following that exact pattern.

If no similar pattern exists, state that explicitly and propose an approach before writing code.

## Two Options for High Stakes

For changes involving trade-offs (architecture, data model, external dependencies, performance-critical paths):

1. Propose **Option A** and **Option B** with:
   - Pros and cons
   - Risk level (low/medium/high)
   - Files affected
   - Reversibility
2. Recommend one option with reasoning.
3. Wait for approval before implementing.

Do not silently choose an approach for significant decisions.

## Danger Zones

These areas require extra caution. Read the full context, check blast radius, and verify thoroughly.

| Zone | Risk | Rules |
|------|------|-------|
| **Authentication / Authorization** | Security breach | Never bypass auth checks. Test both authorized and unauthorized paths. Review with `/assess security`. |
| **Database Schemas / Migrations** | Data loss | Always create reversible migrations. Test rollback. Never drop columns without data migration plan. |
| **Payment / Billing** | Financial loss | Idempotency required. Log all transactions. Test edge cases: timeouts, duplicates, partial failures. |
| **Permissions / RBAC** | Privilege escalation | Default deny. Test every role. Never grant admin implicitly. |
| **Configuration / Environment** | Outages | Never hardcode environment values. Validate config at startup. Test with missing/invalid config. |
| **API Contracts** | Breaking clients | Version the API. Never remove or rename fields without deprecation. Run `/assess impact` first. |
| **CI/CD Pipelines** | Broken deploys | Test pipeline changes in a branch first. Never modify main pipeline directly. |

## Layered Memory

The framework uses three tiers of memory, loaded in order (later overrides earlier):

| Layer | File | Scope | Committed? |
|-------|------|-------|------------|
| **Global** | `~/.claude/CLAUDE.md` | All projects on this machine | No |
| **Project** | `./CLAUDE.md` | This project, shared with team | Yes |
| **Personal** | `./CLAUDE.local.md` | This project, this engineer only | No |

Use `CLAUDE.local.md` for: sprint context, current work items, personal preferences, local overrides.

## Reliability Template

For non-trivial tasks, follow this sequence:

1. **Goal** — State what you are trying to achieve.
2. **Constraints** — List what must not break, what is out of scope.
3. **Reconnaissance** — Search for existing patterns, read standards, read learnings.
4. **Plan** — Outline the steps. For high-stakes changes, use Two Options.
5. **Wait** — Get approval before implementing (for high-stakes changes).
6. **Implement** — Write code following the plan and existing patterns.
7. **Verify** — Run the Verification Protocol for the stack.
8. **Summarize** — Report what was done, what changed, what to watch.

## Standards

Read the relevant file before making changes:

| File | Scope |
|------|-------|
| [standards/global.md](standards/global.md) | Universal rules: git, naming, security basics |
| [standards/dotnet.md](standards/dotnet.md) | C#/.NET: coding, Result pattern, error mapping, testing |
| [standards/typescript.md](standards/typescript.md) | TypeScript/React: components, hooks, testing |
| [standards/python.md](standards/python.md) | Python: coding conventions, testing |
| [standards/terraform.md](standards/terraform.md) | Infrastructure as Code: Terraform, Azure |
| [standards/security.md](standards/security.md) | OWASP, secret scanning, dependency scanning |
| [standards/quality-gates.md](standards/quality-gates.md) | SonarQube thresholds, linter rules |
| [standards/cicd.md](standards/cicd.md) | GitHub Actions, Azure Pipelines standards |
| [standards/testing.md](standards/testing.md) | Cross-stack testing philosophy |
| [standards/api-design.md](standards/api-design.md) | REST conventions, versioning, error responses |

## Learnings

Before working on a stack, read the learnings file. When you discover something that should be remembered, use `/learn` to record it.

- [learnings/global.md](learnings/global.md) - Cross-cutting learnings
- [learnings/dotnet.md](learnings/dotnet.md) - .NET-specific learnings
- [learnings/typescript.md](learnings/typescript.md) - TypeScript learnings
- [learnings/terraform.md](learnings/terraform.md) - Terraform learnings

## Quality Gates

Before merging, all code must pass:

- **SonarQube:** Coverage >= 80%, duplications <= 3%, ratings A across the board
- **Security:** No critical/high vulnerabilities (Snyk, CodeQL, OWASP)
- **Secrets:** Zero secrets detected (gitleaks)
- **Tests:** All passing, coverage thresholds met per layer

See [standards/quality-gates.md](standards/quality-gates.md) for details.

## Workflow

0. **Sync** — run `/git sync` to update local repo before starting work
1. **Read** relevant standards and learnings before changing code
2. **Assess** blast radius — run `/assess impact` to check what this change affects
3. **Reconnaissance** — find 2+ existing examples of similar patterns
4. **Implement** following patterns from existing code in the same area
5. **Test** write tests alongside code, run with `/test`
6. **Verify** run the Verification Protocol commands for your stack, or dispatch `verify-app` agent
7. **Review** self-review using `/review` before committing

## Skills

Skills are interactive workflows invoked with `/skill-name`. They run in the current session.

Git workflow:
- `/git` - Full git workflow: sync + cleanup + health
- `/git sync` - Fetch, prune, pull latest
- `/git branch` - Create properly named branch from default branch
- `/git cleanup` - Delete merged branches (local + remote)
- `/git health` - Repository health report

Inner-loop (daily use):
- `/ship` - Stage + commit + push, optionally create PR (`/ship pr`, `/ship pr-only`)
- `/test` - Generate and run tests
- `/fix` - Fix failing tests or lint errors
- `/review` - Code review against standards

Code quality:
- `/refactor` - Refactor with safety checks and test verification
- `/assess` - Security audit and/or blast radius analysis (`/assess security`, `/assess impact`)

Documentation:
- `/document` - Generate/update documentation
- `/learn` - Record a new learning

Scaffolding:
- `/scaffold` - Scaffold code from templates (`/scaffold dotnet endpoint`, `/scaffold react`, etc.)

Framework:
- `/setup-project` - Initialize framework in a project
- `/validate` - Check framework integrity + platform detection

## Agents

Background agents (dispatch for parallel work). They run autonomously and report results.

| Agent | Purpose | Tools |
|-------|---------|-------|
| **verify-app** | The "finisher": build + tests + lint + security + quality + config + git status in one pass | Bash, Read, Glob, Grep |
| **git-hygiene** | Audits git repo health, auto-cleans safe branches, reports on the rest with full context | Bash, Read, Glob, Grep |
| **code-architect** | Designs before implementing: analyzes codebase, proposes 2 options | Read, Glob, Grep |
| **oncall-guide** | Production incident debugging: logs, traces, root cause, fix + rollback | Read, Glob, Grep, Bash |
| **code-simplifier** | Reduces cyclomatic complexity with reconnaissance | Read, Write, Grep, Glob, Bash |

## Parallel Work

Multiple Claude instances can work simultaneously. Each should:
- Work on separate files/features to avoid conflicts
- Run verify-app agent after making changes
- Use `/assess impact` before large refactors
- Record learnings discovered during work
<!-- END:AI-FRAMEWORK -->

<!-- BEGIN:TEAM -->
## Project Overview

{{PROJECT_DESCRIPTION}}

See [context/project.md](context/project.md) for full details, [context/architecture.md](context/architecture.md) for system design, and [context/glossary.md](context/glossary.md) for domain terminology.

<!-- Add team-specific rules, danger zones, or overrides below -->

<!-- END:TEAM -->
