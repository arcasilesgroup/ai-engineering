"""The loop termination criterion, spec 031 / B-031-2.

An autonomous loop is done only after two consecutive identical green runs (a single green
can be luck). A no-op pass still counts as a green, so a converged or stalled loop reaches
the two-identical stop instead of looping forever on invisible progress; a diverging green
restarts the identical-run requirement; a failed pass resets it. This reports when an
orchestrator may stop; it never approves or accepts anything (Loop-Engineering).
"""

from __future__ import annotations

from typing import Any


def record(
    history: list[dict[str, Any]],
    outcome: str,
    digest: str,
    *,
    changed: bool,
) -> None:
    """Append one run to the loop's history.

    `outcome` is PASS or FAIL, `digest` identifies the run's outcome, and `changed` is
    whether the run altered the tree (a no-op pass is still a real green).
    """
    history.append({"outcome": outcome, "digest": digest, "changed": changed})


def done(history: list[dict[str, Any]]) -> bool:
    """True only when the last two consecutive green runs are PASS with identical digests.

    The trailing green run is walked back over any no-op passes — a no-op green counts as a
    green, so a converged loop stops. A FAIL anywhere in the reach breaks the run.
    """
    greens: list[dict[str, Any]] = []
    for entry in reversed(history):
        if entry.get("outcome") != "PASS":
            break
        greens.append(entry)
        if len(greens) >= 2:
            first, second = greens[-1], greens[-2]
            return first.get("digest") == second.get("digest")
    return False
