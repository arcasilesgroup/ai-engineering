"""Unit tests for ``ai_engineering.adapters.host.probe`` (spec-139 M2).

These tests cover the per-platform backends and parsing helpers without
relying on the real host the test happens to run on. Each backend
takes its inputs from either ``_run_subprocess`` (mocked) or ``Path``
reads (monkeypatched via the module-level ``_PROC_*`` symbols), so the
fail-open contract and parsing edge cases are exercised on every
runner.
"""

from __future__ import annotations

import subprocess
import sys as _sys
from typing import Any
from unittest import mock

import pytest

import ai_engineering.adapters.host.probe  # noqa: F401  (registers submodule)
from ai_engineering.config.concurrency import HostProbe

# The parent package re-exports the `probe` function with the same name as
# the submodule, so `import ai_engineering.adapters.host.probe as x` binds
# to the function — not the module. Grab the module object from sys.modules.
probe_mod = _sys.modules["ai_engineering.adapters.host.probe"]


# ---------------------------------------------------------------------------
# probe() dispatch
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "platform,backend_name",
    [
        ("darwin", "_probe_darwin"),
        ("linux", "_probe_linux"),
        ("win32", "_probe_windows"),
    ],
)
def test_probe_dispatches_per_platform(
    monkeypatch: pytest.MonkeyPatch, platform: str, backend_name: str
) -> None:
    sentinel = HostProbe(cores=99, free_ram_gb=99, pressure_pct=99, platform=platform)
    monkeypatch.setattr(probe_mod.sys, "platform", platform)
    monkeypatch.setattr(probe_mod, backend_name, lambda: sentinel)
    assert probe_mod.probe() is sentinel


def test_probe_unknown_platform_returns_degraded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe_mod.sys, "platform", "haiku")
    result = probe_mod.probe()
    assert result.platform == "unknown"
    assert result.free_ram_gb == 0
    assert result.pressure_pct == 0
    assert result.swap_used_pct == 0


def test_probe_backend_exception_returns_degraded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe_mod.sys, "platform", "darwin")

    def boom() -> HostProbe:
        raise RuntimeError("boom")

    monkeypatch.setattr(probe_mod, "_probe_darwin", boom)
    result = probe_mod.probe()
    assert result.platform == "darwin"
    assert result.free_ram_gb == 0


# ---------------------------------------------------------------------------
# _degraded_probe / _run_subprocess
# ---------------------------------------------------------------------------


def test_degraded_probe_preserves_platform_tag() -> None:
    result = probe_mod._degraded_probe("freebsd")
    assert result.platform == "freebsd"
    assert result.cores >= 0  # os.cpu_count is platform-agnostic


def test_run_subprocess_missing_binary_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_fnf(*_a: Any, **_k: Any) -> Any:
        raise FileNotFoundError("no helper")

    monkeypatch.setattr(probe_mod.subprocess, "run", raise_fnf)
    assert probe_mod._run_subprocess(["nope"]) == ""


def test_run_subprocess_timeout_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_timeout(*_a: Any, **_k: Any) -> Any:
        raise subprocess.TimeoutExpired(cmd=["x"], timeout=1.0)

    monkeypatch.setattr(probe_mod.subprocess, "run", raise_timeout)
    assert probe_mod._run_subprocess(["x"]) == ""


def test_run_subprocess_nonzero_exit_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        probe_mod.subprocess,
        "run",
        lambda *_a, **_k: subprocess.CompletedProcess(args=["x"], returncode=1, stdout="ignored"),
    )
    assert probe_mod._run_subprocess(["x"]) == ""


def test_run_subprocess_success_returns_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        probe_mod.subprocess,
        "run",
        lambda *_a, **_k: subprocess.CompletedProcess(args=["x"], returncode=0, stdout="hello\n"),
    )
    assert probe_mod._run_subprocess(["x"]) == "hello\n"


# ---------------------------------------------------------------------------
# darwin helpers
# ---------------------------------------------------------------------------


def _fake_subprocess(table: dict[tuple[str, ...], str]):
    def _runner(args: list[str]) -> str:
        key = tuple(args)
        return table.get(key, "")

    return _runner


def test_probe_darwin_aggregates_all_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    vm_stat = (
        "Mach Virtual Memory Statistics: (page size of 4096 bytes)\n"
        "Pages free:                               100.\n"
        "Pages inactive:                            50.\n"
        "Pages speculative:                         10.\n"
    )
    table = {
        ("sysctl", "-n", "hw.ncpu"): "8\n",
        ("sysctl", "-n", "hw.memsize"): str(16 * probe_mod._BYTES_PER_GIB) + "\n",
        ("vm_stat",): vm_stat,
        ("sysctl", "-n", "vm.swapusage"): "total = 1024.00M  used = 256.00M  free = 768.00M\n",
    }
    monkeypatch.setattr(probe_mod, "_run_subprocess", _fake_subprocess(table))
    result = probe_mod._probe_darwin()
    assert result.platform == "darwin"
    assert result.cores == 8
    # 160 pages * 4096 bytes = 655360 bytes — far under 1 GiB so the floor is 0.
    assert result.free_ram_gb == 0
    # pressure = (total - free) / total — free is tiny so should be ~100.
    assert 0 <= result.pressure_pct <= 100
    assert result.swap_used_pct == 25


def test_darwin_cores_falls_back_to_os_cpu_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe_mod, "_run_subprocess", lambda _args: "")
    monkeypatch.setattr(probe_mod.os, "cpu_count", lambda: 7)
    assert probe_mod._darwin_cores() == 7


def test_darwin_cores_handles_non_integer_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe_mod, "_run_subprocess", lambda _args: "notanumber\n")
    monkeypatch.setattr(probe_mod.os, "cpu_count", lambda: 3)
    assert probe_mod._darwin_cores() == 3


def test_darwin_total_memory_empty_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe_mod, "_run_subprocess", lambda _args: "")
    assert probe_mod._darwin_total_memory_bytes() == 0


def test_darwin_total_memory_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe_mod, "_run_subprocess", lambda _args: "garbage\n")
    assert probe_mod._darwin_total_memory_bytes() == 0


def test_darwin_free_memory_no_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe_mod, "_run_subprocess", lambda _args: "")
    assert probe_mod._darwin_free_memory_bytes() == 0


def test_darwin_free_memory_no_page_size(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe_mod, "_run_subprocess", lambda _args: "no page size here\n")
    assert probe_mod._darwin_free_memory_bytes() == 0


def test_darwin_parse_page_size_invalid_match() -> None:
    assert probe_mod._darwin_parse_page_size("nothing useful") == 0


def test_darwin_parse_pages_missing_label() -> None:
    assert probe_mod._darwin_parse_pages(["Pages other: 1."], "Pages free") == 0


def test_darwin_parse_pages_invalid_number() -> None:
    assert probe_mod._darwin_parse_pages(["Pages free:    notnum."], "Pages free") == 0


def test_darwin_pressure_zero_total() -> None:
    assert probe_mod._darwin_pressure_pct(0, 0) == 0


def test_darwin_pressure_clamps_negative() -> None:
    # free > total → clamped to 0 (used = max(0, negative))
    assert probe_mod._darwin_pressure_pct(100, 200) == 0


def test_darwin_swap_used_no_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(probe_mod, "_run_subprocess", lambda _args: "")
    assert probe_mod._darwin_swap_used_pct() == 0


def test_darwin_swap_used_zero_total(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        probe_mod, "_run_subprocess", lambda _args: "total = 0.00M  used = 0.00M  free = 0.00M\n"
    )
    assert probe_mod._darwin_swap_used_pct() == 0


def test_darwin_parse_swap_value_unparseable() -> None:
    assert probe_mod._darwin_parse_swap_value("total = abcM", "total") == 0


def test_darwin_parse_swap_value_with_gibibyte_unit() -> None:
    # 1 GiB swap usage parses as 1024^3 bytes (the multiplier table).
    assert probe_mod._darwin_parse_swap_value("used = 1.00G", "used") == 1024**3


# ---------------------------------------------------------------------------
# linux helpers
# ---------------------------------------------------------------------------


def test_probe_linux_aggregates_meminfo(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    meminfo = tmp_path / "meminfo"
    meminfo.write_text(
        "MemTotal:       8000000 kB\n"
        "MemFree:        2000000 kB\n"
        "Buffers:         100000 kB\n"
        "Cached:          500000 kB\n"
        "MemAvailable:   3000000 kB\n",
        encoding="utf-8",
    )
    swaps = tmp_path / "swaps"
    swaps.write_text(
        "Filename Type Size Used Priority\n/swap1 file 1000 250 -2\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(probe_mod, "_PROC_MEMINFO", meminfo)
    monkeypatch.setattr(probe_mod, "_PROC_SWAPS", swaps)
    monkeypatch.setattr(probe_mod.os, "cpu_count", lambda: 4)

    result = probe_mod._probe_linux()
    assert result.platform == "linux"
    assert result.cores == 4
    # (2_000_000 + 100_000 + 500_000) KiB = 2_600_000 KiB = 2 GiB floor.
    assert result.free_ram_gb == 2
    assert 0 <= result.pressure_pct <= 100
    assert result.swap_used_pct == 25


def test_linux_parse_meminfo_missing_file(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(probe_mod, "_PROC_MEMINFO", tmp_path / "nope")
    assert probe_mod._linux_parse_meminfo() == {}


def test_linux_parse_meminfo_unreadable(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    fake = tmp_path / "meminfo"
    fake.write_text("ignored", encoding="utf-8")
    monkeypatch.setattr(probe_mod, "_PROC_MEMINFO", fake)

    def raise_oserror(*_a: Any, **_k: Any) -> Any:
        raise OSError("denied")

    monkeypatch.setattr(probe_mod.Path, "read_text", raise_oserror)
    assert probe_mod._linux_parse_meminfo() == {}


def test_linux_parse_meminfo_skips_malformed_lines(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    fake = tmp_path / "meminfo"
    fake.write_text("garbage line\nMemTotal: 1000 kB\nNoColon\n:emptykey\n", encoding="utf-8")
    monkeypatch.setattr(probe_mod, "_PROC_MEMINFO", fake)
    result = probe_mod._linux_parse_meminfo()
    assert result == {"MemTotal": 1000}


def test_linux_pressure_zero_total() -> None:
    assert probe_mod._linux_pressure_pct(0, 0) == 0


def test_linux_pressure_clamps_negative() -> None:
    assert probe_mod._linux_pressure_pct(100, 200) == 0


def test_linux_swap_missing_file(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(probe_mod, "_PROC_SWAPS", tmp_path / "nope")
    assert probe_mod._linux_swap_used_pct() == 0


def test_linux_swap_unreadable(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    fake = tmp_path / "swaps"
    fake.write_text("ignored", encoding="utf-8")
    monkeypatch.setattr(probe_mod, "_PROC_SWAPS", fake)

    def raise_oserror(*_a: Any, **_k: Any) -> Any:
        raise OSError("denied")

    monkeypatch.setattr(probe_mod.Path, "read_text", raise_oserror)
    assert probe_mod._linux_swap_used_pct() == 0


def test_linux_swap_zero_total(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    fake = tmp_path / "swaps"
    fake.write_text("Filename Type Size Used Priority\n", encoding="utf-8")
    monkeypatch.setattr(probe_mod, "_PROC_SWAPS", fake)
    assert probe_mod._linux_swap_used_pct() == 0


def test_linux_swap_skips_short_rows(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    fake = tmp_path / "swaps"
    fake.write_text("hdr\nshortrow\n/x file 100 25 -1\n", encoding="utf-8")
    monkeypatch.setattr(probe_mod, "_PROC_SWAPS", fake)
    assert probe_mod._linux_swap_used_pct() == 25


def test_linux_swap_handles_non_integer(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    fake = tmp_path / "swaps"
    fake.write_text("hdr\n/x file abc xyz -1\n/y file 100 25 -1\n", encoding="utf-8")
    monkeypatch.setattr(probe_mod, "_PROC_SWAPS", fake)
    assert probe_mod._linux_swap_used_pct() == 25


# ---------------------------------------------------------------------------
# windows backend
# ---------------------------------------------------------------------------


def test_probe_windows_without_psutil(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing psutil → degraded zero-RAM probe with platform tag preserved."""

    import importlib

    real_import_module = importlib.import_module

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "psutil":
            raise ImportError("not installed")
        return real_import_module(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", fake_import)
    monkeypatch.setattr(probe_mod.os, "cpu_count", lambda: 12)
    result = probe_mod._probe_windows()
    assert result == HostProbe(
        cores=12, free_ram_gb=0, pressure_pct=0, swap_used_pct=0, platform="win32"
    )


def test_probe_windows_with_psutil(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock psutil and verify the populated probe shape."""

    class _VM:
        available = 8 * probe_mod._BYTES_PER_GIB
        percent = 42

    class _SW:
        percent = 17

    fake_psutil = mock.MagicMock()
    fake_psutil.virtual_memory.return_value = _VM()
    fake_psutil.swap_memory.return_value = _SW()

    import importlib

    real_import_module = importlib.import_module

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "psutil":
            return fake_psutil
        return real_import_module(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", fake_import)
    monkeypatch.setattr(probe_mod.os, "cpu_count", lambda: 6)
    result = probe_mod._probe_windows()
    assert result.platform == "win32"
    assert result.cores == 6
    assert result.free_ram_gb == 8
    assert result.pressure_pct == 42
    assert result.swap_used_pct == 17


def test_probe_windows_swallows_psutil_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Per-call psutil errors degrade individual fields, never raise."""

    fake_psutil = mock.MagicMock()
    fake_psutil.virtual_memory.side_effect = RuntimeError("boom")
    fake_psutil.swap_memory.side_effect = RuntimeError("boom")

    import importlib

    real_import_module = importlib.import_module

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "psutil":
            return fake_psutil
        return real_import_module(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", fake_import)
    monkeypatch.setattr(probe_mod.os, "cpu_count", lambda: 4)
    result = probe_mod._probe_windows()
    assert result.platform == "win32"
    assert result.cores == 4
    assert result.free_ram_gb == 0
    assert result.pressure_pct == 0
    assert result.swap_used_pct == 0


# ---------------------------------------------------------------------------
# __all__ surface
# ---------------------------------------------------------------------------


def test_module_exports_probe_and_hostprobe() -> None:
    assert "probe" in probe_mod.__all__
    assert "HostProbe" in probe_mod.__all__
