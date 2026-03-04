---
id: "033"
slug: "audit-remediation"
status: "done"
created: "2026-03-04"
---

# Spec 033 — 18-Dimension Audit Remediation

## Problem

An 18-dimension full audit (`references/audit-18d-2026-03-04.md`) scored the framework at **68/100** with a **NO-GO** release verdict. The audit identified:

- **1 P0 blocker**: Gitleaks wrong command in `workflows.py:225` (`detect --staged` instead of `protect --staged`) — security regression in the commit workflow.
- **6 P1 issues**: Version inconsistency (install-manifest vs manifest.yml), stale README/GEMINI.md (v2 counts), missing documentation gate in workflows, stale ownership-map.json, template drift, tool-availability code duplication.
- **13 P2 advisories**: Backward-compat shims (145 LOC), test pyramid skew, no maintenance CI cron, missing `.gitattributes`, SSRF semgrep rule, circular imports, test stubs.

The framework cannot be released until at least P0 is fixed, and P1 issues should be addressed to bring the audit score above 80/100 and achieve a GO verdict.

## Solution

Implement all P0, P1, and P2 improvements from the audit in a phased approach:

1. **P0 — Security fix** (immediate): Fix gitleaks command, add test.
2. **P1 — Release blockers** (next): Version sync, doc updates, ownership-map regeneration, template sync, tool dedup.
3. **P2 — Quality hardening** (backlog): Remove backward-compat shims, extract doctor/models.py, add E2E tests, fill test stubs, add .gitattributes, wire check_platforms(), add CI cron, SSRF rule, GEMINI.md update, mirror_sync coverage.

## Scope

### In Scope

- Fix gitleaks command in `workflows.py` (P0-1)
- Sync `install-manifest.json` version and schema (P1-1, P1-2)
- Update README.md and GEMINI.md to v3 counts (P1-3, P2-11)
- Sync template `manifest.yml` and `README.md` (P1-6)
- Regenerate `ownership-map.json` with missing paths (P1-5)
- Merge tool-availability primitives into shared module (P2-1)
- Remove `gates.py` `__getattr__` + doctor/service.py backward-compat wrappers (P2-2)
- Extract `doctor/models.py` to break circular imports (P2-3)
- Implement 6 test stubs with real assertions (P2-5)
- Add `.gitattributes` for cross-OS line endings (P2-6)
- Fix Windows venv paths in template `settings.json` (P2-7)
- Wire `check_platforms()` into `diagnose()` (P2-8)
- Add CI cron for `ai-eng maintenance all` (P2-9)
- Add SSRF semgrep rule (P2-10)
- Add `mirror_sync.py` coverage for root-level files (P2-12)

### Out of Scope

- Documentation gate implementation in workflows (P1-4) — requires design spec for CHANGELOG/README auto-check logic; deferred to follow-up spec.
- E2E test expansion to 5% target (P2-4) — multi-session effort; tracked as separate backlog item.
- Spec status close-time enum enforcement (P2-13) — cosmetic for archived specs.
- Contract compliance FAIL clauses (empty-repo wizard, commit format, branch naming, remote-skills default) — architectural decisions requiring separate specs.

## Acceptance Criteria

1. `gitleaks protect --staged --no-banner` used in `workflows.py` with passing test.
2. `install-manifest.json` at `frameworkVersion: "0.2.0"`, `schemaVersion: "1.2"` with all model fields present.
3. README.md shows 34 skills, 7 agents, 37 slash commands (no v2 counts remain).
4. GEMINI.md shows 34 skills, 7 agents, correct `/ai:` command syntax.
5. Template `manifest.yml` and `README.md` synced with canonical.
6. `ownership-map.json` includes `.github/prompts/**`, `.github/agents/**`, `.claude/**`, `state/session-checkpoint.json`.
7. `doctor/checks/tools.py` delegates to shared tool primitives (no duplicated `shutil.which` + pip/uv logic).
8. `gates.py` has no `__getattr__` block; `doctor/service.py` has no backward-compat wrapper functions.
9. `doctor/models.py` exists with `CheckResult`, `CheckStatus`, `DoctorReport`; no circular import between doctor modules.
10. All 6 test stubs replaced with real assertions.
11. `.gitattributes` exists with LF enforcement for `.sh` scripts.
12. Template `.claude/settings.json` includes Windows-compatible venv paths.
13. `check_platforms()` callable from `diagnose()` via `--check-platforms` flag.
14. CI maintenance cron workflow exists (weekly schedule).
15. `.semgrep.yml` includes SSRF detection rule.
16. `mirror_sync.py` covers `manifest.yml` and `README.md` root-level files.
17. All existing tests pass; no regressions.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | Merge tool primitives into `detector/readiness.py` (not new `tools_util.py`) | `detector/readiness.py` already has the most complete implementation; avoids creating a new module. |
| D2 | Rename `CheckStatus` in `validator/_shared.py` to `IntegrityStatus` | Eliminates naming collision with `doctor/models.py::CheckStatus`. |
| D3 | Keep doc gate (P1-4) out of scope | Requires design decisions on CHANGELOG classification logic; separate spec. |
| D4 | Keep contract FAIL clauses out of scope | Architectural decisions (wizard, commit format enforcement) need their own specs. |
