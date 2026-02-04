---
description: Migrate an API endpoint to a new version
---

## Context

Migrates an existing API endpoint from one version to the next (e.g., v1 → v2), creating the new version while maintaining backward compatibility with the old version.

## Inputs

$ARGUMENTS - Endpoint to migrate (e.g., "GET /api/v1/users") and description of changes

## Steps

### 1. Analyze Current Endpoint

- Find the current controller, provider, service for the endpoint.
- Document the current request/response contract.
- Identify all consumers (blast radius analysis).

### 2. Plan Migration

Based on $ARGUMENTS, determine:
- What changes in the new version (new fields, removed fields, type changes).
- Whether this is a breaking change.
- What backward compatibility is needed.

Present plan to user for approval.

### 3. Create New Version

- Copy the endpoint to the new API version.
- Apply the requested changes.
- Create new DTOs for the new version (don't modify existing DTOs).
- Update the provider/service layer to support both versions.

### 4. Mark Old Version as Deprecated

- Add `[Obsolete]` attribute or deprecation notice to the old endpoint.
- Add `Sunset` header to old endpoint responses.
- Update API documentation.

### 5. Generate Tests

- Create tests for the new version endpoint.
- Verify old version still works unchanged.

### 6. Verify

- Both old and new versions work correctly.
- All tests pass.
- API documentation updated.

## Verification

- New version returns expected responses
- Old version unchanged and still functional
- Deprecation notice on old version
- Tests cover both versions
