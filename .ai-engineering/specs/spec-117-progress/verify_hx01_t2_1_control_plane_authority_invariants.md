# Verify HX-01 T-2.1 Control-Plane Authority Invariants

## Ordered Verification

1. `uv run pytest tests/e2e/test_install_clean.py -k 'required_dirs or root_constitution or project_templates'`
   - `PASS`
2. `uv run pytest tests/unit/config/test_manifest.py -k 'session_context_prefers_root_constitution' tests/e2e/test_install_clean.py -k 'root_constitution or project_templates'`
   - `PASS`
3. `uv run pytest tests/unit/config/test_manifest.py -k 'control_plane_authority_table_exists or template_control_plane_authority_table_exists'`
   - `PASS`

## Key Signals

- The repo now has executable coverage that treats root `CONSTITUTION.md` as the install-time constitutional authority surface.
- Template manifest parity is checked directly instead of assuming the bundled workspace matches the live repo.
- The explicit `control_plane` authority table is now covered as a first-class control-plane invariant.