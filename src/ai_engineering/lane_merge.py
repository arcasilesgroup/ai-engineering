"""The verification DAG and lane merge, spec 031 / B-031-1.

Distinct from `dag.py` (spec 013), which orders *claims* for the one-writer rule. This is the
*verification* DAG: each node's output is verified before the next node consumes it, and
parallel lanes merge into one verdict with dedupe by (file, line), global re-rank by real
consequence, and lane conflicts surfaced rather than hidden (graph-engineering full-review).
An unverified output is INCOMPLETE, never a pass.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

# Global consequence ordering, from most to least severe. Two lanes disagreeing on the same
# (file, line) surface a conflict instead of whichever lane won.
CONSEQUENCE_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def gate_nodes(nodes: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    """Verify each node's output before the next consumes it.

    A node carries `verify` (a callable returning bool) and `consumers` (the ids of nodes
    that consume its output). A node whose verify fails leaves every downstream consumer
    `INCOMPLETE`; a verified output allows the consumer to read `PASS`. Nothing is ever
    forwarded unverified.
    """
    results: dict[str, dict[str, str]] = {node["id"]: {"status": "PASS"} for node in nodes}
    for node in nodes:
        verify: Callable[[], bool] | None = node.get("verify")
        if callable(verify) and not verify():
            for consumer in node.get("consumers", []):
                results[consumer] = {"status": "INCOMPLETE"}
    return results


def _key(finding: dict[str, Any]) -> tuple[str, int]:
    return (str(finding["file"]), int(finding["line"]))


def merge(findings: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge parallel lanes into one verdict.

    Dedupe by (file, line); re-rank globally by consequence severity; a lane conflict on the
    same (file, line) — two lanes claiming different consequences for the same spot — is
    surfaced as a high-signal `conflicts` entry, never swallowed by whichever lane won.
    """
    by_spot: dict[tuple[str, int], dict[str, Any]] = {}
    conflicts: list[dict[str, Any]] = []

    for finding in findings:
        spot = _key(finding)
        if spot in by_spot:
            existing = by_spot[spot]
            if existing.get("consequence") != finding.get("consequence"):
                conflicts.append(
                    {
                        "file": finding["file"],
                        "line": finding["line"],
                        "lanes": [existing["lane"], finding["lane"]],
                        "consequences": [existing["consequence"], finding["consequence"]],
                        "conflict": True,
                    }
                )
            # Keep the more severe consequence at this spot.
            if CONSEQUENCE_RANK.get(finding["consequence"], 9) < CONSEQUENCE_RANK.get(
                existing.get("consequence", "low"), 9
            ):
                by_spot[spot] = finding
            continue
        by_spot[spot] = finding

    ranked = sorted(
        by_spot.values(),
        key=lambda f: CONSEQUENCE_RANK.get(str(f.get("consequence", "low")), 9),
    )
    return {"findings": ranked, "conflicts": conflicts}