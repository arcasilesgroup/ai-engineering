# Framework NestJS Stack Standards

## Update Metadata

- Rationale: establish NestJS-specific patterns for enterprise backend services with modular architecture.
- Expected gain: consistent NestJS code quality, dependency injection patterns, and API design.
- Potential impact: NestJS projects get enforceable module, guard, pipe, and testing patterns.

## Stack Scope

- Primary language: TypeScript (strict mode).
- Framework: NestJS 10+ (Express or Fastify adapter).
- Base standard: extends `standards/framework/stacks/typescript.md` — all TS rules apply.
- Supporting formats: Markdown, YAML, JSON.
- Toolchain baseline: inherits from TypeScript + NestJS CLI.
- Distribution: Docker container, cloud service, or serverless deployment.

## Required Tooling

- Inherits all tooling from `typescript.md`.
- CLI: `@nestjs/cli` (`nest` commands).
- Testing: Jest (NestJS default) or Vitest with NestJS testing utilities.
- API documentation: Swagger/OpenAPI via `@nestjs/swagger`.
- Database: TypeORM, Prisma, or MikroORM per project convention.

## Minimum Gate Set

- Pre-commit: inherits from `typescript.md`.
- Pre-push: inherits from `typescript.md` + `nest build` (compile check).

## Quality Baseline

- Inherits all quality rules from `typescript.md`.
- Every module must have its own `*.module.ts` with explicit imports/exports.
- DTOs validated with `class-validator` + `class-transformer` (or `zod`).
- All endpoints documented with Swagger decorators.
- Guards and interceptors for cross-cutting concerns (auth, logging, rate limiting).

## Code Patterns

- **Module architecture**: one module per domain. Modules declare controllers, providers, imports, exports.
- **Dependency injection**: constructor injection via NestJS IoC container. Custom providers for external services.
- **Controllers**: thin — delegate to services. Use decorators for routing, validation, auth.
- **Services**: business logic layer. Injectable, testable, no HTTP awareness.
- **DTOs**: separate request/response DTOs. Validate input with pipes.
- **Guards**: `@UseGuards()` for auth/authorization. Implement `CanActivate`.
- **Interceptors**: logging, caching, response transformation via `NestInterceptor`.
- **Pipes**: input validation and transformation. Global `ValidationPipe` recommended.
- **Exception filters**: centralized error handling with `@Catch()` decorators.
- **Configuration**: `@nestjs/config` with Joi or Zod validation.
- **Project layout**: `src/modules/<domain>/` with controller, service, dto, entity subdirs.

## Testing Patterns

- Inherits patterns from `typescript.md`.
- Unit tests: mock providers with `Test.createTestingModule()`.
- Integration tests: `@nestjs/testing` with `INestApplication` for API testing.
- E2E: supertest with compiled NestJS app.
- Database tests: use in-memory database or test containers.

## Update Contract

This file is framework-managed and may be updated by framework releases.
