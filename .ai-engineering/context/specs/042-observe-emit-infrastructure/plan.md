---
spec: "042"
phases: 6
estimated_tasks: 18
---

# Execution Plan — Spec 042

## Phase 1: Enrich Session Event (3 tasks)

1. Modify `checkpoint.py:checkpoint_save()` — read checkpoint file data before emitting, pass real values to `emit_session_event()`
2. Read task name, progress, blocked_on from checkpoint JSON
3. Test: verify enriched session_metric events contain real data

## Phase 2: Auto-Remediation Tracking (4 tasks)

4. In `gates.py:_run_pre_commit_checks()` — detect auto-remediation by ruff format/fix
5. Add `auto_remediated_count` field to gate_result detail in `emit_gate_event()`
6. Add `noise_ratio_from()` aggregator to `signals.py`
7. Test: verify gate events include remediation count, aggregator works

## Phase 3: Agent Instruction Updates (3 tasks)

8. Update `.ai-engineering/agents/build.md` — add emission step after build operations
9. Update `.ai-engineering/agents/verify.md` — add emission step after scan operations
10. Sync templates in `src/ai_engineering/templates/.ai-engineering/agents/`

## Phase 4: Dashboard Expansion (4 tasks)

11. Team dashboard — add Token Economy section (from session_metric events)
12. Team dashboard — add Noise Ratio section (from gate_result events)
13. AI dashboard — enrich Context Efficiency with real session data fields
14. Test: verify new dashboard sections render correctly

## Phase 5: Health Score Integration (2 tasks)

15. Add noise ratio as optional health component
16. Test: verify health score includes noise ratio when data exists

## Phase 6: Verification (2 tasks)

17. Full test suite + ruff + ty
18. Manual smoke test of all 5 observe modes
