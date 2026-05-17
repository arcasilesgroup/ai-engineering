"""Resource preflight probe (spec-139 M2, D-139-02 / D-139-09).

Dispatches to platform-specific backends to produce a
:class:`ai_engineering.config.HostProbe` snapshot used by
``/ai-autopilot`` Phase 0 and ``/ai-build`` step 0 to decide whether
parallel fan-out is safe. Each backend is fail-open: any subprocess
error, parse failure, or missing dependency returns a degraded
zero-valued field rather than raising. The resolver then clamps to
the safe ``WAVE_FLOOR`` per :func:`config.concurrency.resolve_wave_cap`.

Hexagonal placement (D-139-09)
------------------------------

This module lives under ``ai_engineering.adapters.host`` -- the outer
adapter ring. It imports :class:`HostProbe` from
:mod:`ai_engineering.config.concurrency` (single-source-of-truth shape)
and emits framework events via :mod:`ai_engineering.state.observability`,
but the inner ring (``config`` / ``state``) does NOT import from here.
The architecture test ``tests/architecture/test_layer_isolation.py``
enforces the direction of the dependency graph.

Platform support
----------------

* darwin: ``vm_stat`` (free pages times page size), ``sysctl hw.memsize``,
  ``sysctl hw.ncpu``, ``sysctl vm.swapusage``. macOS-specific so
  ``ok_to_dispatch`` aligns with the kernel-panic trigger the spec
  closes (WindowServer watchdog + memory compressor 100 % under fan-out).
* linux: ``/proc/meminfo`` (``MemFree`` + ``Buffers`` + ``Cached``
  for free; ``MemAvailable`` for pressure proxy), ``os.cpu_count()``,
  ``/proc/swaps``. All reads are best-effort; missing files / bad
  parses degrade to zeros.
* win32: uses ``psutil`` if importable; falls back to
  ``os.cpu_count()`` + zero RAM/pressure when ``psutil`` is absent.
  Windows is a secondary surface for the framework so the degraded
  path is acceptable.

Each subprocess call carries a 1-second timeout so a hung helper can't
block Phase 0 dispatch -- the fail-open contract turns the timeout
into a degraded probe rather than a hard error.
"""

from __future__ import annotations

import contextlib
import os
import re
import subprocess
import sys
from pathlib import Path

from ai_engineering.config.concurrency import HostProbe

# Subprocess timeout for every helper invocation. The probe is on the
# Phase 0 critical path, so a hung helper must NOT block fan-out: any
# timeout collapses to a degraded snapshot via the fail-open contract.
_SUBPROCESS_TIMEOUT_SEC: float = 1.0

# Conversion constants. Kept local to keep the module self-contained;
# upstream callers consume integer gibibytes only.
_BYTES_PER_GIB: int = 1024 * 1024 * 1024
_KIB_PER_GIB: int = 1024 * 1024

# /proc paths -- declared at module scope so the test suite can patch
# them with fixtures without monkey-patching the os module.
_PROC_MEMINFO = Path("/proc/meminfo")
_PROC_SWAPS = Path("/proc/swaps")


def probe() -> HostProbe:
    """Return a :class:`HostProbe` for the current platform.

    Dispatch matrix
    ---------------

    * ``sys.platform == "darwin"`` → :func:`_probe_darwin`
    * ``sys.platform == "linux"`` → :func:`_probe_linux`
    * ``sys.platform == "win32"`` → :func:`_probe_windows`
    * anything else → degraded probe (``cores`` from
      :func:`os.cpu_count`, everything else 0).

    Any backend exception escapes as a zero-valued :class:`HostProbe`
    so the orchestrator clamps to ``WAVE_FLOOR`` instead of crashing.
    """
    platform = sys.platform
    try:
        if platform == "darwin":
            return _probe_darwin()
        if platform == "linux":
            return _probe_linux()
        if platform == "win32":
            return _probe_windows()
    except Exception:  # fail-open contract; any error degrades
        return _degraded_probe(platform)
    return _degraded_probe("unknown")


def _degraded_probe(platform: str) -> HostProbe:
    """Build a zero-valued probe with the platform tag preserved.

    Used as the universal fallback whenever a backend raises or the
    runtime platform is not one we have an adapter for. ``cores`` is
    still populated from :func:`os.cpu_count` because that call is
    platform-agnostic and cheap; everything else is zero so the resolver
    in :mod:`ai_engineering.config.concurrency` collapses the wave cap
    to the safe floor.
    """
    return HostProbe(
        cores=os.cpu_count() or 0,
        free_ram_gb=0,
        pressure_pct=0,
        swap_used_pct=0,
        platform=platform,
    )


def _run_subprocess(args: list[str]) -> str:
    """Run a helper command and return its stdout, or ``""`` on failure.

    Centralises the 1-second timeout and the fail-open contract so each
    backend can compose helpers without repeating the boilerplate. Every
    branch (``FileNotFoundError`` for missing binary, ``TimeoutExpired``,
    ``CalledProcessError`` for non-zero exit) collapses to an empty
    string -- the caller treats an empty result as "unknown" and the
    field stays at zero.
    """
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT_SEC,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout or ""


# ---------------------------------------------------------------------------
# darwin adapter
# ---------------------------------------------------------------------------


def _probe_darwin() -> HostProbe:
    """Build a :class:`HostProbe` from macOS helpers.

    Combines four subprocess calls (``vm_stat``, ``sysctl hw.memsize``,
    ``sysctl hw.ncpu``, ``sysctl vm.swapusage``) into a single probe.
    Any individual failure degrades that field to zero; the probe as a
    whole still returns rather than raising so the caller can clamp.
    """
    cores = _darwin_cores()
    total_bytes = _darwin_total_memory_bytes()
    free_bytes = _darwin_free_memory_bytes()
    free_ram_gb = free_bytes // _BYTES_PER_GIB if free_bytes else 0
    pressure_pct = _darwin_pressure_pct(total_bytes, free_bytes)
    swap_used_pct = _darwin_swap_used_pct()
    return HostProbe(
        cores=cores,
        free_ram_gb=free_ram_gb,
        pressure_pct=pressure_pct,
        swap_used_pct=swap_used_pct,
        platform="darwin",
    )


def _darwin_cores() -> int:
    raw = _run_subprocess(["sysctl", "-n", "hw.ncpu"]).strip()
    if raw:
        with contextlib.suppress(ValueError):
            return max(0, int(raw))
    return os.cpu_count() or 0


def _darwin_total_memory_bytes() -> int:
    raw = _run_subprocess(["sysctl", "-n", "hw.memsize"]).strip()
    if not raw:
        return 0
    with contextlib.suppress(ValueError):
        return max(0, int(raw))
    return 0


def _darwin_free_memory_bytes() -> int:
    """Compute free RAM in bytes from ``vm_stat`` output.

    The first ``vm_stat`` line is "Mach Virtual Memory Statistics:
    (page size of N bytes)". Subsequent lines look like
    ``Pages free:     12345.``. Free RAM is the page size times the
    sum of ``Pages free`` + ``Pages inactive`` + ``Pages speculative``,
    matching how Activity Monitor reports "Memory Free".
    """
    stdout = _run_subprocess(["vm_stat"])
    if not stdout:
        return 0
    lines = stdout.splitlines()
    if not lines:
        return 0
    page_size = _darwin_parse_page_size(lines[0])
    if page_size <= 0:
        return 0
    free_pages = _darwin_parse_pages(lines, "Pages free")
    inactive_pages = _darwin_parse_pages(lines, "Pages inactive")
    speculative_pages = _darwin_parse_pages(lines, "Pages speculative")
    total_pages = free_pages + inactive_pages + speculative_pages
    return total_pages * page_size


def _darwin_parse_page_size(header: str) -> int:
    match = re.search(r"page size of (\d+) bytes", header)
    if not match:
        return 0
    with contextlib.suppress(ValueError):
        return int(match.group(1))
    return 0


def _darwin_parse_pages(lines: list[str], label: str) -> int:
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith(label):
            continue
        # "Pages free:                       12345."
        # → "12345." → strip trailing dot, parse.
        value = stripped.split(":", 1)[-1].strip().rstrip(".")
        with contextlib.suppress(ValueError):
            return int(value)
    return 0


def _darwin_pressure_pct(total_bytes: int, free_bytes: int) -> int:
    """Estimate memory pressure as ``(total - free) / total * 100``.

    macOS exposes a richer ``memory_pressure`` binary but it requires
    root for some metrics and is slower; the heuristic above mirrors
    the linux ``MemAvailable``-derived proxy so the cross-platform
    comparison stays consistent. Returns 0 when ``total_bytes`` is
    unknown so the resolver can't be tricked into a serial wave cap by
    a degraded probe.
    """
    if total_bytes <= 0:
        return 0
    used_bytes = max(0, total_bytes - free_bytes)
    pct = int((used_bytes * 100) // total_bytes)
    return min(100, max(0, pct))


def _darwin_swap_used_pct() -> int:
    """Parse swap usage from ``sysctl vm.swapusage`` output.

    Output looks like ``total = 2048.00M  used = 512.00M  free = 1536.00M``.
    Returns ``0`` when total is zero or unparseable -- swap thrash is
    the only failure mode we care about, and zero usage is safe.
    """
    raw = _run_subprocess(["sysctl", "-n", "vm.swapusage"])
    if not raw:
        return 0
    total = _darwin_parse_swap_value(raw, "total")
    used = _darwin_parse_swap_value(raw, "used")
    if total <= 0:
        return 0
    pct = int((used * 100) // total)
    return min(100, max(0, pct))


def _darwin_parse_swap_value(text: str, label: str) -> int:
    """Parse "label = NUMBER<unit>" out of a vm.swapusage line.

    Units are M / G / K -- the sysctl output is always in mebibytes in
    practice but parse defensively so unit drift in a future macOS
    release doesn't make the probe lie about pressure. Returns 0 when
    the label is absent or the number is unparseable.
    """
    match = re.search(rf"{re.escape(label)}\s*=\s*([0-9.]+)([KMGT]?)", text)
    if not match:
        return 0
    try:
        value = float(match.group(1))
    except ValueError:
        return 0
    unit = match.group(2)
    multiplier = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}.get(unit, 1)
    return int(value * multiplier)


# ---------------------------------------------------------------------------
# linux adapter
# ---------------------------------------------------------------------------


def _probe_linux() -> HostProbe:
    """Build a :class:`HostProbe` from ``/proc`` reads.

    ``/proc/meminfo`` provides ``MemFree``, ``Buffers``, ``Cached``,
    ``MemTotal``, ``MemAvailable``. ``MemAvailable`` is the most
    accurate "pressure" proxy in recent kernels (it accounts for
    reclaimable slabs); we derive pressure as
    ``1 - MemAvailable / MemTotal``. Free RAM is the sum of the three
    pages that the kernel would happily hand to a fresh allocation
    request without swapping.
    """
    meminfo = _linux_parse_meminfo()
    cores = os.cpu_count() or 0
    mem_total_kib = meminfo.get("MemTotal", 0)
    mem_free_kib = meminfo.get("MemFree", 0)
    buffers_kib = meminfo.get("Buffers", 0)
    cached_kib = meminfo.get("Cached", 0)
    mem_available_kib = meminfo.get("MemAvailable", mem_free_kib + buffers_kib + cached_kib)

    free_ram_gb = (mem_free_kib + buffers_kib + cached_kib) // _KIB_PER_GIB
    pressure_pct = _linux_pressure_pct(mem_total_kib, mem_available_kib)
    swap_used_pct = _linux_swap_used_pct()
    return HostProbe(
        cores=cores,
        free_ram_gb=max(0, free_ram_gb),
        pressure_pct=pressure_pct,
        swap_used_pct=swap_used_pct,
        platform="linux",
    )


def _linux_parse_meminfo() -> dict[str, int]:
    """Return a dict of MemKey → kibibyte values from /proc/meminfo.

    Missing file, permission error, or malformed line collapses to an
    empty dict so the linux probe degrades to the zero-RAM safe path.
    Each numeric value is parsed as integer kibibytes (the suffix is
    always ``kB`` per kernel source -- we strip it without validating
    case so a future kernel that lowercases the suffix still works).
    """
    if not _PROC_MEMINFO.exists():
        return {}
    try:
        text = _PROC_MEMINFO.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    out: dict[str, int] = {}
    for raw_line in text.splitlines():
        if ":" not in raw_line:
            continue
        key, _, rest = raw_line.partition(":")
        rest = rest.strip()
        # Drop the unit suffix ("kB") if present; the kernel emits KiB.
        parts = rest.split()
        if not parts:
            continue
        with contextlib.suppress(ValueError):
            out[key.strip()] = int(parts[0])
    return out


def _linux_pressure_pct(total_kib: int, available_kib: int) -> int:
    if total_kib <= 0:
        return 0
    used_kib = max(0, total_kib - available_kib)
    pct = int((used_kib * 100) // total_kib)
    return min(100, max(0, pct))


def _linux_swap_used_pct() -> int:
    """Compute swap utilisation as the ratio of Used/Size across all swaps.

    ``/proc/swaps`` has a header line plus one row per swap area:
    ``Filename    Type    Size    Used    Priority``. We sum ``Size``
    and ``Used`` across rows and divide. Missing file collapses to 0
    (no swap, no thrash possible).
    """
    if not _PROC_SWAPS.exists():
        return 0
    try:
        text = _PROC_SWAPS.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    total_size = 0
    total_used = 0
    for raw_line in text.splitlines()[1:]:  # skip header
        parts = raw_line.split()
        if len(parts) < 4:
            continue
        with contextlib.suppress(ValueError):
            total_size += int(parts[2])
            total_used += int(parts[3])
    if total_size <= 0:
        return 0
    pct = int((total_used * 100) // total_size)
    return min(100, max(0, pct))


# ---------------------------------------------------------------------------
# windows adapter
# ---------------------------------------------------------------------------


def _probe_windows() -> HostProbe:
    """Build a :class:`HostProbe` on Windows.

    Uses ``psutil`` when importable for full coverage; degrades to
    ``os.cpu_count`` with zero RAM/pressure/swap when psutil is absent.
    Windows is a secondary surface for the framework, so the degraded
    path is acceptable -- the resolver will clamp to ``WAVE_FLOOR``.
    """
    cores = os.cpu_count() or 0
    free_ram_gb = 0
    pressure_pct = 0
    swap_used_pct = 0

    try:
        import importlib

        psutil = importlib.import_module("psutil")
    except ImportError:
        return HostProbe(
            cores=cores,
            free_ram_gb=0,
            pressure_pct=0,
            swap_used_pct=0,
            platform="win32",
        )

    with contextlib.suppress(Exception):
        vm = psutil.virtual_memory()
        free_ram_gb = int(getattr(vm, "available", 0) // _BYTES_PER_GIB)
        pressure_pct = int(getattr(vm, "percent", 0))

    with contextlib.suppress(Exception):
        sw = psutil.swap_memory()
        swap_used_pct = int(getattr(sw, "percent", 0))

    return HostProbe(
        cores=cores,
        free_ram_gb=max(0, free_ram_gb),
        pressure_pct=min(100, max(0, pressure_pct)),
        swap_used_pct=min(100, max(0, swap_used_pct)),
        platform="win32",
    )


__all__ = ["HostProbe", "probe"]
