"""Static guard: forbidden install-command substrings must not appear in code.

Spec-101 D-101-02 — belt-and-suspenders. The runtime `_safe_run` allowlist is
the load-bearing control; this static grep catches accidental introductions of
elevated or system-scope install commands in installer / doctor / prereqs
modules.

Forbidden literals (per spec D-101-02):
    - sudo
    - apt install / yum install / dnf install
    - npm install -g / npm install --global
    - choco install
    - Install-Package without an explicit `-Scope CurrentUser`

This test parametrises over every Python file under three globs:
    src/ai_engineering/installer/**/*.py
    src/ai_engineering/doctor/**/*.py
    src/ai_engineering/prereqs/**/*.py

The `prereqs` directory is required by spec D-101-14 (T-1.x will create it).
A glob that matches no files fails `TestGlobsCoverFiles`, which is the RED
state for this RED-phase task.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Repo root resolved from this file's location.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src" / "ai_engineering"

# Forbidden regex patterns. The `Install-Package` pattern uses a negative
# lookahead so user-scope PowerShell calls (`Install-Package ... -Scope
# CurrentUser`) are permitted on the same line.
_FORBIDDEN_PATTERNS: list[str] = [
    r"\bsudo\b",
    r"\bapt install\b",
    r"\byum install\b",
    r"\bdnf install\b",
    r"npm install -g",
    r"npm install --global",
    r"\bchoco install\b",
    r"Install-Package(?![^|]*-Scope CurrentUser)",
]

# Globs (relative to _SRC_ROOT) that must be scanned.
_GLOB_PATTERNS: list[str] = [
    "installer/**/*.py",
    "doctor/**/*.py",
    "prereqs/**/*.py",
]

# Self-exclude: this test file legitimately contains the forbidden literals as
# regex strings. Excluded via absolute path comparison.
_SELF_PATH = Path(__file__).resolve()

# spec-113 D-113-06: distro-hint files emit ``sudo apt-get install``,
# ``sudo dnf install``, ``sudo pacman`` as user-facing TEXT recommendations
# (template strings printed to stdout/stderr). The framework never
# executes them -- the user reads the hint and runs the command at their
# own elevation. D-101-02 user-scope invariant remains intact because
# every subprocess call still flows through ``_safe_run`` whose argv
# allowlist still rejects ``sudo`` / package-manager invocations.
#
# Each entry maps a relative source path to the patterns it is permitted
# to surface as text. New files must NOT be added without spec-level
# approval and a code review confirming the literal is text-only.
_DISTRO_HINT_TEXT_ALLOWLIST: dict[str, frozenset[str]] = {
    "src/ai_engineering/installer/distro.py": frozenset(
        {r"\bsudo\b", r"\bdnf install\b", r"\bapt install\b", r"\byum install\b"}
    ),
    "src/ai_engineering/installer/user_scope_install.py": frozenset(
        {r"\bsudo\b", r"\bdnf install\b", r"\bapt install\b", r"\byum install\b"}
    ),
    "src/ai_engineering/doctor/output_formatter.py": frozenset(
        {r"\bsudo\b", r"\bdnf install\b", r"\bapt install\b", r"\byum install\b"}
    ),
}


def _files_for_glob(glob: str) -> list[Path]:
    """Return all Python files matching `glob` under `_SRC_ROOT`, excluding self."""
    return sorted(
        path.resolve()
        for path in _SRC_ROOT.glob(glob)
        if path.is_file() and path.resolve() != _SELF_PATH
    )


def _all_scanned_files() -> list[Path]:
    """Union of files from every glob (deduplicated, sorted)."""
    seen: set[Path] = set()
    for glob in _GLOB_PATTERNS:
        for path in _files_for_glob(glob):
            seen.add(path)
    return sorted(seen)


def _file_pattern_pairs() -> list[tuple[Path, str]]:
    """Cartesian product of (file, pattern) for parametrisation."""
    return [(path, pattern) for path in _all_scanned_files() for pattern in _FORBIDDEN_PATTERNS]


def _pair_id(pair: tuple[Path, str]) -> str:
    path, pattern = pair
    return f"{path.relative_to(_REPO_ROOT)}::{pattern}"


class TestNoForbiddenSubstrings:
    """Every Python file in scope must be free of forbidden install literals."""

    @pytest.mark.parametrize(
        ("path", "pattern"),
        _file_pattern_pairs(),
        ids=[_pair_id(pair) for pair in _file_pattern_pairs()],
    )
    def test_file_has_no_forbidden_pattern(self, path: Path, pattern: str) -> None:
        """File must NOT contain a forbidden regex match."""
        rel = str(path.relative_to(_REPO_ROOT))
        # spec-113 D-113-06: distro-hint files publish text recommendations
        # that include ``sudo`` / package-manager strings. Skip those
        # (file, pattern) pairs explicitly via the allowlist.
        allowlisted = _DISTRO_HINT_TEXT_ALLOWLIST.get(rel)
        if allowlisted is not None and pattern in allowlisted:
            pytest.skip(
                f"{rel}: pattern {pattern!r} is allowed as text-only distro-install hint (D-113-06)"
            )
        text = path.read_text(encoding="utf-8")
        match = re.search(pattern, text)
        assert match is None, (
            f"Forbidden literal {pattern!r} found in "
            f"{path.relative_to(_REPO_ROOT)}: {match.group(0)!r}"
        )


class TestGlobsCoverFiles:
    """Each declared glob must match at least one file (catches typos / missing dirs)."""

    @pytest.mark.parametrize("glob", _GLOB_PATTERNS, ids=_GLOB_PATTERNS)
    def test_glob_matches_at_least_one_file(self, glob: str) -> None:
        """Glob must resolve to one or more Python files under `_SRC_ROOT`."""
        matches = _files_for_glob(glob)
        assert matches, (
            f"Glob {glob!r} matched no files under {_SRC_ROOT}. "
            "Either the directory is missing or the glob has a typo."
        )


class TestExceptions:
    """Verify the self-exclusion mechanism behaves as expected."""

    def test_self_path_resolves_to_this_file(self) -> None:
        """`_SELF_PATH` must point at this test module so it is excluded from scans."""
        assert _SELF_PATH.exists()
        assert _SELF_PATH.name == "test_no_forbidden_substrings.py"

    def test_self_file_is_not_in_scanned_files(self) -> None:
        """This test file must NOT appear in the scanned-file list."""
        scanned = _all_scanned_files()
        assert _SELF_PATH not in scanned

    def test_self_file_contains_forbidden_literals_as_data(self) -> None:
        """Sanity: this file does contain forbidden literals (as regex strings).

        If exclusion ever fails, the parametric scan will catch it via the
        `TestNoForbiddenSubstrings` cartesian product.
        """
        text = _SELF_PATH.read_text(encoding="utf-8")
        # Each forbidden pattern's literal source appears as a string here.
        assert "sudo" in text
        assert "apt install" in text
        assert "Install-Package" in text
