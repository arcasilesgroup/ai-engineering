"""Human-facing CLI output module.

Provides branded Rich console output for the ai-engineering CLI.
All messaging goes to stderr; data goes to stdout (CLIG guideline).
Respects NO_COLOR, TERM=dumb, and TTY detection.
"""

from __future__ import annotations

import os
import re
import sys
from functools import lru_cache

from rich.console import Console
from rich.rule import Rule
from rich.theme import Theme

from ai_engineering.__version__ import __version__

# Brand colour extracted from .github/assets/banner-dark.svg
BRAND_TEAL = "#00D4AA"

THEME = {
    "brand": f"bold {BRAND_TEAL}",
    "brand.dim": f"dim {BRAND_TEAL}",
    "success": "bold green",
    "warning": "bold yellow",
    "error": "bold red",
    "info": "bold blue",
    "muted": "dim",
    "path": f"{BRAND_TEAL} underline",
    "key": "bold",
}

_MARKUP_RE = re.compile(r"\[/?[^\]]*\]")
"""Regex to strip Rich markup tags for plain-text fallback."""


def _is_no_color() -> bool:
    """Check if colour output should be suppressed."""
    return "NO_COLOR" in os.environ or os.environ.get("TERM") == "dumb"


@lru_cache(maxsize=1)
def get_console() -> Console:
    """Rich Console for messaging on stderr.

    Respects NO_COLOR, TERM=dumb, and TTY detection.
    """
    no_color = _is_no_color()
    return Console(
        stderr=True,
        theme=Theme(THEME),
        no_color=no_color,
        highlight=False,
    )


def get_stdout_console() -> Console:
    """Console for data output to stdout (no colours when piped)."""
    no_color = _is_no_color()
    return Console(
        theme=Theme(THEME),
        no_color=no_color,
        highlight=False,
    )


def _safe_print(msg: str) -> None:
    """Print to stderr via Rich, falling back to plain text on failure.

    Rich 14.x has a bug where ``importlib.import_module`` fails for
    hyphenated unicode data modules (e.g. ``unicode16-0-0``) on some
    Python 3.12 / platform combinations.  When this happens, strip
    Rich markup and write plain text to stderr.
    """
    try:
        get_console().print(msg)
    except (ImportError, ModuleNotFoundError):
        plain = _MARKUP_RE.sub("", msg)
        sys.stderr.write(plain + "\n")


# ── Logo ──────────────────────────────────────────────────────────


def show_logo() -> None:
    """Print the branded logo to stderr (TTY only).

    Design mirrors the SVG banner (``.github/assets/banner-dark.svg``):
    corner brackets, ``{ai}`` mark with teal braces, letter-spaced
    engineering text.
    """
    con = get_console()
    if not con.is_terminal:
        return
    try:
        con.print()
        con.print("  [brand.dim]┌─                                  ─┐[/brand.dim]")
        con.print(
            "      [brand]{[/brand] [bold]ai[/bold] [brand]}[/brand]"
            "   [brand]e n g i n e e r i n g[/brand]"
        )
        con.print("  [brand.dim]└─                                  ─┘[/brand.dim]")
        con.print(f"  [muted]v{__version__} · AI Governance Framework[/muted]")
        con.print()
    except (ImportError, ModuleNotFoundError):
        pass


# ── Message helpers (all write to stderr) ─────────────────────────


def success(msg: str) -> None:
    """Print a green success message to stderr."""
    _safe_print(f"[success]{msg}[/success]")


def warning(msg: str) -> None:
    """Print a yellow warning to stderr."""
    _safe_print(f"[warning]{msg}[/warning]")


def error(msg: str) -> None:
    """Print a red error message to stderr."""
    _safe_print(f"[error]{msg}[/error]")


def info(msg: str) -> None:
    """Print a blue info message to stderr."""
    _safe_print(f"[info]{msg}[/info]")


def header(title: str) -> None:
    """Print a section divider to stderr."""
    try:
        get_console().print(Rule(title, style="brand.dim"))
    except (ImportError, ModuleNotFoundError):
        sys.stderr.write(f"--- {title} ---\n")


def kv(key: str, value: object) -> None:
    """Print an aligned key-value pair to stderr."""
    _safe_print(f"  [key]{key}[/key]  {value}")


def status_line(status: str, name: str, msg: str) -> None:
    """Print a check result line to stderr.

    Args:
        status: One of 'ok', 'warn', 'fail', 'fixed'.
        name: Check name.
        msg: Detail message.
    """
    icons = {
        "ok": "[success]\u2713 PASS[/success]",
        "info": "[dim]\u00b7 SKIP[/dim]",
        "warn": "[warning]\u26a0 WARN[/warning]",
        "fail": "[error]\u2717 FAIL[/error]",
        "fixed": "[info]\U0001f527 FIXED[/info]",
    }
    icon = icons.get(status, "?")
    _safe_print(f"  {icon} [key]{name}[/key]: {msg}")


def result_header(label: str, status: str, detail: str = "") -> None:
    """Print a command result header to stderr.

    Example: ``Doctor [PASS] /path``
    """
    style = "success" if status == "PASS" else "error" if status == "FAIL" else "warning"
    suffix = f" {detail}" if detail else ""
    _safe_print(f"[key]{label}[/key] [{style}][{status}][/{style}]{suffix}")


def suggest_next(steps: list[tuple[str, str]]) -> None:
    """Print next-step suggestions to stderr.

    Args:
        steps: List of ``(command, description)`` tuples.
    """
    _safe_print("")
    _safe_print("[muted]Next steps:[/muted]")
    for command, description in steps:
        _safe_print(f"  [brand.dim]\u2192[/brand.dim] {command}  [muted]{description}[/muted]")


def file_count(label: str, count: int) -> None:
    """Print a labelled file count to stderr."""
    kv(label, f"{count} files")


def print_stdout(msg: str) -> None:
    """Write a plain-text line to stdout (for data/assertions)."""
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


# ── Dashboard primitives (observe) ───────────────────────────────


def section(title: str) -> None:
    """Print a dashboard section title to stderr."""
    _safe_print(f"\n[brand]{title}[/brand]")


def progress_bar(
    label: str,
    value: float,
    max_val: float = 100,
    threshold: float | None = None,
) -> None:
    """Print a colored progress bar with label to stderr."""
    pct = min(value / max_val * 100, 100) if max_val > 0 else 0
    bar_width = 12
    filled = round(pct / 100 * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)
    target = threshold if threshold is not None else 80
    if pct >= target:
        style = "success"
    elif pct >= 60:
        style = "warning"
    else:
        style = "error"
    _safe_print(f"  [key]{label:<20}[/key] [{style}]{bar}[/{style}] {pct:.1f}%")


def score_badge(score: int, label: str = "") -> None:
    """Print a semaphore score badge to stderr."""
    if score >= 80:
        style, icon = "success", "●"
    elif score >= 60:
        style, icon = "warning", "●"
    else:
        style, icon = "error", "●"
    prefix = f"{label} " if label else ""
    _safe_print(f"  [{style}]{icon}[/{style}] {prefix}[key]{score}/100[/key]")


def metric_table(rows: list[tuple[str, str, str]]) -> None:
    """Print aligned metric rows with status coloring to stderr."""
    status_styles = {"ok": "success", "warn": "warning", "fail": "error", "none": "muted"}
    for label, value, status in rows:
        style = status_styles.get(status, "muted")
        _safe_print(f"  {label:<22} [{style}]{value}[/{style}]")
