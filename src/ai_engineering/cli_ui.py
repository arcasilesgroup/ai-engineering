"""Human-facing CLI output module.

Provides branded Rich console output for the ai-engineering CLI.
All messaging goes to stderr; data goes to stdout (CLIG guideline).
Respects NO_COLOR, TERM=dumb, and TTY detection.
"""

from __future__ import annotations

import os
import re
import sys
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.rule import Rule
from rich.theme import Theme

from ai_engineering.__version__ import __version__

if TYPE_CHECKING:
    from ai_engineering.updater.service import FileChange

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


def render_update_tree(
    changes: list[FileChange],
    *,
    root: Path,
    dry_run: bool,
) -> None:
    """Render updater results as a single unified file tree on stderr.

    All non-unchanged changes are merged into one tree grouped by directory
    hierarchy.  Each leaf shows an inline state label (new, updated, protected,
    overwrite).  Unchanged files are excluded from the tree and summarised in a
    footer line.
    """
    visible: list[FileChange] = []
    unchanged_count = 0

    for change in changes:
        outcome = change.outcome(dry_run=dry_run)
        if outcome == "unchanged":
            unchanged_count += 1
        else:
            visible.append(change)

    if visible:
        tree = _TreeNode("")
        for change in sorted(visible, key=lambda c: _tree_sort_key(c, root=root)):
            parts = _tree_parts(change.path, root=root)
            tree.add(parts, change)
        _safe_print("")
        for line in tree.render():
            _safe_print(f"  {line}")

    if unchanged_count:
        _safe_print(f"  [dim]{unchanged_count} files unchanged[/dim]")


def _tree_sort_key(change: FileChange, *, root: Path) -> tuple[tuple[str, ...], str]:
    parts = _tree_parts(change.path, root=root)
    return tuple(part.casefold() for part in parts), change.reason_code


def _tree_parts(path: Path, *, root: Path) -> tuple[str, ...]:
    if path.is_absolute():
        try:
            parts = path.relative_to(root).parts
        except ValueError:
            parts = (path.name,) if path.name else path.parts
    else:
        parts = path.parts or (path.as_posix(),)
    return tuple(part for part in parts if part not in ("", "."))


_STATE_LABELS: dict[str, tuple[str, str]] = {
    "create": ("new", "green"),
    "update": ("updated", "yellow"),
    "skip-denied": ("protected", "red"),
    "overwrite": ("overwrite", "bold red"),
    "skip-unchanged": ("unchanged", "dim"),
}
"""Map FileChange.action to (label, Rich style) for inline display."""


class _TreeNode:
    """Minimal deterministic text tree for update previews."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.children: OrderedDict[str, _TreeNode] = OrderedDict()
        self.change: FileChange | None = None

    def add(self, parts: tuple[str, ...], change: FileChange) -> None:
        if not parts:
            self.change = change
            return
        head, *tail = parts
        child = self.children.setdefault(head, _TreeNode(head))
        child.add(tuple(tail), change)

    def render(self) -> list[str]:
        lines: list[str] = []
        children = list(self.children.values())
        for index, child in enumerate(children):
            child._render_into(lines, prefix="", is_last=index == len(children) - 1)
        return lines

    def _render_into(self, lines: list[str], *, prefix: str, is_last: bool) -> None:
        # Collapse single-child directory chains: a/b/c -> "a/b/c" on one line.
        node = self
        collapsed_name = self.name
        while node.change is None and len(node.children) == 1:
            only_child = next(iter(node.children.values()))
            collapsed_name = f"{collapsed_name}/{only_child.name}"
            node = only_child

        branch = "\u2514\u2500\u2500" if is_last else "\u251c\u2500\u2500"

        if node.change is not None:
            label, style = _STATE_LABELS.get(node.change.action, ("", "dim"))
            lines.append(f"{prefix}{branch} {collapsed_name}  [{style}]{label}[/{style}]")
        else:
            lines.append(f"{prefix}{branch} {collapsed_name}")

        pipe = "\u2502"
        child_prefix = f"{prefix}{'    ' if is_last else f'{pipe}   '}"
        children = list(node.children.values())
        for index, child in enumerate(children):
            child._render_into(
                lines,
                prefix=child_prefix,
                is_last=index == len(children) - 1,
            )


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
