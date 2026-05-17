"""Concurrency budget primitive (spec-139 M1).

Single global cap that prevents the kernel-panic class observed in the
spec-139 brief's trigger incident (macOS M1 Pro: WindowServer watchdog
171 s, memory compressor 100% segments) caused by unbounded fan-out of
parallel sub-agents during Phase 2 / Phase 4 / Phase 5 dispatch.

Provides three resolver functions plus the shared bounded ``_env_int``
parser, all consumed by:

- the autopilot skill handlers
  (``phase-deep-plan.md`` / ``phase-implement.md`` / ``phase-quality.md``)
  via the runtime env vars below;
- the policy orchestrator's ``ThreadPoolExecutor`` calls
  (``orchestrator.py:489`` and ``:1209``) which read the
  ``AIENG_MAX_THREAD_WORKERS`` / manifest knob to cap parallel checkers.

Auto-tune algorithm (D-139-01)
------------------------------

When no env var and no manifest value are supplied, the wave cap is
derived from host capacity:

* If ``host.pressure_pct >= 50`` → ``cap = 1`` (single-agent serial).
* Else ``cap = min(host.free_ram_gb // 4, host.cores // 2, 6)``,
  clamped to ``[2, 6]``.

The :class:`HostProbe` dataclass is provided as an injectable port so
M2 (resource preflight) can supply real darwin/linux measurements.
Until M2 lands, ``resolve_wave_cap`` falls back to a degraded probe
that uses only :func:`os.cpu_count` and clamps to the same range.

Env precedence
--------------

``AIENG_MAX_WAVE_AGENTS`` > ``performance.concurrency.max_wave_agents``
manifest knob > auto-tune from :class:`HostProbe` > floor (2).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final

# Lower / upper safety rails for the wave cap. ``WAVE_CEILING_HARD`` is a
# defence-in-depth ceiling that even an env-supplied value cannot bypass —
# AIENG_MAX_WAVE_AGENTS=999 still resolves to ``WAVE_CEILING_HARD``.
WAVE_FLOOR: Final[int] = 2
WAVE_CEILING_AUTO: Final[int] = 6
WAVE_CEILING_HARD: Final[int] = 64

# Phase 5 is intentionally low: verify / guard / review are heavy
# multi-tool agents, not lightweight workers. Default is 3 and the env
# var clamps it down further but never up.
QUALITY_DEFAULT_CAP: Final[int] = 3

# Thread-pool default for orchestrator parallel checkers. 4 matches the
# previous implicit ceiling (most repos have ≤ 4 active checkers).
THREAD_WORKERS_DEFAULT: Final[int] = 4
THREAD_WORKERS_CEILING: Final[int] = 32


@dataclass(frozen=True)
class HostProbe:
    """Snapshot of host capacity used to auto-tune the wave cap.

    Populated by :mod:`ai_engineering.adapters.host.probe` (spec-139 M2).
    The probe adapter dispatches by ``sys.platform`` to ``_probe_darwin`` /
    ``_probe_linux`` / ``_probe_windows`` and returns this dataclass with
    real measurements; failures degrade to zero-valued fields so the
    resolver clamps to the safe ``WAVE_FLOOR`` rather than crashing.

    Attributes
    ----------
    cores:
        Logical core count.
    free_ram_gb:
        Free RAM in gibibytes (integer floor). ``0`` when unknown.
    pressure_pct:
        Memory pressure as a percentage 0-100 (per macOS ``memory_pressure``
        / linux ``MemAvailable``-derived heuristic). ``0`` when unknown.
    swap_used_pct:
        Swap utilisation as a percentage 0-100. ``0`` when unknown.
        Spec-139 M2 adds this so the dispatch guard refuses to fan out
        into swap thrash.
    platform:
        ``sys.platform`` string captured by the probe adapter:
        ``"darwin"`` | ``"linux"`` | ``"win32"`` | ``"unknown"``.
        Defaults to ``"unknown"`` so callers that construct ``HostProbe``
        without the spec-139 M2 fields keep working unchanged.
    """

    cores: int
    free_ram_gb: int
    pressure_pct: int
    swap_used_pct: int = 0
    platform: str = "unknown"

    @property
    def ok_to_dispatch(self) -> bool:
        """Whether the host has enough headroom to fan out parallel agents.

        Three independent guards, all must pass:

        * ``free_ram_gb * 1024 >= 2048`` — at least 2 GiB free RAM.
        * ``pressure_pct < 50`` — memory pressure below the auto-tune
          serial-mode cutoff (matches :func:`_auto_tune_from_probe`).
        * ``swap_used_pct < 20`` — host is not actively swap thrashing.

        Callers (``/ai-autopilot`` Phase 0, ``/ai-build`` step 0) emit a
        ``host_pressure_warning`` and degrade to ``cap=1`` when this
        predicate is False.
        """
        return (
            self.free_ram_gb * 1024 >= 2048 and self.pressure_pct < 50 and self.swap_used_pct < 20
        )


def _env_int(name: str, default: int | None, *, ceiling: int | None = None) -> int | None:
    """Strict positive-integer env parser.

    Returns ``default`` when the env var is unset, empty, non-numeric,
    or non-positive (≤ 0). When ``ceiling`` is supplied, parsed values
    above the ceiling clamp to the ceiling.

    The signature intentionally matches the hook-side ``_env_int`` in
    ``templates/.ai-engineering/scripts/hooks/_lib/runtime_state.py`` so
    a future deduplication move would be a rename-only refactor.
    """
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if value <= 0:
        return default
    if ceiling is not None and value > ceiling:
        return ceiling
    return value


def _auto_tune_from_probe(probe: HostProbe | None) -> int:
    """Compute the wave cap from a host snapshot per D-139-01.

    Falls back to a degraded :func:`os.cpu_count` estimate when
    ``probe`` is ``None`` (M2 not yet integrated). The degraded path
    always returns a value in ``[WAVE_FLOOR, WAVE_CEILING_AUTO]``.
    """
    if probe is None:
        cores = os.cpu_count() or 0
        estimate = cores // 2 or WAVE_FLOOR
        return max(WAVE_FLOOR, min(WAVE_CEILING_AUTO, estimate))

    if probe.pressure_pct >= 50:
        # Host is under memory pressure — collapse to serial to avoid
        # the WindowServer watchdog / memory-compressor saturation class
        # documented in the spec-139 brief.
        return 1

    ram_budget = max(0, probe.free_ram_gb // 4)
    cpu_budget = max(0, probe.cores // 2)
    raw_cap = min(ram_budget, cpu_budget, WAVE_CEILING_AUTO)
    return max(WAVE_FLOOR, min(WAVE_CEILING_AUTO, raw_cap))


def resolve_wave_cap(
    env_var: str | None,
    manifest_value: int | str | None,
    host_probe: HostProbe | None = None,
) -> int:
    """Resolve the Phase 2 / Phase 4 wave cap (spec-139 M1).

    Precedence (highest wins):

    1. ``env_var`` — typically the raw string from ``os.environ.get(
       "AIENG_MAX_WAVE_AGENTS")``. A bare positive integer parses to
       itself, clamped to ``[1, WAVE_CEILING_HARD]``. Values ≤ 0,
       non-numeric, or empty fall through to the next layer.
    2. ``manifest_value`` — the ``performance.concurrency.max_wave_agents``
       knob. ``"auto"`` (case-insensitive) is treated as "no opinion"
       and falls through to host auto-tune. A positive integer clamps to
       ``[1, WAVE_CEILING_HARD]``.
    3. Auto-tune from :class:`HostProbe` per :func:`_auto_tune_from_probe`.
    4. Floor (``WAVE_FLOOR``) if every layer above returns nothing.

    Parameters
    ----------
    env_var:
        Raw env-var string (or ``None`` when unset). Pass the raw value;
        the resolver does its own parsing so callers don't have to
        duplicate the strict ``_env_int`` rules.
    manifest_value:
        Already-parsed manifest knob — either an ``int``, the literal
        string ``"auto"``, or ``None`` when the field is absent.
    host_probe:
        Optional host snapshot (spec-139 M2). ``None`` triggers the
        degraded ``os.cpu_count`` fallback.

    Returns
    -------
    int
        A positive integer in ``[1, WAVE_CEILING_HARD]``. Never zero,
        never negative, never above the hard ceiling regardless of input.
    """
    # Layer 1: env var
    if env_var is not None:
        env_stripped = env_var.strip()
        if env_stripped:
            try:
                parsed = int(env_stripped)
            except ValueError:
                parsed = 0
            if parsed >= 1:
                return min(parsed, WAVE_CEILING_HARD)

    # Layer 2: manifest knob
    if manifest_value is not None:
        if isinstance(manifest_value, str):
            if manifest_value.strip().lower() != "auto":
                try:
                    parsed_m = int(manifest_value.strip())
                except ValueError:
                    parsed_m = 0
                if parsed_m >= 1:
                    return min(parsed_m, WAVE_CEILING_HARD)
        elif isinstance(manifest_value, int) and manifest_value >= 1:
            return min(manifest_value, WAVE_CEILING_HARD)

    # Layer 3: auto-tune
    auto = _auto_tune_from_probe(host_probe)
    if auto >= 1:
        return auto

    # Layer 4: floor (defensive — _auto_tune_from_probe always returns ≥ 1)
    return WAVE_FLOOR


def resolve_quality_cap(env_var: str | None, manifest_value: int | None = None) -> int:
    """Resolve the Phase 5 quality-loop cap.

    Phase 5 dispatches verify + guard + review in parallel. The cap is
    deliberately small (default 3, ceiling 3) because each agent is
    itself a multi-tool orchestrator. ``AIENG_MAX_QUALITY_AGENTS`` can
    only lower the cap, never raise it above ``QUALITY_DEFAULT_CAP``.
    """
    env_parsed = _env_int("AIENG_MAX_QUALITY_AGENTS", None) if env_var is None else None
    if env_var is not None:
        env_stripped = env_var.strip()
        if env_stripped:
            try:
                parsed = int(env_stripped)
                if parsed >= 1:
                    env_parsed = parsed
            except ValueError:
                pass

    if env_parsed is not None and env_parsed >= 1:
        return min(env_parsed, QUALITY_DEFAULT_CAP)
    if isinstance(manifest_value, int) and manifest_value >= 1:
        return min(manifest_value, QUALITY_DEFAULT_CAP)
    return QUALITY_DEFAULT_CAP


def resolve_thread_workers(env_var: str | None = None, manifest_value: int | None = None) -> int:
    """Resolve the orchestrator ``ThreadPoolExecutor`` worker cap.

    Used by ``src/ai_engineering/policy/orchestrator.py`` at the two
    parallel-checker sites (Wave 2 and dispatch). The previous code
    used ``max(1, len(checkers))`` which provided no upper bound;
    spec-139 M1 caps it at ``AIENG_MAX_THREAD_WORKERS`` (env) or the
    ``performance.concurrency.max_thread_workers`` manifest knob,
    defaulting to ``THREAD_WORKERS_DEFAULT``.

    The caller still wraps the result with ``min(N, cap)`` to preserve
    the "shrink to fit when fewer items than cap" behavior; this
    resolver returns only the cap.
    """
    if env_var is None:
        raw = os.environ.get("AIENG_MAX_THREAD_WORKERS", "").strip()
    else:
        raw = env_var.strip()

    if raw:
        try:
            parsed = int(raw)
        except ValueError:
            parsed = 0
        if parsed >= 1:
            return min(parsed, THREAD_WORKERS_CEILING)

    if isinstance(manifest_value, int) and manifest_value >= 1:
        return min(manifest_value, THREAD_WORKERS_CEILING)

    return THREAD_WORKERS_DEFAULT


__all__ = [
    "QUALITY_DEFAULT_CAP",
    "THREAD_WORKERS_CEILING",
    "THREAD_WORKERS_DEFAULT",
    "WAVE_CEILING_AUTO",
    "WAVE_CEILING_HARD",
    "WAVE_FLOOR",
    "HostProbe",
    "resolve_quality_cap",
    "resolve_thread_workers",
    "resolve_wave_cap",
]
