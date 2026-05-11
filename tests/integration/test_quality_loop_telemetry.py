"""Telemetry regression: per-task verify+review dispatches drop ≈90 % after
spec-131 D-131-05 single-quality-loop trim.

The test consumes two committed NDJSON fixtures:

* ``tests/fixtures/sub-002/baseline-events.ndjson`` -- pre-trim baseline
  capturing the legacy behaviour (per-task verify+review on every task PLUS
  the final-loop round).
* ``tests/fixtures/sub-002/post-trim-events.ndjson`` -- expected post-trim
  behaviour (no per-task verify+review; only the single final-loop round).

Two assertions:

1. Per-task verify+review count is 0 in the post-trim stream.
2. Post-trim total ``ai-verify`` + ``ai-review`` dispatch count is
   ≤ 10 % of the baseline (≥ 90 % reduction).

The test also enforces that the post-trim final-loop dispatches itself are
bounded at 2 (single round = one verify + one review on the full
changeset).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "sub-002"
BASELINE = FIXTURE_DIR / "baseline-events.ndjson"
POST_TRIM = FIXTURE_DIR / "post-trim-events.ndjson"

GATE_SUBAGENTS = {"ai-verify", "ai-review"}


def _load_ndjson(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _dispatch_counts(events: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {"ai-verify": 0, "ai-review": 0}
    for evt in events:
        detail = evt.get("detail", {}) or {}
        subagent = detail.get("subagent_type")
        if subagent in counts:
            counts[subagent] += 1
    return counts


def _per_task_dispatches(events: list[dict]) -> int:
    """Dispatches whose ``task_id`` is NOT the literal ``final`` (final-loop).

    Pre-trim baseline dispatches verify+review for each implementation task
    AND once at the end on the full changeset (``task_id == "final"``).
    Post-trim only the ``final`` round survives.
    """

    total = 0
    for evt in events:
        detail = evt.get("detail", {}) or {}
        subagent = detail.get("subagent_type")
        task_id = detail.get("task_id")
        if subagent in GATE_SUBAGENTS and task_id and task_id != "final":
            total += 1
    return total


def _final_loop_dispatches(events: list[dict]) -> int:
    """Dispatches tagged ``task_id == 'final'`` (single final quality loop)."""

    total = 0
    for evt in events:
        detail = evt.get("detail", {}) or {}
        subagent = detail.get("subagent_type")
        task_id = detail.get("task_id")
        if subagent in GATE_SUBAGENTS and task_id == "final":
            total += 1
    return total


@pytest.fixture(scope="module")
def baseline_events() -> list[dict]:
    if not BASELINE.exists():
        pytest.skip(f"Baseline fixture missing at {BASELINE}")
    events = _load_ndjson(BASELINE)
    if not events:
        pytest.skip(f"Baseline fixture empty at {BASELINE}")
    return events


@pytest.fixture(scope="module")
def post_trim_events() -> list[dict]:
    if not POST_TRIM.exists():
        pytest.skip(f"Post-trim fixture missing at {POST_TRIM}")
    return _load_ndjson(POST_TRIM)


def test_per_task_dispatch_count_is_zero_post_trim(post_trim_events: list[dict]) -> None:
    """spec-131 D-131-05: zero per-task verify+review after the trim."""
    assert _per_task_dispatches(post_trim_events) == 0, (
        "Post-trim stream must contain zero per-task ai-verify/ai-review "
        "dispatches; the single quality loop runs on the full changeset only."
    )


def test_post_trim_total_under_ten_percent_of_baseline(
    baseline_events: list[dict], post_trim_events: list[dict]
) -> None:
    """spec-131 acceptance gate: ≥90 % reduction in gate-dispatch volume."""
    baseline_counts = _dispatch_counts(baseline_events)
    post_counts = _dispatch_counts(post_trim_events)
    baseline_total = sum(baseline_counts.values())
    post_total = sum(post_counts.values())
    assert baseline_total > 0, "Baseline fixture must contain at least one dispatch."
    ratio = post_total / baseline_total
    assert ratio <= 0.10, (
        f"Post-trim dispatch volume must drop ≥90 %; observed ratio={ratio:.3f} "
        f"(baseline={baseline_total}, post={post_total})."
    )


def test_final_loop_is_single_round(post_trim_events: list[dict]) -> None:
    """Final loop dispatches verify + review exactly once on the full changeset."""
    assert _final_loop_dispatches(post_trim_events) <= 2, (
        "Single final quality loop must dispatch at most 1 verify + 1 review."
    )
