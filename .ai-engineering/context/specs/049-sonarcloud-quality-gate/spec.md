---
id: "049"
slug: sonarcloud-quality-gate
status: active
created: "2026-03-10"
size: M
tags: [security, sonarcloud, governance, quality-gate]
branch: fix/049-sonarcloud-quality-gate
pipeline: standard
decisions: []
---

# Spec 049 — Fix SonarCloud Quality Gate + No-Suppression Rule

## Problem

SonarCloud Quality Gate is FAILED on `main`, blocking CI. Two conditions fail:

1. **`security_rating` = E** (actual: 5, threshold: A/1) — 4 BLOCKER path traversal (S2083) + 1 MAJOR command injection (S6350) vulnerability. All false positives from taint analysis that doesn't understand validated paths.
2. **`security_hotspots_reviewed` = 0%** (threshold: 100%) — 4 regex DoS hotspots (S5852). All false positives — simple patterns with no nested quantifiers.

Additionally, the framework lacks an explicit rule prohibiting AI agents from using suppression comments (`# NOSONAR`, `# nosec`, `# type: ignore`, `# noqa`, etc.) as shortcuts. As a governance, quality, and security framework, we must fix root causes — not silence tools.

## Solution

1. **Fix vulnerabilities in code** — add path containment validation (`resolve().relative_to()`) and argument type validation to satisfy SonarCloud's taint analyzer. No suppression comments.
2. **Add no-suppression governance rule** — explicit prohibition in CLAUDE.md, AGENTS.md, and core standards preventing AI from adding suppression comments. False positives must be resolved by refactoring code to satisfy the analyzer, or escalated to the user.
3. **User reviews hotspots** — 4 regex DoS hotspots must be marked "Safe" in SonarCloud UI (no code-level fix possible for hotspot review status).

## Scope

### In Scope

- Fix 5 SonarCloud vulnerabilities via code changes (path validation, argument validation)
- Add no-suppression rule to CLAUDE.md, AGENTS.md, framework core.md
- Sync all template mirrors
- Content integrity validation

### Out of Scope

- Snyk badge (already working, will populate after `snyk monitor` runs on main)
- Changes to SonarCloud Quality Gate configuration
- Regex refactoring (hotspots are safe as-is)

## Acceptance Criteria

- [ ] SonarCloud `security_rating` = A (zero open vulnerabilities)
- [ ] No-suppression rule exists in CLAUDE.md, AGENTS.md, core.md
- [ ] All template mirrors synced
- [ ] All tests pass, no lint/type errors
- [ ] Content integrity validation passes
