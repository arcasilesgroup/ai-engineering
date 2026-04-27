"""Compatibility shim for the legacy v2 pre-push gates.

The v3 redesign moves Python code under `python/` (uv workspaces).
This package only exists so the legacy `ai-eng gate pre-push` can find
the verification helpers it expects until Phase 4 ships v3-native
gates that read directly from the new layout.

DELETE this shim once the legacy framework is uninstalled or once the
v3 driving adapters (Phase 4) replace `ai-eng gate pre-push`.
"""
