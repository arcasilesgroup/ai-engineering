---
spec: "026"
approach: "serial-phases"
---

# Plan — Gemini Support

## Architecture
### New Files
| File | Purpose |
|---|---|
| `GEMINI.md` | Context and instructions for Gemini CLI. |
| `.ai-engineering/context/specs/026-gemini-support/spec.md` | Spec definition. |
| `.ai-engineering/context/specs/026-gemini-support/plan.md` | Execution plan. |
| `.ai-engineering/context/specs/026-gemini-support/tasks.md` | Task tracking. |

### Modified Files
| File | Purpose |
|---|---|
| `.ai-engineering/context/specs/_active.md` | Update active spec. |
| `.ai-engineering/context/product/product-contract.md` | Cross-reference new spec. |

## Session Map
- **Phase 0: Scaffold** (S) - Create spec files and activate.
- **Phase 1: Implementation** (M) - Create `GEMINI.md` and verify.
- **Phase 2: Documentation** (S) - Update docs to reflect support.
- **Phase 3: Close** (S) - Verify and merge.

## Patterns
- Follow `CLAUDE.md` structure for `GEMINI.md`.
- Ensure commands are compatible with Gemini CLI's capabilities.
