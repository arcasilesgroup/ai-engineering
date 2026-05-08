# Handler: solution-intent-validate

## Purpose

Read-only completeness and freshness check. Produces a scorecard without modifying files.

## Procedure

### 1. Read document
Load `docs/solution-intent.md`.

### 2. Check completeness per section

For each of the 7 sections and their subsections:

| Section | Subsections to check |
|---------|---------------------|
| 1. Introduction | 1.1 Identity, 1.2 Objective, 1.3 Problem, 1.4 Outcomes, 1.5 Scope, 1.6 Personas |
| 2. Requirements | 2.1 Architecture, 2.2 Functional, 2.3 NFRs, 2.4 Integrations |
| 3. Technical Design | 3.1 Stack, 3.2 Environments, 3.3 API Policies, 3.4 Publication |
| 4. Observability | 4.1 Measurements, 4.2 SLIs/SLOs, 4.3 Logging, 4.4 Runbooks |
| 5. Security | 5.1 Auth, 5.2 Exposure, 5.3 Recovery, 5.4 Hardening |
| 6. Quality | 6.1 Gates, 6.2 Patterns, 6.3 Testing, 6.4 Scalability |
| 7. Next Objectives | 7.1 Roadmap, 7.2 Epics, 7.3 KPIs, 7.4 Active Spec, 7.5 Risks |

Per subsection, verify:
- Header exists
- At least one table OR Mermaid diagram present
- No placeholder markers (`<...>`) remain
- Content is populated (not empty)
- TBD markers are allowed (they indicate intentional gaps)

### 3. Check freshness
Parse `Last Review:` date in header:
- If > 30 days ago: WARNING (stale)
- If > 60 days ago: CRITICAL (very stale)
- If missing: INFO (never reviewed)

### 4. Check consistency
Cross-reference with project state:
- manifest.yml skill count vs Section 2.2 skill count
- manifest.yml agent count vs Section 2.2 agent count
- manifest.yml tooling vs Section 3.1 tooling
- manifest.yml quality gates vs Section 6.1 gates
- Active spec pointer vs Section 7.4
- state.db.decisions active count vs Section 2.2 decisions

### 5. Produce scorecard

```
| Section | Status | Notes |
|---------|--------|-------|
| 1.1 Identity | COMPLETE | |
| 1.2 Objective | COMPLETE | |
| 1.3 Problem Statement | COMPLETE | |
| 1.4 Desired Outcomes | COMPLETE | |
| 1.5 Scope | COMPLETE | |
| 1.6 Personas | PARTIAL | Missing DevSecOps journey |
| 2.1 Architecture | COMPLETE | Diagram present |
| 2.2 Functional Requirements | COMPLETE | |
| ... | ... | ... |
| --- | --- | --- |
| Freshness | OK | Last review: 5 days ago |
| Consistency | WARN | Skill count mismatch (30 vs 28) |
```

### 6. Report

- Scorecard table
- Summary: N/M sections COMPLETE, N TBD, N PARTIAL
- Recommended actions (if any)
