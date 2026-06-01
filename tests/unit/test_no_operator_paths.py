"""Static guard: shipped content must not leak an operator home path.

spec-158 D-158-09 / AC11 — Hard Rule 4 (anonymous content). A public framework
that any company installs must never ship an operator's machine path or name.
This gate scans every shipped surface for an absolute home path
(``/Users/<name>`` or ``/home/<name>``, plus the Windows ``\\Users\\<name>``
form) whose user segment is NOT one of a small set of generic placeholders.

It is NAME-AGNOSTIC by design: it flags ANY real operator name (today's leak
was ``soydachi``), so a future operator's path is caught automatically rather
than relying on a per-name denylist.

Out of scope (not shipped / synthetic): ``tests/``, ``.ai-engineering/runtime``,
``.ai-engineering/specs``, ``.ai-engineering/observations`` and this file itself.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SELF = Path(__file__).resolve()

# Absolute home-path shapes across POSIX + Windows. Group 2 is the user segment.
_HOME_PATH = re.compile(r"[/\\](Users|home)[/\\]([A-Za-z][A-Za-z0-9_.-]*)")

# Generic, non-identifying user segments that are allowed in shipped examples.
_GENERIC_SEGMENTS = frozenset(
    {
        "user",
        "users",
        "you",
        "youruser",
        "username",
        "runner",
        "linuxbrew",
        "root",
        "test",
        "example",
        "name",
        "project",
        "app",
        "ci",
        "build",
        "home",
        "someone",
        "developer",
    }
)

# Shipped surfaces: installed into a user's repo or published to PyPI.
_SCAN_GLOBS = (
    "src/ai_engineering/**/*",
    ".ai-engineering/scripts/**/*",
    "docs/**/*.md",
    "*.md",
)


def _offending_segments(text: str) -> list[str]:
    """Return user segments in *text* that are not generic placeholders."""
    return [seg for _root, seg in _HOME_PATH.findall(text) if seg.lower() not in _GENERIC_SEGMENTS]


def _shipped_files() -> list[Path]:
    seen: set[Path] = set()
    for glob in _SCAN_GLOBS:
        for path in _REPO_ROOT.glob(glob):
            resolved = path.resolve()
            if not path.is_file() or resolved == _SELF:
                continue
            seen.add(resolved)
    return sorted(seen)


def test_matcher_flags_operator_paths_and_passes_generics() -> None:
    """The matcher catches a planted operator path and passes generic ones."""
    assert _offending_segments("/Users/plantedoperator/repos/x") == ["plantedoperator"]
    assert _offending_segments("C:\\Users\\plantedoperator\\x") == ["plantedoperator"]
    # Generic placeholders and the Linuxbrew default must NOT be flagged.
    assert _offending_segments("/home/linuxbrew/.linuxbrew") == []
    assert _offending_segments("/Users/you/.local/bin") == []
    assert _offending_segments("/home/runner/work") == []


def test_no_shipped_file_leaks_an_operator_path() -> None:
    """No shipped surface may embed a non-generic operator home path."""
    violations: list[str] = []
    for path in _shipped_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary / unreadable — nothing to scan
        offenders = _offending_segments(text)
        if offenders:
            rel = path.relative_to(_REPO_ROOT)
            violations.append(f"{rel}: {sorted(set(offenders))}")
    assert not violations, "Operator home paths leaked in shipped content:\n" + "\n".join(
        violations
    )


def test_scan_globs_match_files() -> None:
    """Sanity: the scan actually covers files (catches a broken glob)."""
    assert _shipped_files(), "operator-path scan matched no shipped files"
