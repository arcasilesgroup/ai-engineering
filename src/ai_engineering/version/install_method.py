"""Detect how ai-engineering was installed (spec version-update-notice).

``detect`` inspects the running interpreter's prefix and the package file
location to choose the correct upgrade command. The heuristics are pure and
accept injected ``prefix`` / ``package_file`` paths so they are deterministic
under test. The return is always ``(method, upgrade_argv)`` where
``upgrade_argv`` is a ready-to-run command list — never a half-resolved guess.

Detection order (most specific first):

1. **pipx** — package lives under a ``pipx/venvs`` tree.
2. **uv tool** — package lives under a ``uv/tools`` tree.
3. **brew** — package lives under a Homebrew ``Cellar`` tree.
4. **pip** (default) — upgrade via this interpreter's pip.
"""

from __future__ import annotations

import sys
from pathlib import Path

import ai_engineering

PACKAGE_NAME = "ai-engineering"


def _norm_parts(path: Path) -> list[str]:
    """Return lowercase path segments, splitting on both separators.

    Windows pipx/uv paths may arrive with backslashes even on POSIX, so we
    normalise both separators before matching to keep detection cross-OS.
    """
    text = str(path).replace("\\", "/").lower()
    return [part for part in text.split("/") if part]


def _has_adjacent(parts: list[str], first: str, second: str) -> bool:
    """Return True when ``first`` is immediately followed by ``second``."""
    return any(parts[i] == first and parts[i + 1] == second for i in range(len(parts) - 1))


def detect(
    *,
    prefix: Path | None = None,
    package_file: Path | None = None,
) -> tuple[str, list[str]]:
    """Return ``(method, upgrade_argv)`` for the current install.

    Args:
        prefix: Interpreter prefix to inspect. Defaults to ``sys.prefix``.
        package_file: Path to the installed ``ai_engineering`` package.
            Defaults to ``ai_engineering.__file__``.
    """
    prefix = prefix if prefix is not None else Path(sys.prefix)
    package_file = package_file if package_file is not None else Path(ai_engineering.__file__)

    # Inspect both the prefix and the package location: an editable / tool
    # install may place the package outside the interpreter prefix.
    parts = _norm_parts(prefix) + _norm_parts(package_file)

    if _has_adjacent(parts, "pipx", "venvs"):
        return "pipx", ["pipx", "upgrade", PACKAGE_NAME]

    if _has_adjacent(parts, "uv", "tools"):
        return "uv tool", ["uv", "tool", "upgrade", PACKAGE_NAME]

    if "cellar" in parts:
        return "brew", ["brew", "upgrade", PACKAGE_NAME]

    return "pip", [sys.executable, "-m", "pip", "install", "-U", PACKAGE_NAME]
