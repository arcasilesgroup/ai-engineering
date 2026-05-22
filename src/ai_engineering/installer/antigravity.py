"""Antigravity runtime diagnostics.

The workspace surface is installed through regular template maps. The CLI
runtime is optional for users who only use the Antigravity app, so this module
keeps `agy` detection as a small fail-soft adapter rather than a hard install
gate.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgyProbeResult:
    """Result of probing the Antigravity CLI runtime."""

    available: bool
    binary: str | None
    version: str | None
    reason: str


Which = Callable[[str], str | None]


def find_agy_binary(*, which: Which = shutil.which) -> str | None:
    """Return the first Antigravity CLI binary on PATH, if any."""
    return which("agy") or which("agy.exe")


def probe_agy_cli(
    *,
    which: Which = shutil.which,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    timeout: float = 3.0,
) -> AgyProbeResult:
    """Detect `agy`/`agy.exe` and capture its version when available.

    Missing or failing binaries degrade to ``available=False`` rather than
    raising. This lets project installs support the Antigravity app even when
    the terminal runtime is not installed on the operator machine.
    """
    binary = find_agy_binary(which=which)
    if binary is None:
        return AgyProbeResult(
            available=False,
            binary=None,
            version=None,
            reason="Antigravity CLI binary 'agy' was not found on PATH.",
        )

    try:
        completed = run(
            [binary, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return AgyProbeResult(
            available=False,
            binary=binary,
            version=None,
            reason=f"Antigravity CLI probe failed: {exc}",
        )

    output = (completed.stdout or completed.stderr or "").strip()
    if completed.returncode != 0:
        return AgyProbeResult(
            available=False,
            binary=binary,
            version=output or None,
            reason=f"Antigravity CLI exited with status {completed.returncode}.",
        )

    return AgyProbeResult(
        available=True,
        binary=binary,
        version=output or None,
        reason="Antigravity CLI is available.",
    )


__all__ = ["AgyProbeResult", "find_agy_binary", "probe_agy_cli"]
