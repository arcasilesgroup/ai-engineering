"""Suppression-marker scanner — pure stdlib, single regex pass per file.

Detects every suppression comment / config directive forbidden by
``CONSTITUTION.md`` Article VII and returns structured ``Finding``
records the CLI can join against the allowlist.

The patterns are intentionally narrow:

* ``NOSONAR`` and ``// NOSONAR`` — SonarCloud per-line bypass.
* ``# nosec`` — Bandit bypass.
* ``# noqa`` — Ruff / Flake8 bypass.
* ``# pragma: no cover`` — coverage.py bypass.
* ``# type: ignore`` and ``// @ts-ignore`` — type-checker bypass.
* ``# nolint`` / ``// nolint`` — generic linter bypass.
* ``# eslint-disable`` / ``// eslint-disable`` — ESLint bypass.
* ``sonar.issue.ignore.multicriteria`` — Sonar properties bypass.

Each detection records the rule (Sonar / Semgrep / Ruff / etc. code)
when present so the allowlist can match by file glob + rule.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

__all__ = ("DEFAULT_EXCLUDE_GLOBS", "DEFAULT_INCLUDE_GLOBS", "Finding", "scan_paths", "scan_text")


_RULE_TAG = r"(?:[A-Za-z][A-Za-z0-9_:.\-]+)"

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("nosonar", re.compile(rf"\bNOSONAR\b(?:\(({_RULE_TAG})\))?")),
    ("nosec", re.compile(rf"#\s*nosec\b(?:[:\s]+({_RULE_TAG}))?")),
    ("noqa", re.compile(rf"#\s*noqa\b(?:[:\s]+({_RULE_TAG}))?")),
    ("pragma_no_cover", re.compile(r"#\s*pragma\s*:\s*no\s+cover\b")),
    ("type_ignore", re.compile(rf"#\s*type\s*:\s*ignore\b(?:\[({_RULE_TAG})\])?")),
    ("ts_ignore", re.compile(r"//\s*@ts-ignore\b")),
    ("nolint_hash", re.compile(rf"#\s*nolint\b(?:[:\s]+({_RULE_TAG}))?")),
    ("nolint_slash", re.compile(rf"//\s*nolint\b(?:[:\s]+({_RULE_TAG}))?")),
    ("eslint_disable_hash", re.compile(r"#\s*eslint-disable\b")),
    ("eslint_disable_slash", re.compile(r"//\s*eslint-disable\b")),
    (
        "sonar_multicriteria",
        re.compile(r"^\s*sonar\.issue\.ignore\.multicriteria(?:\.\w+)?(?:\.\w+)?\s*="),
    ),
)


DEFAULT_INCLUDE_GLOBS: tuple[str, ...] = (
    # Production code + tooling. Markdown skills/agents are intentionally
    # excluded — they often *describe* the suppression patterns as
    # negative examples ("never use # noqa"), which would generate
    # spurious findings.
    "src/**/*.py",
    "tools/**/*.py",
    "scripts/**/*.py",
    ".ai-engineering/scripts/**/*.py",
    "sonar-project.properties",
    ".github/workflows/**/*.yml",
    ".github/workflows/**/*.yaml",
    "pyproject.toml",
)


DEFAULT_EXCLUDE_GLOBS: tuple[str, ...] = (
    # The scanner's own source defines the patterns it detects.
    "tools/no_suppression/**",
    "tests/unit/no_suppression/**",
    "tests/unit/test_skill_contract_completeness.py",
    "tests/unit/test_no_suppression*.py",
    "tests/unit/test_path_safety.py",
)


@dataclass(frozen=True)
class Finding:
    """One suppression detection inside a scanned file."""

    path: Path
    line: int
    column: int
    rule_id: str  # "nosonar", "noqa", "pragma_no_cover", ...
    rule_target: str  # The bypassed engine rule when captured (S2083, etc.)
    snippet: str

    def fingerprint(self) -> str:
        """Stable identity used to dedupe and join against the allowlist."""
        return f"{self.path.as_posix()}::{self.rule_id}::{self.rule_target}"


def _normalise_target(match: re.Match[str], rule_id: str) -> str:
    """Pull the engine-specific rule out of the regex match, when present."""
    groups = match.groups()
    if not groups:
        return ""
    captured = next((g for g in groups if g), "")
    return captured or rule_id


def scan_text(path: Path, text: str) -> list[Finding]:
    """Scan a single in-memory text blob.

    Surfaced so unit tests can exercise the regex pass without touching the
    filesystem.
    """
    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for rule_id, pattern in _PATTERNS:
            match = pattern.search(line)
            if match is None:
                continue
            target = _normalise_target(match, rule_id)
            findings.append(
                Finding(
                    path=path,
                    line=lineno,
                    column=match.start() + 1,
                    rule_id=rule_id,
                    rule_target=target,
                    snippet=line.strip()[:200],
                )
            )
    return findings


def _iter_candidate_paths(
    root: Path,
    include_globs: Iterable[str],
    exclude_globs: Iterable[str],
) -> Iterator[Path]:
    excludes = tuple(exclude_globs)
    seen: set[Path] = set()
    for pattern in include_globs:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            relative_posix = path.relative_to(root).as_posix()
            if any(Path(relative_posix).match(exc) for exc in excludes):
                continue
            if path in seen:
                continue
            seen.add(path)
            yield path


def scan_paths(
    root: Path,
    include_globs: Iterable[str] = DEFAULT_INCLUDE_GLOBS,
    exclude_globs: Iterable[str] = DEFAULT_EXCLUDE_GLOBS,
) -> list[Finding]:
    """Scan every file under ``root`` matching the include/exclude policy."""
    findings: list[Finding] = []
    for path in _iter_candidate_paths(root, include_globs, exclude_globs):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        findings.extend(scan_text(path.relative_to(root), text))
    findings.sort(key=lambda f: (f.path.as_posix(), f.line, f.column))
    return findings
