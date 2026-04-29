"""RED-phase test for spec-110 Phase 1 — entry-point overlay consistency.

Spec acceptance criterion (governance v3 harvest, Phase 1):
    The IDE-specific entry-point overlays (``CLAUDE.md``, ``GEMINI.md``,
    ``.github/copilot-instructions.md``) must each reference the canonical
    multi-IDE rulebook ``AGENTS.md`` via a relative markdown link so that
    every assistant funnels through the same source of truth. Verifiable
    by ``tests/integration/test_entry_points_consistency.py::
    test_overlays_reference_agents_md`` which scans each overlay for a
    relative link of the form ``[<text>AGENTS.md<text>](AGENTS.md)`` (or
    ``./AGENTS.md`` / ``../AGENTS.md`` for files in subdirectories).

Status: RED (overlays do not yet contain the link). Tasks T-1.9..T-1.11
add the references after ``AGENTS.md`` is refactored in T-1.8. This test
deliberately fails now to drive the GREEN phase.
"""

from __future__ import annotations

import re
from pathlib import Path

# Repo root: tests/integration/<this file> → up 3 levels.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Overlays whose entry points must funnel into AGENTS.md.
OVERLAY_PATHS: tuple[Path, ...] = (
    REPO_ROOT / "CLAUDE.md",
    REPO_ROOT / "GEMINI.md",
    REPO_ROOT / ".github" / "copilot-instructions.md",
)

# Tolerant matcher: ``[<any text containing AGENTS.md>](<optional ./ or ../>AGENTS.md)``.
# - The link text must contain the literal ``AGENTS.md`` (escaped dot).
# - The link target must be the relative path ``AGENTS.md`` with an optional
#   single ``./`` or ``../`` prefix (one level only — overlays sit in repo root
#   or one directory deep, e.g. ``.github/``).
AGENTS_MD_LINK_RE = re.compile(r"\[[^\]]*AGENTS\.md[^\]]*\]\((?:\.{1,2}/)?AGENTS\.md\)")


def test_overlays_reference_agents_md() -> None:
    """Each IDE overlay contains a relative markdown link to ``AGENTS.md``.

    Asserts:
    1. Every overlay file in ``OVERLAY_PATHS`` exists at its expected path.
    2. Each overlay file contains at least one markdown link whose link
       text mentions ``AGENTS.md`` and whose target is the relative path
       ``AGENTS.md`` (optionally prefixed with ``./`` or ``../``).
    """
    missing_files: list[str] = []
    overlays_without_link: list[str] = []

    for overlay_path in OVERLAY_PATHS:
        if not overlay_path.is_file():
            missing_files.append(str(overlay_path.relative_to(REPO_ROOT)))
            continue

        content = overlay_path.read_text(encoding="utf-8")
        if not AGENTS_MD_LINK_RE.search(content):
            overlays_without_link.append(str(overlay_path.relative_to(REPO_ROOT)))

    assert not missing_files, (
        "Expected IDE overlay entry points are missing from the repo: "
        f"{missing_files}. Overlays must exist at the canonical paths so "
        "they can funnel into AGENTS.md per spec-110 Phase 1."
    )

    assert not overlays_without_link, (
        "Each IDE overlay must contain a relative markdown link to "
        "AGENTS.md (e.g. '[AGENTS.md](AGENTS.md)' or "
        "'[AGENTS.md](../AGENTS.md)'). Overlays missing the link: "
        f"{overlays_without_link}. Refactor them per spec-110 tasks "
        "T-1.9..T-1.11 to delegate canonical rules to AGENTS.md."
    )
