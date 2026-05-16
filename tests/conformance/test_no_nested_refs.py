"""No nested references — every `<skill>/references/*.md` is one level deep.

Pairing: TDD RED partner of plan T-4.9 (`tools/skill_lint/checks/no_nested_refs.py`).
**DO NOT MODIFY THIS FILE during T-4.9 GREEN.** The checker implementation
must change to satisfy these assertions.

Rule (per sub-spec sub-004 brief §22): a markdown reference file inside a
skill `references/` directory must NOT link to any other path containing
`references/`. Cross-skill `<other-skill>/references/...` links are
forbidden; same-skill `./references/...` self-loops are forbidden;
sibling-ref links (`other-ref.md` from inside the same `references/`
directory) are allowed only if the link target string itself does not
contain `references/`.

Allowed link targets: upward to the skill body (`../SKILL.md`), to the
project root, or to external URLs (`http://`, `https://`).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Markdown link regex: capture only the URL/path inside parentheses.
# `\[.*?\]` matches the link text (non-greedy); `\(([^)]+)\)` captures the
# target. Reference-style and image-style links use the same shape.
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

# Targets that are explicitly safe and never count as nested references:
# external URLs, anchors only, mailto / file protocols, and pure root-relative
# repo paths that travel UP out of `references/`.
_EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "ftp://", "file://", "#")


def _iter_reference_files(skills_root: Path):
    """Yield every Markdown file under `<skill>/references/`."""
    for skill_dir in sorted(skills_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        refs_dir = skill_dir / "references"
        if not refs_dir.is_dir():
            continue
        yield from sorted(refs_dir.glob("*.md"))


def _extract_links(md_path: Path) -> list[str]:
    text = md_path.read_text(encoding="utf-8")
    return _LINK_RE.findall(text)


def _is_nested_reference(link_target: str) -> bool:
    """A nested reference is any link target that contains 'references/'.

    Sibling-ref links written as bare filenames (e.g. `easing-curves.md`)
    do NOT contain 'references/' and pass the rule. The intent is to
    ban depth-2+ navigation graphs that re-enter the references tree.
    """
    cleaned = link_target.strip()
    if cleaned.startswith(_EXTERNAL_PREFIXES):
        return False
    return "references/" in cleaned


@pytest.fixture(scope="session")
def all_reference_files(skills_root: Path) -> list[Path]:
    return list(_iter_reference_files(skills_root))


def test_reference_files_discovered(all_reference_files: list[Path]) -> None:
    """At least one reference file ships under the slimmed skills.

    sub-004 ships `references/` for ai-animation, ai-video-editing,
    ai-governance, ai-platform-audit, ai-skill-evolve. The fixture
    must surface them — empty results imply the test is mis-rooted.
    """
    assert len(all_reference_files) >= 5, (
        f"expected ≥5 reference files across slimmed skills, got "
        f"{len(all_reference_files)}: {[str(p) for p in all_reference_files]}"
    )


def test_no_nested_references(all_reference_files: list[Path]) -> None:
    """No `<skill>/references/*.md` links to another `references/` path.

    Failure surfaces the offending reference file and the offending link
    so the operator can see exactly which target violates the rule.
    """
    violations: list[tuple[Path, str]] = []
    for md_file in all_reference_files:
        for link_target in _extract_links(md_file):
            if _is_nested_reference(link_target):
                violations.append((md_file, link_target))

    assert not violations, (
        "Nested-reference links forbidden — references/ must stay one "
        "level deep. Offenders:\n"
        + "\n".join(f"  - {path}: {target!r}" for path, target in violations)
    )


def test_checker_module_importable() -> None:
    """The shipping checker exports `check_no_nested_refs` over a Path.

    Pairs with `tools/skill_lint/checks/no_nested_refs.py` (T-4.9). The
    callable must accept a skill directory and return a sequence of
    rubric-style results.
    """
    from skill_lint.checks.no_nested_refs import check_no_nested_refs

    assert callable(check_no_nested_refs), "check_no_nested_refs must be callable"


def test_checker_returns_results_for_valid_skill(skills_root: Path) -> None:
    """Calling the checker on a slimmed skill returns iterable results.

    The checker must return an empty (or all-OK) result list for skills
    that already pass the rule. ai-animation is slimmed in sub-004 with
    a flat `references/` tree.
    """
    from skill_lint.checks.no_nested_refs import check_no_nested_refs

    skill_dir = skills_root / "ai-animation"
    assert skill_dir.is_dir(), f"sub-004 ships ai-animation slim — missing {skill_dir}"

    results = check_no_nested_refs(skill_dir)
    # Either an empty list or a list of OK-severity results.
    assert hasattr(results, "__iter__"), (
        f"check_no_nested_refs must return an iterable, got {type(results)!r}"
    )
    materialised = list(results)
    for r in materialised:
        assert hasattr(r, "severity"), (
            f"each result must expose .severity, got {r!r} from {skill_dir}"
        )
        assert r.severity in {"OK", "INFO", "MINOR", "MAJOR", "CRITICAL"}, (
            f"unexpected severity {r.severity!r} from {skill_dir}"
        )
