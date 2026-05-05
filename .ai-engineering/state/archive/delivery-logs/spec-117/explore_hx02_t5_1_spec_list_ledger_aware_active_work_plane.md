# Explore - HX-02 / T-5.1 / spec-list-ledger-aware-active-work-plane

## Slice Goal

Make `ai-eng spec list` treat a placeholder `spec.md` as active when the resolved spec-local work plane still has live tasks in its readable `task-ledger.json`, instead of reporting `No active spec.` from placeholder prose alone.

## Local Anchor

- `src/ai_engineering/cli_commands/spec_cmd.py::spec_list()`
- `tests/unit/test_spec_cmd.py::TestSpecListCli`

## Existing Behavior

- `spec_list()` already resolves the active work plane through `_specs_dir(root)`.
- It still exits early on `# No active spec` before consulting the resolved ledger.
- That makes spec-local work planes look idle in the CLI even when the active ledger still has live tasks.

## Falsifiable Hypothesis

If `spec_list()` mirrors the same placeholder-to-ledger rule already used in Wave 1 and the work-items service, then a placeholder-backed resolved work plane with at least one non-done task will stop printing `No active spec.` and can fall back to the work-plane directory name when no real spec title exists.

## Cheapest Discriminating Check

Add a focused unit test that points the active work plane at a spec-local directory with placeholder `spec.md`, writes a readable ledger containing one live task, runs `spec_list()`, and asserts that stderr no longer contains `No active spec` and instead contains the active work-plane directory name.

## Proposed Write Scope

- `src/ai_engineering/cli_commands/spec_cmd.py`
- `tests/unit/test_spec_cmd.py`

## Notes

- This slice only needs an activity predicate and a display fallback title; it does not need to invent or synthesize a frontmatter spec ID.
- Remaining `T-5.1` readers after this slice likely include identifier-driven consumers such as PR description and state audit.
