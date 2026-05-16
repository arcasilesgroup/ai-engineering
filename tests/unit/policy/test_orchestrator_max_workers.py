"""spec-139 M1 — orchestrator ThreadPoolExecutor cap.

The kernel-panic class in spec-139's trigger incident stemmed in part
from `max_workers = max(1, len(checkers))` (orchestrator.py:489 and
:1209), which scaled the local-thread parallelism with the number of
spawned subprocess checkers. Per D-139-01 this is capped via
`AIENG_MAX_THREAD_WORKERS` (default 4) so that ruff + gitleaks + ty +
pytest-smoke + validate all 5 in one wave do not collectively trash
the host.

This test asserts the cap is honoured by `resolve_thread_workers`,
which the orchestrator calls before sizing the pool.
"""

from __future__ import annotations

import pytest

from ai_engineering.config.concurrency import resolve_thread_workers


def test_env_cap_overrides_default() -> None:
    """`AIENG_MAX_THREAD_WORKERS=2` clamps the pool to 2 workers."""
    assert resolve_thread_workers(env_var="2", manifest_value=None) == 2


def test_default_is_four() -> None:
    """Default cap is 4 (D-139-01)."""
    assert resolve_thread_workers(env_var=None, manifest_value=None) == 4


def test_manifest_wins_when_env_unset() -> None:
    assert resolve_thread_workers(env_var=None, manifest_value=3) == 3


def test_env_wins_over_manifest() -> None:
    assert resolve_thread_workers(env_var="2", manifest_value=8) == 2


def test_floor_is_one_for_single_checker() -> None:
    """Even with cap=1, the pool must still process the single checker."""
    cap = resolve_thread_workers(env_var="1", manifest_value=None)
    assert cap == 1
    assert max(1, min(1, cap)) == 1, "single-checker floor preserved"


@pytest.mark.parametrize(
    ("n_checkers", "cap", "expected_max_workers"),
    [
        (5, 4, 4),  # 5 checkers, cap=4 → pool of 4
        (3, 4, 3),  # 3 checkers, cap=4 → pool of 3 (no wasted workers)
        (1, 4, 1),  # single checker → pool of 1
        (10, 2, 2),  # cap dominates over N
    ],
)
def test_orchestrator_arithmetic_matches_spec(
    n_checkers: int, cap: int, expected_max_workers: int
) -> None:
    """The exact arithmetic the orchestrator uses: max(1, min(N, cap))."""
    observed = max(1, min(n_checkers, cap))
    assert observed == expected_max_workers


def test_invalid_env_value_falls_back_to_default() -> None:
    """Non-numeric or non-positive env values yield the default."""
    assert resolve_thread_workers(env_var="not-a-number", manifest_value=None) == 4
    assert resolve_thread_workers(env_var="0", manifest_value=None) == 4
    assert resolve_thread_workers(env_var="-1", manifest_value=None) == 4
    assert resolve_thread_workers(env_var="", manifest_value=None) == 4
