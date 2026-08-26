"""Tests for spec 034 / B-034-3: the constellation rule over verdicts.

A cluster of same-class signals in one context reads as systemic failure; a single isolated
signal in a clean context reads as noise. The module classifies a cluster — it never erases
or downgrades an individual guard's fail (astryx).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_engineering import constellation  # noqa: E402


def test_a_cluster_of_same_class_reads_systemic():
    signals = [
        {"class": "policy", "context": "check", "fail": True},
        {"class": "policy", "context": "check", "fail": True},
        {"class": "policy", "context": "check", "fail": True},
    ]
    assert constellation.classify(signals) == "systemic"


def test_a_single_signal_in_a_clean_context_reads_isolated():
    signals = [{"class": "policy", "context": "check", "fail": True}]
    assert constellation.classify(signals) == "isolated"


def test_a_fail_is_never_erased():
    """Two different-class signals is not a constellation, but each fail remains a fail."""
    signals = [
        {"class": "policy", "context": "check", "fail": True},
        {"class": "secret", "context": "check", "fail": True},
    ]
    assert constellation.classify(signals) == "isolated"
    assert all(s["fail"] for s in signals)  # no fail was downgraded
