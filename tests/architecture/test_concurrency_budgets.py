"""spec-139 M1 — concurrency budget primitive contract.

Asserts that ``resolve_wave_cap`` honours env > manifest > auto-tune
precedence and the D-139-01 floor=2 / ceiling=6 invariant. Six scenarios
cover the full decision matrix.

Anchored at spec-139 brief D-139-01 and the kernel-panic trigger
incident in `.ai-engineering/specs/drafts/framework-performance-hardening-brief.md`.
"""

from __future__ import annotations

import os
from unittest import mock

import pytest

from ai_engineering.config.concurrency import (
    HostProbe,
    resolve_quality_cap,
    resolve_thread_workers,
    resolve_wave_cap,
)


def test_env_var_wins_over_manifest_and_auto() -> None:
    """Scenario 1: env var set explicitly → env wins regardless of host."""
    cap = resolve_wave_cap(env_var="5", manifest_value=2, host_probe=None)
    assert cap == 5


def test_manifest_wins_when_env_unset() -> None:
    """Scenario 2: manifest value set, env unset → manifest wins."""
    cap = resolve_wave_cap(env_var=None, manifest_value=4, host_probe=None)
    assert cap == 4


def test_auto_tune_within_bounds_when_both_unset() -> None:
    """Scenario 3: both unset → auto-tune resolves within [2, 6]."""
    with mock.patch.object(os, "cpu_count", return_value=8):
        cap = resolve_wave_cap(env_var=None, manifest_value=None, host_probe=None)
    assert 2 <= cap <= 6


def test_auto_tune_with_stressed_host_returns_serial() -> None:
    """Scenario 4: stressed host (pressure_pct >= 50) → cap=1 serial."""
    probe = HostProbe(cores=8, free_ram_gb=8, pressure_pct=60)
    cap = resolve_wave_cap(env_var=None, manifest_value=None, host_probe=probe)
    assert cap == 1


def test_explicit_cap_of_one_serializes() -> None:
    """Scenario 5: cap=1 explicit → serial."""
    cap = resolve_wave_cap(env_var="1", manifest_value=None, host_probe=None)
    assert cap == 1


def test_cap_does_not_shrink_to_fit_smaller_N() -> None:
    """Scenario 6: explicit cap > N agents → resolver returns cap, not N.

    The cap is independent of how many agents the caller intends to
    dispatch. Batching the caller's N agents in groups of `cap` is the
    caller's responsibility, not the resolver's.
    """
    cap = resolve_wave_cap(env_var="6", manifest_value=None, host_probe=None)
    assert cap == 6


def test_quality_cap_capped_at_three_per_d_139_recommendation() -> None:
    """`/ai-autopilot` Phase 5 dispatches at most 3 quality assessors."""
    assert resolve_quality_cap(env_var=None, manifest_value=None) == 3
    assert resolve_quality_cap(env_var="2", manifest_value=None) == 2
    # Env value > 3 still clamps to 3 (the canonical quality-loop contract).
    assert resolve_quality_cap(env_var="10", manifest_value=None) == 3


def test_thread_workers_default_four() -> None:
    """Orchestrator ThreadPoolExecutor caps at 4 workers by default."""
    assert resolve_thread_workers(env_var=None, manifest_value=None) == 4
    assert resolve_thread_workers(env_var="2", manifest_value=None) == 2


def test_thread_workers_env_overrides_manifest() -> None:
    assert resolve_thread_workers(env_var="3", manifest_value=8) == 3


@pytest.mark.parametrize(
    ("env_value", "expected_floor"),
    [(None, 2), ("1", 1), ("2", 2)],
)
def test_floor_invariant(env_value: str | None, expected_floor: int) -> None:
    """When the env or manifest pushes below the floor, the floor wins.

    Floor = 2 except when the env explicitly sets cap=1 (operator
    opt-in to serial mode); we honour the explicit serial choice but
    never let auto-tune drift below 2 on its own.
    """
    cap = resolve_wave_cap(env_var=env_value, manifest_value=None, host_probe=None)
    assert cap == expected_floor
