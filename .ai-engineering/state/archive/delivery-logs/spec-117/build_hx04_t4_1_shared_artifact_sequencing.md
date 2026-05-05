# Build Packet - HX-04 / T-4.1 / shared-artifact-sequencing

## Task ID

HX-04-T-4.1-shared-artifact-sequencing-locks

## Objective

Add explicit adapter-owned sequencing and single-writer enforcement for mirror sync, framework events, and gate findings publication.

## Minimum Change

- add one shared `artifact_lock` helper under `ai_engineering.state`
- run `ai-eng sync` and mirror-reading validation entry points under the same `mirror-sync` lock instead of inventing a new composite command path
- serialize `framework-events.ndjson` appends while `prev_event_hash` is read and the next event is written
- serialize `gate-findings.json` publication so adapter-owned persistence remains explicit and single-writer-safe
- add a focused `HX-04` sequencing test slice that pins these owned seams without widening validator or state-plane ownership

## Verification

- `uv run pytest tests/unit/test_harness_sequencing.py tests/unit/test_cli_sync.py tests/unit/test_framework_observability.py tests/unit/test_gate_adapter_parity.py tests/integration/test_cli_command_modules.py`
- `uv run ai-eng validate -c manifest-coherence`