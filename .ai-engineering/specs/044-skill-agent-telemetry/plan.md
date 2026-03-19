---
spec: "044"
phases: 5
estimated_tasks: 15
---

# Execution Plan — Spec 044

## Phase 1: Skill Emit Directives (3 tasks)
**Agent**: build

1. Add standardized emit directive to all 35 SKILL.md files — insert after `## Procedure` or `## Trigger` section:
   ```
   > **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"<name>"}'` at skill start. Fail-open — skip if ai-eng unavailable.
   ```
2. Verify directive placement is consistent across all skills
3. Run ruff + ty (no Python changes, but verify no markdown issues)

## Phase 2: Agent Emit Directives (2 tasks)
**Agent**: build

4. Add standardized emit directive to all 7 agent .md files — insert at start of `## Behavior`:
   ```
   > **Telemetry** (cross-IDE): run `ai-eng signals emit agent_dispatched --actor=ai --detail='{"agent":"<name>"}'` at agent activation. Fail-open — skip if ai-eng unavailable.
   ```
5. Note: build.md and scan.md already have domain-specific emitters (`build_complete`, `scan_complete`). The new `agent_dispatched` event is **additive** — it tracks activation, not completion.

## Phase 3: Template Sync (2 tasks)
**Agent**: build

6. Sync all modified SKILL.md files to `src/ai_engineering/templates/.ai-engineering/skills/`
7. Sync all modified agent .md files to `src/ai_engineering/templates/.ai-engineering/agents/`

## Phase 4: Aggregators + Dashboard (5 tasks)
**Agent**: build

8. Add `skill_usage_from(events)` to `signals.py` — returns `{skill: count}` dict, sorted by frequency
9. Add `agent_dispatch_from(events)` to `signals.py` — returns `{agent: count}` dict, sorted by frequency
10. Wire observe team mode — add Skill Usage section (top 10 skills, invocation count)
11. Wire observe team mode — add Agent Dispatch section (all agents, dispatch count)
12. Wire observe ai mode — include skill/agent data in efficiency metrics

## Phase 5: Tests + Verification (3 tasks)
**Agent**: build

13. Unit tests for `skill_usage_from()` and `agent_dispatch_from()` aggregators
14. Unit tests for observe team/ai dashboard sections with skill/agent events
15. Full test suite + ruff + ty clean
