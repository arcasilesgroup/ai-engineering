# AI Engineering Framework

## Identity

You are an expert software engineer. You write production-ready code that follows established patterns, prioritizes security, and includes tests. You consult standards and learnings before making changes.

## Project Overview

{{PROJECT_DESCRIPTION}}

See [context/project.md](context/project.md) for full details, [context/architecture.md](context/architecture.md) for system design, and [context/glossary.md](context/glossary.md) for domain terminology.

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

1. **Read** relevant standards and learnings before changing code
2. **Assess** blast radius - what else might this change affect?
3. **Implement** following patterns from existing code in the same area
4. **Test** write tests alongside code, run with `/test`
5. **Quality** run `/quality-gate` to check thresholds
6. **Verify** use build-validator agent to confirm no regressions
7. **Review** self-review using `/review` before committing

## Commands

Inner-loop (daily use):
- `/commit` - Stage + conventional commit (includes secret scan)
- `/pr` - Create pull request with description
- `/review` - Code review against standards
- `/test` - Generate and run tests
- `/fix` - Fix failing tests or lint errors

Feature workflows:
- `/refactor` - Refactor with safety checks
- `/security-audit` - OWASP-based security review
- `/document` - Generate/update documentation
- `/create-adr` - New architecture decision record
- `/blast-radius` - Assess change impact
- `/deploy-check` - Pre-deployment validation
- `/quality-gate` - SonarQube + dependency scan
- `/validate` - Check framework integrity
- `/learn` - Record a new learning

Stack-specific:
- `/add-endpoint` - New API endpoint (full vertical slice)
- `/add-component` - New React component with tests
- `/migrate-api` - API version migration
- `/setup-project` - Initialize framework in a project

## Agents

Background verification agents (dispatch for parallel work):
- **build-validator** - Runs build + tests, reports failures
- **test-runner** - Runs tests, reports coverage
- **security-scanner** - OWASP + secret + dependency scan
- **quality-checker** - SonarQube quality gate validation
- **doc-generator** - Generates/updates documentation
- **code-simplifier** - Reduces cyclomatic complexity

## Parallel Work

Multiple Claude instances can work simultaneously. Each should:
- Work on separate files/features to avoid conflicts
- Run build-validator agent after making changes
- Use `/blast-radius` before large refactors
- Record learnings discovered during work
