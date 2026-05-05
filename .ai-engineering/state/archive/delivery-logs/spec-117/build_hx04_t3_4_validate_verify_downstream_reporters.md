# Build Packet - HX-04 / T-3.4 / validate-verify-downstream-reporters

## Task ID

HX-04-T-3.4-validate-verify-downstream-reporters

## Objective

Keep `validate` and `verify` downstream of kernel or repo data rather than letting them behave like alternate local gate authorities.

## Minimum Change

- leave `validate` untouched as a strict reporter over repository integrity state
- make `verify` quality/security consume `.ai-engineering/state/gate-findings.json` when present instead of re-running tool subprocesses on that path
- keep architecture, feature, and governance verification on their existing repo-data/reporting roles
- add focused verify-service coverage that fails if quality/security touch subprocess execution while the canonical kernel artifact exists

## Verification

- `uv run pytest tests/unit/test_verify_service.py -q`
- `uv run ai-eng validate -c manifest-coherence`