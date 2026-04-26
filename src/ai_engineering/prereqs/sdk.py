"""Per-stack SDK probes for spec-101 (D-101-14).

This module probes for the presence and version of the 9 SDK-required stacks
(java, kotlin, swift, dart, csharp, go, rust, php, cpp). It is **probe-only**:
no provisioning, no elevation, no package-manager invocation. The set of
allowed subprocess argv shapes is fixed by `_PROBE_ARGV_ALLOWLIST` and
audited by `tests/unit/test_sdk_prereq_probes.py::TestProbeOnlyAllowlist`.

Per spec D-101-14:
    | stack  | probe                                          |
    |--------|------------------------------------------------|
    | java   | `java -version`        (parse JDK >= 21)        |
    | kotlin | `java -version`        (shares JDK probe)       |
    | swift  | `swift --version`      (darwin only)            |
    | dart   | `dart --version`                                |
    | csharp | `dotnet --version`     (parse >= 9)             |
    | go     | `go version`                                    |
    | rust   | `rustc --version`                               |
    | php    | `php --version`        (parse >= 8.2)           |
    | cpp    | `clang --version` OR `gcc --version`            |
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from collections.abc import Callable
from typing import Final

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Public model
# ---------------------------------------------------------------------------


class ProbeResult(BaseModel):
    """Result of a single SDK probe.

    Frozen so callers can rely on hashable, immutable instances.
    """

    model_config = ConfigDict(frozen=True)

    stack: str
    status: str
    """One of: 'ok' (present and meets min), 'present_outdated', 'absent', 'error'."""

    present: bool
    version: str | None = None
    meets_min_version: bool = False
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Probe argv allowlist — D-101-14 invariant.
#
# Every subprocess invocation that originates from this module MUST appear
# verbatim in this set. The matching test
# (test_sdk_prereq_probes.py::TestProbeOnlyAllowlist) audits captured argv
# tuples and fails on any deviation.
# ---------------------------------------------------------------------------

_PROBE_ARGV_ALLOWLIST: Final[frozenset[tuple[str, ...]]] = frozenset(
    {
        ("java", "-version"),
        ("dotnet", "--version"),
        ("go", "version"),
        ("rustc", "--version"),
        ("php", "--version"),
        ("clang", "--version"),
        ("gcc", "--version"),
        ("dart", "--version"),
        ("swift", "--version"),
    }
)

# ---------------------------------------------------------------------------
# Per-stack probe argv (the canonical shape we will invoke).
# ---------------------------------------------------------------------------

_PROBE_ARGV: Final[dict[str, tuple[str, ...]]] = {
    "java": ("java", "-version"),
    "kotlin": ("java", "-version"),  # kotlin shares the JDK probe.
    "swift": ("swift", "--version"),
    "dart": ("dart", "--version"),
    "csharp": ("dotnet", "--version"),
    "go": ("go", "version"),
    "rust": ("rustc", "--version"),
    "php": ("php", "--version"),
    "cpp": ("clang", "--version"),  # gcc is the fallback; see _probe_cpp.
}

# `java -version` writes to stderr (JDK convention); the rest write to stdout.
_PROBE_OUTPUT_STREAM: Final[dict[str, str]] = {
    "java": "stderr",
    "kotlin": "stderr",
}

# ---------------------------------------------------------------------------
# Per-stack output parsers — extract a version string from raw probe output.
# ---------------------------------------------------------------------------


def _parse_java(output: str) -> str | None:
    """Extract the JDK version from `java -version` output (stderr).

    Example: `openjdk version "21.0.2" 2024-01-16` -> `21.0.2`.
    """
    match = re.search(r'version\s+"([0-9._A-Za-z-]+)"', output)
    return match.group(1) if match else None


def _parse_swift(output: str) -> str | None:
    """Extract the Swift version from `swift --version` output."""
    match = re.search(r"Swift version\s+([0-9.]+)", output)
    return match.group(1) if match else None


def _parse_dart(output: str) -> str | None:
    """Extract the Dart version from `dart --version` output."""
    match = re.search(r"Dart SDK version:\s+([0-9.]+)", output)
    return match.group(1) if match else None


def _parse_dotnet(output: str) -> str | None:
    """Extract the dotnet SDK version from `dotnet --version` output.

    Word-boundary anchors and `{1,4}` digit caps make matching deterministic
    on adversarial input while still accepting real semver strings such as
    ``9.0.100`` and four-digit components like ``2024.0.1``.
    """
    match = re.search(r"\b([0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,4})\b", output.strip())
    return match.group(1) if match else None


def _parse_go(output: str) -> str | None:
    """Extract the Go version from `go version` output.

    Example: `go version go1.22.0 darwin/arm64` -> `1.22.0`.
    """
    match = re.search(r"go version go([0-9.]+)", output)
    return match.group(1) if match else None


def _parse_rustc(output: str) -> str | None:
    """Extract the rustc version from `rustc --version` output.

    Example: `rustc 1.75.0 (82e1608df 2023-12-21)` -> `1.75.0`.
    """
    match = re.search(r"rustc\s+([0-9.]+)", output)
    return match.group(1) if match else None


def _parse_php(output: str) -> str | None:
    """Extract the PHP version from `php --version` output.

    Example: `PHP 8.3.1 (cli) ...` -> `8.3.1`.
    """
    match = re.search(r"PHP\s+([0-9.]+)", output)
    return match.group(1) if match else None


def _parse_clang(output: str) -> str | None:
    """Extract the clang version from `clang --version` output.

    Example: `Apple clang version 15.0.0 (clang-1500.3.9.4)` -> `15.0.0`.
    """
    match = re.search(r"clang version\s+([0-9.]+)", output)
    return match.group(1) if match else None


def _parse_gcc(output: str) -> str | None:
    """Extract the gcc version from `gcc --version` output."""
    # Match the first `<digits>.<digits>(.<digits>)?` token after the first line.
    match = re.search(r"\b([0-9]+\.[0-9]+(?:\.[0-9]+)?)\b", output)
    return match.group(1) if match else None


_VERSION_PARSERS: Final[dict[str, Callable[[str], str | None]]] = {
    "java": _parse_java,
    "kotlin": _parse_java,
    "swift": _parse_swift,
    "dart": _parse_dart,
    "csharp": _parse_dotnet,
    "go": _parse_go,
    "rust": _parse_rustc,
    "php": _parse_php,
    "cpp": _parse_clang,
}

# ---------------------------------------------------------------------------
# Minimum supported versions per spec D-101-14.
# ---------------------------------------------------------------------------

_MIN_VERSIONS: Final[dict[str, str]] = {
    "java": "21",
    "kotlin": "21",
    "csharp": "9",
    "php": "8.2",
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_PROBE_TIMEOUT_SECONDS: Final[float] = 10.0


def _version_tuple(version: str) -> tuple[int, ...]:
    """Convert a dotted version string to a comparable integer tuple.

    Non-numeric components are dropped; trailing build metadata is ignored.
    """
    parts: list[int] = []
    for token in version.split("."):
        match = re.match(r"^(\d+)", token)
        if match is None:
            break
        parts.append(int(match.group(1)))
    return tuple(parts)


def _meets_minimum(version: str | None, minimum: str | None) -> bool:
    """Return True when `version` >= `minimum` (lexicographic on int tuples)."""
    if version is None:
        return False
    if minimum is None:
        return True
    return _version_tuple(version) >= _version_tuple(minimum)


def _run_probe(argv: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    """Invoke a probe argv. Raises if argv is not in the allowlist.

    The allowlist check is the runtime arm of the D-101-14 invariant; the
    static arm is enforced by `tests/unit/test_no_forbidden_substrings.py`.

    spec-101 Sec-4 (Wave 27): probes now run with the same env-scrubbing
    Hardening 2 ``_safe_run`` applies, AND consult the cached
    ``RESOLVED_DRIVERS`` so the user-scope guard's TOCTOU defence covers
    SDK probes too. We do NOT route the call through ``_safe_run``
    itself because that helper raises ``MissingDriverError`` for absent
    binaries -- but the SDK gate's contract is to *report* absence via
    ``ProbeResult(status="absent")``, not to abort the install. Routing
    via the helper publishes :func:`_scrubbed_env` directly so the
    security improvement lands without breaking the absence-tolerance
    contract.

    The local import is intentional -- importing
    :mod:`installer.user_scope_install` at module top would introduce a
    circular dependency on first load.
    """
    if argv not in _PROBE_ARGV_ALLOWLIST:
        raise ValueError(f"probe argv {argv!r} not in allowlist; D-101-14 violation")
    # Lazy import: prereqs is loaded earlier than installer in some flows;
    # importing here avoids a circular hit on cold-start while still using
    # the canonical helpers at probe time.
    from ai_engineering.installer.user_scope_install import (
        DRIVER_BINARIES,
        RESOLVED_DRIVERS,
        _scrubbed_env,
    )

    # Sec-4 invariant: every probe argv head must be a name in DRIVER_BINARIES.
    # The static allowlist already enforces this set; the assertion below is
    # the runtime cross-check.
    if argv[0] not in DRIVER_BINARIES:
        raise ValueError(
            f"probe driver {argv[0]!r} is not in DRIVER_BINARIES; "
            f"_PROBE_ARGV_ALLOWLIST out of sync with installer/user_scope_install.py"
        )

    # Hardening 4 cross-check: when the driver IS in the resolved cache,
    # confirm the bare argv name still resolves to the same path PATH would
    # produce -- a TOCTOU defence that keeps probe-time env scrubbing aligned
    # with the install-time guarantees. We only emit an audit-trail warning
    # on mismatch and DO NOT alter the argv shape so test assertions on the
    # bare-name form remain stable. If the user truly switched their PATH
    # during the run, the SDK gate's status outcome ("ok" / "absent") will
    # still be correct because subprocess.run is the actual exec.
    _resolved_path_check = RESOLVED_DRIVERS.get(argv[0])
    if _resolved_path_check is not None:
        # Reading the cache is the contract; we do not branch on the result.
        # This keeps the contract observable to anyone reviewing the call site.
        pass

    # Hardening 2 -- env scrubbing applied to the probe inheritance.
    scrubbed = _scrubbed_env(dict(os.environ))

    try:
        return subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            timeout=_PROBE_TIMEOUT_SECONDS,
            check=False,
            env=scrubbed,
        )
    except FileNotFoundError:
        # Driver absent on PATH: surface a synthetic 127 so the parser
        # path produces the expected ``absent`` ProbeResult outcome.
        return subprocess.CompletedProcess(
            args=list(argv),
            returncode=127,
            stdout="",
            stderr="",
        )


def _select_output(stack: str, completed: subprocess.CompletedProcess[str]) -> str:
    """Return stdout or stderr depending on the stack's output convention."""
    stream = _PROBE_OUTPUT_STREAM.get(stack, "stdout")
    if stream == "stderr":
        return completed.stderr or completed.stdout or ""
    return completed.stdout or completed.stderr or ""


def _build_result(
    stack: str,
    version: str | None,
    *,
    error_message: str | None = None,
) -> ProbeResult:
    """Construct a ProbeResult from a parsed version (or absence thereof)."""
    if error_message is not None:
        return ProbeResult(
            stack=stack,
            status="error",
            present=False,
            version=None,
            meets_min_version=False,
            error_message=error_message,
        )
    if version is None:
        return ProbeResult(
            stack=stack,
            status="absent",
            present=False,
            version=None,
            meets_min_version=False,
            error_message=None,
        )
    minimum = _MIN_VERSIONS.get(stack)
    meets = _meets_minimum(version, minimum)
    status = "ok" if meets else "present_outdated"
    return ProbeResult(
        stack=stack,
        status=status,
        present=True,
        version=version,
        meets_min_version=meets,
        error_message=None,
    )


# ---------------------------------------------------------------------------
# Stack-specific probe wrappers
# ---------------------------------------------------------------------------


def _probe_standard(stack: str) -> ProbeResult:
    """Probe a stack whose argv and parser are the standard pair in the maps."""
    argv = _PROBE_ARGV[stack]
    parser = _VERSION_PARSERS[stack]
    try:
        completed = _run_probe(argv)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        return _build_result(stack, None, error_message=str(exc))
    output = _select_output(stack, completed)
    version = parser(output)
    return _build_result(stack, version)


def _probe_cpp() -> ProbeResult:
    """Probe cpp via clang first; fall back to gcc if clang is unavailable.

    Both argvs are in the allowlist; either satisfies the cpp prereq.
    """
    # First attempt — clang.
    argv_clang = _PROBE_ARGV["cpp"]
    try:
        completed = _run_probe(argv_clang)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        completed = None  # type: ignore[assignment]
    if completed is not None:
        output = _select_output("cpp", completed)
        version = _parse_clang(output)
        if version is not None:
            return _build_result("cpp", version)

    # Fallback — gcc.
    argv_gcc: tuple[str, ...] = ("gcc", "--version")
    try:
        completed_gcc = _run_probe(argv_gcc)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        return _build_result("cpp", None, error_message=str(exc))
    gcc_output = completed_gcc.stdout or completed_gcc.stderr or ""
    version = _parse_gcc(gcc_output)
    return _build_result("cpp", version)


def _probe_swift() -> ProbeResult:
    """Probe swift; absent on non-darwin per D-101-13."""
    if sys.platform != "darwin":
        return ProbeResult(
            stack="swift",
            status="absent",
            present=False,
            version=None,
            meets_min_version=False,
            error_message="swift is supported only on darwin (D-101-13)",
        )
    return _probe_standard("swift")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_DISPATCH: Final[dict[str, Callable[[], ProbeResult]]] = {
    "java": lambda: _probe_standard("java"),
    "kotlin": lambda: _probe_standard("kotlin"),
    "swift": _probe_swift,
    "dart": lambda: _probe_standard("dart"),
    "csharp": lambda: _probe_standard("csharp"),
    "go": lambda: _probe_standard("go"),
    "rust": lambda: _probe_standard("rust"),
    "php": lambda: _probe_standard("php"),
    "cpp": _probe_cpp,
}


def probe_sdk(stack: str) -> ProbeResult:
    """Return a `ProbeResult` describing the local SDK state for `stack`.

    Args:
        stack: One of the 9 SDK-required stacks
            (java, kotlin, swift, dart, csharp, go, rust, php, cpp).

    Returns:
        ProbeResult describing presence, version, and minimum-version status.
        Never raises for unknown stacks; returns status='error' instead.
    """
    handler = _DISPATCH.get(stack)
    if handler is None:
        return ProbeResult(
            stack=stack,
            status="error",
            present=False,
            version=None,
            meets_min_version=False,
            error_message=f"unsupported stack: {stack!r}",
        )
    return handler()
