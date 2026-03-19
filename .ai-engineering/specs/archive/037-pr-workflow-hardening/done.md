---
spec: "037"
slug: "pr-workflow-hardening"
completed: "2026-03-05"
---

# Done — PR Workflow Hardening

## Summary

Completed end-to-end hardening of governed PR behavior to enforce deterministic create-or-update semantics and improve PR body reliability.

Delivered outcomes:

1. **Deterministic upsert path** in `commands/workflows.py`:
   - Added explicit existing-PR detection (`check-existing-pr`).
   - New PR path remains `create-pr`.
   - Existing PR path now `update-pr` with append-only body extension under `## Additional Changes`.

2. **Provider contract parity** in `vcs/protocol.py`:
   - Added `find_open_pr()` and `update_pr()` to protocol.
   - Extended `VcsContext` with optional `body_file` for file-backed payload support.

3. **Provider implementations updated**:
   - `vcs/github.py`: create/update now use file-backed body handling (`--body-file`), plus open PR lookup.
   - `vcs/azure_devops.py`: open PR lookup and PR update methods added; auto-complete and review now reuse lookup.
   - `vcs/api_fallback.py`: added explicit fallback responses for lookup/update operations.

4. **Prompt/contract consolidation**:
   - Unified `.github/prompts/pr.prompt.md` with `ai-pr` governed description surface.
   - Updated PR command contract in `.ai-engineering/manifest.yml` to include `check_existing_pr` and `create_or_update_pr`.
   - Synced corresponding template mirrors.

5. **Regression coverage**:
   - Added create-vs-update assertions in `tests/integration/test_command_workflows.py`.
   - Added provider-level upsert tests in `tests/unit/test_vcs_providers.py`.
   - Added fallback provider tests in `tests/unit/test_api_fallback.py`.
   - Updated release orchestrator fake provider compatibility in `tests/unit/test_release_orchestrator.py`.

## Verification

- `uv run ruff check src/ai_engineering/commands/workflows.py src/ai_engineering/vcs/protocol.py src/ai_engineering/vcs/github.py src/ai_engineering/vcs/azure_devops.py src/ai_engineering/vcs/api_fallback.py tests/integration/test_command_workflows.py tests/unit/test_vcs_providers.py tests/unit/test_api_fallback.py tests/unit/test_release_orchestrator.py`
- `uv run pytest tests/unit/test_vcs_providers.py tests/unit/test_api_fallback.py tests/unit/test_release_orchestrator.py tests/integration/test_command_workflows.py -q`
- `uv run ai-eng validate`

All commands pass.

## Acceptance Criteria Status

- [x] Existing PR path extends description append-only (never overwrite)
- [x] New PR path creates structured description
- [x] Body handling hardened with file-backed path support
- [x] Prompt and command contract surfaces aligned
- [x] Tests cover create + update deterministic behavior
- [x] Governance validation remains PASS
