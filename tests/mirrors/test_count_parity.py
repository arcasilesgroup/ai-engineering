"""Mirror count-parity tests for spec-127 sub-005 (M4) — renames + mergers.

Asserts the canonical surface counts are stable across all IDE mirror trees:

* `.claude/skills/` (canonical source, Claude Code only)
* `.agents/skills/` (the shared tree every other surface reads)

spec-201 D-201-04 collapsed the seven skill trees to those two, so the
former `.github/skills/` and `.codex/skills/` legs are gone.

The disk count target landed by sub-005 is documented in
`.ai-engineering/manifest.yml skills.total`. The umbrella spec target was
46/23; sub-005 achieved 48 skills and 24 agents on disk; Wave 8
(D-127-10 strict-count enforcement) demoted `/ai-help` to a reference
file under `.claude/skills/ai-branch-cleanup/references/`, leaving 47 skills
and 24 agents (see CHANGELOG Wave 8 section for the gap explanation).
The test reads the achieved counts from the manifest as the single
source of truth so it remains correct under future rename / merger
waves without churn here.

Each test surfaces the *count parity* invariant — every IDE mirror tree
must contain the same number of skill directories as the canonical
`.claude/skills/` source.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.config.loader import load_manifest_config

REPO_ROOT = Path(__file__).resolve().parents[2]
CLAUDE_SKILLS = REPO_ROOT / ".claude" / "skills"
CLAUDE_AGENTS = REPO_ROOT / ".claude" / "agents"
ANTIGRAVITY_SKILLS = REPO_ROOT / ".agents" / "skills"
MANIFEST = REPO_ROOT / ".ai-engineering" / "manifest.yml"


# Provider-scoped skills that opt out of specific IDE mirrors.
# spec-187 D-187-04: the sole provider-scoped skill was hard-deleted, so no
# skill currently opts out of any mirror. The map is retained so a future
# Claude-Code-only skill can re-register its opt-out.
PROVIDER_SCOPED_SKIPS: dict[str, set[str]] = {
    "antigravity": set(),
}


def _count_skill_dirs(root: Path, *, ide: str | None = None) -> int:
    """Count `ai-*/SKILL.md` skill directories in a mirror tree.

    Excludes the `_shared/` helper directory (not a skill, just shared
    fragments consumed by the orchestrators) and any provider-scoped
    skills documented as opting out of the named ``ide`` mirror.
    """
    if not root.is_dir():
        return 0
    skips = PROVIDER_SCOPED_SKIPS.get(ide or "", set())
    count = 0
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        if entry.name.startswith("_"):
            continue
        if entry.name in skips:
            continue
        if (entry / "SKILL.md").exists():
            count += 1
    return count


def _count_agent_files(root: Path) -> int:
    """Count `*.md` agent files in `.claude/agents/` (orchestrators + specialists)."""
    if not root.is_dir():
        return 0
    return len([p for p in root.glob("*.md") if p.is_file()])


def _manifest_total(section: str) -> int:
    """Read effective manifest totals after framework defaults injection."""
    config = load_manifest_config(REPO_ROOT)
    if section == "skills":
        return config.skills.total
    if section == "agents":
        return config.agents.total
    raise AssertionError(f"unsupported manifest section: {section}")


# ---------------------------------------------------------------------------
# Skill-count parity (the headline invariant for sub-005)
# ---------------------------------------------------------------------------


class TestSkillCountParity:
    def test_canonical_skill_count_matches_manifest(self) -> None:
        """`.claude/skills/` count matches `manifest.skills.total`."""
        expected = _manifest_total("skills")
        actual = _count_skill_dirs(CLAUDE_SKILLS)
        assert actual == expected, (
            f"manifest.skills.total = {expected} but `.claude/skills/` "
            f"contains {actual} skill directories on disk"
        )

    def test_antigravity_mirror_count_matches_canonical(self) -> None:
        canonical = _count_skill_dirs(CLAUDE_SKILLS, ide="antigravity")
        mirror = _count_skill_dirs(ANTIGRAVITY_SKILLS, ide="antigravity")
        assert mirror == canonical, (
            f".agents/skills/ has {mirror} entries; canonical .claude/skills/ has {canonical} "
            f"(provider-scoped opt-outs applied)"
        )


# ---------------------------------------------------------------------------
# Agent-count parity (orchestrator manifest entry)
# ---------------------------------------------------------------------------


class TestAgentCountParity:
    def test_orchestrator_count_matches_manifest(self) -> None:
        """`manifest.agents.total` covers ai-* orchestrators only.

        Specialist agents (reviewer-*, verifier-*, verify-*, review-*) are
        tracked separately by the sync script and are excluded from this
        count. The total disk count of `.claude/agents/*.md` is captured
        by `test_disk_agent_total_in_documented_range` below.
        """
        expected = _manifest_total("agents")
        # Orchestrator agents are `ai-*.md` only.
        orchestrators = sorted(p.name for p in CLAUDE_AGENTS.glob("ai-*.md"))
        actual = len(orchestrators)
        assert actual == expected, (
            f"manifest.agents.total = {expected} but `.claude/agents/ai-*.md` "
            f"contains {actual} orchestrator agents on disk: {orchestrators}"
        )

    def test_disk_agent_total_in_documented_range(self) -> None:
        """Total `.claude/agents/*.md` reflects the post-collapse roster.

        spec-140 W3 collapsed six reviewer/verifier specialists and spec-134
        promotes only 9 first-class `ai-*` orchestrators. The current canonical
        disk roster is 19 files: 9 orchestrators plus 10 internal reviewer /
        verifier support agents. This pins the achieved count so future
        accidental resurrection of deleted specialists is caught loudly.
        """
        actual = _count_agent_files(CLAUDE_AGENTS)
        assert actual == 19, (
            f"`.claude/agents/*.md` count is {actual}; spec-140 W3 collapse "
            "committed 19 canonical agent files. If you intentionally adjusted "
            "this, update the assertion + CHANGELOG."
        )
