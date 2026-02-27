---
id: "003"
slug: "governance-enforcement"
status: "in-progress"
created: "2026-02-10"
---

# Spec 003 — Governance Enforcement

## Problem

Two critical governance gaps remain after Spec 002:

1. **No spec-first enforcement** — the framework has no mechanism to guide or require an active spec before non-trivial changes. Agents can make large, untracked modifications without a formal spec.
2. **No content integrity validation** — after creating, deleting, or renaming governance documents, nothing validates cross-references, mirrors, counters, or instruction file consistency. Broken links and stale references accumulate silently.

## Solution

1. Create **4 new lifecycle skills** that close both gaps:
   - `create-spec` — guides spec creation with branch strategy (feat/*, bug/*, hotfix/*).
   - `delete-skill` — inverse of create-skill with dependency checks.
   - `delete-agent` — inverse of create-agent with dependency checks.
   - `content-integrity` — 6-category validation of all governance content.

2. **Expand verify-app agent** with content integrity capability.

3. **Add enforcement rules** to `core.md` and `framework-contract.md`:
   - Spec-first: non-trivial changes require an active spec.
   - Content integrity: post-change validation is mandatory.

## Scope

### In Scope

- 4 new skills in `skills/govern/`.
- Enforcement sections in `standards/framework/core.md`.
- Framework-contract updates (9.5 session contract steps 0 and 7).
- `verify-app.md` expansion.
- `manifest.yml` close_actions update.
- Cross-references, mirrors, instruction files, counters, changelog.

### Out of Scope

- Automated hook-based enforcement (content-integrity as skill, not hook — D7).
- New agents (expand verify-app instead — D6).
- Python code changes.

## Acceptance Criteria

1. `create-spec` skill exists with branch-first step and 8-phase procedure.
2. `delete-skill` and `delete-agent` skills exist with dependency-check-first inverse procedures.
3. `content-integrity` skill exists with 6 validation categories.
4. `verify-app` includes content integrity as capability and behavior step.
5. `core.md` has "Spec-First Enforcement" and "Content Integrity Enforcement" sections.
6. `framework-contract.md` 9.5 has steps 0 (create-spec) and 7 (content-integrity).
7. `manifest.yml` close_actions includes `validate_content_integrity`.
8. All 6 instruction files list 6 lifecycle skills.
9. Product-contract counters: 25 skills, 8 agents.
10. All canonical/mirror pairs byte-identical.
11. No broken cross-references.
12. `content-integrity` skill passes on its own output (dogfooding).

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | `lifecycle/` for all framework lifecycle skills | Separation from SWE; lifecycle = framework meta-operations |
| D2 | Spec 003 scope: governance enforcement | Distinct from Spec 002 (cross-ref hardening) |
| D3 | `create-spec` branch-first step | Every non-trivial change starts on a dedicated branch |
| D4 | `content-integrity` as skill not hook | Content-first principle; avoid Python complexity |
| D5 | Expand verify-app not new agent | Avoid agent proliferation |
| D6 | "Non-trivial" = >3 files, new feature, refactor, architectural, governance change | Clear heuristic for spec-first enforcement |
| D7 | Exempt from spec: typos, single-line, formatting, dependency bumps | Keep trivial changes lightweight |
