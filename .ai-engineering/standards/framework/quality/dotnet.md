# Framework Quality Profile (.NET)

## Update Metadata

- Rationale: define quality contract for .NET stack; mirror python.md quality profile structure.
- Expected gain: predictable quality outcomes for .NET projects with measurable criteria.
- Potential impact: missing tools or failing checks block governed operations for .NET stacks.

## Mandatory Local Checks

- `dotnet format --verify-no-changes`
- `dotnet build --no-restore`
- `dotnet test --no-build`
- `dotnet list package --vulnerable`

## Test and Coverage Policy

- Minimum overall coverage target: 80 percent.
- Governance-critical paths (authentication, authorization, data access): target 90 percent.
- New behavior requires at least one unit or integration test.

## Complexity and Maintainability

- Methods: <50 lines, single responsibility.
- Cyclomatic complexity: target <=10 per method.
- Cognitive complexity: target <=15 per method.
- Prefer explicit error handling over exception swallowing.
- Nullable reference types must be enabled project-wide.

## Security Rules

- No secrets in source or committed artifacts.
- Dependencies must be audited locally before push (`dotnet list package --vulnerable`).
- Security findings are fixed locally; bypass guidance is prohibited.
- HTTPS enforced for all API endpoints.
