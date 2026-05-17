"""Verifier roster count enforcement (spec-140 W3).

Spec-140 W3 collapsed the verifier specialist roster. The brief
header advertised "4 → 3" but the concrete operations enumerated
(keep deterministic, merge governance + feature into acceptance,
delete architecture and move its heuristics to /ai-advise) yield a
post-W3 count of 2, not 3. The deviation is documented in the
spec-140 CHANGELOG block; this test pins the actual landed count.

Kept (1):
    - verifier-deterministic

Merged → new file (2 → 1):
    - verifier-governance + verifier-feature → verifier-acceptance

Deleted, heuristics moved to /ai-advise (1 → 0):
    - verifier-architecture  (advisory in /ai-advise drift mode)

Net post-W3 roster: 2 (deterministic, acceptance).
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CANONICAL_AGENTS = _REPO_ROOT / ".claude" / "agents"

EXPECTED_VERIFIERS: frozenset[str] = frozenset(
    {
        "verifier-deterministic",
        "verifier-acceptance",
    }
)


def _verifier_files() -> list[Path]:
    """Return the sorted list of verifier-* agent files under .claude/agents/."""
    return sorted(_CANONICAL_AGENTS.glob("verifier-*.md"))


@pytest.mark.unit
def test_verifier_roster_has_two_entries() -> None:
    """Post spec-140 W3, exactly 2 verifier-* specialists remain.

    NOTE on the spec header "4 → 3": the brief operations
    (delete 3 files, create 1) actually yield a net of 2, not 3.
    The test reflects the actual landed roster. See spec-140
    CHANGELOG for the documented deviation.
    """
    verifiers = _verifier_files()
    assert len(verifiers) == 2, (
        f"Expected 2 verifier-* agents post spec-140 W3, found {len(verifiers)}: "
        f"{sorted(f.stem for f in verifiers)}"
    )


@pytest.mark.unit
def test_verifier_roster_names_match_canonical_set() -> None:
    """Disk names must match the canonical post-W3 verifier set."""
    names = {f.stem for f in _verifier_files()}
    assert names == EXPECTED_VERIFIERS, (
        "Verifier roster drift vs spec-140 W3 canonical set. "
        f"Missing: {EXPECTED_VERIFIERS - names}, "
        f"Extra: {names - EXPECTED_VERIFIERS}"
    )
