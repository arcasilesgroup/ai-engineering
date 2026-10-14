# Checkpoint 10 adversarial review

## Goal

The English hub presents all-projects, per-project overview/history, status filters, and persistent root settings with native folder selection, validation, and clear loading, empty, and error states.

## Acceptance

- Only repositories accepted by the shared ai-eng governance gate appear under configured search roots.
- A valid `in_progress` checkpoint remains In progress rather than Unknown.
- Project and worktree navigation matches the approved collapsed disclosure tree, without duplicate Overview/History tabs, and view transitions preserve the toolbar position.
- Repository evidence issues remain visible in a compact disclosure without obscuring project content.
- Folder selection, path validation, persistence, filters, overview/history data, and loading/empty/error/retry states preserve their documented behavior.
- The prototype UI gate covers the listed in-scope regions and states.

## changed_files

- `src/workspace/folder-picker.ts`
- `src/workspace/settings.ts`
- `src/workspace/ui.ts`
- `src/workspace/api.ts`
- `src/workspace/discovery.ts`
- `src/workspace/status.ts`
- `src/workspace/server.ts`
- `templates/workspace.html.tpl`
- `src/assets.ts`
- `skills/ai-review-ui/SKILL.md`
- `skills/ai-review-ui/capture.cjs`
- `tests/workspace-discovery.spec.ts`
- `tests/workspace-settings.spec.ts`
- `tests/workspace-ui.spec.ts`
- `tests/workspace-server.spec.ts`
- `.ai-engineering/workflow/prototypes/001-worktree-overview.html`
- `.ai-engineering/workflow/prototypes/001-worktree-overview.states.json`

## Verify

- `bun test ./tests/embed-canon.spec.ts`
- `bun test ./tests/workspace-discovery.spec.ts`
- `bun test ./tests/workspace-settings.spec.ts`
- `bun test ./tests/workspace-ui.spec.ts`
- `bun test ./tests/workspace-server.spec.ts`
- `bun run typecheck`
- `bun run lint`
- `bun test ./tests/arch.spec.ts`
- `bun run build`
