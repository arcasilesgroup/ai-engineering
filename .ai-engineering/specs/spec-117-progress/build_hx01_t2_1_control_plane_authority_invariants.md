# Build Packet - HX-01 / T-2.1 / control-plane-authority-invariants

## Task ID

HX-01-T-2.1-control-plane-authority-invariants

## Objective

Write failing tests or invariant coverage for the normalized constitutional authority contract and the explicit control-plane authority table, including live/template parity.

## Minimum Change

- require installs to materialize root `CONSTITUTION.md` while retaining `.ai-engineering/CONSTITUTION.md` only as a workspace charter
- add live/template manifest invariants that prefer root `CONSTITUTION.md` in `session.context_files`
- add raw-manifest coverage for one explicit `control_plane` authority table that classifies canonical inputs, generated projections, and descriptive metadata

## Verification

- `uv run pytest tests/e2e/test_install_clean.py -k 'required_dirs or root_constitution or project_templates or governance_content'`
- `uv run pytest tests/unit/config/test_manifest.py -k 'session_context_prefers_root_constitution or control_plane_authority_table_exists or template_control_plane_authority_table_exists'`