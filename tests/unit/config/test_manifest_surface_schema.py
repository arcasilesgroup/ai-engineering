"""Tests for SurfacesConfig + surfaces field (spec-133 D-133-16).

The migration is in-flight: ``surfaces.enabled`` is the canonical
key going forward; ``ai_providers.enabled`` + ``providers.ides``
are legacy mirrors retained for in-flight compat on PR #509.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.config.loader import load_manifest_config
from ai_engineering.config.manifest import ManifestConfig, SurfacesConfig


def test_surfaces_config_defaults() -> None:
    s = SurfacesConfig()
    assert s.enabled == ["claude-code"]


def test_manifest_config_has_surfaces_field() -> None:
    cfg = ManifestConfig()
    assert isinstance(cfg.surfaces, SurfacesConfig)
    assert cfg.surfaces.enabled == ["claude-code"]


def test_load_manifest_reads_surfaces_key(tmp_path: Path) -> None:
    yml = tmp_path / ".ai-engineering" / "manifest.yml"
    yml.parent.mkdir(parents=True)
    yml.write_text(
        "surfaces:\n  enabled: [claude-code, opencode, cursor]\n",
        encoding="utf-8",
    )
    cfg = load_manifest_config(tmp_path)
    assert cfg.surfaces.enabled == ["claude-code", "opencode", "cursor"]


def test_load_manifest_mirrors_surfaces_to_ai_providers(tmp_path: Path) -> None:
    """In-flight compat: setting surfaces.enabled mirrors to ai_providers.enabled."""
    yml = tmp_path / ".ai-engineering" / "manifest.yml"
    yml.parent.mkdir(parents=True)
    yml.write_text(
        "surfaces:\n  enabled: [claude-code, gemini-cli]\n",
        encoding="utf-8",
    )
    cfg = load_manifest_config(tmp_path)
    assert cfg.ai_providers.enabled == ["claude-code", "gemini-cli"]


def test_load_manifest_populates_surfaces_from_legacy_ai_providers(tmp_path: Path) -> None:
    """Reverse: legacy-only manifest still populates surfaces.enabled."""
    yml = tmp_path / ".ai-engineering" / "manifest.yml"
    yml.parent.mkdir(parents=True)
    yml.write_text(
        "ai_providers:\n  enabled: [codex]\n  primary: codex\n",
        encoding="utf-8",
    )
    cfg = load_manifest_config(tmp_path)
    assert cfg.surfaces.enabled == ["codex"]


def test_surfaces_enabled_accepts_new_surface_ids(tmp_path: Path) -> None:
    """opencode + cursor + antigravity are valid in surfaces.enabled."""
    yml = tmp_path / ".ai-engineering" / "manifest.yml"
    yml.parent.mkdir(parents=True)
    yml.write_text(
        "surfaces:\n  enabled: [opencode, cursor, antigravity]\n",
        encoding="utf-8",
    )
    cfg = load_manifest_config(tmp_path)
    assert set(cfg.surfaces.enabled) == {"opencode", "cursor", "antigravity"}
