"""Tests for Category 3: Counter Accuracy + Category 4: Cross-Reference Integrity.

Split from tests/unit/test_validator.py during spec-140 W2.5.T4.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.validator.service import (
    IntegrityCategory,
    IntegrityStatus,
    validate_content_integrity,
)

from .conftest import (
    _AGENT_PATHS,
    _SKILL_PATHS,
    _make_governance,
    _make_instruction_content,
    _setup_full_project,
    _write_active_spec,
    _write_all_instruction_files,
    _write_manifest,
    _write_readme,
)


class TestCounterAccuracy:
    """Tests for counter-accuracy validation."""

    def test_consistent_counts_pass(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.COUNTER_ACCURACY],
        )
        assert report.category_passed(IntegrityCategory.COUNTER_ACCURACY)

    def test_mismatched_skill_counts_detected(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        shorter = _make_instruction_content(skills=_SKILL_PATHS[:-1])
        (tmp_path / "AGENTS.md").write_text(shorter, encoding="utf-8")
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.COUNTER_ACCURACY],
        )
        fail_checks = [
            c
            for c in report.checks
            if c.category == IntegrityCategory.COUNTER_ACCURACY and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) >= 1

    def test_missing_instruction_file(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        (tmp_path / "CLAUDE.md").unlink()
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.COUNTER_ACCURACY],
        )
        fail_checks = [
            c for c in report.checks if c.status == IntegrityStatus.FAIL and "missing" in c.name
        ]
        assert len(fail_checks) >= 1

    def test_table_format_counts_detected(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        skill_row = "| " + ", ".join(s.split("/")[1] for s in _SKILL_PATHS) + " |"
        lines = [
            "# Instructions",
            "",
            f"## Skills ({len(_SKILL_PATHS)})",
            "",
            "| Skills (alphabetical) |",
            "|-----------------------|",
            skill_row,
            "",
            f"## Agents ({len(_AGENT_PATHS)})",
            "",
            "| Agent | Purpose | Scope |",
            "|-------|---------|-------|",
        ]
        for agent in _AGENT_PATHS:
            agent_name = Path(agent).stem
            lines.append(f"| {agent_name} | test purpose | read-write |")
        table_content = "\n".join(lines) + "\n"

        _write_all_instruction_files(tmp_path, content=table_content)

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.COUNTER_ACCURACY],
        )

        assert report.category_passed(IntegrityCategory.COUNTER_ACCURACY)


class TestCrossReference:
    """Tests for cross-reference validation."""

    def test_valid_references_pass(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        # Cross-reference validator scans IDE-specific dirs (.claude/skills/)
        # Reference ai-commit which exists in the setup via _SKILL_PATHS
        skill_dir = tmp_path / ".claude" / "skills" / "ai-debug"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            "# Debug\n\n## References\n\n- `skills/ai-commit/SKILL.md`\n",
            encoding="utf-8",
        )
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.CROSS_REFERENCE],
        )
        assert report.category_passed(IntegrityCategory.CROSS_REFERENCE)

    def test_broken_reference_detected(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        # Cross-reference validator scans IDE-specific dirs (.claude/skills/)
        skill_dir = tmp_path / ".claude" / "skills" / "debug"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            "# Debug\n\n## References\n\n- `skills/nonexistent/SKILL.md`\n",
            encoding="utf-8",
        )
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.CROSS_REFERENCE],
        )
        assert report.category_passed(IntegrityCategory.CROSS_REFERENCE) is False

    def test_no_governance_dir_skips(self, tmp_path: Path) -> None:
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.CROSS_REFERENCE],
        )
        assert report.passed is True


class TestCounterAccuracyPointerFormat:
    """Tests for pointer-format counting (Skills (N) / Agents (N)) in instruction files."""

    def test_pointer_format_consistent(self, tmp_path: Path) -> None:
        """Instruction files using 'Skills (N)' pointer format produce consistent counts."""
        ai = _make_governance(tmp_path)
        _write_manifest(ai)
        _write_readme(ai)
        _write_active_spec(ai)

        pointer_content = (
            "# Instructions\n\n"
            "## Skills (5)\n\nSee skills directory for details.\n\n"
            "## Agents (3)\n\nSee agents directory for details.\n"
        )
        _write_all_instruction_files(tmp_path, content=pointer_content)

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.COUNTER_ACCURACY],
        )
        ok_checks = [
            c
            for c in report.checks
            if c.category == IntegrityCategory.COUNTER_ACCURACY
            and c.status == IntegrityStatus.OK
            and "consistent" in c.name
        ]
        assert len(ok_checks) >= 1

    def test_agent_count_mismatch_detected(self, tmp_path: Path) -> None:
        """Mismatched agent counts across instruction files are flagged."""
        _setup_full_project(tmp_path)
        # Overwrite one file with different agent list
        shorter_agents = _AGENT_PATHS[:-1]
        shorter = _make_instruction_content(agents=shorter_agents)
        (tmp_path / "AGENTS.md").write_text(shorter, encoding="utf-8")
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.COUNTER_ACCURACY],
        )
        fail_checks = [
            c
            for c in report.checks
            if c.category == IntegrityCategory.COUNTER_ACCURACY
            and c.status == IntegrityStatus.FAIL
            and "agent-count-mismatch" in c.name
        ]
        assert len(fail_checks) >= 1

    def test_no_instruction_files_returns_empty(self, tmp_path: Path) -> None:
        """No instruction files results in no counter checks (early return)."""
        ai = _make_governance(tmp_path)
        _write_manifest(ai)
        _write_active_spec(ai)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.COUNTER_ACCURACY],
        )
        counter_checks = [
            c for c in report.checks if c.category == IntegrityCategory.COUNTER_ACCURACY
        ]
        # With no files found, the checker returns early -- no results
        assert all(c.name.startswith("missing-") for c in counter_checks)


class TestCounterAccuracyManifest:
    """Tests for manifest.yml skill/agent count matching."""

    def test_manifest_skill_mismatch(self, tmp_path: Path) -> None:
        """Manifest skills.total != instruction file count is flagged."""
        ai = _make_governance(tmp_path)
        _write_readme(ai)
        _write_active_spec(ai)
        # Manifest with skills.total = 99 (wrong)
        _write_manifest(
            ai,
            providers=("claude-code",),
            skills_total=99,
            agents_total=0,
        )
        _write_all_instruction_files(tmp_path)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.COUNTER_ACCURACY],
        )
        fail_checks = [
            c
            for c in report.checks
            if c.name == "manifest-skills" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "99" in fail_checks[0].message

    def test_manifest_skill_match(self, tmp_path: Path) -> None:
        """Manifest skills.total matching instruction file count passes."""
        ai = _make_governance(tmp_path)
        _write_readme(ai)
        _write_active_spec(ai)
        skill_count = len(_SKILL_PATHS)
        _write_manifest(
            ai,
            providers=("claude-code",),
            skills_total=skill_count,
            agents_total=0,
        )
        _write_all_instruction_files(tmp_path)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.COUNTER_ACCURACY],
        )
        ok_checks = [
            c
            for c in report.checks
            if c.name == "manifest-skills" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_manifest_agent_mismatch(self, tmp_path: Path) -> None:
        """Manifest agents.total != instruction file count is flagged."""
        ai = _make_governance(tmp_path)
        _write_readme(ai)
        _write_active_spec(ai)
        _write_manifest(
            ai,
            providers=("claude-code",),
            skills_total=0,
            agents_total=99,
        )
        _write_all_instruction_files(tmp_path)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.COUNTER_ACCURACY],
        )
        fail_checks = [
            c
            for c in report.checks
            if c.name == "manifest-agents" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "99" in fail_checks[0].message

    def test_manifest_agent_match(self, tmp_path: Path) -> None:
        """Manifest agents.total matching instruction file count passes."""
        ai = _make_governance(tmp_path)
        _write_readme(ai)
        _write_active_spec(ai)
        agent_count = len(_AGENT_PATHS)
        _write_manifest(
            ai,
            providers=("claude-code",),
            skills_total=0,
            agents_total=agent_count,
        )
        _write_all_instruction_files(tmp_path)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.COUNTER_ACCURACY],
        )
        ok_checks = [
            c
            for c in report.checks
            if c.name == "manifest-agents" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1
