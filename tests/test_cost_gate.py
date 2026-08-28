"""Tests for spec 029 / B-029-4: the cost calibration gate before expensive lanes.

Bounded-sample first: `--limit <n>` samples a small batch, projects total cost and
wall-time from observed samples, and refuses to continue without consent above a
`policy/`-declared threshold — in non-interactive mode, absent consent, it fails closed
(deepsec `calibrate.sh` made mandatory, headstart's ArXiv gate).
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering import cost

ROOT = Path(__file__).resolve().parents[1]


def test_a_bounded_sample_projects_and_stays_under_threshold(monkeypatch):
    """`--limit 50` over 2 observed samples projects a total; under threshold, it may pass."""
    monkeypatch.setattr(cost, "policy", lambda: {"threshold_usd": 100.0, "limit": 5})
    total, projected, ok = cost.calibrate(50, [0.5, 0.7])
    assert total == 50
    assert projected < 100.0
    assert ok is True


def test_a_projection_over_threshold_refuses_without_consent_in_non_interactive(monkeypatch):
    """Over the threshold with no consent → INCOMPLETE (fail-closed)."""
    monkeypatch.setattr(cost, "policy", lambda: {"threshold_usd": 100.0, "limit": 5})
    total, projected, ok = cost.calibrate(50, [10.0])
    assert total == 50
    assert projected >= 100.0
    assert ok is False


def test_no_samples_is_incomplete(monkeypatch):
    """An empty sample cannot project anything: INCOMPLETE, never a guess."""
    monkeypatch.setattr(cost, "policy", lambda: {"threshold_usd": 100.0, "limit": 5})
    total, projected, ok = cost.calibrate(50, [])
    assert ok is False
    assert projected is None


def test_threshold_declared_in_policy_is_read():
    """The threshold lives in `policy/cost-thresholds.toml`, not as a literal in code."""
    raw = (ROOT / "policy" / "cost-thresholds.toml").read_text(encoding="utf-8")
    assert "threshold_usd" in raw
    assert "limit" in raw
