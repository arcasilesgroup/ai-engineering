"""Tests for Category 2: Mirror Sync validation.

Split from tests/unit/test_validator.py during spec-140 W2.5.T4. Covers
canonical/template SHA-256 parity, per-IDE skill/agent mirrors,
generated-provenance frontmatter, and public root contracts.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.validator.service import (
    IntegrityCategory,
    IntegrityStatus,
    validate_content_integrity,
)

from .conftest import (
    _copilot_agents_pair,
    _frontmatter_with_provenance,
    _mirror_pair,
    _setup_full_project,
    _setup_governance_mirror,
)


def _mirror_report(tmp_path: Path):
    """Run validator for the MIRROR_SYNC category."""
    return validate_content_integrity(tmp_path, categories=[IntegrityCategory.MIRROR_SYNC])


def _mkdirs(*paths: Path) -> None:
    for p in paths:
        p.mkdir(parents=True)


class TestMirrorSync:
    """Tests for mirror-sync validation."""

    def test_non_source_repo_skips_mirrors(self, tmp_path: Path) -> None:
        """In a target project (no templates dir), mirror sync is skipped."""
        report = _mirror_report(tmp_path)
        assert report.passed is True
        skipped = [c for c in report.checks if c.name == "mirror-sync-skipped"]
        assert len(skipped) == 1

    def test_source_repo_missing_canonical_root(self, tmp_path: Path) -> None:
        """In the source repo, missing canonical root is a failure."""
        # Create templates dir so _is_source_repo returns True
        (tmp_path / "src" / "ai_engineering" / "templates").mkdir(parents=True)
        assert _mirror_report(tmp_path).passed is False

    def test_synced_mirrors_pass(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        mirror_root = tmp_path / "src" / "ai_engineering" / "templates" / ".ai-engineering"
        # Mirror governance files (contexts, runbooks, manifest, README)
        for subdir in ("contexts",):
            src_dir = ai / subdir
            if not src_dir.is_dir():
                continue
            for f in sorted(src_dir.rglob("*.md")):
                rel = f.relative_to(ai)
                dest = mirror_root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(f.read_bytes())
        # Mirror root-level files (manifest.yml, README.md)
        for root_file in ("manifest.yml", "README.md"):
            src = ai / root_file
            if src.is_file():
                dest = mirror_root / root_file
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(src.read_bytes())
        report = _mirror_report(tmp_path)
        governance_fails = [
            c
            for c in report.checks
            if c.category == IntegrityCategory.MIRROR_SYNC
            and c.status == IntegrityStatus.FAIL
            and "claude" not in c.name
        ]
        assert len(governance_fails) == 0

    def test_desynced_mirror_detected(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        # spec-136 D-136-01: governance mirror now syncs reference/**/*.md.
        canonical_ref = ai / "reference" / "principles.md"
        canonical_ref.parent.mkdir(parents=True, exist_ok=True)
        canonical_ref.write_text("CANONICAL CONTENT", encoding="utf-8")
        mirror_root = tmp_path / "src" / "ai_engineering" / "templates" / ".ai-engineering"
        for subdir in ("reference",):
            src_dir = ai / subdir
            if not src_dir.is_dir():
                continue
            for f in sorted(src_dir.rglob("*.md")):
                rel = f.relative_to(ai)
                dest = mirror_root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(f.read_bytes())
        for root_file in ("manifest.yml", "README.md"):
            src = ai / root_file
            if src.is_file():
                dest = mirror_root / root_file
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(src.read_bytes())
        # Desync a governance file that IS in the mirror pattern
        (mirror_root / "reference" / "principles.md").write_text(
            "DESYNCED CONTENT", encoding="utf-8"
        )
        desync_checks = [
            c
            for c in _mirror_report(tmp_path).checks
            if c.status == IntegrityStatus.FAIL and "desync" in c.name
        ]
        assert len(desync_checks) >= 1


class TestCopilotSkillsMirror:
    """Tests for Copilot skills mirror-sync validation."""

    def test_copilot_skills_mirror_sync_ok(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical, mirror = _mirror_pair(tmp_path, ".github", "skills", "ai-test")
        _mkdirs(canonical, mirror)
        content = _frontmatter_with_provenance(
            [("name", "ai-test"), ("mode", "agent")],
            family_id="copilot-skills",
            canonical_source=".claude/skills/ai-test/SKILL.md",
            body="Test skill.\n",
        )
        (canonical / "SKILL.md").write_text(content, encoding="utf-8")
        (mirror / "SKILL.md").write_text(content, encoding="utf-8")
        ok_checks = [
            c
            for c in _mirror_report(tmp_path).checks
            if c.name == "copilot-skills-mirrors" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_copilot_skills_mirror_desync(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical, mirror = _mirror_pair(tmp_path, ".github", "skills", "ai-test")
        _mkdirs(canonical, mirror)
        (canonical / "SKILL.md").write_text("canonical", encoding="utf-8")
        (mirror / "SKILL.md").write_text("different", encoding="utf-8")
        fail_checks = [
            c
            for c in _mirror_report(tmp_path).checks
            if c.status == IntegrityStatus.FAIL and "copilot-skill-desync" in c.name
        ]
        assert len(fail_checks) >= 1

    def test_copilot_skills_mirror_missing_root(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        # Create canonical skills but no mirror directory
        canonical, _mirror = _mirror_pair(tmp_path, ".github", "skills", "ai-test")
        canonical.mkdir(parents=True)
        (canonical / "SKILL.md").write_text("content", encoding="utf-8")
        fail_checks = [
            c
            for c in _mirror_report(tmp_path).checks
            if c.name == "copilot-skill-mirror-root" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1

    def test_copilot_skills_missing_mirror_file(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical, _ = _mirror_pair(tmp_path, ".github", "skills", "ai-orphan")
        _, mirror_parent = _mirror_pair(tmp_path, ".github", "skills")
        canonical.mkdir(parents=True)
        mirror_parent.mkdir(parents=True, exist_ok=True)
        # File exists in canonical but not in mirror
        (canonical / "SKILL.md").write_text("content", encoding="utf-8")
        fail_checks = [
            c
            for c in _mirror_report(tmp_path).checks
            if c.status == IntegrityStatus.FAIL and "copilot-skill-missing" in c.name
        ]
        assert len(fail_checks) >= 1


class TestClaudeSkillsMirror:
    """Tests for Claude skills mirror-sync validation."""

    def test_claude_skills_mirror_sync_ok(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical, mirror = _mirror_pair(tmp_path, ".claude", "skills", "ai-test")
        _mkdirs(canonical, mirror)
        content = "---\nname: ai-test\nmode: agent\n---\nTest skill.\n"
        (canonical / "SKILL.md").write_text(content, encoding="utf-8")
        (mirror / "SKILL.md").write_text(content, encoding="utf-8")
        ok_checks = [
            c
            for c in _mirror_report(tmp_path).checks
            if c.name == "claude-skills-mirrors" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_claude_skills_mirror_desync(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical, mirror = _mirror_pair(tmp_path, ".claude", "skills", "ai-test")
        _mkdirs(canonical, mirror)
        (canonical / "SKILL.md").write_text("canonical", encoding="utf-8")
        (mirror / "SKILL.md").write_text("different", encoding="utf-8")
        fail_checks = [
            c
            for c in _mirror_report(tmp_path).checks
            if c.status == IntegrityStatus.FAIL and "claude-skill-desync" in c.name
        ]
        assert len(fail_checks) >= 1


class TestClaudeAgentsMirror:
    """Tests for Claude agents mirror-sync validation."""

    def test_claude_agents_mirror_sync_ok(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical, mirror = _mirror_pair(tmp_path, ".claude", "agents")
        _mkdirs(canonical, mirror)
        content = "---\nname: ai-test\ndescription: test\n---\nAgent.\n"
        (canonical / "ai-test.md").write_text(content, encoding="utf-8")
        (mirror / "ai-test.md").write_text(content, encoding="utf-8")
        ok_checks = [
            c
            for c in _mirror_report(tmp_path).checks
            if c.name == "claude-agents-mirrors" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_claude_agents_missing_mirror_file(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical, mirror = _mirror_pair(tmp_path, ".claude", "agents")
        _mkdirs(canonical, mirror)
        (canonical / "ai-orphan.md").write_text("content", encoding="utf-8")
        fail_checks = [
            c
            for c in _mirror_report(tmp_path).checks
            if c.status == IntegrityStatus.FAIL and "claude-agent-missing" in c.name
        ]
        assert len(fail_checks) >= 1


class TestClaudeSpecialistAgentsMirror:
    """Tests for generated Claude specialist agent mirror-sync validation."""

    def test_claude_specialist_agents_mirror_sync_ok(self, tmp_path: Path) -> None:
        from scripts.sync_command_mirrors import generate_specialist_agent

        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical, mirror = _mirror_pair(tmp_path, ".claude", "agents")
        _mkdirs(canonical, mirror)

        specialist = canonical / "reviewer-correctness.md"
        specialist.write_text(
            "---\nname: reviewer-correctness\ndescription: test\nmodel: opus\n"
            "color: cyan\ntools: [Read]\n---\n\nBody\n",
            encoding="utf-8",
        )
        (mirror / specialist.name).write_text(
            generate_specialist_agent(specialist),
            encoding="utf-8",
        )

        ok_checks = [
            c
            for c in _mirror_report(tmp_path).checks
            if c.name == "claude-specialist-agents-mirrors" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_claude_specialist_agents_mirror_desync(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical, mirror = _mirror_pair(tmp_path, ".claude", "agents")
        _mkdirs(canonical, mirror)

        specialist = canonical / "reviewer-correctness.md"
        specialist.write_text(
            "---\nname: reviewer-correctness\ndescription: test\nmodel: opus\n"
            "color: cyan\ntools: [Read]\n---\n\nBody\n",
            encoding="utf-8",
        )
        (mirror / specialist.name).write_text("different", encoding="utf-8")

        fail_checks = [
            c
            for c in _mirror_report(tmp_path).checks
            if c.status == IntegrityStatus.FAIL
            and "claude-specialist-agent-desync-reviewer-correctness.md" in c.name
        ]
        assert len(fail_checks) >= 1


class TestCodexSkillsMirror:
    """Tests for .codex skills mirror-sync validation."""

    def test_codex_skills_mirror_sync_ok(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical, mirror = _mirror_pair(tmp_path, ".codex", "skills", "ai-test")
        _mkdirs(canonical, mirror)
        content = _frontmatter_with_provenance(
            [("name", "ai-test"), ("mode", "agent")],
            family_id="codex-skills",
            canonical_source=".claude/skills/ai-test/SKILL.md",
            body="Skill.\n",
        )
        (canonical / "SKILL.md").write_text(content, encoding="utf-8")
        (mirror / "SKILL.md").write_text(content, encoding="utf-8")
        ok_checks = [
            c
            for c in _mirror_report(tmp_path).checks
            if c.name == "codex-skills-mirrors" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1


class TestCodexAgentsMirror:
    """Tests for .codex agents mirror-sync validation."""

    def test_codex_agents_mirror_sync_ok(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical, mirror = _mirror_pair(tmp_path, ".codex", "agents")
        _mkdirs(canonical, mirror)
        content = _frontmatter_with_provenance(
            [("name", "ai-test"), ("description", "test")],
            family_id="codex-agents",
            canonical_source=".claude/agents/ai-test.md",
            body="Agent.\n",
        )
        (canonical / "ai-test.md").write_text(content, encoding="utf-8")
        (mirror / "ai-test.md").write_text(content, encoding="utf-8")
        ok_checks = [
            c
            for c in _mirror_report(tmp_path).checks
            if c.name == "codex-agents-mirrors" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1


class TestCopilotAgentsMirror:
    """Tests for Copilot agents mirror-sync validation."""

    def test_copilot_agents_mirror_sync_ok(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical, mirror = _copilot_agents_pair(tmp_path)
        _mkdirs(canonical, mirror)
        content = _frontmatter_with_provenance(
            [("name", "Test"), ("description", "test")],
            family_id="copilot-agents",
            canonical_source=".claude/agents/ai-test.md",
            body="Test agent.\n",
        )
        (canonical / "test.agent.md").write_text(content, encoding="utf-8")
        (mirror / "test.agent.md").write_text(content, encoding="utf-8")
        ok_checks = [
            c
            for c in _mirror_report(tmp_path).checks
            if c.name == "copilot-agents-mirrors" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_copilot_agents_mirror_desync(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical, mirror = _copilot_agents_pair(tmp_path)
        _mkdirs(canonical, mirror)
        (canonical / "test.agent.md").write_text("canonical", encoding="utf-8")
        (mirror / "test.agent.md").write_text("different", encoding="utf-8")
        fail_checks = [
            c
            for c in _mirror_report(tmp_path).checks
            if c.status == IntegrityStatus.FAIL and "copilot-agent-desync" in c.name
        ]
        assert len(fail_checks) >= 1

    def test_copilot_agents_mirror_missing_root(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical, _mirror = _copilot_agents_pair(tmp_path)
        canonical.mkdir(parents=True)
        (canonical / "test.agent.md").write_text("content", encoding="utf-8")
        fail_checks = [
            c
            for c in _mirror_report(tmp_path).checks
            if c.name == "copilot-agent-mirror-root" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1

    def test_copilot_agents_missing_mirror_file(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical, mirror = _copilot_agents_pair(tmp_path)
        _mkdirs(canonical, mirror)
        (canonical / "orphan.agent.md").write_text("content", encoding="utf-8")
        fail_checks = [
            c
            for c in _mirror_report(tmp_path).checks
            if c.status == IntegrityStatus.FAIL and "copilot-agent-missing" in c.name
        ]
        assert len(fail_checks) >= 1


class TestGeneratedMirrorProvenance:
    """Tests for negative provenance validation on generated mirrors."""

    def test_generated_codex_skill_missing_provenance_fails_even_when_pair_matches(
        self, tmp_path: Path
    ) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical, mirror = _mirror_pair(tmp_path, ".codex", "skills", "ai-test")
        _mkdirs(canonical, mirror)
        content = "---\nname: ai-test\nmode: agent\n---\n\nSkill.\n"
        (canonical / "SKILL.md").write_text(content, encoding="utf-8")
        (mirror / "SKILL.md").write_text(content, encoding="utf-8")

        report = _mirror_report(tmp_path)
        fail_checks = [
            c
            for c in report.checks
            if c.status == IntegrityStatus.FAIL
            and c.name.startswith("generated-provenance-codex-skills")
        ]
        assert len(fail_checks) >= 1
        assert report.category_passed(IntegrityCategory.MIRROR_SYNC) is False


class TestPublicAgentRootContract:
    """Tests for rejecting ungoverned entries in public agent roots."""

    def test_copilot_public_agent_root_rejects_stray_specialist_peer(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical, mirror = _copilot_agents_pair(tmp_path)
        _mkdirs(canonical, mirror)

        content = "---\nname: reviewer-bad\ndescription: test\n---\n\nBad peer.\n"
        (canonical / "reviewer-bad.md").write_text(content, encoding="utf-8")
        (mirror / "reviewer-bad.md").write_text(content, encoding="utf-8")

        report = _mirror_report(tmp_path)
        fail_checks = [
            c
            for c in report.checks
            if c.status == IntegrityStatus.FAIL
            and c.name.startswith("ungoverned-public-agent-entry-")
        ]
        assert len(fail_checks) >= 1
        assert report.category_passed(IntegrityCategory.MIRROR_SYNC) is False


class TestPublicSkillRootContract:
    """Tests for rejecting ungoverned entries in public skill roots."""

    def test_copilot_public_skill_root_rejects_ungoverned_directory(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical, mirror = _mirror_pair(tmp_path, ".github", "skills", "reviewer-bad")
        _mkdirs(canonical, mirror)
        (canonical / "SKILL.md").write_text("# Bad skill\n", encoding="utf-8")
        (mirror / "SKILL.md").write_text("# Bad skill\n", encoding="utf-8")

        report = _mirror_report(tmp_path)
        fail_checks = [
            c
            for c in report.checks
            if c.status == IntegrityStatus.FAIL
            and c.name.startswith("ungoverned-public-skill-entry-")
        ]
        assert len(fail_checks) >= 1
        assert report.category_passed(IntegrityCategory.MIRROR_SYNC) is False


class TestNonClaudeLocalReferenceLeaks:
    """Tests for rejecting leaked Claude-local skill/agent paths."""

    def test_copilot_skill_script_rejects_claude_skill_path_leak_even_when_pair_matches(
        self, tmp_path: Path
    ) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical, mirror = _mirror_pair(tmp_path, ".github", "skills", "ai-test")
        canonical = canonical / "scripts"
        mirror = mirror / "scripts"
        _mkdirs(canonical, mirror)

        content = 'SKILL_DIR=".claude/skills/ai-${SKILL_NAME}"\n'
        (canonical / "scaffold-skill.sh").write_text(content, encoding="utf-8")
        (mirror / "scaffold-skill.sh").write_text(content, encoding="utf-8")

        report = _mirror_report(tmp_path)
        fail_checks = [
            c
            for c in report.checks
            if c.status == IntegrityStatus.FAIL
            and c.name.startswith("non-claude-local-reference-leak-")
        ]
        assert len(fail_checks) >= 1
        assert report.category_passed(IntegrityCategory.MIRROR_SYNC) is False

    def test_generated_copilot_agent_wrong_canonical_source_fails_even_when_pair_matches(
        self, tmp_path: Path
    ) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical, mirror = _copilot_agents_pair(tmp_path)
        _mkdirs(canonical, mirror)

        content = _frontmatter_with_provenance(
            [("name", "Test"), ("description", "test")],
            family_id="copilot-agents",
            canonical_source=".claude/agents/build.md",
            body="Test agent.\n",
        )
        (canonical / "test.agent.md").write_text(content, encoding="utf-8")
        (mirror / "test.agent.md").write_text(content, encoding="utf-8")

        report = _mirror_report(tmp_path)
        fail_checks = [
            c
            for c in report.checks
            if c.status == IntegrityStatus.FAIL
            and c.name.startswith("generated-provenance-copilot-agents")
        ]
        assert len(fail_checks) >= 1
        assert report.category_passed(IntegrityCategory.MIRROR_SYNC) is False


# spec-128 D-128-04, D-128-07: TestGeneratedInstructionsMirror class removed.
# .github/instructions/ surface deleted entirely; mirror validation no longer applies.
