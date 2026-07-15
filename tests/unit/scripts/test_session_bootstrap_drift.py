"""spec-184 D-184-05: /ai-start dashboard framework-drift block."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SB = Path(__file__).resolve().parents[3] / ".ai-engineering" / "scripts" / "session_bootstrap.py"


def _load():
    spec = importlib.util.spec_from_file_location("_sb_drift", _SB)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dashboard_shows_drift_block_when_behind() -> None:
    sb = _load()
    md = sb._render_markdown(
        {
            "project_name": "t",
            "framework_drift": {"applied": "0.5.0", "installed": "0.12.3", "behind": True},
        }
    )
    assert "⟳ Framework drift" in md
    assert "run `ai-eng update`" in md
    assert "0.5.0" in md


def test_dashboard_no_block_when_current() -> None:
    sb = _load()
    md = sb._render_markdown({"project_name": "t", "framework_drift": {"behind": False}})
    assert "⟳ Framework drift" not in md


def test_framework_drift_helper_fail_open(tmp_path: Path) -> None:
    sb = _load()
    # a dir with no manifest → helper returns a dict with behind False (fail-open)
    result = sb._framework_drift(tmp_path)
    assert result is None or result.get("behind") is False
