"""No-orphan-dirs checker — enforces D-133-13 hard deletions.

Spec-133 D-133-13 deleted 4 orphan directory trees and stated:

    `tools/skill_lint/checks/no_orphan_dirs.py` (NEW) enforces absence.

This module is that enforcement. It walks a repo root and verifies that
none of the canonical orphan paths reappear (e.g., via a `git revert`,
a sync regression, or a bad merge). Hard rules (CONSTITUTION §13.3
forbids backwards-compat shims) — the check refuses to allow even an
empty placeholder dir.

Canonical orphan paths (D-133-13 + D-133-10):

1. ``.ai-engineering/adapters/``           — renamed to ``overrides/`` (D-128-01)
2. ``.ai-engineering/contexts/frameworks/`` — eliminated by D-128-01
3. ``.ai-engineering/contexts/languages/``  — eliminated by D-128-01
4. ``.claude/skills/ai-debug/handlers/``    — moved to ``overrides/<stack>/debug.md`` (D-133-10)
5. ``.claude/skills/ai-review/handlers/``   — moved to ``overrides/<stack>/review.md`` (D-133-10)

Surface mirrors of the ai-debug / ai-review handlers/ dirs are scanned
under .codex, .gemini, .github, and the template tree, since
``ai-eng sync`` regenerates them and any one of those copies leaking
back constitutes a regression.

Pure-stdlib. Mirrors the dataclass + ``RubricResult`` shape of the
neighbouring ``no_nested_refs.py`` so the CLI renderer aggregates
without translation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_VALID_SEVERITIES = {"OK", "INFO", "MINOR", "MAJOR", "CRITICAL"}


@dataclass(frozen=True)
class RubricResult:
    """Outcome of running the no-orphan-dirs check against a repo root."""

    rule_name: str
    severity: str
    reason: str

    def __post_init__(self) -> None:
        if self.severity not in _VALID_SEVERITIES:
            raise ValueError(f"severity {self.severity!r} not in {sorted(_VALID_SEVERITIES)}")


# Surfaces that mirror the canonical .claude/skills/ tree. ai-debug and
# ai-review live in each of these as part of the mirror-sync output, so
# their handlers/ dirs must not reappear in any of them either.
_SURFACE_SKILLS_ROOTS: tuple[str, ...] = (
    ".claude/skills",
    ".codex/skills",
    ".gemini/skills",
    ".github/skills",
    "src/ai_engineering/templates/project/.claude/skills",
    "src/ai_engineering/templates/project/.codex/skills",
    "src/ai_engineering/templates/project/.gemini/skills",
    "src/ai_engineering/templates/project/.github/skills",
)

_HANDLERS_OWNERS: tuple[str, ...] = ("ai-debug", "ai-review")

# Repo-rooted paths that must never exist (D-133-13 hard deletes).
_FIXED_ORPHAN_PATHS: tuple[str, ...] = (
    ".ai-engineering/adapters",
    ".ai-engineering/contexts/frameworks",
    ".ai-engineering/contexts/languages",
)


def _enumerate_orphan_paths(repo_root: Path) -> list[Path]:
    """Return every path the rule forbids, expanded against ``repo_root``."""
    paths: list[Path] = [repo_root / rel for rel in _FIXED_ORPHAN_PATHS]
    for surface_root in _SURFACE_SKILLS_ROOTS:
        for owner in _HANDLERS_OWNERS:
            paths.append(repo_root / surface_root / owner / "handlers")
    return paths


def check_no_orphan_dirs(repo_root: Path) -> list[RubricResult]:
    """Run the no-orphan-dirs check against ``repo_root``.

    Returns one ``RubricResult``:

    * ``OK`` — every canonical orphan path is absent.
    * ``MAJOR`` — at least one orphan path exists. ``reason`` enumerates
      every offender so a single ``rm -rf`` pass can resolve.
    """
    if not repo_root.is_dir():
        return [
            RubricResult(
                "no_orphan_dirs",
                "OK",
                f"repo root {repo_root} not found — nothing to check",
            )
        ]

    offenders = [p for p in _enumerate_orphan_paths(repo_root) if p.exists()]
    if offenders:
        # spec-128 D-128-XX: use POSIX-style paths so the reason string is
        # stable across Windows (backslashes) and POSIX (forward slashes).
        rel = "; ".join(p.relative_to(repo_root).as_posix() for p in offenders)
        return [
            RubricResult(
                "no_orphan_dirs",
                "MAJOR",
                f"{len(offenders)} orphan path(s) present (D-133-13/D-133-10): {rel}",
            )
        ]
    return [
        RubricResult(
            "no_orphan_dirs",
            "OK",
            "every canonical orphan path is absent (D-133-13/D-133-10)",
        )
    ]
