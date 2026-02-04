---
name: add-endpoint
description: Create a new ASP.NET Core API endpoint (full vertical slice)
disable-model-invocation: true
---

## Context

Scaffolds a complete vertical slice for a new API endpoint, including the controller, provider, service, domain models, error mappings, DI registration, and tests.

## Inputs

$ARGUMENTS - HTTP method (GET/POST/PUT/DELETE), route (e.g., /api/v1/users), and entity name (e.g., User)

## Steps

### 1. Parse Arguments

Extract from $ARGUMENTS:
- **HTTP method** (GET, POST, PUT, DELETE)
- **Route** (e.g., `/api/v1/users/{id}`)
- **Entity name** (e.g., `User`)

If any are missing, ask the user.

### 2. Read Standards

Read `standards/dotnet.md` for coding conventions, naming, and patterns.

### 3. Create/Update Controller

- If controller exists for this entity, add the new action method.
- Otherwise, create new controller with `[ApiVersion]` and `[Route]` attributes.
- Use `[Http{Method}]` attribute with route template.
- Return `result.ToActionResult(_errorMapper, response => Ok(response))`.

### 4. Create Provider

- Create `I{Entity}Provider` interface with method signature.
- Create `{Entity}Provider` implementation with constructor injection.

### 5. Create Service

- Create `I{Entity}Service` interface.
- Create `{Entity}Service` implementation.

### 6. Create Domain Models

- Request DTO: `{Entity}{Method}Request` with validation attributes.
- Response DTO: `{Entity}{Method}Response`.
- Error types if needed (e.g., `{Entity}NotFoundError`).

### 7. Register Error Mappings

Add mapping for new error types in error mapping configuration.

### 8. Register DI

Register provider and service as scoped in DI configuration.

### 9. Generate Tests

Create `{Entity}ProviderTests` with tests for happy path and error paths.

### 10. Verify

Run `dotnet build` and `dotnet test` to confirm everything works.

## Verification

- Solution builds without errors
- All tests pass
- Error mappings registered for new error types
- DI registrations complete
