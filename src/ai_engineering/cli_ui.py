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
from datetime import UTC
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.rule import Rule
from rich.theme import Theme

from ai_engineering import __version__

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


def show_banner() -> None:
    """Print a compact 1-line brand banner for subcommands (TTY only)."""
    con = get_console()
    if not con.is_terminal:
        return
    try:
        con.print()
        con.print(
            "  [brand]{[/brand] [bold]ai[/bold] [brand]}[/brand]"
            " [brand]engineering[/brand]"
            f" [muted]· v{__version__}[/muted]"
        )
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


def print_stderr(msg: str) -> None:
    """Write a plain-text line to stderr (for assertion markers).

    Used by callers that need a grep-able signal without contaminating
    stdout for JSON consumers in ``--non-interactive`` mode.
    """
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


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
    "skip-denied": ("protected", "dim"),
    "overwrite": ("overwrite", "bold red"),
    "skip-unchanged": ("unchanged", "dim"),
    "orphan": ("orphan", "dim magenta"),
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


# ── Update-available notice (spec version-update-notice) ──────────────


def _load_version_check_config() -> object:
    """Load the manifest ``version_check`` block from the cwd project root.

    Returns a config object exposing ``enabled``/``ttl_hours``. Fail-open:
    a missing/unreadable manifest yields the all-defaults config.
    """
    from ai_engineering.config.manifest import VersionCheckConfig

    try:
        from ai_engineering.config.loader import load_manifest_config

        return load_manifest_config(Path.cwd()).version_check
    except Exception:
        return VersionCheckConfig()


def maybe_render_update_notice(config: object | None = None, *, force: bool = False) -> None:
    """Render a one-line "update available" notice when appropriate.

    Reads the version-check cache, the installed ``__version__``, and the
    manifest ``version_check`` block. Emits nothing when the installed
    version is current, when the notice was shown within ``ttl_hours``,
    when disabled (``AIENG_NO_UPDATE_CHECK`` truthy or
    ``version_check.enabled`` false), or in JSON mode. When the cache is
    stale (older than TTL) it fires a detached background refresh and still
    renders from whatever the cache currently holds.

    ``force`` bypasses ONLY the once-per-``ttl_hours`` show throttle (not the
    up-to-date / disabled / JSON gates), for explicit "look at the tool"
    surfaces like bare ``ai-eng`` that should behave like ``ai-eng version``
    rather than a frequent automation command.

    When ``config`` (the resolved ``version_check`` block) is supplied by the
    caller, the manifest is NOT re-parsed here — the CLI hot path loads it
    once and threads it in (spec-157 review F7). When ``None`` the config is
    loaded lazily. Fail-open: any error is swallowed so the CLI hot path
    never breaks.
    """
    try:
        _render_update_notice(config, force=force)
    except Exception:
        return


def _render_update_notice(config: object | None = None, *, force: bool = False) -> None:
    from ai_engineering.cli_output import is_json_mode
    from ai_engineering.version import cache, resolve_latest_known
    from ai_engineering.version.compare import is_newer

    if is_json_mode():
        return
    if _truthy_env("AIENG_NO_UPDATE_CHECK"):
        return

    if config is None:
        config = _load_version_check_config()
    if not getattr(config, "enabled", True):
        return
    ttl_hours = int(getattr(config, "ttl_hours", 24))

    # Stale cache -> kick off a detached refresh, still render current cache.
    if cache.is_stale(ttl_hours):
        from ai_engineering.version import refresh

        refresh.spawn_background()

    # SSOT: the newer of the bundled registry and the PyPI cache. Reading the
    # cache alone left the notice silent whenever the cache lagged the registry.
    latest = resolve_latest_known()
    if not isinstance(latest, str) or not latest:
        return
    if not is_newer(latest, __version__):
        return

    data = cache.read()

    # Throttle: suppress if shown within the TTL window — unless ``force`` (the
    # caller is an explicit version-check surface, e.g. bare ``ai-eng``).
    last_shown = data.get("last_shown_at")
    if (
        not force
        and isinstance(last_shown, str)
        and last_shown
        and not _shown_window_elapsed(last_shown, ttl_hours)
    ):
        return

    con = get_console()
    # Pure-ASCII variant for raw stderr writes (pipes / CI / legacy cp1252
    # consoles), so a non-UTF-8 stream never hits UnicodeEncodeError. The
    # styled terminal path keeps the ◈/→ marks via Rich, which encodes safely.
    plain_message = f"ai-engineering {__version__} -> {latest} (run: ai-eng version upgrade)"
    if con.is_terminal and not _is_no_color():
        markup = (
            f"[brand.dim]◈ ai-engineering {__version__} → {latest}[/brand.dim] "
            "[muted]· run [brand.dim]`ai-eng version upgrade`[/brand.dim][/muted]"
        )
        try:
            con.print(markup)
        except (ImportError, ModuleNotFoundError):
            sys.stderr.write(plain_message + "\n")
    else:
        sys.stderr.write(plain_message + "\n")

    cache.mark_shown()


def _drift_cache_path() -> Path:
    return Path.home() / ".ai-engineering" / "state" / "framework-drift.json"


def _drift_shown_recently(key: str, ttl_hours: int = 24) -> bool:
    # Per-project throttle: drift is a per-project axis, so the timestamp is
    # keyed by project root — a drifted project B is not silenced because a
    # sibling project A showed the banner within the window.
    import json
    from datetime import datetime

    try:
        data = json.loads(_drift_cache_path().read_text(encoding="utf-8"))
        last = datetime.fromisoformat(data[key])
        return (datetime.now(UTC) - last).total_seconds() < ttl_hours * 3600
    except Exception:
        return False


def _drift_mark_shown(key: str) -> None:
    import json
    from datetime import UTC, datetime

    try:
        path = _drift_cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        # Read existing timestamps; construct a fresh sanitized dict to break
        # SonarCloud S2083 taint flow (false positive: path is fixed, not
        # user-controlled). Only preserve string keys with ISO-timestamp values.
        entries: dict[str, str] = {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for k, v in raw.items():
                    if isinstance(k, str) and isinstance(v, str):
                        entries[k] = v
        except Exception:
            pass
        entries[key] = datetime.now(UTC).isoformat()
        path.write_text(json.dumps(entries), encoding="utf-8")
    except Exception:
        return


def maybe_render_framework_drift_notice(target: object, *, force: bool = False) -> None:
    """spec-184 D-184-05: advise-only ``⟳`` banner when the project's framework
    files are behind the installed package (run ``ai-eng update``).

    Distinct from the ◈ PyPI notice — different mark (``⟳``) and verb
    (``ai-eng update``, not ``version upgrade``). Never blocks (advise-only),
    suppressed in JSON mode and under ``AIENG_NO_UPDATE_CHECK``, throttled
    once-per-``ttl_hours`` (``force`` bypasses only the throttle), and
    fail-open. Plain-ASCII (no ``⟳`` glyph) on non-TTY / NO_COLOR so a
    non-UTF-8 stream never raises.
    """
    try:
        from ai_engineering.cli_output import is_json_mode
        from ai_engineering.version.framework_drift import detect_framework_drift

        if is_json_mode() or _truthy_env("AIENG_NO_UPDATE_CHECK"):
            return
        root = Path(str(target))
        key = str(root.resolve())
        drift = detect_framework_drift(root)
        if not drift.behind:
            return
        if not force and _drift_shown_recently(key):
            return

        con = get_console()
        plain = (
            f"ai-engineering project {drift.applied} -> installed {drift.installed} "
            "(run: ai-eng update)"
        )
        if con.is_terminal and not _is_no_color():
            markup = (
                f"[warning]⟳ ai-engineering project {drift.applied} → {drift.installed}[/warning]"
                " [muted]· run [warning]`ai-eng update`[/warning][/muted]"
            )
            try:
                con.print(markup)
            except (ImportError, ModuleNotFoundError):
                sys.stderr.write(plain + "\n")
        else:
            sys.stderr.write(plain + "\n")
        _drift_mark_shown(key)
    except Exception:
        return


def render_version_status(installed: str, latest: str | None) -> None:
    """Render the ``ai-eng version`` status block — coherent, single-source.

    Outdated → two lines (installed version + update CTA). Up-to-date or unknown
    → one line. Uses the same ``◈`` brand mark and dim ink as the inline update
    notice so both surfaces read as one design system, and takes its ``latest``
    from the SSOT resolver so it can never contradict the notice.
    """
    from ai_engineering.version.compare import is_newer

    con = get_console()
    outdated = bool(latest) and is_newer(latest, installed)
    styled = con.is_terminal and not _is_no_color()

    # The styled path keeps the ◈/→ marks (Rich encodes them safely for the
    # terminal). The plain path is for pipes/CI/legacy consoles (e.g. Windows
    # cp1252) and stays pure ASCII so a raw write never hits UnicodeEncodeError.
    if outdated:
        if styled:
            con.print(f"[brand]◈ ai-engineering[/brand] [bold]{installed}[/bold]")
            con.print(
                f"  [brand.dim]update available → {latest}[/brand.dim] "
                "[muted]· run [brand.dim]`ai-eng version upgrade`[/brand.dim][/muted]"
            )
        else:
            sys.stdout.write(
                f"ai-engineering {installed} -> {latest} (run: ai-eng version upgrade)\n"
            )
        return

    if styled:
        con.print(
            f"[brand]◈ ai-engineering[/brand] [bold]{installed}[/bold] [muted]· up to date[/muted]"
        )
    else:
        sys.stdout.write(f"ai-engineering {installed} (up to date)\n")


def _truthy_env(name: str) -> bool:
    """Return True when the named env var holds a truthy value."""
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _shown_window_elapsed(last_shown: str, ttl_hours: int) -> bool:
    """Return True when ``ttl_hours`` have passed since ``last_shown``.

    Fail-open: an unparseable stamp is treated as elapsed (show again).
    """
    from datetime import datetime

    try:
        stamp = datetime.fromisoformat(last_shown)
    except ValueError:
        return True
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=UTC)
    age = datetime.now(UTC) - stamp
    return age.total_seconds() > ttl_hours * 3600
