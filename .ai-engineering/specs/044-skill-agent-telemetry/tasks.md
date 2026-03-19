---
spec: "044"
total: 15
completed: 15
---

# Tasks — Spec 044

## Phase 1: Skill Emit Directives
- [x] T01: Add emit directive to all 35 SKILL.md files
- [x] T02: Verify directive placement consistency (35/35 confirmed via grep)
- [x] T03: Validate no formatting issues

## Phase 2: Agent Emit Directives
- [x] T04: Add emit directive to all 7 agent .md files
- [x] T05: Verify build.md/scan.md have both domain + dispatch emitters

## Phase 3: Template Sync
- [x] T06: Sync SKILL.md templates to src/ai_engineering/templates/
- [x] T07: Sync agent .md templates to src/ai_engineering/templates/

## Phase 4: Aggregators + Dashboard
- [x] T08: Add `skill_usage_from()` to signals.py
- [x] T09: Add `agent_dispatch_from()` to signals.py
- [x] T10: Wire observe team — Skill Usage section
- [x] T11: Wire observe team — Agent Dispatch section
- [x] T12: Wire observe ai — skill/agent efficiency

## Phase 5: Tests + Verification
- [x] T13: Unit tests for aggregators (11 tests)
- [x] T14: Unit tests for dashboard sections (2 tests)
- [x] T15: Full test suite (1799 passed) + ruff + ty clean
