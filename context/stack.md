# Technology Stack

## Backend

### .NET 8

| Component | Technology | Version |
|-----------|------------|---------|
| Runtime | .NET | 8.0 LTS |
| Web Framework | ASP.NET Core | 8.0 |
| Serverless | Azure Functions | Isolated Worker |
| ORM | Entity Framework Core | 8.0 (where used) |
| Serialization | Newtonsoft.Json | 13.x |

#### Key Libraries

| Library | Purpose |
|---------|---------|
| {ProjectName}.Foundation | Result pattern, error mapping |
| Polly | Resilience and transient-fault handling |
| FluentValidation | Input validation |
| Swashbuckle | OpenAPI/Swagger generation |
| Asp.Versioning | API versioning |

> ℹ️ Replace `{ProjectName}.Foundation` with your shared library name, or implement the patterns directly.

#### Patterns in Use

- **Result Pattern** - Railway-oriented programming (see [standards/dotnet/patterns/result-pattern.md](../standards/dotnet/patterns/result-pattern.md))
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

---

## Frontend

### TypeScript + React

| Component | Technology | Version |
|-----------|------------|---------|
| Language | TypeScript | 5.x |
| Framework | React | 18.x |
| Build Tool | Vite | 5.x |
| State | React Query / Zustand | Latest |
| Styling | Tailwind CSS | 3.x |

### Mobile

| Component | Technology |
|-----------|------------|
| Framework | React Native |
| Navigation | React Navigation |

### Testing (Frontend)

| Tool | Purpose |
|------|---------|
| Vitest / Jest | Unit tests |
| React Testing Library | Component tests |
| Playwright | E2E tests |

---

## Infrastructure

### Cloud Platform

| Service | Purpose |
|---------|---------|
| Azure App Service | Web API hosting |
| Azure Functions | Serverless compute |
| Azure API Management | API gateway |
| Azure API Center | API catalog |
| Azure Key Vault | Secrets |
| Azure Storage | Blobs, Tables, Queues |
| Application Insights | Monitoring |
| Azure AD / Entra ID | Identity |

### Infrastructure as Code

| Tool | Purpose |
|------|---------|
| Terraform | Multi-cloud IaC |
| Bicep | Azure-native IaC |
| Azure DevOps Pipelines | CI/CD |

---

## Scripting

### PowerShell

- Version: 7.x (Core) / 5.1 (Windows)
- Use cases: Build scripts, automation, Azure DevOps tasks

### Bash

- Use cases: Linux scripts, CI/CD pipelines, Docker

---

## Development Tools

| Tool | Purpose |
|------|---------|
| Visual Studio 2022 | .NET development |
| VS Code | TypeScript, scripts, IaC |
| Azure Data Studio | Database management |
| Postman | API testing |
| Git | Version control |
| Azure DevOps | Project management, CI/CD |

---

## Version Compatibility Matrix

| Component | Minimum | Recommended | Maximum |
|-----------|---------|-------------|---------|
| .NET | 8.0 | 8.0 | 8.x |
| Node.js | 18.x | 20.x | 22.x |
| TypeScript | 5.0 | 5.4+ | 5.x |
| Terraform | 1.5 | 1.7+ | 1.x |
| PowerShell | 7.2 | 7.4+ | 7.x |
