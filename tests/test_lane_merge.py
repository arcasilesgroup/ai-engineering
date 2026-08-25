"""Tests for spec 031 / B-031-1: the verification DAG and lane merge.

Distinct from `dag.py` (spec 013), which orders *claims* for the one-writer rule. This is the
*verification* DAG: each node's output is verified before the next node consumes it, and
parallel lanes merge into one verdict with dedupe by (file, line), global re-rank by real
consequence, and lane conflicts surfaced rather than hidden (graph-engineering full-review).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_engineering import lane_merge  # noqa: E402


def _finding(file: str, line: int, consequence: str, lane: str) -> dict:
    return {"file": file, "line": line, "consequence": consequence, "lane": lane}


def test_a_failed_node_verify_leaves_downstream_incomplete():
    """An unverified output must never feed the next node — INCOMPLETE, not a pass."""
    nodes = [
        {"id": "a", "verify": lambda: False, "consumers": ["b"]},
        {"id": "b"},
    ]
    result = lane_merge.gate_nodes(nodes)
    assert result["a"]["status"] == "PASS"  # the node itself ran
    assert result["b"]["status"] == "INCOMPLETE"  # but its consumer is gated


def test_a_passed_node_verify_allows_consumption():
    nodes = [
        {"id": "a", "verify": lambda: True, "consumers": ["b"]},
        {"id": "b"},
    ]
    result = lane_merge.gate_nodes(nodes)
    assert result["a"]["status"] == "PASS"
    assert result["b"]["status"] == "PASS"


def test_merge_dedupes_by_file_line():
    findings = [
        _finding("src/app.py", 5, "high", "security"),
        _finding("src/app.py", 5, "high", "correctness"),  # same file:line, dedupe
        _finding("src/other.py", 2, "medium", "design"),
    ]
    merged = lane_merge.merge(findings)
    assert len(merged["findings"]) == 2  # deduped the duplicate
    assert merged["conflicts"] == []  # same consequence, not a conflict


def test_merge_reranks_globally_and_surfaces_conflicts():
    """Global re-rank by consequence severity, and a lane conflict on the same (file, line)
    is surfaced as a high-signal conflict entry, never hidden by whichever lane won."""
    findings = [
        _finding("src/app.py", 5, "high", "security"),
        _finding("src/app.py", 5, "low", "design"),  # conflict on same spot
        _finding("src/other.py", 2, "critical", "security"),
    ]
    merged = lane_merge.merge(findings)
    # Critical ranks above high: the critical finding is first globally.
    assert merged["findings"][0]["consequence"] == "critical"
    # Dedupe left one entry for src/app.py:5 (the more severe: high).
    assert len(merged["findings"]) == 2
    # The conflict is surfaced, carrying the two lanes and the flag.
    assert merged["conflicts"] == [
        {
            "file": "src/app.py",
            "line": 5,
            "lanes": ["security", "design"],
            "consequences": ["high", "low"],
            "conflict": True,
        }
    ]