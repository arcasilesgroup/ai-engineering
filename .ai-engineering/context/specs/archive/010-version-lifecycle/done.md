# Spec 010: Version Lifecycle — Done

## Completion Date

2026-02-11

## Summary

Implemented three-layer version lifecycle system: embedded version registry, version checker service, and CLI/gate integration for deprecation enforcement and upgrade warnings.

## Changes Delivered

- **Version registry**: `version/registry.json` — embedded JSON declaring all known versions with lifecycle status (current, supported, deprecated, eol)
- **Version checker**: `version/checker.py` — pure-function service comparing installed version against registry, returning typed results
- **Version models**: `version/models.py` — Pydantic models for registry entries and check results
- **CLI callback**: app-level Typer callback blocks deprecated versions on all commands except version/update/doctor
- **Doctor integration**: version lifecycle diagnostic check (OK/WARN/FAIL)
- **Gate integration**: defense-in-depth deprecation block in pre-push gate
- **Maintenance integration**: version status field in maintenance report
- **Version command**: enhanced with lifecycle status display
- **Audit logging**: version events logged to audit-log.ndjson
- **Wheel inclusion**: `pyproject.toml` includes `version/registry.json` in built wheel

## Quality Gate

- `test_version_checker.py` — version checker service tests
- `test_version_lifecycle.py` — lifecycle enforcement tests
- Coverage >=90% on version modules
- All 11 acceptance criteria verified
- Fail-open on registry errors confirmed

## Decision References

- D-010-1: Embedded registry (not remote) — content-first principle
- D-010-2: CLI callback for all-command blocking — single enforcement point
- D-010-3: Fail-open on registry errors — version check is safety net, not hard dependency
- D-010-4: Semver comparison via tuple parsing — no external library needed
