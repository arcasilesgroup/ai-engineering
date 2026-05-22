"""Hard-delete enforcement for spec-140 W3 reviewer/verifier collapse.

Spec-140 W3 deleted 6 specialist agent files. CONSTITUTION §13.3
(no backwards-compat shims) requires the deletes propagate to every
IDE mirror; this test enforces that contract by scanning every
surface directory for any of the deleted filenames.

The mirror sync (``ai-eng dev sync``) is responsible for the actual
propagation. This test is the safety net: if the sync regresses or
an operator restores a file by hand, the next test run blocks the
commit.

Deleted in spec-140 W3:
    - reviewer-architecture.md     (heuristics absorbed into reviewer-correctness)
    - reviewer-maintainability.md  (heuristics absorbed into reviewer-correctness)
    - reviewer-backend.md          (categorically mismatched; no backend tier)
    - verifier-governance.md       (merged into verifier-acceptance)
    - verifier-feature.md          (merged into verifier-acceptance)
    - verifier-architecture.md     (heuristics moved to /ai-advise drift mode)
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Every active runtime + mirror surface root scanned (Surface Axiom A1).
_SURFACE_ROOTS: tuple[Path, ...] = (
    _REPO_ROOT / ".claude",
    _REPO_ROOT / ".codex",
    _REPO_ROOT / ".agents",
    _REPO_ROOT / ".github",
    _REPO_ROOT / ".opencode",
    _REPO_ROOT / ".cursor",
    _REPO_ROOT / "src" / "ai_engineering" / "templates" / "project",
)

DELETED_AGENT_FILENAMES: frozenset[str] = frozenset(
    {
        "reviewer-architecture.md",
        "reviewer-maintainability.md",
        "reviewer-backend.md",
        "verifier-governance.md",
        "verifier-feature.md",
        "verifier-architecture.md",
    }
)


def _collect_residuals() -> dict[str, list[Path]]:
    """Find every survivor of the deleted-agent set across all surfaces.

    Returns a mapping {filename -> [absolute paths where it still exists]}.
    """
    residuals: dict[str, list[Path]] = {name: [] for name in DELETED_AGENT_FILENAMES}
    for root in _SURFACE_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            if path.name in DELETED_AGENT_FILENAMES:
                residuals[path.name].append(path)
    return residuals


@pytest.mark.unit
@pytest.mark.parametrize("filename", sorted(DELETED_AGENT_FILENAMES))
def test_deleted_agent_filename_absent_from_all_surfaces(filename: str) -> None:
    """Each spec-140 W3 deleted filename must not exist in any IDE mirror."""
    residuals = _collect_residuals()
    survivors = residuals[filename]
    assert not survivors, (
        f"spec-140 W3 deleted {filename!r}, but it still exists in "
        f"{len(survivors)} location(s):\n  - "
        + "\n  - ".join(str(p.relative_to(_REPO_ROOT)) for p in survivors)
        + "\nRun `.venv/bin/ai-eng dev sync` to propagate the canonical delete."
    )


@pytest.mark.unit
def test_no_deleted_agents_present_anywhere() -> None:
    """Aggregate guard: zero survivors total across all deleted filenames."""
    residuals = _collect_residuals()
    total = sum(len(paths) for paths in residuals.values())
    assert total == 0, (
        f"{total} survivor(s) of spec-140 W3 deletions remain across the "
        "mirror surfaces. Run `.venv/bin/ai-eng dev sync` to propagate.\n"
        + "\n".join(
            f"  {name}: " + ", ".join(str(p.relative_to(_REPO_ROOT)) for p in paths)
            for name, paths in residuals.items()
            if paths
        )
    )
