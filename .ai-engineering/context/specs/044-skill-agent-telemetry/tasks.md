---
spec: "044"
total: 15
completed: 0
---

# Tasks — Spec 044

## Phase 1: Skill Emit Directives
- [ ] T01: Add emit directive to all 35 SKILL.md files
- [ ] T02: Verify directive placement consistency
- [ ] T03: Validate no formatting issues

## Phase 2: Agent Emit Directives
- [ ] T04: Add emit directive to all 7 agent .md files
- [ ] T05: Verify build.md/scan.md have both domain + dispatch emitters

## Phase 3: Template Sync
- [ ] T06: Sync SKILL.md templates to src/ai_engineering/templates/
- [ ] T07: Sync agent .md templates to src/ai_engineering/templates/

## Phase 4: Aggregators + Dashboard
- [ ] T08: Add `skill_usage_from()` to signals.py
- [ ] T09: Add `agent_dispatch_from()` to signals.py
- [ ] T10: Wire observe team — Skill Usage section
- [ ] T11: Wire observe team — Agent Dispatch section
- [ ] T12: Wire observe ai — skill/agent efficiency

## Phase 5: Tests + Verification
- [ ] T13: Unit tests for aggregators
- [ ] T14: Unit tests for dashboard sections
- [ ] T15: Full test suite + ruff + ty clean
