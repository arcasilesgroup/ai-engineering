# HX-02 T-5.1 Work Items Ledger-Aware Active Spec Dir - Exploration Handoff

## Current Anchor

- Owning seam: src/ai_engineering/work_items/service.py
- Nearest decision point: _is_active_spec_dir(specs_dir)
- Immediate behavior impact: work-item sync target selection for spec-local work planes

## Local Hypothesis

The work-items sync path still treats placeholder spec.md as authoritative idle state.
A resolved work plane whose spec.md is placeholder-backed but whose readable task-ledger.json
still contains non-done tasks should remain active for sync targeting instead of being
filtered out as idle.

## Recommended Next Slice

- Name the slice work-items-ledger-aware-active-spec-dir.
- Keep ownership inside src/ai_engineering/work_items/service.py.
- Reuse read_task_ledger(...) and resolve_active_work_plane(project_root) semantics.
- Preserve true idle behavior for placeholder plus fully-done or unreadable ledger.
- Add pointer-aware coverage in tests/unit/test_work_items_service.py.

## Allowed Write Scope

- src/ai_engineering/work_items/service.py
- tests/unit/test_work_items_service.py

## Failing-Test-First Candidate

- Add one pointer-aware regression where the active work plane is spec-local,
  spec.md is placeholder-backed, task-ledger.json has one non-done task, and the
  sync target selection must still treat that directory as active.
- Keep the true-idle placeholder case green when the ledger is fully done.

## Cheapest Validation

- uv run pytest tests/unit/test_work_items_service.py -k active_spec_dir -q
- uv run pytest tests/unit/test_work_items_service.py -q

## Boundaries

- Do not widen into validator, CLI list, PR description, or reset flows in this slice.
- Do not change ledger schema or resolver behavior.