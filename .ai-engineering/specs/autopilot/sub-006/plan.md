---
total: 4
completed: 4
---

# Plan: sub-006 Review Architecture Refresh and Adversarial Validation

## Plan

- [x] T-6.1 Refactor the canonical review contract to review-only and thin the agent wrapper.
  Done when: the skill is the procedural source of truth, the agent stops introducing divergent behavior, and `find` / `learn` are removed from live and mirrored review surfaces.

- [x] T-6.2 Introduce the specialist-prompt architecture and single-handler orchestration.
  Done when: review uses one primary handler, explicit specialist Markdown assets inspired by `review-code`, backend joins frontend in the roster, and both `normal` and `--full` profiles are represented clearly.

- [x] T-6.3 Add adversarial finding validation across both profiles.
  Done when: `finding-validator` is part of `review normal` and `review --full`, evaluates all findings, and preserves specialist-level attribution in the final output.

- [x] T-6.4 Extend mirror, template, and regression coverage for the new review architecture.
  Done when: sync/parity tests catch stale review artifacts across `.agents`, `.claude`, `.github`, and templates, and the new review contract is fully propagated.

## Exports

- `review_skill_contract`
- `review_specialist_prompt_architecture`
- `review_output_contract`
- `review_mirror_propagation_requirements`

## Self-Report
- Narrowed `review` to review-only and removed canonical `find` / `learn` handlers so sync can purge the old surface later.
- Added explicit specialist review resources, including `backend`, plus shared `context-explorer` and `finding-validator` assets.
- Reworked the canonical handler and agent so `normal` and `--full` differ only in decomposition, not in specialist coverage.
- Closed the mirror/template follow-up by running `python scripts/sync_command_mirrors.py` and keeping `test_sync_mirrors.py` green against the propagated review surface.
