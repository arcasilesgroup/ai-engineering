"""spec-184 Phase B: ai-eng update advances framework_version, preserving user config."""

from __future__ import annotations

from pathlib import Path

import yaml

from ai_engineering import __version__
from ai_engineering.updater.framework_version_advance import advance_framework_version

_MANIFEST_WITH_USER_KEYS = """\
# ai-engineering manifest (user config)
schema_version: "2.0"
framework_version: "0.10.0"
name: my-project
providers:
  # user's stack choice
  stacks:
    - python
quality:
  coverage: 80  # team threshold
"""


def _write_manifest(root: Path, body: str) -> Path:
    d = root / ".ai-engineering"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "manifest.yml"
    p.write_text(body, encoding="utf-8")
    return p


def test_advance_updates_framework_version(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, _MANIFEST_WITH_USER_KEYS)
    report = advance_framework_version(tmp_path, dry_run=False)
    assert report.applied is True
    assert report.previous == "0.10.0"
    assert report.advanced_to == __version__
    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    assert data["framework_version"] == __version__


def test_user_keys_and_comments_preserved(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, _MANIFEST_WITH_USER_KEYS)
    advance_framework_version(tmp_path, dry_run=False)
    text = manifest.read_text(encoding="utf-8")
    # user keys byte-intact
    assert "name: my-project" in text
    assert "- python" in text
    assert "coverage: 80" in text
    # comments preserved (ruamel round-trip)
    assert "# user's stack choice" in text
    assert "# team threshold" in text
    assert "# ai-engineering manifest (user config)" in text


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, _MANIFEST_WITH_USER_KEYS)
    report = advance_framework_version(tmp_path, dry_run=True)
    assert report.applied is False
    assert report.advanced_to == __version__  # plan reported
    assert 'framework_version: "0.10.0"' in manifest.read_text(encoding="utf-8")  # unchanged


def test_slim_manifest_inserts_missing_key(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, "name: slim\nproviders:\n  stacks: [python]\n")
    report = advance_framework_version(tmp_path, dry_run=False)
    assert report.applied is True
    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    assert data["framework_version"] == __version__
    assert data["name"] == "slim"  # user key intact


def test_already_current_is_noop(tmp_path: Path) -> None:
    _write_manifest(tmp_path, f'framework_version: "{__version__}"\nname: cur\n')
    report = advance_framework_version(tmp_path, dry_run=False)
    assert report.applied is False


def test_missing_manifest_fail_open(tmp_path: Path) -> None:
    report = advance_framework_version(tmp_path, dry_run=False)  # no manifest
    assert report.applied is False  # no raise
