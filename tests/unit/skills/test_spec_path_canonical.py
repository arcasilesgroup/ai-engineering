"""CI guard for spec-path canonicalization (spec-122-d D-122-40).

Skill markdown across `.claude/skills/`, `.gemini/skills/`, `.codex/skills/`
must reference the canonical active-spec path
`.ai-engineering/specs/spec.md` (matches the resolver default in
`src/ai_engineering/state/work_plane.py:240`). Legacy paths
(`specs/spec.md`, `specs/plan.md`, `specs/autopilot/...`) caused user-
visible autopilot Step-0 failures because the resolver looks elsewhere.

This guard fails on any bare `specs/<file>.md` reference that is not
preceded by `.ai-engineering/`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_TREES = [
    REPO_ROOT / ".claude" / "skills",
    REPO_ROOT / ".gemini" / "skills",
    REPO_ROOT / ".codex" / "skills",
]

# Negative-lookbehind: match `specs/spec.md`, `specs/plan.md`, or
# `specs/autopilot/` only when NOT preceded by `.ai-engineering/`.
# Matches any of the three legacy patterns.
LEGACY_PATTERN = re.compile(r"(?<!\.ai-engineering/)specs/(?:spec\.md|plan\.md|autopilot/)")


def _scan_skill_tree(root: Path) -> list[tuple[Path, int, str]]:
    """Return list of (file, line_number, line_text) for legacy hits."""
    if not root.is_dir():
        return []
    hits: list[tuple[Path, int, str]] = []
    for md_file in root.rglob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if LEGACY_PATTERN.search(line):
                hits.append((md_file, lineno, line))
    return hits


def test_no_legacy_specs_paths_in_skill_trees() -> None:
    """No skill markdown references legacy `specs/spec.md` etc.

    Per D-122-40: paths must be `.ai-engineering/specs/spec.md`.
    Re-running the rewrite must not double-prefix; if this test fails
    after a rewrite pass, check the regex idempotency.
    """
    all_hits: list[tuple[Path, int, str]] = []
    for root in SKILL_TREES:
        all_hits.extend(_scan_skill_tree(root))

    if all_hits:
        unique_files = sorted({str(h[0].relative_to(REPO_ROOT)) for h in all_hits})
        first_5 = all_hits[:5]
        sample_lines = "\n".join(
            f"  {h[0].relative_to(REPO_ROOT)}:{h[1]}: {h[2].strip()[:80]}" for h in first_5
        )
        pytest.fail(
            f"Found {len(all_hits)} legacy specs/ references in "
            f"{len(unique_files)} files (D-122-40 violation).\n"
            f"First 5 violators:\n{sample_lines}\n\n"
            f"Fix: rewrite to `.ai-engineering/specs/spec.md` "
            f"(see test docstring)."
        )


def test_idempotency_marker() -> None:
    """The canonical path must NOT be itself flagged as legacy.

    This test acts as a regex sanity check -- it asserts the negative
    lookbehind correctly excludes already-canonical paths so re-running
    the rewrite is a no-op.
    """
    canonical = ".ai-engineering/specs/spec.md"
    legacy = "Some text mentioning specs/spec.md as a reference"
    assert LEGACY_PATTERN.search(canonical) is None, (
        "Canonical path must not match legacy pattern (would cause double-prefixing on re-run)."
    )
    assert LEGACY_PATTERN.search(legacy) is not None, "Legacy bare path must match (sanity check)."
