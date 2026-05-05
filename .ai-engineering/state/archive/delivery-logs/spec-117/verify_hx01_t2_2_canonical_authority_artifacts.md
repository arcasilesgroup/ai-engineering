# Verify HX-01 T-2.2 Canonical Authority Artifacts

## Ordered Verification

1. `uv run pytest tests/e2e/test_install_clean.py -k 'required_dirs or root_constitution or project_templates'`
   - `PASS`
2. `uv run pytest tests/unit/config/test_manifest.py -k 'session_context_prefers_root_constitution' tests/e2e/test_install_clean.py -k 'root_constitution or project_templates'`
   - `PASS`
3. `uv run pytest tests/unit/config/test_manifest.py -k 'control_plane_authority_table_exists or template_control_plane_authority_table_exists'`
   - `PASS`

## Key Signals

- Installed workspaces now receive the canonical root constitution instead of relying only on the workspace charter alias.
- Live and template manifests carry the same authority-model contract for constitutional winner, canonical inputs, generated projections, and descriptive metadata.
- The Phase 2 artifact cutover landed without breaking the focused install or manifest validation slices.