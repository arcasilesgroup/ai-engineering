# Rediseno tree display en ai-eng update

**Discovery Date**: 2026-03-31
**Context**: UX friction with multiple trees in `ai-eng update` output
**Spec**: spec-B

## Problem

`ai-eng update` renders multiple separate trees, making output verbose and hard to scan. Metadata lines (Reason/Next/Why) clutter unchanged files. No color differentiation by file state.

## Findings

Reemplazar multiples trees por bucket con un unico tree unificado con colores por estado de fichero. Ficheros clave: `cli_ui.py:206-233` (`render_update_tree`), `core.py:478-498` (double render en interactive mode). Eliminar metadata verbosa (Reason/Next/Why) para ficheros unchanged.

Colores por estado:
- **success** (green): applied / available
- **warning** (yellow): protected
- **muted** (dim): unchanged
- **error** (red): failed

## Code Examples

Target files:
- `cli_ui.py:206-233` -- `render_update_tree` function, entry point for tree rendering
- `core.py:478-498` -- double render in interactive mode

## Pitfalls

- Do not remove metadata for files that actually changed -- only strip Reason/Next/Why from unchanged files
- Double render in interactive mode (`core.py:478-498`) must be addressed or the unified tree will render twice

## Related

- `ai-eng update` CLI command
- Rich library tree rendering
