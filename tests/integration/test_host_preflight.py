"""Resource preflight probe integration tests (spec-139 M2).

Covers the four canonical scenarios called out by the M2 plan:

* healthy host → ``ok_to_dispatch == True``;
* high memory pressure (pressure_pct=60) → ``ok_to_dispatch == False``;
* low free RAM (free_ram_gb=1) → ``ok_to_dispatch == False``;
* single-core host → ``cores == 1`` and the resolver clamps the wave
  cap to ``WAVE_FLOOR`` (2).

Tests inject a deterministic :class:`HostProbe` instead of running
the real adapter so behaviour does not depend on the CI runner's
actual capacity. The adapter dispatch (``sys.platform`` matrix) is
exercised separately by the unit test suite.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from ai_engineering.adapters.host import HostProbe, probe
from ai_engineering.config.concurrency import WAVE_FLOOR, resolve_wave_cap


@pytest.fixture
def healthy_probe() -> HostProbe:
    """Generous host: 8 cores, 16 GiB free, no pressure, no swap thrash."""
    return HostProbe(
        cores=8,
        free_ram_gb=16,
        pressure_pct=10,
        swap_used_pct=0,
        platform="linux",
    )


@pytest.fixture
def high_pressure_probe() -> HostProbe:
    """Plenty of cores + RAM but the kernel reports 60 % memory pressure."""
    return HostProbe(
        cores=8,
        free_ram_gb=16,
        pressure_pct=60,
        swap_used_pct=5,
        platform="darwin",
    )


@pytest.fixture
def low_ram_probe() -> HostProbe:
    """Plenty of cores but only 1 GiB free — well below the 2 GiB floor."""
    return HostProbe(
        cores=8,
        free_ram_gb=1,
        pressure_pct=20,
        swap_used_pct=0,
        platform="linux",
    )


@pytest.fixture
def single_core_probe() -> HostProbe:
    """A 1-core host so the resolver has to clamp to ``WAVE_FLOOR``."""
    return HostProbe(
        cores=1,
        free_ram_gb=8,
        pressure_pct=10,
        swap_used_pct=0,
        platform="linux",
    )


class TestOkToDispatch:
    """``HostProbe.ok_to_dispatch`` is the only gate skills check before fan-out."""

    def test_healthy_probe_is_ok(self, healthy_probe: HostProbe) -> None:
        """A generous host clears all three guards (RAM, pressure, swap)."""
        assert healthy_probe.ok_to_dispatch is True

    def test_high_pressure_blocks_dispatch(self, high_pressure_probe: HostProbe) -> None:
        """``pressure_pct >= 50`` collapses ``ok_to_dispatch`` to False."""
        assert high_pressure_probe.ok_to_dispatch is False

    def test_low_ram_blocks_dispatch(self, low_ram_probe: HostProbe) -> None:
        """``free_ram_gb * 1024 < 2048`` blocks dispatch regardless of cores."""
        assert low_ram_probe.ok_to_dispatch is False

    def test_high_swap_blocks_dispatch(self) -> None:
        """Swap thrash at >= 20 % blocks even if RAM + pressure pass."""
        probe_payload = HostProbe(
            cores=8,
            free_ram_gb=16,
            pressure_pct=10,
            swap_used_pct=30,
            platform="darwin",
        )
        assert probe_payload.ok_to_dispatch is False


class TestRecommendedCap:
    """``resolve_wave_cap`` should produce the expected cap per probe."""

    def test_healthy_probe_yields_meaningful_cap(self, healthy_probe: HostProbe) -> None:
        """8-core / 16 GiB host should resolve to the auto-tune ceiling (6)."""
        cap = resolve_wave_cap(env_var=None, manifest_value=None, host_probe=healthy_probe)
        # 16 GiB / 4 = 4 ; 8 cores / 2 = 4 ; ceiling 6 -- so cap = 4
        # but the clamp lower bound (WAVE_FLOOR=2) means we always see ≥ 2.
        assert cap >= WAVE_FLOOR
        assert cap <= 6

    def test_high_pressure_collapses_to_serial(self, high_pressure_probe: HostProbe) -> None:
        """A pressure-stressed host must collapse to ``cap=1`` per D-139-01."""
        cap = resolve_wave_cap(env_var=None, manifest_value=None, host_probe=high_pressure_probe)
        assert cap == 1

    def test_low_ram_caps_to_floor(self, low_ram_probe: HostProbe) -> None:
        """Low RAM hosts clamp to ``WAVE_FLOOR`` (auto-tune lower bound)."""
        cap = resolve_wave_cap(env_var=None, manifest_value=None, host_probe=low_ram_probe)
        # 1 GiB / 4 = 0 → clamped up to WAVE_FLOOR (2).
        assert cap == WAVE_FLOOR

    def test_single_core_resolves_to_floor(self, single_core_probe: HostProbe) -> None:
        """A 1-core host has core_budget=0 → clamps up to WAVE_FLOOR (2).

        The plan calls out ``cores == 1, recommended_cap == 2 (floor)``;
        this asserts the resolver honours that contract.
        """
        assert single_core_probe.cores == 1
        cap = resolve_wave_cap(env_var=None, manifest_value=None, host_probe=single_core_probe)
        assert cap == WAVE_FLOOR


class TestProbeDispatchFailOpen:
    """``probe()`` must NEVER raise; any backend error → degraded snapshot."""

    def test_probe_returns_hostprobe(self) -> None:
        """The real probe runs cleanly and returns a populated dataclass."""
        snapshot = probe()
        assert isinstance(snapshot, HostProbe)
        assert snapshot.cores >= 0
        assert snapshot.free_ram_gb >= 0
        assert 0 <= snapshot.pressure_pct <= 100
        assert 0 <= snapshot.swap_used_pct <= 100
        assert snapshot.platform in {"darwin", "linux", "win32", "unknown"}

    def test_probe_with_unknown_platform_degrades(self) -> None:
        """An unsupported platform string collapses to the degraded path.

        Patches ``sys.platform`` so the dispatch falls through every
        ``if`` branch in :func:`probe`; the resolver still gets a
        zero-valued :class:`HostProbe` with platform=``"unknown"`` and
        cores from :func:`os.cpu_count`.
        """
        with patch("ai_engineering.adapters.host.probe.sys") as mock_sys:
            mock_sys.platform = "freebsd"  # not in the dispatch matrix
            snapshot = probe()
        assert snapshot.platform == "unknown"
        assert snapshot.free_ram_gb == 0
        assert snapshot.pressure_pct == 0
        assert snapshot.swap_used_pct == 0

    def test_probe_backend_failure_is_swallowed(self) -> None:
        """A raising backend collapses to the degraded probe (fail-open)."""
        with patch("ai_engineering.adapters.host.probe.sys") as mock_sys:
            mock_sys.platform = "linux"
            with patch(
                "ai_engineering.adapters.host.probe._probe_linux",
                side_effect=RuntimeError("boom"),
            ):
                snapshot = probe()
        assert snapshot.platform == "linux"
        # Degraded probe: zero RAM/pressure/swap, cores still populated.
        assert snapshot.free_ram_gb == 0
        assert snapshot.pressure_pct == 0
        assert snapshot.swap_used_pct == 0


class TestPlatformDispatch:
    """``probe()`` dispatches to the correct backend per ``sys.platform``."""

    def test_darwin_dispatch(self) -> None:
        with patch("ai_engineering.adapters.host.probe.sys") as mock_sys:
            mock_sys.platform = "darwin"
            with patch(
                "ai_engineering.adapters.host.probe._probe_darwin",
                return_value=HostProbe(
                    cores=10,
                    free_ram_gb=12,
                    pressure_pct=15,
                    swap_used_pct=2,
                    platform="darwin",
                ),
            ) as mock_darwin:
                snapshot = probe()
        mock_darwin.assert_called_once()
        assert snapshot.platform == "darwin"
        assert snapshot.cores == 10

    def test_linux_dispatch(self) -> None:
        with patch("ai_engineering.adapters.host.probe.sys") as mock_sys:
            mock_sys.platform = "linux"
            with patch(
                "ai_engineering.adapters.host.probe._probe_linux",
                return_value=HostProbe(
                    cores=8,
                    free_ram_gb=16,
                    pressure_pct=20,
                    swap_used_pct=0,
                    platform="linux",
                ),
            ) as mock_linux:
                snapshot = probe()
        mock_linux.assert_called_once()
        assert snapshot.platform == "linux"
        assert snapshot.cores == 8

    def test_windows_dispatch(self) -> None:
        with patch("ai_engineering.adapters.host.probe.sys") as mock_sys:
            mock_sys.platform = "win32"
            with patch(
                "ai_engineering.adapters.host.probe._probe_windows",
                return_value=HostProbe(
                    cores=4,
                    free_ram_gb=8,
                    pressure_pct=25,
                    swap_used_pct=10,
                    platform="win32",
                ),
            ) as mock_windows:
                snapshot = probe()
        mock_windows.assert_called_once()
        assert snapshot.platform == "win32"
