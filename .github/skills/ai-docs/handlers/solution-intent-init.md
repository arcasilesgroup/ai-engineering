# Handler: solution-intent-init

## Purpose

Scaffold a comprehensive `docs/solution-intent.md` from real project state. This is the Solution Intent -- defines what you are building, how, and why.

## Prerequisites

- Run `/ai-explore` or equivalent deep audit of the repo BEFORE writing. Every data point must come from verified sources (code, config, state files).
- Use `/ai-write` patterns: visual priority (diagrams > tables > text), audience = technical team, no filler.

## Procedure

### 1. Check existence
If `docs/solution-intent.md` exists, warn and ask user to confirm overwrite.

### 2. Deep audit
Gather data from REAL project state -- never from old documentation:

| Source | What to extract |
|--------|----------------|
| `pyproject.toml` | Name, version, description, license, Python version, dependencies |
| `.ai-engineering/manifest.yml` | Skills count, agents, stacks, providers, IDEs, quality gates, tooling, ownership |
| `.ai-engineering/state/decision-store.json` | Active decisions, risk acceptances |
| `.ai-engineering/specs/spec.md` | Current spec, status |
| `.ai-engineering/contexts/` | Available language/framework/team contexts |
| `.ai-engineering/runbooks/` | Available operational runbooks |
| `src/ai_engineering/` | Module structure, CLI commands, services, layers |
| `.github/skills/` | Actual skill count and categories |
| `.github/agents/` | Actual agent count, models, colors |
| `.github/hooks/` | Telemetry hook configuration |
| `scripts/` | Sync, validation, work item scripts |

### 3. Scaffold 7 sections

Each section MUST have at least one Mermaid diagram or table. If data is not available, mark as **TBD -- pending team definition**.

**Section 1: Introduction**
- 1.1 Identity (table: name, org/repo, version, status, model, license)
- 1.2 Objective (1 paragraph from pyproject.toml description + manifest purpose)
- 1.3 Problem Statement (why this framework exists)
- 1.4 Desired Outcomes (bullet list of measurable goals)
- 1.5 Scope (in/out explicit lists)
- 1.6 Stakeholders and Personas (table: persona, journey, primary actions)

**Section 2: Requirements (Solution Intent)**
- 2.1 High-Level Solution Architecture (mermaid flowchart TB -- real component map)
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

**Writing patterns**: use `/ai-write` conventions -- audience = technical team, concise, no filler.

**Ownership**: `docs/solution-intent.md` is project-managed. The sync mode updates data fields but never removes user-authored content. The framework updater (`ai-eng update`) does not touch this file.
