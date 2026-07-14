"""spec-184 Phase C: framework drift detector."""

from __future__ import annotations

from pathlib import Path

from ai_engineering import __version__
from ai_engineering.version.framework_drift import detect_framework_drift


def _manifest(root: Path, framework_version: str | None) -> None:
    d = root / ".ai-engineering"
    d.mkdir(parents=True, exist_ok=True)
    body = "name: p\n"
    if framework_version is not None:
        body += f'framework_version: "{framework_version}"\n'
    (d / "manifest.yml").write_text(body, encoding="utf-8")


def test_behind_when_applied_older_than_installed(tmp_path: Path) -> None:
    _manifest(tmp_path, "0.0.1")
    drift = detect_framework_drift(tmp_path)
    assert drift.behind is True
    assert drift.applied == "0.0.1"
    assert drift.installed == __version__
    assert drift.recovery == "ai-eng update"


def test_up_to_date_when_equal(tmp_path: Path) -> None:
    _manifest(tmp_path, __version__)
    drift = detect_framework_drift(tmp_path)
    assert drift.behind is False


def test_not_behind_when_applied_newer(tmp_path: Path) -> None:
    _manifest(tmp_path, "999.0.0")
    assert detect_framework_drift(tmp_path).behind is False


def test_missing_framework_version_is_not_drift(tmp_path: Path) -> None:
    _manifest(tmp_path, None)
    drift = detect_framework_drift(tmp_path)
    assert drift.behind is False
    assert drift.applied is None


def test_missing_manifest_fail_open(tmp_path: Path) -> None:
    drift = detect_framework_drift(tmp_path)
    assert drift.behind is False
    assert drift.applied is None
