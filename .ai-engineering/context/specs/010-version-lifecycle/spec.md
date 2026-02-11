---
id: "010"
slug: "version-lifecycle"
status: "in-progress"
created: "2026-02-11"
---

# Spec 010 — Version Lifecycle: Deprecation Enforcement & Upgrade Warnings

## Problem

ai-engineering tracks `framework_version` (currently `0.1.0`) in install-manifest.json, __version__.py, and pyproject.toml, but has NO mechanism to:

1. **Notify users** when a newer version is available — users run outdated governance rules without awareness.
2. **Block operations** when the installed version is deprecated for security reasons — deprecated versions with known vulnerabilities continue to operate normally, bypassing the framework's "mandatory local enforcement" principle.

This violates the non-negotiable: "no policy weakening without risk acceptance." A deprecated version IS a weakened policy, and without enforcement, users cannot know or act on it.

## Solution

Implement a three-layer version lifecycle system:

1. **Version Registry** — embedded JSON file (`version/registry.json`) shipped with the package, declaring all known versions and their lifecycle status (current, supported, deprecated, eol).
2. **Version Checker Service** — pure-function module comparing installed version against the registry, returning a typed result.
3. **CLI & Gate Integration** — inject version checks into:
   - Typer app-level callback (blocks deprecated on all commands except version/update/doctor)
   - Doctor diagnostic (version status check)
   - Gate system (defense-in-depth deprecation block in git hooks)
   - Maintenance report (version status field)
   - Version command (show lifecycle status)

## Scope

### In Scope

- Version registry data model and embedded JSON
- Version checker service (pure functions, no side effects)
- CLI app-level callback for deprecation block + outdated warning
- Doctor diagnostic check for version lifecycle
- Gate check for version deprecation (defense-in-depth)
- Enhanced version command with lifecycle status display
- Maintenance report version status field
- Audit logging for version events
- Risk acceptance bypass for deprecated versions (formal process only)
- Test suite >=90% coverage on new code
- pyproject.toml wheel includes for registry.json

### Out of Scope

- Remote version checking endpoint (future enhancement)
- Automatic self-update mechanism
- Schema migration framework (deferred per D-009-2)
- framework_version bump post-update
- Remote skill update flow

## Acceptance Criteria

1. `ai-eng version` shows lifecycle status from registry (e.g., "0.1.0 (current)")
2. When installed version is outdated, CLI prints warning to stderr on any command (non-blocking)
3. When installed version is deprecated, `ai-eng gate pre-commit` exits non-zero with security message
4. When installed version is deprecated, `ai-eng install` exits non-zero (CLI callback blocks)
5. When installed version is deprecated, `ai-eng version`, `ai-eng update`, `ai-eng doctor` still work (exempt)
6. `ai-eng doctor` includes a version lifecycle check (OK/WARN/FAIL)
7. Registry.json is valid and ships in the wheel
8. Risk acceptance bypass downgrades deprecated block to warning (formal process)
9. Version events are logged to audit-log.ndjson
10. `pytest --cov=ai_engineering.version` >=90% coverage
11. All existing tests remain green; no regressions

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D-010-1 | Embedded registry (not remote) | Content-first principle; Python is minimal runtime. Remote check is future enhancement. Registry ships with each release, so deprecation data for the user's version is always available. |
| D-010-2 | CLI callback for all-command blocking | Single enforcement point. Gate-level check is defense-in-depth only. Exempt commands: version, update, doctor (needed for diagnosis and remediation). |
| D-010-3 | Fail-open on registry errors | Corrupted/missing registry must not block all operations. Version check is safety net, not hard dependency. |
| D-010-4 | Semver comparison via tuple parsing | No external library needed. Framework uses strict X.Y.Z format. `tuple(int(x) for x in v.split("."))` is sufficient. |
