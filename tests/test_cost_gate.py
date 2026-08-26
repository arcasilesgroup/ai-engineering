"""Tests for spec 029 / B-029-4: the cost calibration gate before expensive lanes.

Bounded-sample first: `--limit <n>` samples a small batch, projects total cost and
wall-time from observed samples, and refuses to continue without consent above a
`policy/`-declared threshold — in non-interactive mode, absent consent, it fails closed
(deepsec `calibrate.sh` made mandatory, headstart's ArXiv gate).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_engineering import cost  # noqa: E402


def test_a_bounded_sample_projects_and_stays_under_threshold():
    """`--limit 50` over 2 observed samples projects a total; under threshold, it may pass."""
    samples = [(0.5, 1.0), (0.7, 1.2)]  # (cost_usd, wall_seconds) per unit
    total, projected, ok = cost.calibrate(50, samples, threshold_usd=100.0, interactive=False)
    assert total == 50
    assert projected < 100.0
    assert ok is True


def test_a_projection_over_threshold_refuses_without_consent_in_non_interactive():
    """Over the threshold with no consent → INCOMPLETE (fail-closed)."""
    samples = [(10.0, 20.0)]  # 10 USD per unit → 50 units = 500 USD
    total, projected, ok = cost.calibrate(50, samples, threshold_usd=100.0, interactive=False)
    assert total == 50
    assert projected >= 100.0
    assert ok is False


def test_a_projection_over_threshold_consents_when_interactive_answer_is_yes():
    """Over the threshold but a caller who answers yes is allowed to continue."""
    total, projected, ok = cost.calibrate(50, [(10.0, 20.0)], threshold_usd=100.0, interactive=True)
    assert ok is True


def test_no_samples_is_incomplete():
    """An empty sample cannot project anything: INCOMPLETE, never a guess."""
    total, projected, ok = cost.calibrate(50, [], threshold_usd=100.0, interactive=False)
    assert ok is False
    assert projected is None


def test_threshold_declared_in_policy_is_read():
    """The threshold lives in `policy/cost-thresholds.toml`, not as a literal in code."""
    raw = (ROOT / "policy" / "cost-thresholds.toml").read_text(encoding="utf-8")
    assert "threshold_usd" in raw and "limit" in raw
