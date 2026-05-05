# Build HX-01 T-5.1 Strict Workspace Charter Role Contract

## Task ID

HX-01-T-5.1-strict-workspace-charter-role-contract

## Objective

Flip the remaining validator and fixture coverage from implicit charter semantics to an explicit normalized-contract requirement: `.ai-engineering/CONSTITUTION.md` must stay a subordinate workspace charter, not a peer constitution.

## Minimum Change

- enrich the source-repo validator fixture so live and template workspace charters carry normalized subordinate-role language
- add focused `manifest_coherence` tests for the workspace-charter role pass and drift-fail cases
- add a first-class `workspace-charter-role` manifest-coherence check over the live and template charter files

## Verification

- `uv run pytest tests/unit/test_validator.py -k 'control_plane_authority_contract or workspace_charter_role_contract'`
- `uv run ai-eng validate -c manifest-coherence`