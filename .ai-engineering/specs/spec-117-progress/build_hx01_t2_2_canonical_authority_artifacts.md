# Build Packet - HX-01 / T-2.2 / canonical-authority-artifacts

## Task ID

HX-01-T-2.2-canonical-authority-artifacts

## Objective

Implement the constitutional demotion and explicit authority-model artifacts in both the live repo and the installed workspace template.

## Minimum Change

- ship `CONSTITUTION.md` as a common project template so installs materialize the canonical constitutional surface at repo root
- keep `.ai-engineering/CONSTITUTION.md` as the subordinate workspace charter compatibility alias
- align live and template manifests with the same `session.context_files` seed and `control_plane` authority table

## Verification

- `uv run pytest tests/e2e/test_install_clean.py -k 'required_dirs or root_constitution or project_templates or governance_content'`
- `uv run pytest tests/unit/config/test_manifest.py -k 'session_context_prefers_root_constitution or control_plane_authority_table_exists or template_control_plane_authority_table_exists'`