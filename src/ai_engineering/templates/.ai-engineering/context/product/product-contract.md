# Product Contract — <project-name>

## Update Metadata

- Rationale: living project document. Agents update this when closing specs.
- Expected gain: AI agents can determine project state, objectives, and history from a single document.
- Potential impact: this is the primary document for project-specific decisions.

## 1. Project Identity

- **Name**: <project-name>
- **Repository**: `<org>/<repo>`
- **Owner**: <org>
- **Status**: <Active development | Maintenance | Pre-release>
- **License**: <license>
- **Distribution**: <distribution method>
- **Primary language**: <language>
- **Governance model**: content-first, AI-governed
- **Framework contract**: `context/product/framework-contract.md` — defines eternal framework rules

## 2. Roadmap and Release Plan

### 2.1 Roadmap Phases

#### Phase 1 — <status>

- <milestone 1>
- <milestone 2>

#### Phase 2 — <status>

- <milestone 1>
- <milestone 2>

### 2.2 Rollout Plan

| Phase | Name | Status |
|-------|------|--------|
| 1 | <phase name> | <status> |

### 2.3 Release Status

- **Current version**: <version>
- **Next milestone**: <version>
- **Blockers**: <none or description>
- **Branch**: `main`

## 3. Product Goals (Current Phase)

<Brief project description.>

### 3.1 Active Objectives

1. <objective 1>
2. <objective 2>

### 3.2 Completed Milestones

| Area | Evidence |
|------|----------|
| <area> | <evidence> |

### 3.3 Success Criteria

```bash
# Define project-specific success criteria here:
# Example: uv run pytest tests/ -v --cov --cov-fail-under=90
```

## 4. Active Spec

No active spec — ready for `/create-spec`.

### Read Sequence

When an active spec exists, agents follow this read sequence:

1. `context/specs/_active.md` (pointer to the current spec)
2. The active spec's `spec.md`, `plan.md`, and `tasks.md`

## 5. KPIs

| Metric | Target | Current | Trend |
|--------|--------|---------|-------|
| Quality gate pass rate | 100% | — | — |
| Security scan pass rate | 100% — zero medium+ | — | — |
| Test coverage | 90% | — | — |

## 6. Governance Surface Summary

### 6.1 Skills

Populated automatically by the framework. Run `ai-eng skill status` to see installed skills.

### 6.2 Agents

Populated automatically by the framework. See `.ai-engineering/agents/` for available agents.

### 6.3 Stack Standards

Run `ai-eng stack list` to see detected stacks.

### 6.4 Spec History

| Spec | Title | Status |
|------|-------|--------|
| — | No specs yet | — |

## 7. Architecture Snapshot

<Describe project modules, CI/CD workflows, and test suite here.>

## 8. Stakeholders

- **Maintainers**: <org> — project ownership.
- **Contributors**: governed by standards and skills.
- **Users**: <target users>.

## 9. Decision Log Summary

All decisions persisted in `state/decision-store.json`.
Agents MUST check the decision store before prompting for any previously decided question.
