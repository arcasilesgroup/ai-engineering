---
name: scaffold
description: Scaffold code from templates for any stack (dotnet, react, etc.)
disable-model-invocation: true
---

## Context

Unified scaffolding skill that generates boilerplate code following project patterns. Supports multiple stacks with stack-specific subcommands. Each scaffold: reads standards, creates files, registers dependencies, generates tests, and verifies the build.

## Inputs

$ARGUMENTS - Stack, type, and type-specific arguments:

```
/scaffold dotnet endpoint <METHOD> <route> <EntityName>
/scaffold dotnet provider <Name> <ServiceName>
/scaffold dotnet http-client <Name> [BaseURL]
/scaffold dotnet error <Name> <StatusCode> <Description>
/scaffold react <ComponentName> [page|feature|ui]
/scaffold cicd github [stacks]
/scaffold cicd azure [stacks]
/scaffold cicd both [stacks]
```

## Steps

### 1. Parse Arguments

Extract from $ARGUMENTS:
- **Stack**: `dotnet`, `react`, or `cicd`
- **Type**: `endpoint`, `provider`, `http-client`, `error`, component type, or CI/CD platform (`github`, `azure`, `both`)
- **Remaining args**: type-specific parameters

If any required arguments are missing, ask the user.

### 2. Read Standards

Read the appropriate standards file:
- **dotnet**: `standards/dotnet.md`
- **react**: `standards/typescript.md`
- **cicd**: `standards/cicd.md`, `standards/quality-gates.md`, `standards/security.md`

### 3. Execute Stack-Specific Scaffold

---

## .NET: endpoint

**Input:** HTTP method (GET/POST/PUT/DELETE), route (e.g., `/api/v1/users/{id}`), entity name (e.g., `User`)

Creates a full vertical slice:

1. **Controller**: Create or update controller with `[ApiVersion]`, `[Route]`, `[Http{Method}]` attributes. Return `result.ToActionResult(_errorMapper, response => Ok(response))`.
2. **Provider**: Create `I{Entity}Provider` interface and `{Entity}Provider` implementation with constructor injection.
3. **Service**: Create `I{Entity}Service` interface and `{Entity}Service` implementation.
4. **Domain Models**: Request DTO (`{Entity}{Method}Request` with validation attributes), Response DTO (`{Entity}{Method}Response`), Error types if needed (`{Entity}NotFoundError`).
5. **Error Mappings**: Register new error types in error mapping configuration.
6. **DI Registration**: Register provider and service as scoped.
7. **Tests**: Create `{Entity}ProviderTests` for happy path and error paths.

---

## .NET: provider

**Input:** Provider name (e.g., `Order`), service it wraps (e.g., `OrderService`)

1. **Interface**: Create `I{Name}Provider` with method signatures returning `Task<Result<T>>`.
2. **Implementation**: Create `{Name}Provider` with constructor injection, implementing Result pattern (check `IsError` before accessing `Value`).
3. **DI Registration**: `services.AddScoped<I{Name}Provider, {Name}Provider>();`
4. **Tests**: Happy path and error path tests using Result pattern.

---

## .NET: http-client

**Input:** Client name (e.g., `PaymentGateway`), base URL (e.g., `https://api.payment.com`)

1. **Interface**: Create `I{Name}Client` with methods returning `Task<Result<T>>`.
2. **Implementation**: Create `{Name}Client` with `HttpClient` constructor injection.
3. **DelegatingHandler**: Create `{Name}DelegatingHandler` for cross-cutting concerns (headers, logging, retry).
4. **DI Registration**:
   ```csharp
   services.AddTransient<{Name}DelegatingHandler>();
   services.AddHttpClient<I{Name}Client, {Name}Client>(client =>
   {
       client.BaseAddress = new Uri(configuration["{Name}:BaseUrl"]);
   })
   .AddHttpMessageHandler<{Name}DelegatingHandler>();
   ```
5. **Configuration**: Add `"{Name}": { "BaseUrl": "<url>" }` to `appsettings.json`.
6. **Tests**: Test client methods with mocked `HttpMessageHandler`.

---

## .NET: error

**Input:** Error name (e.g., `OrderNotFound`), HTTP status code (e.g., `404`), description

1. **Error Class**:
   ```csharp
   public class {Name}Error : IResultError
   {
       public string Message { get; }
       public {Name}Error(string message = "{description}") { Message = message; }
   }
   ```
2. **Error Mapping**: Register in error mapping configuration:
   ```csharp
   mappings.Map<{Name}Error>()
       .To<ProblemDetails>(StatusCodes.Status{Code})
       .WithMapping((error, problemDetails) =>
       {
           problemDetails.Title = "{Human-readable title}";
           problemDetails.Detail = error.Message;
       });
   ```

---

## React Component

**Input:** Component name (e.g., `UserProfile`), type (page, feature, ui - defaults to `ui`)

Determine location based on type:
- `ui` → `src/components/ui/{ComponentName}/`
- `feature` → `src/components/features/{ComponentName}/`
- `page` → `src/pages/{ComponentName}/`

1. **Component File** (`{ComponentName}.tsx`):
   ```typescript
   interface {ComponentName}Props {
     // Props here
   }

   export function {ComponentName}({ }: {ComponentName}Props) {
     return <div>{/* Component content */}</div>;
   }
   ```
2. **Test File** (`{ComponentName}.test.tsx`):
   ```typescript
   import { render, screen } from '@testing-library/react';
   import { {ComponentName} } from './{ComponentName}';

   describe('{ComponentName}', () => {
     it('renders without crashing', () => {
       render(<{ComponentName} />);
     });
   });
   ```
3. **Index File** (`index.ts`):
   ```typescript
   export { {ComponentName} } from './{ComponentName}';
   export type { {ComponentName}Props } from './{ComponentName}';
   ```

---

---

## CI/CD Pipeline

**Input:** Platform (`github`, `azure`, or `both`), stacks (auto-detected from project files if not provided)

1. **Detect Stacks**: Scan the project for stack indicators:
   - `.csproj` or `.sln` → dotnet
   - `package.json` → typescript
   - `pyproject.toml` or `requirements.txt` or `*.py` → python
   - `*.tf` → terraform

2. **Read Standards**: Read `standards/cicd.md` (especially Section 8: Pipeline Generation Checklist), `standards/quality-gates.md`, and `standards/security.md`.

3. **Generate Platform Files**:
   - **GitHub** (`github` or `both`):
     - `.github/workflows/ci.yml` — Lint + Build + Test for detected stacks
     - `.github/workflows/security.yml` — Gitleaks + Dependency scanning + SAST
     - `.github/workflows/quality-gate.yml` — SonarQube/SonarCloud analysis
   - **Azure** (`azure` or `both`):
     - `pipelines/ci.yml` — Stages: Lint, Test, Build for detected stacks
     - `pipelines/security.yml` — Secret + Dependency + SAST scanning
     - `pipelines/quality-gate.yml` — SonarQube integration
     - `pipelines/templates/` — Reusable templates per detected stack

4. **Customize for Stacks**: Include ONLY the detected/specified stacks in the matrix/stages. Do not generate jobs for stacks that are not present.

5. **Add CUSTOMIZE Markers**: Add clear `# CUSTOMIZE:` comments for values the user must change (solution path, working directories, SonarQube project key, version numbers).

6. **Verify**: Validate YAML syntax of all generated files.

---

### 4. Verify

Run stack-appropriate verification:
- **.NET**: `dotnet build --no-restore && dotnet test --no-build`
- **React**: `npx tsc --noEmit && npm test`
- **CI/CD**: Validate YAML syntax of generated pipeline files

## Verification

- Build/compilation succeeds without errors (code scaffolds)
- All tests pass (code scaffolds)
- DI registrations complete (if applicable)
- Error mappings registered (if applicable)
- Files follow project standards and naming conventions
- Result pattern correctly implemented (if .NET)
- YAML syntax valid (CI/CD scaffolds)
- All detected stacks included in pipeline (CI/CD scaffolds)
- CUSTOMIZE markers present for project-specific values (CI/CD scaffolds)
