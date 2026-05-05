# Build Packet - HX-01 / T-4.1 / control-plane-validator-hardening

## Task ID

HX-01-T-4.1-control-plane-validator-hardening

## Objective

Make the normalized control-plane contract explicit in validator coverage instead of relying on indirect drift signals.

## Minimum Change

- add a `manifest_coherence` check for the normalized `session.context_files` and `control_plane` authority table in both live and template manifests
- add a `file_existence` check for the canonical constitutional/control-plane files that must exist in the source repo and bundled templates
- verify the plan-named validator categories stay green together after the new checks land

## Verification

- `uv run pytest tests/unit/test_validator.py -k 'control_plane_paths_present_pass or missing_project_constitution_template_fails or control_plane_authority_contract_passes or control_plane_authority_contract_drift_fails'`
- `uv run ai-eng validate -c manifest-coherence`
- `uv run ai-eng validate -c file-existence`
- `uv run ai-eng validate -c mirror-sync`
- `uv run ai-eng validate -c cross-reference`