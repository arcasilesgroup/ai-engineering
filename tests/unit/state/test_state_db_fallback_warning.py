"""Tests for ``_warn_on_deprecated_fallbacks`` (spec-125 D-125-03).

The state.db ``connect()`` helper detects lingering JSON fallbacks (files
that were migrated to state.db tables but still appear on disk) and emits
a ``framework_error`` event so operators can investigate.

Spec-125 wave 1 extended the watchlist with ``install-state.json`` and
``framework-capabilities.json`` (T-1.1). These tests confirm both new
entries trigger the warning.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.state import state_db


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Tmp project root with state directory but no JSON fallbacks present."""
    state_dir = tmp_path / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return tmp_path


def _create_fallback(project_root: Path, filename: str) -> Path:
    """Create a JSON fallback file with empty content."""
    path = project_root / ".ai-engineering" / "state" / filename
    path.write_text("{}", encoding="utf-8")
    return path


def test_install_state_json_in_deprecated_tuple() -> None:
    """spec-125 T-1.1: install-state.json must be in the deprecated tuple."""
    assert "install-state.json" in state_db._DEPRECATED_JSON_FALLBACKS


def test_framework_capabilities_json_in_deprecated_tuple() -> None:
    """spec-125 T-1.1: framework-capabilities.json must be in the deprecated tuple."""
    assert "framework-capabilities.json" in state_db._DEPRECATED_JSON_FALLBACKS


def test_warn_fires_for_install_state(project_root: Path, caplog) -> None:
    """A lingering install-state.json triggers _warn_on_deprecated_fallbacks."""
    import logging

    state_dir = project_root / ".ai-engineering" / "state"
    _create_fallback(project_root, "install-state.json")
    with caplog.at_level(logging.WARNING):
        state_db._warn_on_deprecated_fallbacks(state_dir)
    assert any("install-state.json" in r.getMessage() for r in caplog.records)


def test_warn_fires_for_framework_capabilities(project_root: Path, caplog) -> None:
    """A lingering framework-capabilities.json triggers _warn_on_deprecated_fallbacks."""
    import logging

    state_dir = project_root / ".ai-engineering" / "state"
    _create_fallback(project_root, "framework-capabilities.json")
    with caplog.at_level(logging.WARNING):
        state_db._warn_on_deprecated_fallbacks(state_dir)
    assert any("framework-capabilities.json" in r.getMessage() for r in caplog.records)


def test_no_warning_when_fallbacks_absent(project_root: Path, caplog) -> None:
    """A clean state directory produces no warnings."""
    import logging

    state_dir = project_root / ".ai-engineering" / "state"
    with caplog.at_level(logging.WARNING):
        state_db._warn_on_deprecated_fallbacks(state_dir)
    for filename in state_db._DEPRECATED_JSON_FALLBACKS:
        assert not any(filename in r.getMessage() for r in caplog.records), (
            f"Unexpected warning about {filename}"
        )
