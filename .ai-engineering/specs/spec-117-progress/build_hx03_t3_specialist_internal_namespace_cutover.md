# Build: HX-03 T-3 Specialist Internal Namespace Cutover

## Scope

- Move provider-mirrored specialist review and verify agents out of public `agents/` roots into provider-local `agents/internal/` namespaces.
- Rewrite provider-local `ai-review` and `ai-verify` references so their preflight and handler paths point at the internal namespace rather than peer public agent paths.
- Add a shared mirror-inventory helper for provider-local specialist targets so the sync generator stops hard-coding one-off internal roots.

## Changes

- Added `get_internal_specialist_agent_targets()` to `src/ai_engineering/config/mirror_inventory.py` so provider-local repo/template roots for internal specialist mirrors come from the shared HX-03 contract.
- Updated `scripts/sync_command_mirrors.py` to:
  - translate `.claude/agents/<specialist>.md` references to `.github/.codex/.gemini/agents/internal/<specialist>.md`
  - write specialist mirrors into provider-local `agents/internal/` directories instead of the public agent roots
  - keep the Claude install-template copy in the canonical `.claude/agents/` location for now
  - track the new internal directories in orphan cleanup so stale top-level specialist mirrors are removed on sync
- Expanded regression coverage in `tests/unit/test_sync_mirrors.py`, `tests/unit/config/test_mirror_inventory.py`, and `tests/unit/test_constitution_skill_paths.py` for the new internal namespace contract.

## Outcome

- Provider-mirrored specialist agents no longer appear as peer public entry points under `.github/agents`, `.codex/agents`, or `.gemini/agents`.
- Review and verify provider-local surfaces now point at resolvable internal specialist paths.
- The shared mirror inventory now models provider-local internal specialist destinations explicitly instead of implying a Copilot-only internal family root.