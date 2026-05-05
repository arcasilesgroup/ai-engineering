# Explore - HX-02 / T-5.1 / pr-description-ledger-aware-active-spec-id

## Slice Goal

Make `vcs.pr_description._read_active_spec()` stop treating placeholder `spec.md` as authoritative `None` when the resolved spec-local work plane still has live ledger tasks, while keeping work-item lookup identity aligned with the existing work-plane contract.

## Local Anchor

- `src/ai_engineering/vcs/pr_description.py::_read_active_spec()`
- `tests/unit/test_pr_description.py::TestReadActiveSpec`
- immediate user-facing consumers: `build_pr_title()` and `build_pr_description()`

## Existing Behavior

- `_read_active_spec()` resolves the active work plane, then returns `None` immediately for placeholder `spec.md`.
- `build_pr_title()` and `build_pr_description()` use that helper for visible title/body text.
- issue lookup still flows through `work_items.service.get_linked_issue_id(project_root, spec)` and therefore depends on the canonical lookup identifier staying stable.

## Falsifiable Hypothesis

If `_read_active_spec()` mirrors the same placeholder-to-ledger rule already landed elsewhere, returns the raw work-plane directory name for lookup identity, and title/body rendering normalize only display text, then PR generation will stay spec-aware for live placeholder-backed work planes without breaking linked-issue lookup.

## Cheapest Discriminating Checks

- add a helper regression where the pointed placeholder-backed work plane has a live ledger and `_read_active_spec()` returns the raw work-plane name
- add one public builder regression proving the title renders `feat(spec-117-hx-02): ...` rather than `feat(spec-spec-117-hx-02): ...`
- add one raw-lookup regression that asserts `build_pr_description()` still passes the raw work-plane name into issue lookup while rendering a normalized display id

## Proposed Write Scope

- `src/ai_engineering/vcs/pr_description.py`
- `tests/unit/test_pr_description.py`

## Notes

- The canonical lookup id should stay aligned with `work_items.service`; normalization belongs only in user-facing rendering.
- The done-ledger idle branch should be locked at both the helper and public-builder levels.