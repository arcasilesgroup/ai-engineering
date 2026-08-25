"""Tests for spec 030 / B-030-2: coverage rules separated from prompts.

What a guard may scan is declared as data — a coverage file naming roots — and read at run
time. Adjusting coverage is a one-file data change; a guard scanning outside its declared
coverage is INCOMPLETE, never silently widened (deepsec's matchers, astryx detector→verdict).
The evals harness reporters become the first consumers.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_engineering import coverage  # noqa: E402


def _coverage_file(tmp_path: Path, roots: list[str]) -> Path:
    p = tmp_path / "policy" / "coverage"
    p.mkdir(parents=True, exist_ok=True)
    toml = p / "demo.toml"
    toml.write_text(
        'schema = "urn:ai-engineering:coverage:1"\nschema_version = "1"\n\n'
        + "".join(f'roots = ["{r}"]\n' for r in roots),
        encoding="utf-8",
    )
    return toml


def test_a_guard_reading_inside_its_coverage_is_allowed(tmp_path):
    _coverage_file(tmp_path, ["src"])
    assert coverage.may_scan("src/app.py", policy_dir=tmp_path / "policy" / "coverage") is True
    assert coverage.may_scan("src", policy_dir=tmp_path / "policy" / "coverage") is True


def test_a_guard_reading_outside_its_coverage_is_refused(tmp_path):
    """A rule that escapes the declared roots is INCOMPLETE, never a pass."""
    _coverage_file(tmp_path, ["src"])
    assert coverage.may_scan("hooks/chain.py", policy_dir=tmp_path / "policy" / "coverage") is False
    assert coverage.may_scan("etc/passwd", policy_dir=tmp_path / "policy" / "coverage") is False


def test_a_missing_coverage_file_is_incomplete_not_a_guess(tmp_path):
    with pytest.raises(ValueError, match="coverage"):
        coverage.may_scan("src/app.py", policy_dir=tmp_path / "policy" / "coverage")


def test_a_coverage_root_escaping_the_repository_is_refused(tmp_path):
    _coverage_file(tmp_path, ["/etc"])
    assert coverage.may_scan("src/app.py", policy_dir=tmp_path / "policy" / "coverage") is False
    # And even the declared root itself is refused when it escapes the repo root.
    assert coverage.may_scan("/etc", policy_dir=tmp_path / "policy" / "coverage") is False
