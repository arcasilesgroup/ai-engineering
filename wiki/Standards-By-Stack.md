# Standards By Stack

> Quick reference for stack-specific coding standards.

## .NET Standards

**File:** `standards/dotnet.md`

### Key Patterns

| Pattern | Rule |
|---------|------|
| **Result Pattern** | All service/provider methods return `Result<T>` |
| **Error Mapping** | Controllers map errors to HTTP status codes |
| **Async** | Use `async/await` throughout, never `.Result` |
| **DI** | Constructor injection, register in Program.cs |

### Verification Commands

```bash
dotnet build --no-restore
dotnet test --no-build --verbosity normal
dotnet format --verify-no-changes
```

### Common Mistakes

```csharp
// WRONG: Accessing Value without IsError check
var user = result.Value;

// CORRECT
if (result.IsError)
    return result.Errors;
var user = result.Value;
```

---

## TypeScript Standards

**File:** `standards/typescript.md`

### Key Patterns

| Pattern | Rule |
|---------|------|
| **Components** | Functional components with TypeScript |
| **Props** | Define interface for all component props |
| **Hooks** | Custom hooks for reusable logic |
| **State** | Use appropriate state management |

### Verification Commands

```bash
npx tsc --noEmit
npm test
npx eslint .
```

### Common Mistakes

```typescript
// WRONG: any type
function process(data: any) { ... }

// CORRECT: specific type
function process(data: UserData) { ... }
```

---

## Python Standards

**File:** `standards/python.md`

### Key Patterns

| Pattern | Rule |
|---------|------|
| **Type Hints** | All function signatures have type hints |
| **Exceptions** | Use custom exception hierarchy |
| **Async** | Use `asyncio` for I/O operations |
| **Testing** | pytest with fixtures |

### Verification Commands

```bash
python -m py_compile <file>
pytest
ruff check .
mypy .
```

### Common Mistakes

```python
# WRONG: bare except
try:
    do_something()
except:
    pass

# CORRECT: specific exception
try:
    do_something()
except ValueError as e:
    logger.error(f"Invalid value: {e}")
    raise
```

---

## Terraform Standards

**File:** `standards/terraform.md`

### Key Patterns

| Pattern | Rule |
|---------|------|
| **Modules** | Reusable modules for common resources |
| **Variables** | All variables have descriptions and types |
| **State** | Remote state with locking |
| **Naming** | `{environment}-{region}-{resource}` |

### Verification Commands

```bash
terraform fmt -check
terraform validate
terraform plan
```

### Common Mistakes

```hcl
# WRONG: hardcoded values
resource "azurerm_resource_group" "main" {
  name     = "prod-rg"
  location = "eastus"
}

# CORRECT: variables
resource "azurerm_resource_group" "main" {
  name     = "${var.environment}-${var.project}-rg"
  location = var.location
}
```

---

## Security Standards

**File:** `standards/security.md`

### OWASP Top 10 Focus

| Vulnerability | Mitigation |
|--------------|------------|
| Injection | Parameterized queries, input validation |
| Broken Auth | Strong passwords, MFA, session management |
| Sensitive Data | Encryption at rest and in transit |
| XSS | Output encoding, CSP headers |
| CSRF | Anti-forgery tokens |

### Secret Management

- Never hardcode secrets
- Use environment variables or secret managers
- Scan with gitleaks before commit
- Rotate secrets regularly

---

## API Design Standards

**File:** `standards/api-design.md`

### REST Conventions

| Method | Usage | Idempotent |
|--------|-------|------------|
| GET | Retrieve resource | Yes |
| POST | Create resource | No |
| PUT | Replace resource | Yes |
| PATCH | Partial update | No |
| DELETE | Remove resource | Yes |

### Error Response Format

```json
{
  "type": "https://api.example.com/errors/validation",
  "title": "Validation Error",
  "status": 400,
  "detail": "The email field is required.",
  "instance": "/users",
  "errors": {
    "email": ["The email field is required."]
  }
}
```

### Versioning

- Use URL versioning: `/api/v1/users`
- Never remove or rename fields without deprecation
- Deprecation period: minimum 6 months

---

## Testing Standards

**File:** `standards/testing.md`

### Coverage Requirements

| Layer | Minimum Coverage |
|-------|-----------------|
| Services | 80% |
| Providers | 80% |
| Controllers | 70% |
| Utilities | 90% |

### Test Naming

```
{MethodName}_{Scenario}_{ExpectedResult}
```

Examples:
- `GetUser_WithValidId_ReturnsUser`
- `CreateOrder_WithInsufficientStock_ReturnsError`

### Test Structure (AAA)

```csharp
[Test]
public async Task GetUser_WithValidId_ReturnsUser()
{
    // Arrange
    var userId = Guid.NewGuid();

    // Act
    var result = await _sut.GetUser(userId);

    // Assert
    Assert.That(result.IsError, Is.False);
}
```

---
**See also:** [Standards Overview](Standards-Overview) | [Quality Gates](Standards-Quality-Gates)
