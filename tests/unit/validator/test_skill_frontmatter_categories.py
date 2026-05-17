"""Tests for Category 7: Skill Frontmatter.

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
    _make_governance,
    _setup_full_project,
    _write_active_spec,
    _write_manifest,
)


class TestSkillFrontmatter:
    """Tests for skill-frontmatter validation."""

    def test_valid_frontmatter_passes(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.SKILL_FRONTMATTER],
        )
        assert report.category_passed(IntegrityCategory.SKILL_FRONTMATTER)

    def test_missing_frontmatter_fails(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        # Frontmatter validator scans IDE-specific dirs (.claude/skills/)
        bad_dir = tmp_path / ".claude" / "skills" / "bad-skill"
        bad_dir.mkdir(parents=True, exist_ok=True)
        (bad_dir / "SKILL.md").write_text("# bad-skill\n", encoding="utf-8")
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.SKILL_FRONTMATTER],
        )
        assert report.category_passed(IntegrityCategory.SKILL_FRONTMATTER) is False

    def test_invalid_requires_schema_fails(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        # Frontmatter validator scans IDE-specific dirs (.claude/skills/)
        bad_dir = tmp_path / ".claude" / "skills" / "bad-requires"
        bad_dir.mkdir(parents=True, exist_ok=True)
        (bad_dir / "SKILL.md").write_text(
            "---\n"
            "name: bad-requires\n"
            "version: 1.0.0\n"
            "requires:\n"
            "  bins: ruff\n"
            "---\n\n"
            "# bad-requires\n",
            encoding="utf-8",
        )
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.SKILL_FRONTMATTER],
        )
        assert report.category_passed(IntegrityCategory.SKILL_FRONTMATTER) is False


class TestSkillFrontmatterExtended:
    """Extended tests for skill frontmatter edge cases."""

    def test_invalid_yaml_frontmatter(self, tmp_path: Path) -> None:
        """Invalid YAML in frontmatter block is flagged."""
        _setup_full_project(tmp_path)
        bad_dir = tmp_path / ".claude" / "skills" / "bad-yaml"
        bad_dir.mkdir(parents=True, exist_ok=True)
        (bad_dir / "SKILL.md").write_text(
            "---\nname: bad-yaml\ninvalid: [unclosed\n---\n\n# bad-yaml\n",
            encoding="utf-8",
        )
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.SKILL_FRONTMATTER],
        )
        assert report.category_passed(IntegrityCategory.SKILL_FRONTMATTER) is False

    def test_frontmatter_not_a_mapping(self, tmp_path: Path) -> None:
        """Frontmatter that parses to a non-mapping type is flagged."""
        _setup_full_project(tmp_path)
        bad_dir = tmp_path / ".claude" / "skills" / "bad-type"
        bad_dir.mkdir(parents=True, exist_ok=True)
        (bad_dir / "SKILL.md").write_text(
            "---\n- just\n- a\n- list\n---\n\n# bad-type\n",
            encoding="utf-8",
        )
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.SKILL_FRONTMATTER],
        )
        assert report.category_passed(IntegrityCategory.SKILL_FRONTMATTER) is False

    def test_name_mismatch_fails(self, tmp_path: Path) -> None:
        """Skill name not matching directory name is flagged."""
        _setup_full_project(tmp_path)
        bad_dir = tmp_path / ".claude" / "skills" / "ai-mismatch"
        bad_dir.mkdir(parents=True, exist_ok=True)
        (bad_dir / "SKILL.md").write_text(
            "---\nname: ai-wrong-name\nversion: 1.0.0\n---\n\n# mismatch\n",
            encoding="utf-8",
        )
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.SKILL_FRONTMATTER],
        )
        fail_checks = [c for c in report.checks if c.name == "invalid-name"]
        assert len(fail_checks) >= 1

    def test_valid_os_field(self, tmp_path: Path) -> None:
        """Skill with valid os field passes."""
        _setup_full_project(tmp_path)
        skill_dir = tmp_path / ".claude" / "skills" / "ai-os-valid"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: ai-os-valid\nos:\n  - linux\n  - darwin\n---\n\n# os-valid\n",
            encoding="utf-8",
        )
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.SKILL_FRONTMATTER],
        )
        os_fails = [c for c in report.checks if c.name == "invalid-os-values"]
        assert len(os_fails) == 0

    def test_invalid_os_values(self, tmp_path: Path) -> None:
        """Skill with unsupported OS values is flagged."""
        _setup_full_project(tmp_path)
        skill_dir = tmp_path / ".claude" / "skills" / "ai-os-bad"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: ai-os-bad\nos:\n  - not-an-os\n---\n\n# os-bad\n",
            encoding="utf-8",
        )
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.SKILL_FRONTMATTER],
        )
        os_fails = [c for c in report.checks if c.name == "invalid-os-values"]
        assert len(os_fails) == 1

    def test_os_not_a_list(self, tmp_path: Path) -> None:
        """Skill with os field that is not a list is flagged."""
        _setup_full_project(tmp_path)
        skill_dir = tmp_path / ".claude" / "skills" / "ai-os-str"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: ai-os-str\nos: linux\n---\n\n# os-str\n",
            encoding="utf-8",
        )
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.SKILL_FRONTMATTER],
        )
        os_fails = [c for c in report.checks if c.name == "invalid-os"]
        assert len(os_fails) == 1

    def test_requires_valid_list_fields(self, tmp_path: Path) -> None:
        """Skill with valid requires list fields passes."""
        _setup_full_project(tmp_path)
        skill_dir = tmp_path / ".claude" / "skills" / "ai-req-valid"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: ai-req-valid\nrequires:\n  bins:\n    - ruff\n    - pytest\n---\n\n# req\n",
            encoding="utf-8",
        )
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.SKILL_FRONTMATTER],
        )
        req_fails = [c for c in report.checks if "invalid-requires" in c.name]
        assert len(req_fails) == 0

    def test_version_in_metadata_block(self, tmp_path: Path) -> None:
        """Skill with version in metadata sub-block is accepted."""
        _setup_full_project(tmp_path)
        skill_dir = tmp_path / ".claude" / "skills" / "ai-meta-ver"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: ai-meta-ver\nmetadata:\n  version: 2.0.0\n---\n\n# meta-ver\n",
            encoding="utf-8",
        )
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.SKILL_FRONTMATTER],
        )
        ver_fails = [c for c in report.checks if c.name == "invalid-version"]
        assert len(ver_fails) == 0

    def test_no_skill_dirs_returns_ok(self, tmp_path: Path) -> None:
        """No IDE skill directories results in OK skip."""
        ai = _make_governance(tmp_path)
        _write_manifest(ai)
        _write_active_spec(ai)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.SKILL_FRONTMATTER],
        )
        ok_checks = [
            c
            for c in report.checks
            if c.category == IntegrityCategory.SKILL_FRONTMATTER and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1
