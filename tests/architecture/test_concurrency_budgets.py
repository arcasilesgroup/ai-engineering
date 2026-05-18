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


def test_quality_cap_capped_at_three_per_d_139_recommendation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`/ai-autopilot` Phase 5 dispatches at most 3 quality assessors.

    Hermetic guard: ``resolve_quality_cap(env_var=None, …)`` reads
    ``AIENG_MAX_QUALITY_AGENTS`` from the process environment (line 218
    in concurrency.py). CI hosts that pre-set the var would otherwise
    drive the resolver onto the env-branch and break the documented
    default. Clearing the var keeps the assertion host-independent.
    """
    monkeypatch.delenv("AIENG_MAX_QUALITY_AGENTS", raising=False)
    assert resolve_quality_cap(env_var=None, manifest_value=None) == 3
    assert resolve_quality_cap(env_var="2", manifest_value=None) == 2
    # Env value > 3 still clamps to 3 (the canonical quality-loop contract).
    assert resolve_quality_cap(env_var="10", manifest_value=None) == 3


def test_thread_workers_default_four(monkeypatch: pytest.MonkeyPatch) -> None:
    """Orchestrator ThreadPoolExecutor caps at 4 workers by default.

    Hermetic guard: ``resolve_thread_workers(env_var=None, …)`` reads
    ``AIENG_MAX_THREAD_WORKERS`` from the process environment. Clearing
    the var keeps the "default is 4" claim deterministic across hosts.
    """
    monkeypatch.delenv("AIENG_MAX_THREAD_WORKERS", raising=False)
    assert resolve_thread_workers(env_var=None, manifest_value=None) == 4
    assert resolve_thread_workers(env_var="2", manifest_value=None) == 2


def test_thread_workers_env_overrides_manifest() -> None:
    assert resolve_thread_workers(env_var="3", manifest_value=8) == 3


@pytest.mark.parametrize(
    ("env_value", "expected"),
    [
        # `env="1"` is the operator opt-in serial mode — always returns 1
        # regardless of host cores.
        ("1", lambda c: c == 1),
        # `env="2"` is an explicit cap of 2 — always returns 2 regardless of
        # host cores.
        ("2", lambda c: c == 2),
        # `env=None` defers to auto-tune which depends on `os.cpu_count()`.
        # The resolver guarantees `[WAVE_FLOOR, WAVE_CEILING_AUTO]` = `[2, 6]`.
        # Tests run on hosts with anywhere from 2 to 16+ cores (macOS CI
        # runners are 3-core or 4-core depending on the macOS runner image
        # generation), so the assertion has to accept the whole resolved
        # range — exact equality would be host-dependent flakiness.
        (None, lambda c: 2 <= c <= 6),
    ],
)
def test_floor_invariant(env_value: str | None, expected) -> None:  # type: ignore[no-untyped-def]
    """When the env or manifest pushes below the floor, the floor wins.

    Floor = 2 except when the env explicitly sets cap=1 (operator
    opt-in to serial mode); we honour the explicit serial choice but
    never let auto-tune drift below 2 on its own.
    """
    cap = resolve_wave_cap(env_var=env_value, manifest_value=None, host_probe=None)
    assert expected(cap), (
        f"resolver returned {cap} for env_value={env_value!r}; expected predicate not satisfied"
    )


# ---------------------------------------------------------------------------
# Coverage — edge paths in the resolver and env parser
# ---------------------------------------------------------------------------


def test_env_var_non_numeric_falls_through_to_manifest() -> None:
    """Non-int env value is ignored — manifest takes over."""
    cap = resolve_wave_cap(env_var="not-a-number", manifest_value=3, host_probe=None)
    assert cap == 3


def test_env_var_zero_falls_through() -> None:
    """env=0 is non-positive — ignored, manifest wins."""
    cap = resolve_wave_cap(env_var="0", manifest_value=5, host_probe=None)
    assert cap == 5


def test_env_var_negative_falls_through() -> None:
    """Negative env values are ignored."""
    cap = resolve_wave_cap(env_var="-3", manifest_value=4, host_probe=None)
    assert cap == 4


def test_env_var_whitespace_only_falls_through() -> None:
    """Whitespace-only env values are treated as unset."""
    cap = resolve_wave_cap(env_var="   ", manifest_value=4, host_probe=None)
    assert cap == 4


def test_env_var_above_hard_ceiling_clamps() -> None:
    """env above WAVE_CEILING_HARD is clamped to the hard ceiling."""
    from ai_engineering.config.concurrency import WAVE_CEILING_HARD

    cap = resolve_wave_cap(env_var="9999", manifest_value=None, host_probe=None)
    assert cap == WAVE_CEILING_HARD


def test_manifest_string_auto_falls_through_to_auto_tune() -> None:
    """`auto` (case-insensitive) defers to host auto-tune."""
    cap_lower = resolve_wave_cap(env_var=None, manifest_value="auto", host_probe=None)
    cap_upper = resolve_wave_cap(env_var=None, manifest_value="AUTO", host_probe=None)
    cap_mixed = resolve_wave_cap(env_var=None, manifest_value="  Auto  ", host_probe=None)
    assert 2 <= cap_lower <= 6
    assert cap_lower == cap_upper == cap_mixed


def test_manifest_string_integer_parses() -> None:
    """A numeric string in the manifest knob is parsed."""
    cap = resolve_wave_cap(env_var=None, manifest_value="4", host_probe=None)
    assert cap == 4


def test_manifest_string_non_numeric_falls_through() -> None:
    """Non-numeric manifest strings (other than `auto`) defer to auto-tune."""
    cap = resolve_wave_cap(env_var=None, manifest_value="banana", host_probe=None)
    assert 2 <= cap <= 6


def test_manifest_zero_falls_through() -> None:
    """A manifest int ≤ 0 is ignored."""
    cap = resolve_wave_cap(env_var=None, manifest_value=0, host_probe=None)
    assert 2 <= cap <= 6


def test_auto_tune_with_zero_cores_falls_back_to_floor() -> None:
    """`os.cpu_count() → None` is a real possibility on exotic hosts."""
    with mock.patch.object(os, "cpu_count", return_value=None):
        cap = resolve_wave_cap(env_var=None, manifest_value=None, host_probe=None)
    assert cap == 2  # floor


def test_auto_tune_with_low_free_ram_clamps_to_floor() -> None:
    """Host with 0 GB free RAM clamps to the floor=2."""
    probe = HostProbe(cores=8, free_ram_gb=0, pressure_pct=10)
    cap = resolve_wave_cap(env_var=None, manifest_value=None, host_probe=probe)
    assert cap == 2  # floor


def test_auto_tune_with_low_cores_clamps_to_floor() -> None:
    """Host with 1 core clamps to floor."""
    probe = HostProbe(cores=1, free_ram_gb=16, pressure_pct=10)
    cap = resolve_wave_cap(env_var=None, manifest_value=None, host_probe=probe)
    assert cap == 2


def test_auto_tune_at_pressure_threshold_returns_serial() -> None:
    """pressure_pct = 50 (boundary) → cap=1."""
    probe = HostProbe(cores=8, free_ram_gb=8, pressure_pct=50)
    cap = resolve_wave_cap(env_var=None, manifest_value=None, host_probe=probe)
    assert cap == 1


def test_quality_cap_env_string_invalid_falls_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid env string → default cap.

    Hermetic guard: a non-empty but invalid ``env_var`` still triggers
    the fallback that reads ``os.environ.get("AIENG_MAX_QUALITY_AGENTS")``
    via the resolver's mixed parsing path. Clearing the var keeps the
    "default cap = 3" claim independent of the host shell.
    """
    monkeypatch.delenv("AIENG_MAX_QUALITY_AGENTS", raising=False)
    assert resolve_quality_cap(env_var="banana", manifest_value=None) == 3


def test_quality_cap_env_whitespace_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """Whitespace-only env value → falls through to default."""
    monkeypatch.delenv("AIENG_MAX_QUALITY_AGENTS", raising=False)
    assert resolve_quality_cap(env_var="   ", manifest_value=None) == 3


def test_quality_cap_manifest_zero_falls_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """Manifest value ≤ 0 → default cap."""
    monkeypatch.delenv("AIENG_MAX_QUALITY_AGENTS", raising=False)
    assert resolve_quality_cap(env_var=None, manifest_value=0) == 3


# ---------------------------------------------------------------------------
# _env_int helper coverage
# ---------------------------------------------------------------------------


def test_env_int_returns_default_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    from ai_engineering.config.concurrency import _env_int

    monkeypatch.delenv("AIENG_TEST_VAR_X", raising=False)
    assert _env_int("AIENG_TEST_VAR_X", default=7) == 7


def test_env_int_returns_default_when_blank(monkeypatch: pytest.MonkeyPatch) -> None:
    from ai_engineering.config.concurrency import _env_int

    monkeypatch.setenv("AIENG_TEST_VAR_X", "   ")
    assert _env_int("AIENG_TEST_VAR_X", default=7) == 7


def test_env_int_returns_default_when_non_numeric(monkeypatch: pytest.MonkeyPatch) -> None:
    from ai_engineering.config.concurrency import _env_int

    monkeypatch.setenv("AIENG_TEST_VAR_X", "banana")
    assert _env_int("AIENG_TEST_VAR_X", default=7) == 7


def test_env_int_returns_default_when_zero_or_negative(monkeypatch: pytest.MonkeyPatch) -> None:
    from ai_engineering.config.concurrency import _env_int

    monkeypatch.setenv("AIENG_TEST_VAR_X", "0")
    assert _env_int("AIENG_TEST_VAR_X", default=7) == 7
    monkeypatch.setenv("AIENG_TEST_VAR_X", "-3")
    assert _env_int("AIENG_TEST_VAR_X", default=7) == 7


def test_env_int_clamps_to_ceiling(monkeypatch: pytest.MonkeyPatch) -> None:
    from ai_engineering.config.concurrency import _env_int

    monkeypatch.setenv("AIENG_TEST_VAR_X", "999")
    assert _env_int("AIENG_TEST_VAR_X", default=7, ceiling=10) == 10
    monkeypatch.setenv("AIENG_TEST_VAR_X", "5")
    assert _env_int("AIENG_TEST_VAR_X", default=7, ceiling=10) == 5


def test_env_int_none_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default=None preserved when env unset."""
    from ai_engineering.config.concurrency import _env_int

    monkeypatch.delenv("AIENG_TEST_VAR_X", raising=False)
    assert _env_int("AIENG_TEST_VAR_X", default=None) is None
