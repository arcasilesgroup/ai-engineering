"""No-nested-refs checker — guards `<skill>/references/` flatness.

Sub-spec sub-004 / brief §22 contract: every reference file in a skill's
``references/`` directory must stay one level deep. Linking from one
reference file to another reference file (same skill or cross-skill)
re-introduces the depth-2 navigation graph that progressive disclosure
is meant to eliminate.

Pure-stdlib (re + pathlib) per sub-spec scope. Returns rubric-shaped
``RubricResult`` records so the existing ``skill_lint --check`` rendering
pipeline treats the new check identically to the §3 rules.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

# Reuse the same severity vocabulary the rubric exposes so downstream
# tooling can aggregate without translation. We avoid importing
# ``skill_domain.rubric.RubricResult`` directly to keep this checker
# free of the layered package boundary (the test imports the type
# duck-typed via ``hasattr(r, "severity")``).
_VALID_SEVERITIES = {"OK", "INFO", "MINOR", "MAJOR", "CRITICAL"}


@dataclass(frozen=True)
class RubricResult:
    """Outcome of running the no-nested-refs check against a skill."""

    rule_name: str
    severity: str
    reason: str

    def __post_init__(self) -> None:
        if self.severity not in _VALID_SEVERITIES:
            raise ValueError(f"severity {self.severity!r} not in {sorted(_VALID_SEVERITIES)}")


# Markdown link regex — match the standard ``[text](target)`` form. Image
# links (``![alt](src)``) share the same shape so the same pattern picks
# them up. Reference-style links (``[text][label]``) and autolinks
# (``<http://…>``) are intentionally out of scope: the rule targets
# explicit relative paths.
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

# Targets that are explicitly safe (never count as nested references).
_EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "ftp://", "file://", "#")


def _iter_reference_files(skill_dir: Path) -> Iterable[Path]:
    refs_dir = skill_dir / "references"
    if not refs_dir.is_dir():
        return ()
    return sorted(refs_dir.glob("*.md"))


def _extract_links(md_path: Path) -> list[str]:
    text = md_path.read_text(encoding="utf-8")
    return _LINK_RE.findall(text)


def _is_nested_reference(link_target: str) -> bool:
    cleaned = link_target.strip()
    if cleaned.startswith(_EXTERNAL_PREFIXES):
        return False
    # Strip any anchor fragment so ``other.md#section`` is judged on
    # the path component alone.
    path_part = cleaned.split("#", 1)[0]
    return "references/" in path_part


def check_no_nested_refs(skill_dir: Path) -> list[RubricResult]:
    """Run the no-nested-refs rule against a single skill directory.

    Returns a single ``RubricResult`` summarising the outcome:

    * ``OK`` — every reference file linked only to safe targets, or no
      ``references/`` directory exists.
    * ``MAJOR`` — at least one reference file links to a path containing
      ``references/`` (the depth-2 anti-pattern). ``reason`` enumerates
      every offender so the operator can fix in one pass.
    """
    if not skill_dir.is_dir():
        return [
            RubricResult(
                "no_nested_refs",
                "OK",
                f"skill directory {skill_dir} not found — nothing to check",
            )
        ]

    violations: list[tuple[Path, str]] = []
    file_count = 0
    for md_file in _iter_reference_files(skill_dir):
        file_count += 1
        for link_target in _extract_links(md_file):
            if _is_nested_reference(link_target):
                violations.append((md_file, link_target))

    if violations:
        offenders = "; ".join(
            f"{path.relative_to(skill_dir)} → {target!r}" for path, target in violations
        )
        return [
            RubricResult(
                "no_nested_refs",
                "MAJOR",
                f"{len(violations)} nested-reference link(s): {offenders}",
            )
        ]

    if file_count == 0:
        return [RubricResult("no_nested_refs", "OK", "no references/ directory")]

    return [
        RubricResult(
            "no_nested_refs",
            "OK",
            f"{file_count} reference file(s) — flat, one level deep",
        )
    ]


def check_all_skills(skills_root: Path) -> list[tuple[Path, RubricResult]]:
    """Run the check across every skill under ``skills_root``.

    Helper wired so the CLI can fold the new check into the standard
    lint output without each caller re-implementing the directory walk.
    """
    if not skills_root.is_dir():
        raise FileNotFoundError(f"skills root {skills_root} does not exist")

    results: list[tuple[Path, RubricResult]] = []
    for skill_dir in sorted(skills_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        for result in check_no_nested_refs(skill_dir):
            results.append((skill_dir, result))
    return results
