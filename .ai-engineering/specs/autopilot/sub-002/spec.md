---
id: sub-002
parent: spec-084
title: "Update Tree UX"
status: planned
files:
  - src/ai_engineering/cli_commands/core.py
  - src/ai_engineering/cli_ui.py
  - src/ai_engineering/updater/service.py
  - tests/unit/test_cli_ui.py
  - tests/integration/test_cli_command_modules.py
depends_on:
  - sub-003
---

# Sub-Spec 002: Update Tree UX

## Scope
Redesign `ai-eng update` preview output into a nested file tree comparable to modern git apps, but styled with ai-engineering CLI brand conventions rather than a copied palette. Preserve the current ownership guarantees and JSON/update semantics while making created, updated, protected, unchanged, and skipped paths legible at a glance.

## Exploration

### Existing Files

- `src/ai_engineering/cli_commands/core.py` owns `update_cmd()`, `_render_update_result()`, and `_render_update_change()`, so the human-facing preview contract lives there today.
- `src/ai_engineering/cli_ui.py` is the right place for a reusable tree renderer instead of hard-coding rendering logic in the command module.
- `src/ai_engineering/updater/service.py` already emits the structured file-change data the new tree preview needs; the runtime logic does not need a new updater protocol.
- Existing tests already pin stdout/stderr behavior and preview/apply flows, so the new renderer must preserve the command contract while changing only presentation.

### Patterns and Constraints

- Limit this stream to human-facing text rendering; JSON output and updater semantics stay unchanged.
- Prefer deterministic text-tree generation over a Rich-specific layout that is hard to snapshot and maintain.
- Group by file action using existing updater data instead of inventing a second classification layer.
- Style should follow ai-engineering CLI conventions, not mimic a third-party color system.

### Risks

- Stream regressions can break CLI tests if preview text moves between stdout and stderr.
- Path normalization needs to stay deterministic across platforms or tree snapshots will flake.
- Very large unchanged or denied buckets can swamp the preview if the grouping is not tight.
