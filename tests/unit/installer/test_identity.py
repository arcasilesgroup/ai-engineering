"""Tests for installer project identity initialisation."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.installer.identity import (
    initialize_manifest_project_name,
    project_name_from_root,
)


def _write_manifest(root: Path, name: str) -> Path:
    manifest = root / ".ai-engineering" / "manifest.yml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        f'schema_version: "2.0"\nname: {name}\nversion: "1.0.0"\n',
        encoding="utf-8",
    )
    return manifest


def test_project_name_from_root_uses_folder_name(tmp_path: Path) -> None:
    assert project_name_from_root(tmp_path) == tmp_path.name


def test_initialize_manifest_replaces_template_name(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, "ai-engineering")

    assert initialize_manifest_project_name(tmp_path) is True

    text = manifest.read_text(encoding="utf-8")
    assert f"name: {tmp_path.name}" in text
    assert "name: ai-engineering" not in text


def test_initialize_manifest_preserves_custom_name(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, "customer-api")

    assert initialize_manifest_project_name(tmp_path) is False

    assert "name: customer-api" in manifest.read_text(encoding="utf-8")


def test_initialize_manifest_force_overwrites_custom_name(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, "customer-api")

    assert initialize_manifest_project_name(tmp_path, force=True) is True

    text = manifest.read_text(encoding="utf-8")
    assert f"name: {tmp_path.name}" in text
    assert "name: customer-api" not in text
