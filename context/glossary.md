# Glossary

## Domain Terms

| Term | Definition |
|------|------------|
| **API** | Application Programming Interface - contract for service communication |
| **API Center** | Azure service for API catalog and discovery |
| **API Management (APIM)** | Azure API gateway service |
| **Entity** | Core business object in your domain |
| **Aggregate** | Cluster of domain objects treated as a single unit |
| **Value Object** | Object defined by its attributes rather than identity |

## Technical Terms

| Term | Definition |
|------|------------|
| **Provider** | Business layer class that orchestrates services and contains business logic |
| **Service** | Integration layer class that wraps a single external system |
| **Result Pattern** | Error handling approach using `Result<T>` instead of exceptions |
| **Error Mapping** | Process of converting domain errors to HTTP responses |
| **DTO** | Data Transfer Object - data structure for API communication |
| **ADR** | Architecture Decision Record - documented design decision |

## Abbreviations

| Abbreviation | Full Form |
|--------------|-----------|
| **BFF** | Backend for Frontend |
| **CI/CD** | Continuous Integration / Continuous Deployment |
| **DI** | Dependency Injection |
| **IaC** | Infrastructure as Code |
| **JWT** | JSON Web Token |
| **RBAC** | Role-Based Access Control |
| **SPA** | Single Page Application |
| **TLS** | Transport Layer Security |

## Project-Specific Terms

> ℹ️ Add your project-specific terms here.

| Term | Definition |
|------|------------|
| **{YourService}** | Description of your primary service |
| **Shared Library** | Common NuGet package with patterns and utilities |
| **Reference Data** | Master data used across multiple services |

## Error Types

| Error | HTTP Status | Description |
|-------|-------------|-------------|
| **NotFoundError** | 404 | Resource does not exist |
| **InvalidInputError** | 400 | Request validation failed (simple) |
| **InvalidInputDetailedError** | 400 | Request validation failed (with details) |
| **UnauthorizedError** | 401 | Authentication required |
| **ForbiddenError** | 403 | Insufficient permissions |
| **ConflictError** | 409 | Resource state conflict |
| **InternalError** | 500 | Unexpected server error |
