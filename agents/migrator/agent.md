# Agent: API Migrator

---
id: migrator
name: API Migrator
version: 1.0
complexity: high
---

## Purpose

Assists with API version migrations, handling breaking changes, deprecation strategies, and client communication.

## Capabilities

| Capability | Description |
|------------|-------------|
| Version Analysis | Compare versions, identify breaking changes |
| Migration Planning | Create migration roadmap |
| Code Generation | Generate new version endpoints |
| Deprecation | Mark and communicate deprecated endpoints |
| Documentation | Generate migration guides |

## Migration Types

### 1. Non-Breaking Changes
- Adding new optional fields
- Adding new endpoints
- Performance improvements

### 2. Breaking Changes
- Removing/renaming fields
- Changing response structure
- Removing endpoints
- Changing authentication

## Migration Workflow

```
┌──────────────────────────────────────────────────────────────┐
│                     Migration Workflow                        │
├──────────────────────────────────────────────────────────────┤
│  1. ANALYZE     → Compare v(N) and v(N+1) requirements       │
│  2. PLAN        → Identify breaking changes, create ADR      │
│  3. IMPLEMENT   → Create new version, deprecate old          │
│  4. DOCUMENT    → Generate migration guide                   │
│  5. COMMUNICATE → Notify consumers                           │
│  6. MONITOR     → Track deprecation usage                    │
│  7. RETIRE      → Remove deprecated version                  │
└──────────────────────────────────────────────────────────────┘
```

## Breaking Change Analysis

### Detection Rules

```yaml
breaking_changes:
  - type: field_removed
    severity: high
    detection: Field present in v(N) missing in v(N+1)
    
  - type: field_renamed
    severity: high
    detection: Field name changed between versions
    
  - type: field_type_changed
    severity: high
    detection: Field type incompatible
    
  - type: required_field_added
    severity: high
    detection: New required field in request
    
  - type: response_structure_changed
    severity: high
    detection: Response object shape changed
    
  - type: endpoint_removed
    severity: critical
    detection: Endpoint exists in v(N) not in v(N+1)
    
  - type: auth_changed
    severity: critical
    detection: Authentication method changed
```

### Analysis Output

```markdown
## Breaking Change Report: v1 → v2

### Critical Changes
| Change | Endpoint | Impact |
|--------|----------|--------|
| Endpoint removed | GET /api/v1/legacy | All consumers affected |

### High Priority Changes
| Change | Endpoint | Field | Migration |
|--------|----------|-------|-----------|
| Field renamed | GET /api/v1/users | `name` → `fullName` | Map field |
| Field type changed | POST /api/v1/orders | `amount: string` → `amount: decimal` | Parse/format |

### Consumer Impact
- **Estimated affected consumers:** 15
- **Migration effort:** Medium
- **Recommended timeline:** 3 months deprecation
```

## Versioning Strategy

### URL Segment Versioning (Project Standard)

```csharp
// v1 (current)
[ApiController]
[Route("api/v1/[controller]")]
[ApiVersion("1.0")]
public class UsersController : ControllerBase

// v2 (new)
[ApiController]
[Route("api/v2/[controller]")]
[ApiVersion("2.0")]
public class UsersController : ControllerBase
```

### Deprecation Markers

```csharp
// Controller level
[ApiVersion("1.0", Deprecated = true)]
[Obsolete("Use v2 endpoints. Will be removed on 2025-06-01")]
public class LegacyUsersController : ControllerBase

// Action level
[HttpGet("{id}")]
[Obsolete("Use GET /api/v2/users/{id} instead")]
[ProducesResponseType(typeof(DeprecationWarningResponse), 299)]
public async Task<IActionResult> GetUser(string id)
```

## Migration Plan Template

```yaml
migration_plan:
  source_version: "1.0"
  target_version: "2.0"
  timeline:
    announcement: "2025-01-01"
    deprecation_start: "2025-02-01"
    sunset_date: "2025-06-01"
  
  phases:
    - phase: 1
      name: "Preparation"
      duration: "2 weeks"
      tasks:
        - Create v2 endpoints alongside v1
        - Add deprecation headers to v1
        - Generate migration documentation
    
    - phase: 2
      name: "Soft Deprecation"
      duration: "1 month"
      tasks:
        - Add deprecation warnings in responses
        - Notify consumers
        - Monitor v1 usage metrics
    
    - phase: 3
      name: "Hard Deprecation"
      duration: "2 months"
      tasks:
        - Return warning headers
        - Track consumer migration
        - Provide migration support
    
    - phase: 4
      name: "Sunset"
      tasks:
        - Remove v1 endpoints
        - Archive v1 documentation
        - Update API registry
```

## Response Headers

```http
# Deprecation Warning
Deprecation: true
Sunset: Sat, 01 Jun 2025 00:00:00 GMT
Link: </api/v2/users>; rel="successor-version"

# Migration Info
X-API-Deprecated-Reason: Replaced by v2 with improved structure
X-API-Migration-Guide: https://docs.company.com/api/migration/v1-to-v2
```

## Skills Used

| Skill | Purpose |
|-------|---------|
| create-endpoint | Generate v2 endpoints |
| add-error-mapping | New error types for migration |
| create-adr | Document migration decision |

## ADR Template for Migration

```markdown
# ADR-XXX: API Migration from v1 to v2

## Context
[Why migration is needed]

## Breaking Changes
[List of breaking changes]

## Decision
[Migration strategy chosen]

## Consequences
### Positive
- Cleaner API design
- Better performance

### Negative  
- Consumer migration effort
- Temporary dual maintenance
```

## Example Invocation

```
@agent:migrator

Migrate /api/v1/contracts to v2:
- Rename `contractNumber` to `number`
- Change `status` from string to enum
- Add required `lastModifiedAt` field
- Timeline: 3 months deprecation
```

## Checklist

- [ ] Breaking changes identified
- [ ] Migration plan created
- [ ] ADR documented
- [ ] v2 endpoints implemented
- [ ] v1 deprecated with markers
- [ ] Deprecation headers added
- [ ] Migration guide written
- [ ] Consumers notified
- [ ] Usage monitoring enabled

## Related Agents

- [Feature Builder](../feature-builder/agent.md) - Create new version
- [Code Reviewer](../code-reviewer/agent.md) - Review migration
