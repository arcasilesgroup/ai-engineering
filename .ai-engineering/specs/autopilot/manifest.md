# Autopilot Manifest: spec-080

## Split Strategy
By-concern sequential: each sub-spec maps to one of the 8 thematic areas from the parent spec, ordered by criticality with dependency chains (governance → stack → context → code → validation → generation → docs → work items).

## Sub-Specs

| # | Title | Status | Depends On | Tasks | Confidence |
|---|-------|--------|------------|-------|------------|
| sub-001 | Governance Values Migration | planned | None | 5 | HIGH |
| sub-002 | Unified Stack Detection | planned | None | 5 | 90% |
| sub-003 | Context Loading Enforcement | planned | sub-002 | 5 | HIGH |
| sub-004 | /ai-code Skill Creation | planned | sub-003 | 4 | 93% |
| sub-005 | Build Standards Validation | planned | sub-004 | 3 | 89% |
| sub-006 | AGENTS.md Single-Source Generation | planned | sub-001 | 5 | HIGH |
| sub-007 | Deep Documentation /ai-docs | planned | None | 7 | HIGH |
| sub-008 | Work Item Lifecycle | planned | None | 7 | 90% |

## Deep Plan Summary
- Planned: 8 of 8 sub-specs
- Failed: 0 sub-specs
- Confidence distribution: 6 high, 2 medium-high (89-93%)
- Total tasks: 41

## Coverage Validation

| Parent Spec Section | Sub-Spec(s) |
|---------------------|-------------|
| Sub-spec 1: /ai-code Skill | sub-004 |
| Sub-spec 2: Unified Stack Detection | sub-002 |
| Sub-spec 3: Context Loading Enforcement | sub-003 |
| Sub-spec 4: Build Standards Validation | sub-005 |
| Sub-spec 5: Governance Values Migration | sub-001 |
| Sub-spec 6: AGENTS.md Single-Source Generation | sub-006 |
| Sub-spec 7: Deep Documentation /ai-docs | sub-007 |
| Sub-spec 8: Work Item Lifecycle | sub-008 |
| Scope: CLAUDE.md Effort Levels + skill groups | sub-006 (T-6.4) |
| Scope: manifest.yml skill registry update | sub-007 (T-7.6), sub-008 (T-8.1), sub-004 (T-4.3) |
| Scope: ai-onboard board config | sub-008 (T-8.7) |
| Scope: Mirror changes to templates/IDE surfaces | sub-006 (T-6.1, T-6.2), each sub-spec mirrors own changes |

Coverage: PASSED (all spec sections mapped)

## Execution DAG

### Wave 1 (independent, parallel)
- sub-001: Governance Values Migration
- sub-002: Unified Stack Detection
- sub-007: Deep Documentation /ai-docs
- sub-008: Work Item Lifecycle

### Wave 2 (depends on wave 1)
- sub-003: Context Loading Enforcement (← sub-002)
- sub-006: AGENTS.md Single-Source Generation (← sub-001)

### Wave 3 (depends on wave 2)
- sub-004: /ai-code Skill Creation (← sub-003)

### Wave 4 (depends on wave 3)
- sub-005: Build Standards Validation (← sub-004)

## File Overlap Matrix

| File | Sub-specs that touch it |
|------|------------------------|
| CLAUDE.md | sub-001, sub-006, sub-007 |
| AGENTS.md | sub-001, sub-006 |
| manifest.yml | sub-002, sub-004, sub-007, sub-008 |
| manifest.schema.json | sub-002, sub-004, sub-008 |
| ai-dispatch/SKILL.md | sub-001, sub-003, sub-008 |
| ai-pr/SKILL.md | sub-007, sub-008 |
| ai-commit/SKILL.md | sub-001 |
| ai-build.md | sub-002, sub-004 |
| ai-brainstorm/SKILL.md | sub-008 |
| ai-onboard/SKILL.md | sub-008 |

### Conflict Resolution
- **CLAUDE.md**: sub-001 adds governance values → sub-006 reads and generates AGENTS.md from it → sub-007 updates skill listings. Execution order: sub-001 → sub-006 → sub-007.
- **manifest.yml**: sub-002 updates schema → sub-004 adds contexts.precedence + ai-code → sub-007 updates registry (solution-intent→docs) → sub-008 adds board config. All are additive to different sections.
- **ai-dispatch/SKILL.md**: sub-001 adds guard gate → sub-003 adds context injection → sub-008 adds board-sync call. Sequential order resolves.
- **ai-pr/SKILL.md**: sub-007 replaces doc dispatch → sub-008 adds board-sync. Sequential order resolves.

## Totals
- Sub-specs: 8
- Total tasks: 41
- Waves: 4
- Dependency chain depth: 4 (sub-002 → sub-003 → sub-004 → sub-005)
- Max parallel within wave: 4 (wave 1)
