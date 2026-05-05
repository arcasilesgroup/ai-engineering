# HX-02 T-4.2 Task Artifact Reference Validation - Guard Review

## Slice Verdict

- `PASS with concerns`.
- This is the right next minimal `HX-02 / T-4.2` sub-slice under the existing plan.
- The rule must validate declared ref paths against the active work-plane root, not a hard-coded legacy path and not only `handoffs/` or `evidence/` directories.

## Allowed Write Scope

- `src/ai_engineering/validator/categories/manifest_coherence.py`
- `tests/unit/test_validator.py`

Out of scope:

- `src/ai_engineering/state/models.py`
- `src/ai_engineering/state/work_plane.py`
- `src/ai_engineering/validator/categories/file_existence.py`
- schema changes
- resolver changes
- CLI changes
- new validator categories

## Required Tests And Evidence

- one failing readable-ledger test for a missing handoff ref
- one failing readable-ledger test for a missing evidence ref
- one passing test where all declared refs resolve inside the active work plane
- one passing test where `handoffs` and `evidence` are empty
- preserve idle-spec placeholder behavior
- preserve unreadable-ledger short-circuit behavior
- add one resolver-scoped test proving ref resolution uses the active work plane rather than a hard-coded legacy path
- evidence bar:
  - `uv run pytest tests/unit/test_validator.py::TestManifestCoherence -q`
  - `uv run ai-eng validate -c manifest-coherence`

## Residual Risks

- live ledger refs already use project-relative progress-doc paths; this slice must not invent a stricter path format than the current contract
- reject absolute escapes or out-of-plane traversal, but do not require refs to live only under `handoffs/` or `evidence/`
- keep the new failure mode visible as its own manifest-coherence check instead of hiding it inside `active-task-ledger`

## Go / No-Go

- `GO` if the change stays local to `manifest_coherence`, runs only on the readable-ledger path, resolves refs against the active work plane, and preserves idle/unreadable behavior
- `NO-GO` if it hard-codes legacy specs paths, tightens schema/path syntax, requires non-empty ref lists, moves logic into `file_existence`, or constrains refs to `handoffs/` and `evidence/` only