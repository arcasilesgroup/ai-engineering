"""Console output utilities with cross-platform color support."""

from __future__ import annotations

import os
import sys


def _supports_color() -> bool:
    """Check if the terminal supports ANSI colors."""
    # Check NO_COLOR environment variable (https://no-color.org/)
    if os.environ.get("NO_COLOR"):
        return False

    # Check FORCE_COLOR environment variable
    if os.environ.get("FORCE_COLOR"):
        return True

    # Check if stdout is a TTY
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False

    # Windows-specific checks
    if sys.platform == "win32":
        # Windows 10+ supports ANSI escape codes in Windows Terminal and newer cmd.exe
        # Enable virtual terminal processing
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # Enable ANSI escape sequences on Windows
            kernel32.SetConsoleMode(
                kernel32.GetStdHandle(-11),  # STD_OUTPUT_HANDLE
                0x0001 | 0x0002 | 0x0004,  # ENABLE_PROCESSED_OUTPUT | ENABLE_WRAP_AT_EOL_OUTPUT | ENABLE_VIRTUAL_TERMINAL_PROCESSING
            )
            return True
        except Exception:
            # Check for known terminals that support color
            return os.environ.get("TERM_PROGRAM") in ("vscode", "Windows Terminal") or \
                   os.environ.get("WT_SESSION") is not None

    # Unix-like systems generally support colors
    return True


# Detect color support once at import time
_COLOR_SUPPORTED = _supports_color()


class Colors:
    """ANSI color codes with automatic fallback for unsupported terminals."""

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled and _COLOR_SUPPORTED

    @property
    def cyan(self) -> str:
        return "\033[96m" if self._enabled else ""

    @property
    def green(self) -> str:
        return "\033[92m" if self._enabled else ""

    @property
    def yellow(self) -> str:
        return "\033[93m" if self._enabled else ""

    @property
    def red(self) -> str:
        return "\033[91m" if self._enabled else ""

    @property
    def magenta(self) -> str:
        return "\033[95m" if self._enabled else ""

    @property
    def gray(self) -> str:
        return "\033[90m" if self._enabled else ""

    @property
    def bold(self) -> str:
        return "\033[1m" if self._enabled else ""

    @property
    def reset(self) -> str:
        return "\033[0m" if self._enabled else ""


# Global colors instance
colors = Colors()


def success(message: str) -> str:
    """Format a success message."""
    return f"{colors.green}✅ {message}{colors.reset}"


def error(message: str) -> str:
    """Format an error message."""
    return f"{colors.red}❌ {message}{colors.reset}"


def warning(message: str) -> str:
    """Format a warning message."""
    return f"{colors.yellow}⚠️  {message}{colors.reset}"


def info(message: str) -> str:
    """Format an info message."""
    return f"{colors.cyan}ℹ️  {message}{colors.reset}"


def dim(message: str) -> str:
    """Format a dimmed/gray message."""
    return f"{colors.gray}{message}{colors.reset}"


def header(message: str) -> str:
    """Format a header message."""
    return f"{colors.cyan}{colors.bold}{message}{colors.reset}"
