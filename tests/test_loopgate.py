"""Tests for spec 031 / B-031-2: the loop termination criterion.

An autonomous loop is done only after two consecutive identical green runs (a single green
can be luck); a no-op pass still counts as a green, so a converged or stalled loop reaches
the two-identical stop instead of looping forever on invisible progress; a diverging green
restarts the identical-run requirement; a failed pass resets it (Loop-Engineering).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_engineering import loopgate  # noqa: E402


def _history() -> list[dict]:
    return []


def test_a_single_green_is_not_done():
    h = _history()
    loopgate.record(h, "PASS", "digest-a", changed=True)
    assert loopgate.done(h) is False


def test_two_greens_with_different_digests_are_not_done():
    h = _history()
    loopgate.record(h, "PASS", "digest-a", changed=True)
    loopgate.record(h, "PASS", "digest-b", changed=True)  # diverged
    assert loopgate.done(h) is False


def test_two_identical_greens_are_done():
    h = _history()
    loopgate.record(h, "PASS", "digest-a", changed=True)
    loopgate.record(h, "PASS", "digest-a", changed=True)  # identical
    assert loopgate.done(h) is True


def test_a_noop_pass_counts_as_green_and_converges():
    """The invisible-progress rule: a pass that changed nothing still counts, so a converged
    loop reaches the two-identical stop instead of looping forever."""
    h = _history()
    loopgate.record(h, "PASS", "digest-a", changed=True)
    loopgate.record(h, "PASS", "digest-a", changed=False)  # no-op pass
    assert loopgate.done(h) is True


def test_a_diverging_green_restarts_the_identical_run():
    h = _history()
    loopgate.record(h, "PASS", "digest-a", changed=True)
    loopgate.record(h, "PASS", "digest-b", changed=True)
    loopgate.record(h, "PASS", "digest-b", changed=True)  # now identical pair
    assert loopgate.done(h) is True


def test_a_failed_pass_resets_the_consecutive_run():
    h = _history()
    loopgate.record(h, "PASS", "digest-a", changed=True)
    loopgate.record(h, "FAIL", "digest-x", changed=True)  # reset
    loopgate.record(h, "PASS", "digest-a", changed=True)
    assert loopgate.done(h) is False  # only one green after the fail
