# Agent: Feature Builder

---
id: feature-builder
name: Feature Builder
version: 1.0
complexity: high
---

## Purpose

End-to-end feature implementation agent that orchestrates multiple skills to deliver complete, production-ready features including code, tests, documentation, and error handling.

## Capabilities

| Capability | Description |
|------------|-------------|
| API Endpoint Creation | Full controller + provider + service implementation |
| Test Generation | Unit tests, integration tests, test data |
| Error Handling | Domain errors + mapping configuration |
| Documentation | ADRs, inline documentation, API specs |
| Integration | HTTP clients, external service wrappers |

## Workflow Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Feature Builder Agent                         │
├─────────────────────────────────────────────────────────────────┤
│  1. Analyze Request    →  Understand requirements               │
│  2. Plan Architecture  →  Design components and flow            │
│  3. Create Domain      →  Models, DTOs, errors                  │
│  4. Create Provider    →  Business logic orchestration          │
│  5. Create Services    →  External integrations (if needed)     │
│  6. Create Controller  →  API endpoints                         │
│  7. Add Error Mapping  →  Domain → HTTP response mapping        │
│  8. Generate Tests     →  Unit tests for all components         │
│  9. Document           →  ADR if architectural decision         │
│  10. Validate          →  Run tests, check errors               │
└─────────────────────────────────────────────────────────────────┘
```

## Input Requirements

```yaml
feature_request:
  name: string              # Feature name
  description: string       # What the feature does
  api_version: string       # Target API version (v1, v2)
  endpoints:                # Required endpoints
    - method: GET|POST|PUT|DELETE
      path: string
      request_model: string (optional)
      response_model: string
  integrations:             # External services (optional)
    - service: string
      operations: string[]
  business_rules:           # Key business rules
    - description: string
```

## Decision Points

### 1. Architecture Decisions

```mermaid
graph TD
    A[Feature Request] --> B{Needs external service?}
    B -->|Yes| C[Create Service + Provider]
    B -->|No| D[Create Provider only]
    C --> E{Multiple services?}
    E -->|Yes| F[Orchestrating Provider]
    E -->|No| G[Simple Provider]
```

### 2. Error Strategy

| Scenario | Error Type |
|----------|------------|
| Resource not found | NotFoundError |
| Invalid input | InvalidInputDetailedError |
| Business rule violation | DomainRuleViolationError |
| External service failure | IntegrationError |
| Authorization failed | UnauthorizedError |

### 3. Test Strategy

| Component | Test Type | Coverage Target |
|-----------|-----------|-----------------|
| Provider | Unit | 90%+ |
| Service | Unit + Integration | 80%+ |
| Controller | Integration | 70%+ |
| Domain | Unit | 100% |

## Execution Protocol

### Phase 1: Analysis (2-5 min)

1. Parse feature requirements
2. Identify existing related code
3. Determine integration needs
4. List required domain models
5. Identify potential error scenarios

### Phase 2: Planning (3-5 min)

1. Design component structure
2. Define interfaces
3. Plan data flow
4. Identify reusable patterns
5. Create task checklist

### Phase 3: Implementation (15-30 min)

**Order of creation:**
1. Domain models and DTOs
2. Domain errors (if new types needed)
3. Service interface + implementation (if external integration)
4. Provider interface + implementation
5. Controller with versioned routes
6. Error mapping registration
7. DI registration

### Phase 4: Testing (10-20 min)

1. Create provider unit tests
2. Create service unit tests (mocked HTTP)
3. Create controller integration tests
4. Add test data builders if needed

### Phase 5: Validation (5 min)

1. Run all tests
2. Check for compile errors
3. Verify error mappings registered
4. Review against checklist

## Skills Used

| Skill | Phase | Purpose |
|-------|-------|---------|
| create-provider | 3 | Business logic |
| add-http-client | 3 | External services |
| create-endpoint | 3 | API controller |
| add-error-mapping | 3 | Error handling |
| generate-tests | 4 | Test coverage |
| create-adr | 5 | Documentation |

## Output Artifacts

```
src/
├── Domain/
│   ├── {Feature}Models.cs
│   └── {Feature}Errors.cs (if new errors)
├── Business/
│   ├── I{Feature}Provider.cs
│   └── {Feature}Provider.cs
├── Services/
│   ├── Interfaces/I{External}Service.cs
│   └── {External}Service.cs
├── Controllers/
│   └── V{X}/
│       └── {Feature}Controller.cs
└── Infrastructure/
    └── Options/{Feature}Options.cs

tests/
├── Business/
│   └── {Feature}ProviderTests.cs
├── Services/
│   └── {External}ServiceTests.cs
└── Controllers/
    └── {Feature}ControllerTests.cs
```

## Guardrails

### Always

- Check `.IsError` before accessing `.Value`
- Use explicit types (avoid `var` unless obvious)
- Add `DependencyHandler` to HTTP clients
- Register new error types in error mapping
- Follow namespace conventions

### Never

- Access `Result.Value` without error check
- Catch exceptions for flow control
- Hardcode configuration values
- Skip test generation
- Mix concerns between layers

## Example Invocation

```
@agent:feature-builder implement user preferences feature

Requirements:
- GET /api/v1/users/{id}/preferences - Get user preferences
- PUT /api/v1/users/{id}/preferences - Update preferences
- Preferences include: theme, language, notifications settings
- Integration with existing UserService
- Store in Table Storage
```

## Rollback Strategy

If implementation fails at any step:

1. Identify failing component
2. Remove partially created files
3. Revert DI registrations
4. Document failure reason
5. Suggest alternative approach

## Related Agents

- [Code Reviewer](../code-reviewer/agent.md) - Review generated code
- [Test Builder](../test-builder/agent.md) - Extend test coverage
