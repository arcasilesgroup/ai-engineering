"""spec-177 T-5.1: the skill/agent inventory count must agree across every
human-facing surface and match the filesystem ground-truth. Locks the 47/53/54
drift fix so it cannot silently regress."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _skill_count() -> int:
    return len([p for p in (ROOT / ".claude" / "skills").glob("ai-*") if p.is_dir()])


def _agent_count() -> int:
    return len(list((ROOT / ".claude" / "agents").glob("ai-*.md")))


def test_canonical_inventory_is_53_skills_9_agents() -> None:
    # Ground-truth from the filesystem. If the real counts change, update the
    # surfaces below in the same change (that is the point of this gate).
    assert _skill_count() == 53
    assert _agent_count() == 9


def test_surfaces_state_the_same_counts() -> None:
    skills, agents = _skill_count(), _agent_count()
    surfaces = (
        ROOT / "README.md",
        ROOT / ".ai-engineering" / "README.md",
        ROOT / ".ai-engineering" / "solution-intent.md",
    )
    for path in surfaces:
        text = path.read_text(encoding="utf-8")
        assert f"{skills} skills" in text, f"{path.name} missing '{skills} skills'"
        assert f"{agents} agents" in text, f"{path.name} missing '{agents} agents'"
        # the superseded counts must not linger anywhere
        assert "47 skills" not in text, f"{path.name} still says '47 skills'"
        assert "54 skills" not in text, f"{path.name} still says '54 skills'"
