---
id: "030"
slug: "sonar-cicd-pipeline-integration"
status: "done"
created: "2026-03-02"
---

# Spec 030 - Sonar CI/CD Pipeline Integration

## Problem

Sonar credentials, IDE setup, and local sonar-gate skill exist, but pipeline generation and pre-push hooks do not integrate Sonar analysis. Projects configured with Sonar must manually inject CI analysis and receive no advisory signal before push.

## Solution

Add Sonar-aware CI/CD generation for GitHub Actions and Azure Pipelines, wire Sonar config through install and regenerate flows, add advisory pre-push scanner execution, and extend compliance/injector/template surfaces while preserving silent-skip behavior for non-Sonar teams.

## Scope

### In Scope

- Extend Sonar credential metadata with organization.
- Extend `ai-eng setup sonar` to capture/resolve organization.
- Add Sonar CI/CD state model (`SonarCicdConfig`) and manifest status wiring.
- Inject Sonar analysis blocks into generated `ci.yml` for GitHub and Azure.
- Add Sonar passthrough in install/regenerate flow and manifest updates.
- Add `sonar-project.properties` create-only generation when configured.
- Add compliance informational Sonar detection and injector snippets/templates.
- Add advisory pre-push Sonar gate execution.
- Add and update tests across affected modules.

### Out of Scope

- Changing mandatory gate semantics (risk gates remain blocking).
- Replacing existing pipeline files (create-only behavior remains).
- Introducing Sonar secrets into repository files.
- Modifying remote provider branch policies.

## Acceptance Criteria

1. `SonarConfig` serializes `organization` in `tools.json`.
2. `ai-eng setup sonar --organization <org>` persists organization, with fallback from `sonar-project.properties`.
3. `SonarCicdConfig.is_sonarcloud` correctly classifies mixed-case/trailing-slash SonarCloud URLs via normalized hostname parsing.
4. `generate_pipelines(..., sonar_config=None)` preserves current generated output.
5. GitHub `ci.yml` includes Sonar step when Sonar is enabled, with `fetch-depth: 0`, correct action by platform (Cloud/Qube), and fork secret guard.
6. Azure `ci.yml` includes Sonar Prepare/Analyze/Publish tasks when Sonar is enabled, with action family split by platform (Cloud/Qube) and service connection fallback to `$(SONAR_SERVICE_CONNECTION)`.
7. Install and regenerate flows pass Sonar config through generation and persist Sonar CI/CD status in manifest.
8. Compliance report includes an informational `sonar-analysis-present` check for primary `ci.yml` only, never failing due to missing Sonar.
9. Pre-push Sonar gate is advisory: scanner failures are visible but do not block push.
10. Test suite additions cover model defaults/URL parsing, CI render branches, compliance/injector behavior, setup parsing, installer passthrough, and advisory gate edge cases.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D030-001 | Resolve organization with precedence `--organization` > `sonar-project.properties` > empty and persist in `tools.json`. | Supports explicit CLI control while keeping ergonomic fallback from project config. |
| D030-002 | Resolve Azure Sonar service connection from config first, then `$(SONAR_SERVICE_CONNECTION)` fallback. | Avoids hardcoded connection names while allowing pipeline-level variable defaults. |
| D030-003 | Pre-push Sonar gate is advisory by default and never blocks push. | Aligns with D024-002 optional Sonar model and avoids impacting non-Sonar teams. |
| D030-004 | Determine SonarCloud by normalized `urlparse(host_url).hostname`, not substring matching. | Prevents false positives and handles mixed-case/trailing-slash inputs robustly. |
