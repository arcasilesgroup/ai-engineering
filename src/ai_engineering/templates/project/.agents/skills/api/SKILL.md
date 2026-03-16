---
name: api
description: "Design and review APIs using contract-first approach with OpenAPI specification, versioning strategy, and backward compatibility analysis."
metadata:
  version: 1.0.0
  tags: [api, rest, graphql, openapi, contract, versioning]
  ai-engineering:
    scope: read-write
    token_estimate: 800
---

# API Design

## Purpose

Contract-first API design and review skill. Covers OpenAPI specification authoring, REST/GraphQL convention enforcement, versioning strategy, backward compatibility analysis, and error model standardization. Ensures APIs are consistent, well-documented, and evolvable.

## Trigger

- Command: agent invokes api-design skill or user requests API design/review.
- Context: new API endpoint, API contract review, versioning decision, backward compatibility assessment, API documentation update.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"api"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## When NOT to Use

- **Implementation of API endpoints** — use `code-review` for reviewing implementation code.
- **Security review of API auth** — use `sec-review` for authentication/authorization assessment.
- **Database schema for API data** — use `db` for schema design.
- **CI/CD for API deployment** — use `cicd` for pipeline setup.

## Procedure

1. **Understand context** — identify the API's purpose, consumers, and constraints.
   - Who consumes this API (frontend, mobile, third-party, internal services)?
   - What authentication model is used?
   - Are there existing API conventions in the project?

2. **Design or review contract** — author or evaluate OpenAPI 3.1 specification.
   - URL structure: resources as plural nouns, hierarchical for relationships.
   - HTTP methods: GET (read), POST (create), PUT (replace), PATCH (update), DELETE (remove).
   - Status codes: consistent usage across endpoints.
   - Request/response schemas: typed, validated, documented.

3. **Standardize error model** — ensure consistent error responses.
   - Structure: `{ error: { code, message, details[], requestId } }`.
   - Map error codes to HTTP status codes consistently.
   - Include field-level validation errors in `details[]`.

4. **Design pagination** — for collection endpoints.
   - Keyset (cursor) pagination preferred for large datasets.
   - Include `nextCursor`, `hasMore`, `totalCount` in responses.
   - Support `limit` parameter with sensible defaults and maximums.

5. **Assess backward compatibility** — for API modifications.
   - Classify changes: additive (safe) vs breaking (requires version bump).
   - Additive: new fields, new endpoints, new optional parameters.
   - Breaking: removed fields, type changes, renamed fields, removed endpoints.
   - Apply expand-contract pattern for breaking changes.

6. **Design versioning** (if breaking changes needed).
   - URL versioning: `/v1/`, `/v2/` — simplest, most explicit.
   - Header versioning: `API-Version: 2024-01-15` — for incremental changes.
   - Document sunset timeline: announce → 6-month window → remove.

7. **Validate specification** — lint and verify completeness.
   - Run `spectral lint` or `redocly lint` if available.
   - Verify: all endpoints documented, all parameters typed, all responses defined, all error cases covered.
   - Check: consistent naming, consistent casing (camelCase or snake_case), consistent date formats.

## Output Contract

- OpenAPI 3.1 specification (YAML or JSON).
- Backward compatibility assessment (if reviewing changes).
- Versioning plan (if breaking changes detected).
- API review findings with severity-tagged issues.

## Governance Notes

- API specifications are project-managed — the skill generates, the project maintains.
- Breaking API changes without a versioning plan are blocked.
- Error model consistency is enforced across all endpoints.
- API specifications must be version-controlled alongside code.

### Iteration Limits

- Max 3 attempts to resolve the same API design issue. After 3 failures, escalate to user with evidence.

### Post-Action Validation

- After generating OpenAPI specs, validate YAML/JSON syntax.
- Run API linter (spectral, redocly) if available.
- If validation fails, fix issues and re-validate (max 3 attempts).

## References

- `standards/framework/stacks/typescript.md` — TypeScript API implementation patterns.
- `standards/framework/stacks/dotnet.md` — .NET API implementation patterns.
- `standards/framework/stacks/nestjs.md` — NestJS API patterns.
- `.agents/agents/ai-build.md` — implementation agent that performs API design.
