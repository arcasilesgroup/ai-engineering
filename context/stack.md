# Technology Stack

## Backend

### .NET 8

| Component | Technology | Version |
|-----------|------------|---------|
| Runtime | .NET | 8.0 LTS |
| Web Framework | ASP.NET Core | 8.0 |
| Serverless | Azure Functions | Isolated Worker |
| ORM | Entity Framework Core | 8.0 |
| Serialization | Newtonsoft.Json | 13.x |

#### Key Libraries

| Library | Purpose |
|---------|---------|
| Polly | Resilience and transient-fault handling |
| FluentValidation | Input validation |
| Swashbuckle | OpenAPI/Swagger generation |
| Asp.Versioning | API versioning |

#### Patterns

- **Result Pattern** - Railway-oriented programming (see [standards/dotnet.md](../standards/dotnet.md))
- **Error Mapping** - Domain errors to HTTP responses
- **Options Pattern** - Strongly-typed configuration
- **Dependency Injection** - Constructor injection

### Testing (.NET)

| Tool | Purpose |
|------|---------|
| NUnit | Test framework |
| Moq | Mocking |
| FluentAssertions | Assertion library |
| Coverlet | Code coverage |

## Frontend

### TypeScript + React

| Component | Technology | Version |
|-----------|------------|---------|
| Language | TypeScript | 5.x |
| Framework | React | 18.x |
| Build Tool | Vite | 5.x |
| State | React Query / Zustand | Latest |
| Styling | Tailwind CSS | 3.x |

### Testing (Frontend)

| Tool | Purpose |
|------|---------|
| Vitest / Jest | Unit tests |
| React Testing Library | Component tests |
| Playwright | E2E tests |

## Infrastructure

### Cloud Platform (Azure)

| Service | Purpose |
|---------|---------|
| Azure App Service | Web API hosting |
| Azure Functions | Serverless compute |
| Azure API Management | API gateway |
| Azure Key Vault | Secrets |
| Azure Storage | Blobs, Tables, Queues |
| Application Insights | Monitoring |
| Azure AD / Entra ID | Identity |

### Infrastructure as Code

| Tool | Purpose |
|------|---------|
| Terraform | Multi-cloud IaC |
| Bicep | Azure-native IaC |

### CI/CD Platforms

| Platform | Usage |
|----------|-------|
| GitHub Actions | Open source, GitHub-hosted repos |
| Azure Pipelines | Enterprise, Azure DevOps repos |

## Scripting

- **PowerShell** 7.x - Build scripts, automation, Azure DevOps tasks
- **Bash** - Linux scripts, CI/CD pipelines, Docker

## Version Compatibility Matrix

| Component | Minimum | Recommended | Maximum |
|-----------|---------|-------------|---------|
| .NET | 8.0 | 8.0 | 8.x |
| Node.js | 18.x | 20.x | 22.x |
| TypeScript | 5.0 | 5.4+ | 5.x |
| Terraform | 1.5 | 1.7+ | 1.x |
| PowerShell | 7.2 | 7.4+ | 7.x |
| Python | 3.9 | 3.11+ | 3.12 |
