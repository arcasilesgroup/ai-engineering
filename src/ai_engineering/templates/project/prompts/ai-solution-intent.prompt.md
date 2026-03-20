---
name: ai-solution-intent
description: "Use when maintaining the solution intent document: scaffolding new projects (init), surgical updates after architectural changes (sync), or completeness validation (validate)."
model: opus
effort: high
argument-hint: "init|sync|validate"
mode: agent
tags: [documentation, architecture, governance]
---



# Solution Intent

## Purpose

Manage the solution intent document (`docs/solution-intent.md`) lifecycle. The solution intent defines the architectural decisions, technical design, and evolution roadmap of the project. Three modes ensure the document stays accurate, complete, and fresh.

## When to Use

- New project needs a solution intent document -> `init`
- Architectural changes were made (specs closed, stack changes, new agents/skills) -> `sync`
- Pre-release or periodic health check -> `validate`
- Automatically invoked by `/ai-pr` when staged changes include architecture files

## Process

1. **Detect mode** from arguments: `init`, `sync`, or `validate`
2. **Execute handler** -- follow the matching handler in `handlers/`
3. **Report** -- present summary of actions taken

## Quick Reference

```
/ai-solution-intent init       # scaffold from template
/ai-solution-intent sync       # update sections from project state
/ai-solution-intent validate   # completeness and freshness scorecard
```

## Integration

- **Called by**: `/ai-pr` (step 6.7) when architectural changes detected
- **Calls**: `handlers/init.md`, `handlers/sync.md`, `handlers/validate.md`
- **Reads**: `docs/solution-intent.md`, `.ai-engineering/manifest.yml`, `.ai-engineering/state/decision-store.json`

## Governance Notes

**Visual priority**: diagrams > tables > text. Every section MUST have at least one Mermaid diagram or table. Text accompanies but does not substitute visual representation.

**TBD policy**: if a section's data is not defined, implemented, or in scope, mark it explicitly as TBD. NEVER invent data.

**Writing**: use `/ai-write` patterns for document generation. The handler defines WHAT sections and data to gather; `/ai-write` defines HOW to write them.

**Ownership**: `docs/solution-intent.md` is project-managed. Sync updates data fields but never removes user-authored content. `ai-eng update` does not touch this file.

## References

- `.github/prompts/ai-pr.prompt.md` -- PR workflow that triggers sync automatically
- `.github/prompts/ai-write.prompt.md` -- documentation writing patterns
- `.ai-engineering/manifest.yml` -- governance surface counts, tooling, providers
$ARGUMENTS

---

# Handler: init

## Purpose

Scaffold a comprehensive `docs/solution-intent.md` from real project state. This is the Solution Intent — defines what you are building, how, and why.

## Prerequisites

- Run `/ai-explore` or equivalent deep audit of the repo BEFORE writing. Every data point must come from verified sources (code, config, state files).
- Use `/ai-write` patterns: visual priority (diagrams > tables > text), audience = technical team, no filler.

## Procedure

### 1. Check existence
If `docs/solution-intent.md` exists, warn and ask user to confirm overwrite.

### 2. Deep audit
Gather data from REAL project state — never from old documentation:

| Source | What to extract |
|--------|----------------|
| `pyproject.toml` | Name, version, description, license, Python version, dependencies |
| `.ai-engineering/manifest.yml` | Skills count, agents, stacks, providers, IDEs, quality gates, tooling, ownership |
| `.ai-engineering/state/decision-store.json` | Active decisions, risk acceptances |
| `.ai-engineering/specs/spec.md` | Current spec, status |
| `.ai-engineering/contexts/` | Available language/framework/team contexts |
| `.ai-engineering/runbooks/` | Available operational runbooks |
| `src/ai_engineering/` | Module structure, CLI commands, services, layers |
| `.github/prompts/` | Actual skill count and categories |
| `.github/agents/` | Actual agent count, models, colors |
| `.github/hooks/` | Telemetry hook configuration |
| `scripts/` | Sync, validation, work item scripts |

### 3. Scaffold 7 sections

Each section MUST have at least one Mermaid diagram or table. If data is not available, mark as **TBD — pending team definition**.

**Section 1: Introduction**
- 1.1 Identity (table: name, org/repo, version, status, model, license)
- 1.2 Objective (1 paragraph from pyproject.toml description + manifest purpose)
- 1.3 Problem Statement (why this framework exists)
- 1.4 Desired Outcomes (bullet list of measurable goals)
- 1.5 Scope (in/out explicit lists)
- 1.6 Stakeholders and Personas (table: persona, journey, primary actions)

**Section 2: Requirements (Solution Intent)**
- 2.1 High-Level Solution Architecture (mermaid flowchart TB — real component map)
- 2.2 Functional Requirements by Domain (table: domain, requirement, priority, status)
  - Include Skills table (by type, with actual count)
  - Include Agents table (name, purpose, scope)
  - Include CLI commands table (from actual `src/ai_engineering/cli_commands/`)
- 2.3 Non-Functional Requirements (table: category, requirement, threshold, measurement)
- 2.4 Integrations (mermaid flowchart LR + contracts table: system A/B, protocol, contract, SLA)

**Section 3: Technical Design**
- 3.1 Stack and Architecture (mermaid: real module dependency graph from `src/`)
  - Stack table (layer, component, technology)
- 3.2 Environments (table: environment, purpose, variables, secrets, network)
- 3.3 API and Gateway Policies (table: surface, auth, rate limit, versioning)
- 3.4 Publication and Deployment (mermaid flowchart: dev -> gates -> PR -> CI -> release -> PyPI)
  - Artifacts table (artifact, method, target, trigger)

**Section 4: Observability Plan**
- 4.1 What We Measure (mermaid mindmap from real telemetry events)
- 4.2 SLIs / SLOs / Alerts (table: signal, SLI, SLO, alert threshold, action)
- 4.3 Logging and Reporting (table: log type, format, retention, location)
- 4.4 Runbooks (table from real `.ai-engineering/runbooks/` files)

**Section 5: Security**
- 5.1 Authentication and Authorization (mermaid flowchart + provider table)
- 5.2 Exposure Model (table: surface, visibility, data classification, controls)
- 5.3 Compromised Process Recovery (mermaid sequence diagram)
- 5.4 Hardening Checklist (table: check, tool, gate, status)

**Section 6: Quality**
- 6.1 Quality Gates (mermaid sequence diagram + gates table)
- 6.2 Architecture Patterns (table: pattern, where applied, why)
- 6.3 Testing Strategy (table: level, tool, coverage target, current)
- 6.4 Scalability Plan (table: dimension, current, target, strategy)

**Section 7: Next Objectives**
- 7.1 Roadmap (table: phase, description, status)
- 7.2 Active Epics / Features (table: epic, description, priority, status, target)
- 7.3 KPIs (table: metric, target, current)
- 7.4 Active Spec (pointer to `specs/spec.md`)
- 7.5 Blockers and Risks (table: ID, description, severity, owner, expiry)

### 4. Write
Save to `docs/solution-intent.md` with header:
```
> Status: Evolving
> Last Review: YYYY-MM-DD
```

### 5. Report
Show sections populated vs TBD.

## Governance Notes

**Visual priority**: diagrams > tables > text. Every section MUST have at least one Mermaid diagram or table. Text accompanies but does not substitute visual representation.

**TBD policy**: if a section's data is not defined, implemented, or in scope, mark it explicitly as TBD. NEVER invent data.

**Writing patterns**: use `/ai-write` conventions — audience = technical team, concise, no filler.

**Ownership**: `docs/solution-intent.md` is project-managed. The sync mode updates data fields but never removes user-authored content. The framework updater (`ai-eng update`) does not touch this file.
# Handler: sync

## Purpose

Surgical update of specific sections based on project changes. Never rewrites the entire document. Never deletes user-authored content.

## Trigger Table

| Trigger | Sections Affected | Source |
|---------|-------------------|--------|
| Spec closure (done.md created) | 7.2 epic status, 7.4 active spec | spec lifecycle |
| Release completion | 7.1 roadmap, 7.3 KPIs | release skill |
| Stack add/remove | 3.1 stack & architecture | manifest.yml |
| Security scan delta | 5.4 hardening checklist, 7.3 KPIs | verify agent |
| Decision store update | 2.2 if domain-relevant | decision-store.json |
| Skill/agent add/remove | 2.2 AI Ecosystem, 6.4 scalability | manifest.yml |
| Quality gate change | 6.1 quality gates, 2.3 NFRs | manifest.yml |

## Procedure

1. **Read current document** -- load `docs/solution-intent.md`.

2. **Detect changes** -- compare current project state against document content:
   - Parse manifest.yml for stack/skill/agent counts
   - Parse decision-store.json for active decisions
   - Check specs/spec.md for current spec
   - Check recent spec closures (done.md files)
   - Run quality/security tools if available for fresh data

3. **Apply updates** -- for each affected section:
   - Read existing section content
   - Merge new data (update tables, status fields, counts, diagrams)
   - Preserve all user-authored text and custom content
   - Update `Last Review: YYYY-MM-DD` in header

4. **Stage** -- `git add docs/solution-intent.md`.

5. **Report** -- list sections updated with before/after summary.

## Rules

- **Surgical only** -- update specific fields/tables, never rewrite paragraphs
- **Preserve user content** -- if a section has been manually edited, merge carefully
- **Idempotent** -- running sync twice with no changes produces no diff
- **Diagrams** -- update Mermaid diagrams if the underlying data changed (e.g., new module in architecture)
- **TBD sections** -- do NOT fill TBD sections during sync. Only init or user can populate those.
# Handler: validate

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
- decision-store.json active count vs Section 2.2 decisions

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
