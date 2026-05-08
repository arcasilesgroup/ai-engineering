"""Mirror count-parity tests for spec-127 sub-005 (M4) — renames + mergers.

Asserts the canonical surface counts are stable across all IDE mirror trees:

* `.claude/skills/` (canonical source)
* `.github/skills/` (Copilot Agent Skills mirror)
* `.codex/skills/` (Codex IDE skills mirror)
* `.gemini/skills/` (Gemini CLI skills mirror)

The disk count target landed by sub-005 is documented in
`.ai-engineering/manifest.yml skills.total`. The umbrella spec target was
46/23; sub-005 achieved 48 skills and 24 agents on disk (see CHANGELOG M4
section for the gap explanation). The test reads the achieved counts from
the manifest as the single source of truth so it remains correct under
future rename / merger waves without churn here.

Each test surfaces the *count parity* invariant — every IDE mirror tree
must contain the same number of skill directories as the canonical
`.claude/skills/` source.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CLAUDE_SKILLS = REPO_ROOT / ".claude" / "skills"
CLAUDE_AGENTS = REPO_ROOT / ".claude" / "agents"
GITHUB_SKILLS = REPO_ROOT / ".github" / "skills"
CODEX_SKILLS = REPO_ROOT / ".codex" / "skills"
GEMINI_SKILLS = REPO_ROOT / ".gemini" / "skills"
MANIFEST = REPO_ROOT / ".ai-engineering" / "manifest.yml"


# Provider-scoped skills that opt out of specific IDE mirrors.
# Documented in `.claude/skills/ai-create/SKILL.md`. ai-analyze-permissions
# is Claude-Code-only and never appears in `.github/`, `.codex/`, `.gemini/`.
PROVIDER_SCOPED_SKIPS: dict[str, set[str]] = {
    "github": {"ai-analyze-permissions"},
    "codex": set(),
    "gemini": set(),
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
    """Tiny pyyaml-free reader for `manifest.yml <section>.total`."""
    text = MANIFEST.read_text(encoding="utf-8")
    in_section = False
    for line in text.splitlines():
        if re.match(rf"^{re.escape(section)}:\s*$", line):
            in_section = True
            continue
        if in_section:
            if line and not line.startswith((" ", "\t")):
                in_section = False
                continue
            stripped = line.lstrip()
            if stripped.startswith("total:"):
                return int(stripped.split(":", 1)[1].strip())
    raise AssertionError(f"manifest.yml is missing {section}.total")


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

    def test_github_mirror_count_matches_canonical(self) -> None:
        canonical = _count_skill_dirs(CLAUDE_SKILLS, ide="github")
        mirror = _count_skill_dirs(GITHUB_SKILLS, ide="github")
        assert mirror == canonical, (
            f".github/skills/ has {mirror} entries; canonical .claude/skills/ has {canonical} "
            f"(provider-scoped opt-outs applied)"
        )

    def test_codex_mirror_count_matches_canonical(self) -> None:
        canonical = _count_skill_dirs(CLAUDE_SKILLS, ide="codex")
        mirror = _count_skill_dirs(CODEX_SKILLS, ide="codex")
        assert mirror == canonical, (
            f".codex/skills/ has {mirror} entries; canonical .claude/skills/ has {canonical} "
            f"(provider-scoped opt-outs applied)"
        )

    def test_gemini_mirror_count_matches_canonical(self) -> None:
        canonical = _count_skill_dirs(CLAUDE_SKILLS, ide="gemini")
        mirror = _count_skill_dirs(GEMINI_SKILLS, ide="gemini")
        assert mirror == canonical, (
            f".gemini/skills/ has {mirror} entries; canonical .claude/skills/ has {canonical} "
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
        """Total `.claude/agents/*.md` count is the value committed by sub-005.

        spec-127 umbrella target was 23 agents end-to-end; sub-005 achieved
        24 (`reviewer-design` content was merged into `reviewer-frontend`,
        `ai-run-orchestrator` deleted; the 23 target also assumed an
        additional consolidation that did not materialise — see CHANGELOG
        M4 section for the explanation). This test pins the achieved
        count so future regressions are caught loudly.
        """
        actual = _count_agent_files(CLAUDE_AGENTS)
        assert actual == 24, (
            f"`.claude/agents/*.md` count is {actual}; sub-005 "
            f"committed 24 (M4 audit). If you intentionally adjusted this, "
            f"update the assertion + CHANGELOG."
        )
