---
total: 2
completed: 2
---

# Plan: sub-002 Update Tree UX

## Plan

- [x] T-2.1 Replace the flat `ai-eng update` preview with a branded tree renderer.
  Done when: created, updated, protected, unchanged, skipped, and denied paths render as a nested tree that remains deterministic across platforms and preserves the current command behavior.

- [x] T-2.2 Add regression coverage for the new preview contract.
  Done when: command and renderer tests pin the tree output without changing JSON/update semantics.

## Imports

- final ownership and promoted-context path surface from `sub-003`

## Exports

- `update_tree_preview_contract`
- `cli_tree_renderer`
- `update_preview_regression_net`

## Self-Report
- Replaced the old flat update preview with a grouped tree renderer that mirrors the CLI brand language and keeps per-file reasons visible.
- Preserved stdout/stderr behavior and JSON semantics while moving the human preview into a deterministic tree contract.
- Extended unit and integration coverage so the preview buckets and nested output stay pinned across platforms.
