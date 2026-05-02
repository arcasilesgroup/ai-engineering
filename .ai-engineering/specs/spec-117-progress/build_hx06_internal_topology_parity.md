# Build Handoff: HX-06 Internal Topology Parity

## Scope

- Updated specialist-agent generation so internal reviewers and verifiers are generated with governed provenance metadata.
- Routed specialist-agent mirrors to provider-local `internal/` roots for GitHub Copilot, Gemini, and Codex instead of public agent roots.
- Added internal specialist roots to orphan detection so stale generated specialist files can be found without broadening the public root contract.
- Tightened capability-card topology classification so leaked specialist names become `internal-specialist`, non-public, and unable to accept task packets.

## Implemented Files

- `scripts/sync_command_mirrors.py`
- `src/ai_engineering/state/capabilities.py`
- `tests/unit/test_sync_mirrors.py`
- `tests/unit/test_capabilities.py`

## Boundary

This slice preserves specialist runtime participation while keeping specialist files outside the first-class public agent capability contract. Prompt/tool parity across all public orchestration surfaces remains open for the next HX-06 verification slice.