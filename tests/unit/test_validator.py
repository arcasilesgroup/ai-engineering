"""Tests for ai_engineering.validator.service -- content integrity validation."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from ai_engineering.validator._shared import (
    FileCache,
    _extract_listings,
    _extract_section,
    _extract_subsection,
    _glob_files,
    _instruction_files,
    _is_excluded,
    _is_source_repo,
    _is_table_separator,
    _parse_agent_names,
    _parse_agent_names_from_subsection,
    _parse_skill_names,
    _parse_skill_names_from_subsection,
)
from ai_engineering.validator.service import (
    IntegrityCategory,
    IntegrityCheckResult,
    IntegrityReport,
    IntegrityStatus,
    _parse_counter,
    validate_content_integrity,
)

pytestmark = pytest.mark.unit


# -- Helpers ----------------------------------------------------------------

# Dynamic discovery from real project — never hardcode lists that can drift.
# Canonical source is templates/project/.claude/ (skills and agents live here post spec-055).
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TEMPLATES_CLAUDE_DIR = (
    _PROJECT_ROOT / "src" / "ai_engineering" / "templates" / "project" / ".claude"
)

_SKILL_PATHS = sorted(
    f"skills/{d.name}/SKILL.md"
    for d in (_TEMPLATES_CLAUDE_DIR / "skills").iterdir()
    if d.is_dir() and (d / "SKILL.md").is_file()
)

_AGENT_PATHS = sorted(f"agents/{f.name}" for f in (_TEMPLATES_CLAUDE_DIR / "agents").glob("*.md"))


def _make_governance(root: Path) -> Path:
    """Create a minimal .ai-engineering governance tree."""
    ai = root / ".ai-engineering"
    for d in [
        "contexts/languages",
        "contexts/frameworks",
        "contexts/team",
        "specs",
        "state",
    ]:
        (ai / d).mkdir(parents=True, exist_ok=True)
    return ai


def _write_skill(ai: Path, rel: str) -> None:
    """Create a skill/agent markdown file.

    Skills use flat directory layout: skills/<name>/SKILL.md
    Agents remain flat: agents/<name>.md
    """
    path = ai / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if rel.startswith("skills/"):
        # Flat layout: name = parent dir
        skill_name = path.parent.name
        path.write_text(
            (f"---\nname: {skill_name}\nversion: 1.0.0\n---\n\n# {skill_name}\n"),
            encoding="utf-8",
        )
    else:
        path.write_text(f"# {path.stem}\n", encoding="utf-8")


def _make_instruction_content(
    skills: list[str] | None = None,
    agents: list[str] | None = None,
) -> str:
    """Build instruction file content with skill/agent listings (IDE-specific paths).

    The parser (_SKILL_PATH_PATTERN / _AGENT_PATH_PATTERN) expects IDE-specific
    paths like ``.claude/skills/<name>/SKILL.md`` — not ``.ai-engineering/``.
    """
    skill_list = skills if skills is not None else _SKILL_PATHS
    agent_list = agents if agents is not None else _AGENT_PATHS
    lines = ["# Instructions", "", "## Skills", ""]
    for s in skill_list:
        lines.append(f"- `.claude/{s}`")
    lines.append("")
    lines.extend(["## Agents", ""])
    for a in agent_list:
        lines.append(f"- `.claude/{a}`")
    lines.append("")
    return "\n".join(lines)


def _write_all_instruction_files(
    root: Path,
    content: str | None = None,
) -> None:
    """Write identical instruction files to all 8 standard locations."""
    text = content if content is not None else _make_instruction_content()
    files = [
        root / ".github" / "copilot-instructions.md",
        root / "AGENTS.md",
        root / "CLAUDE.md",
        root / "src" / "ai_engineering" / "templates" / "project" / "copilot-instructions.md",
        root / "src" / "ai_engineering" / "templates" / "project" / "AGENTS.md",
        root / "src" / "ai_engineering" / "templates" / "project" / "CLAUDE.md",
    ]
    for f in files:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")


def _write_manifest(ai: Path) -> None:
    """Write a minimal manifest.yml."""
    m = ai / "manifest.yml"
    m.write_text(
        "name: test-project\nversion: 1.0.0\n"
        "ownership:\n  external_framework_managed:\n"
        "    - AGENTS.md\n    - CLAUDE.md\n",
        encoding="utf-8",
    )


def _write_active_spec(
    ai: Path,
    spec_name: str = "006-test",
) -> Path:
    """Write Working Buffer spec.md and plan.md."""
    specs_dir = ai / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / "spec.md").write_text(
        f'---\nid: "006"\n---\n\n# {spec_name}\n\nTest spec.\n',
        encoding="utf-8",
    )
    (specs_dir / "plan.md").write_text(
        "---\ntotal: 3\ncompleted: 1\n---\n\n# Plan\n\n- [x] Done\n- [ ] Todo\n- [ ] Todo\n",
        encoding="utf-8",
    )
    return specs_dir


def _write_readme(ai: Path) -> None:
    """Write a minimal README.md for the governance tree."""
    readme = ai / "README.md"
    readme.write_text("# ai-engineering\n\nGovernance framework.\n", encoding="utf-8")


def _setup_full_project(root: Path) -> Path:
    """Set up a complete project for happy-path testing."""
    ai = _make_governance(root)
    for s in _SKILL_PATHS:
        _write_skill(ai, s)
    for a in _AGENT_PATHS:
        _write_skill(ai, a)
    _write_all_instruction_files(root)
    _write_manifest(ai)
    _write_readme(ai)
    _write_active_spec(ai)
    return ai


# -- _parse_counter tests -------------------------------------------------


class TestParseCounter:
    """Tests for _parse_counter plain-string parsing (ReDoS-safe)."""

    def test_comma_separated_objective(self) -> None:
        text = "Complete governance content: 37 skills, 9 agents."
        result = _parse_counter(text, ",")
        assert result == (37, 9)

    def test_plus_separated_kpi(self) -> None:
        text = "| Agent coverage | 37 skills + 9 agents | 37/37 |"
        result = _parse_counter(text, "+")
        assert result == (37, 9)

    def test_singular_forms(self) -> None:
        text = "1 skill, 1 agent"
        result = _parse_counter(text, ",")
        assert result == (1, 1)

    def test_no_match_returns_none(self) -> None:
        text = "No counters here at all."
        result = _parse_counter(text, ",")
        assert result is None

    def test_multiline_finds_first_match(self) -> None:
        text = "Header line\n37 skills, 9 agents\nAnother line"
        result = _parse_counter(text, ",")
        assert result == (37, 9)

    def test_empty_text(self) -> None:
        result = _parse_counter("", ",")
        assert result is None

    def test_separator_missing(self) -> None:
        text = "37 skills and 9 agents"
        result = _parse_counter(text, ",")
        assert result is None


# -- IntegrityReport model tests -------------------------------------------


class TestIntegrityReport:
    """Tests for IntegrityReport dataclass."""

    def test_empty_report_passes(self) -> None:
        report = IntegrityReport()
        assert report.passed is True
        assert report.summary == {}

    def test_report_with_ok_passes(self) -> None:
        report = IntegrityReport(
            checks=[
                IntegrityCheckResult(
                    category=IntegrityCategory.FILE_EXISTENCE,
                    name="test",
                    status=IntegrityStatus.OK,
                    message="all good",
                ),
            ]
        )
        assert report.passed is True

    def test_report_with_fail_does_not_pass(self) -> None:
        report = IntegrityReport(
            checks=[
                IntegrityCheckResult(
                    category=IntegrityCategory.FILE_EXISTENCE,
                    name="test",
                    status=IntegrityStatus.FAIL,
                    message="broken",
                ),
            ]
        )
        assert report.passed is False

    def test_report_with_warn_still_passes(self) -> None:
        report = IntegrityReport(
            checks=[
                IntegrityCheckResult(
                    category=IntegrityCategory.FILE_EXISTENCE,
                    name="test",
                    status=IntegrityStatus.WARN,
                    message="warning",
                ),
            ]
        )
        assert report.passed is True

    def test_summary_counts(self) -> None:
        report = IntegrityReport(
            checks=[
                IntegrityCheckResult(
                    category=IntegrityCategory.FILE_EXISTENCE,
                    name="a",
                    status=IntegrityStatus.OK,
                    message="",
                ),
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name="b",
                    status=IntegrityStatus.FAIL,
                    message="",
                ),
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name="c",
                    status=IntegrityStatus.FAIL,
                    message="",
                ),
                IntegrityCheckResult(
                    category=IntegrityCategory.COUNTER_ACCURACY,
                    name="d",
                    status=IntegrityStatus.WARN,
                    message="",
                ),
            ]
        )
        assert report.summary == {"ok": 1, "fail": 2, "warn": 1}

    def test_by_category(self) -> None:
        report = IntegrityReport(
            checks=[
                IntegrityCheckResult(
                    category=IntegrityCategory.FILE_EXISTENCE,
                    name="a",
                    status=IntegrityStatus.OK,
                    message="",
                ),
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name="b",
                    status=IntegrityStatus.FAIL,
                    message="",
                ),
            ]
        )
        cats = report.by_category()
        assert IntegrityCategory.FILE_EXISTENCE in cats
        assert IntegrityCategory.MIRROR_SYNC in cats
        assert len(cats[IntegrityCategory.FILE_EXISTENCE]) == 1

    def test_category_passed(self) -> None:
        report = IntegrityReport(
            checks=[
                IntegrityCheckResult(
                    category=IntegrityCategory.FILE_EXISTENCE,
                    name="a",
                    status=IntegrityStatus.OK,
                    message="",
                ),
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name="b",
                    status=IntegrityStatus.FAIL,
                    message="",
                ),
            ]
        )
        assert report.category_passed(IntegrityCategory.FILE_EXISTENCE) is True
        assert report.category_passed(IntegrityCategory.MIRROR_SYNC) is False

    def test_to_dict_structure(self) -> None:
        report = IntegrityReport(
            checks=[
                IntegrityCheckResult(
                    category=IntegrityCategory.FILE_EXISTENCE,
                    name="a",
                    status=IntegrityStatus.OK,
                    message="ok msg",
                ),
            ]
        )
        d = report.to_dict()
        assert d["passed"] is True
        assert "summary" in d
        assert "categories" in d
        assert "file-existence" in d["categories"]

    def test_to_dict_includes_file_path(self) -> None:
        report = IntegrityReport(
            checks=[
                IntegrityCheckResult(
                    category=IntegrityCategory.FILE_EXISTENCE,
                    name="a",
                    status=IntegrityStatus.FAIL,
                    message="broken",
                    file_path="some/file.md",
                ),
            ]
        )
        d = report.to_dict()
        checks = d["categories"]["file-existence"]["checks"]
        assert checks[0]["file"] == "some/file.md"


# -- Category 1: File Existence -------------------------------------------


class TestFileExistence:
    """Tests for file-existence validation."""

    def test_missing_governance_directory(self, tmp_path: Path) -> None:
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.FILE_EXISTENCE],
        )
        assert report.passed is False
        assert any(c.name == "governance-directory" for c in report.checks)

    def test_all_references_resolve(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.FILE_EXISTENCE],
        )
        assert report.category_passed(IntegrityCategory.FILE_EXISTENCE)

    def test_broken_reference_detected(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        # Write a governance doc with a broken reference
        doc = ai / "contexts" / "languages" / "broken.md"
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text(
            "# Broken\n\nSee `skills/nonexistent/phantom.md` for details.\n",
            encoding="utf-8",
        )
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.FILE_EXISTENCE],
        )
        fail_checks = [
            c
            for c in report.checks
            if c.category == IntegrityCategory.FILE_EXISTENCE and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) >= 1

    def test_spec_buffer_completeness(self, tmp_path: Path) -> None:
        """Missing spec buffer files (spec.md or plan.md) are flagged."""
        ai = _setup_full_project(tmp_path)
        # Remove plan.md to trigger failure
        (ai / "specs" / "plan.md").unlink()
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.FILE_EXISTENCE],
        )
        fail_checks = [
            c for c in report.checks if c.name == "spec-buffer" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "plan.md" in fail_checks[0].message

    def test_spec_buffer_present_passes(self, tmp_path: Path) -> None:
        """Complete spec buffer files (spec.md + plan.md) pass validation."""
        _setup_full_project(tmp_path)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.FILE_EXISTENCE],
        )
        ok_checks = [
            c for c in report.checks if c.name == "spec-buffer" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1


# -- Category 2: Mirror Sync ----------------------------------------------


class TestMirrorSync:
    """Tests for mirror-sync validation."""

    def test_non_source_repo_skips_mirrors(self, tmp_path: Path) -> None:
        """In a target project (no templates dir), mirror sync is skipped."""
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MIRROR_SYNC],
        )
        assert report.passed is True
        skipped = [c for c in report.checks if c.name == "mirror-sync-skipped"]
        assert len(skipped) == 1

    def test_source_repo_missing_canonical_root(self, tmp_path: Path) -> None:
        """In the source repo, missing canonical root is a failure."""
        # Create templates dir so _is_source_repo returns True
        (tmp_path / "src" / "ai_engineering" / "templates").mkdir(parents=True)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MIRROR_SYNC],
        )
        assert report.passed is False

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
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MIRROR_SYNC],
        )
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
        # Ensure canonical has a contexts file to compare against
        canonical_lang = ai / "contexts" / "languages" / "python.md"
        canonical_lang.parent.mkdir(parents=True, exist_ok=True)
        canonical_lang.write_text("CANONICAL CONTENT", encoding="utf-8")
        mirror_root = tmp_path / "src" / "ai_engineering" / "templates" / ".ai-engineering"
        # Mirror governance files (contexts, manifest, README)
        for subdir in ("contexts",):
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
        desynced = mirror_root / "contexts" / "languages" / "python.md"
        desynced.write_text("DESYNCED CONTENT", encoding="utf-8")
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MIRROR_SYNC],
        )
        desync_checks = [
            c for c in report.checks if c.status == IntegrityStatus.FAIL and "desync" in c.name
        ]
        assert len(desync_checks) >= 1


def _setup_governance_mirror(root: Path) -> None:
    """Create minimal governance template mirror so _check_mirror_sync doesn't early-return."""
    ai = root / ".ai-engineering"
    mirror_root = root / "src" / "ai_engineering" / "templates" / ".ai-engineering"
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
    for root_file in ("manifest.yml", "README.md"):
        src = ai / root_file
        if src.is_file():
            dest = mirror_root / root_file
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())


class TestCopilotSkillsMirror:
    """Tests for Copilot skills mirror-sync validation."""

    def test_copilot_skills_mirror_sync_ok(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical = tmp_path / ".github" / "skills" / "ai-test"
        mirror = (
            tmp_path
            / "src"
            / "ai_engineering"
            / "templates"
            / "project"
            / ".github"
            / "skills"
            / "ai-test"
        )
        canonical.mkdir(parents=True)
        mirror.mkdir(parents=True)
        content = "---\nname: ai-test\nmode: agent\n---\nTest skill.\n"
        (canonical / "SKILL.md").write_text(content, encoding="utf-8")
        (mirror / "SKILL.md").write_text(content, encoding="utf-8")
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MIRROR_SYNC],
        )
        ok_checks = [
            c
            for c in report.checks
            if c.name == "copilot-skills-mirrors" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_copilot_skills_mirror_desync(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical = tmp_path / ".github" / "skills" / "ai-test"
        mirror = (
            tmp_path
            / "src"
            / "ai_engineering"
            / "templates"
            / "project"
            / ".github"
            / "skills"
            / "ai-test"
        )
        canonical.mkdir(parents=True)
        mirror.mkdir(parents=True)
        (canonical / "SKILL.md").write_text("canonical", encoding="utf-8")
        (mirror / "SKILL.md").write_text("different", encoding="utf-8")
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MIRROR_SYNC],
        )
        fail_checks = [
            c
            for c in report.checks
            if c.status == IntegrityStatus.FAIL and "copilot-skill-desync" in c.name
        ]
        assert len(fail_checks) >= 1

    def test_copilot_skills_mirror_missing_root(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        # Create canonical skills but no mirror directory
        canonical = tmp_path / ".github" / "skills" / "ai-test"
        canonical.mkdir(parents=True)
        (canonical / "SKILL.md").write_text("content", encoding="utf-8")
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MIRROR_SYNC],
        )
        fail_checks = [
            c
            for c in report.checks
            if c.name == "copilot-skill-mirror-root" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1

    def test_copilot_skills_missing_mirror_file(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical = tmp_path / ".github" / "skills" / "ai-orphan"
        mirror = (
            tmp_path / "src" / "ai_engineering" / "templates" / "project" / ".github" / "skills"
        )
        canonical.mkdir(parents=True)
        mirror.mkdir(parents=True)
        # File exists in canonical but not in mirror
        (canonical / "SKILL.md").write_text("content", encoding="utf-8")
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MIRROR_SYNC],
        )
        fail_checks = [
            c
            for c in report.checks
            if c.status == IntegrityStatus.FAIL and "copilot-skill-missing" in c.name
        ]
        assert len(fail_checks) >= 1


class TestClaudeSkillsMirror:
    """Tests for Claude skills mirror-sync validation."""

    def test_claude_skills_mirror_sync_ok(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical = tmp_path / ".claude" / "skills" / "ai-test"
        mirror = (
            tmp_path
            / "src"
            / "ai_engineering"
            / "templates"
            / "project"
            / ".claude"
            / "skills"
            / "ai-test"
        )
        canonical.mkdir(parents=True)
        mirror.mkdir(parents=True)
        content = "---\nname: ai-test\nmode: agent\n---\nTest skill.\n"
        (canonical / "SKILL.md").write_text(content, encoding="utf-8")
        (mirror / "SKILL.md").write_text(content, encoding="utf-8")
        report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MIRROR_SYNC])
        ok_checks = [
            c
            for c in report.checks
            if c.name == "claude-skills-mirrors" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_claude_skills_mirror_desync(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical = tmp_path / ".claude" / "skills" / "ai-test"
        mirror = (
            tmp_path
            / "src"
            / "ai_engineering"
            / "templates"
            / "project"
            / ".claude"
            / "skills"
            / "ai-test"
        )
        canonical.mkdir(parents=True)
        mirror.mkdir(parents=True)
        (canonical / "SKILL.md").write_text("canonical", encoding="utf-8")
        (mirror / "SKILL.md").write_text("different", encoding="utf-8")
        report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MIRROR_SYNC])
        fail_checks = [
            c
            for c in report.checks
            if c.status == IntegrityStatus.FAIL and "claude-skill-desync" in c.name
        ]
        assert len(fail_checks) >= 1


class TestClaudeAgentsMirror:
    """Tests for Claude agents mirror-sync validation."""

    def test_claude_agents_mirror_sync_ok(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical = tmp_path / ".claude" / "agents"
        mirror = (
            tmp_path / "src" / "ai_engineering" / "templates" / "project" / ".claude" / "agents"
        )
        canonical.mkdir(parents=True)
        mirror.mkdir(parents=True)
        content = "---\nname: ai-test\ndescription: test\n---\nAgent.\n"
        (canonical / "ai-test.md").write_text(content, encoding="utf-8")
        (mirror / "ai-test.md").write_text(content, encoding="utf-8")
        report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MIRROR_SYNC])
        ok_checks = [
            c
            for c in report.checks
            if c.name == "claude-agents-mirrors" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_claude_agents_missing_mirror_file(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical = tmp_path / ".claude" / "agents"
        mirror = (
            tmp_path / "src" / "ai_engineering" / "templates" / "project" / ".claude" / "agents"
        )
        canonical.mkdir(parents=True)
        mirror.mkdir(parents=True)
        (canonical / "ai-orphan.md").write_text("content", encoding="utf-8")
        report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MIRROR_SYNC])
        fail_checks = [
            c
            for c in report.checks
            if c.status == IntegrityStatus.FAIL and "claude-agent-missing" in c.name
        ]
        assert len(fail_checks) >= 1


class TestCodexSkillsMirror:
    """Tests for .codex skills mirror-sync validation."""

    def test_codex_skills_mirror_sync_ok(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical = tmp_path / ".codex" / "skills" / "ai-test"
        mirror = (
            tmp_path
            / "src"
            / "ai_engineering"
            / "templates"
            / "project"
            / ".codex"
            / "skills"
            / "ai-test"
        )
        canonical.mkdir(parents=True)
        mirror.mkdir(parents=True)
        content = "---\nname: test\nmode: agent\n---\nSkill.\n"
        (canonical / "SKILL.md").write_text(content, encoding="utf-8")
        (mirror / "SKILL.md").write_text(content, encoding="utf-8")
        report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MIRROR_SYNC])
        ok_checks = [
            c
            for c in report.checks
            if c.name == "codex-skills-mirrors" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1


class TestCodexAgentsMirror:
    """Tests for .codex agents mirror-sync validation."""

    def test_codex_agents_mirror_sync_ok(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical = tmp_path / ".codex" / "agents"
        mirror = tmp_path / "src" / "ai_engineering" / "templates" / "project" / ".codex" / "agents"
        canonical.mkdir(parents=True)
        mirror.mkdir(parents=True)
        content = "---\nname: ai-test\ndescription: test\n---\nAgent.\n"
        (canonical / "ai-test.md").write_text(content, encoding="utf-8")
        (mirror / "ai-test.md").write_text(content, encoding="utf-8")
        report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MIRROR_SYNC])
        ok_checks = [
            c
            for c in report.checks
            if c.name == "codex-agents-mirrors" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1


class TestCopilotAgentsMirror:
    """Tests for Copilot agents mirror-sync validation."""

    def test_copilot_agents_mirror_sync_ok(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical = tmp_path / ".github" / "agents"
        mirror = tmp_path / "src" / "ai_engineering" / "templates" / "project" / "agents"
        canonical.mkdir(parents=True)
        mirror.mkdir(parents=True)
        content = "---\nname: Test\ndescription: test\n---\nTest agent.\n"
        (canonical / "test.agent.md").write_text(content, encoding="utf-8")
        (mirror / "test.agent.md").write_text(content, encoding="utf-8")
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MIRROR_SYNC],
        )
        ok_checks = [
            c
            for c in report.checks
            if c.name == "copilot-agents-mirrors" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_copilot_agents_mirror_desync(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical = tmp_path / ".github" / "agents"
        mirror = tmp_path / "src" / "ai_engineering" / "templates" / "project" / "agents"
        canonical.mkdir(parents=True)
        mirror.mkdir(parents=True)
        (canonical / "test.agent.md").write_text("canonical", encoding="utf-8")
        (mirror / "test.agent.md").write_text("different", encoding="utf-8")
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MIRROR_SYNC],
        )
        fail_checks = [
            c
            for c in report.checks
            if c.status == IntegrityStatus.FAIL and "copilot-agent-desync" in c.name
        ]
        assert len(fail_checks) >= 1

    def test_copilot_agents_mirror_missing_root(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical = tmp_path / ".github" / "agents"
        canonical.mkdir(parents=True)
        (canonical / "test.agent.md").write_text("content", encoding="utf-8")
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MIRROR_SYNC],
        )
        fail_checks = [
            c
            for c in report.checks
            if c.name == "copilot-agent-mirror-root" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1

    def test_copilot_agents_missing_mirror_file(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical = tmp_path / ".github" / "agents"
        mirror = tmp_path / "src" / "ai_engineering" / "templates" / "project" / "agents"
        canonical.mkdir(parents=True)
        mirror.mkdir(parents=True)
        (canonical / "orphan.agent.md").write_text("content", encoding="utf-8")
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MIRROR_SYNC],
        )
        fail_checks = [
            c
            for c in report.checks
            if c.status == IntegrityStatus.FAIL and "copilot-agent-missing" in c.name
        ]
        assert len(fail_checks) >= 1


# -- Category 3: Counter Accuracy -----------------------------------------


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


# -- Category 4: Cross-Reference Integrity --------------------------------


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


# -- Category 5: Manifest Coherence ---------------------------------------


class TestManifestCoherence:
    """Tests for manifest-coherence validation."""

    def test_complete_manifest_passes(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE)

    def test_missing_manifest_fails(self, tmp_path: Path) -> None:
        _make_governance(tmp_path)
        _write_active_spec(tmp_path / ".ai-engineering")
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE) is False

    def test_active_spec_valid(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )
        ok_checks = [
            c for c in report.checks if c.name == "active-spec" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_active_spec_placeholder(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        (ai / "specs" / "spec.md").write_text(
            "# No active spec\n\nRun /ai-brainstorm to start a new spec.\n",
            encoding="utf-8",
        )
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )
        ok_checks = [
            c for c in report.checks if c.name == "active-spec" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_missing_ownership_directory(self, tmp_path: Path) -> None:
        ai = _make_governance(tmp_path)
        _write_manifest(ai)
        # Remove a directory that IS validated by manifest coherence: contexts
        shutil.rmtree(ai / "contexts")
        _write_active_spec(ai)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )
        fail_checks = [
            c for c in report.checks if c.status == IntegrityStatus.FAIL and "contexts" in c.name
        ]
        assert len(fail_checks) >= 1


# -- Category 7: Skill Frontmatter ----------------------------------------


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


# -- Integration: validate_content_integrity entry point -------------------


class TestValidateContentIntegrity:
    """Tests for the main validate_content_integrity entry point."""

    def test_all_categories_checked_by_default(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        report = validate_content_integrity(tmp_path)
        cats_found = {c.category for c in report.checks}
        assert IntegrityCategory.FILE_EXISTENCE in cats_found
        assert IntegrityCategory.COUNTER_ACCURACY in cats_found
        assert IntegrityCategory.MANIFEST_COHERENCE in cats_found

    def test_category_filter_limits_checks(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.FILE_EXISTENCE],
        )
        cats = {c.category for c in report.checks}
        assert cats == {IntegrityCategory.FILE_EXISTENCE}

    def test_to_dict_roundtrip(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.FILE_EXISTENCE],
        )
        d = report.to_dict()
        assert isinstance(d, dict)
        assert "passed" in d
        assert "categories" in d
        assert isinstance(d["categories"], dict)


# -- Shared utility functions from _shared.py -----------------------------


class TestIsSourceRepo:
    """Tests for _is_source_repo detection."""

    def test_source_repo_detected(self, tmp_path: Path) -> None:
        (tmp_path / "src" / "ai_engineering" / "templates").mkdir(parents=True)
        assert _is_source_repo(tmp_path) is True

    def test_non_source_repo(self, tmp_path: Path) -> None:
        assert _is_source_repo(tmp_path) is False


class TestInstructionFiles:
    """Tests for _instruction_files returning correct list by repo type."""

    def test_source_repo_includes_templates(self, tmp_path: Path) -> None:
        (tmp_path / "src" / "ai_engineering" / "templates").mkdir(parents=True)
        files = _instruction_files(tmp_path)
        assert any("templates" in f for f in files)
        assert len(files) == 6  # 3 base + 3 template

    def test_non_source_repo_base_only(self, tmp_path: Path) -> None:
        files = _instruction_files(tmp_path)
        assert len(files) == 3
        assert all("templates" not in f for f in files)


class TestGlobFiles:
    """Tests for _glob_files utility."""

    def test_glob_collects_matching_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text("a")
        (tmp_path / "b.md").write_text("b")
        (tmp_path / "c.txt").write_text("c")
        result = _glob_files(tmp_path, ["*.md"])
        names = {p.name for p in result}
        assert names == {"a.md", "b.md"}

    def test_glob_multiple_patterns(self, tmp_path: Path) -> None:
        (tmp_path / "x.md").write_text("x")
        (tmp_path / "y.yml").write_text("y: 1")
        result = _glob_files(tmp_path, ["*.md", "*.yml"])
        names = {p.name for p in result}
        assert names == {"x.md", "y.yml"}

    def test_glob_excludes_directories(self, tmp_path: Path) -> None:
        sub = tmp_path / "subdir.md"
        sub.mkdir()
        (tmp_path / "real.md").write_text("real")
        result = _glob_files(tmp_path, ["*.md"])
        assert all(p.is_file() for p in result)
        assert len(result) == 1


class TestIsExcluded:
    """Tests for _is_excluded prefix checking."""

    def test_excluded_prefix_matches(self) -> None:
        assert _is_excluded(Path("contexts/team/readme.md"), ["contexts/team/"]) is True

    def test_non_excluded_prefix(self) -> None:
        assert _is_excluded(Path("contexts/languages/python.md"), ["contexts/team/"]) is False


class TestExtractSection:
    """Tests for _extract_section markdown parser."""

    def test_extracts_section_content(self) -> None:
        content = "## Skills\n\nList of skills.\n\n## Agents\n\nList of agents.\n"
        section = _extract_section(content, "Skills")
        assert "List of skills" in section
        assert "List of agents" not in section

    def test_missing_section_returns_empty(self) -> None:
        content = "## Other\n\nSome content.\n"
        assert _extract_section(content, "Skills") == ""

    def test_last_section_captures_to_end(self) -> None:
        content = "## Skills\n\nOnly section.\n"
        section = _extract_section(content, "Skills")
        assert "Only section." in section


class TestIsTableSeparator:
    """Tests for _is_table_separator."""

    def test_separator_row(self) -> None:
        assert _is_table_separator("|---|---|") is True
        assert _is_table_separator("|:---:|:---:|") is True

    def test_non_separator(self) -> None:
        assert _is_table_separator("| name | value |") is False
        assert _is_table_separator("") is False


class TestParseSkillNames:
    """Tests for _parse_skill_names from bullet and table formats."""

    def test_bullet_format(self) -> None:
        section = "- `.claude/skills/ai-test/SKILL.md`\n- `.claude/skills/ai-debug/SKILL.md`\n"
        names = _parse_skill_names(section)
        assert names == {"ai-test", "ai-debug"}

    def test_table_format(self) -> None:
        section = "| Skills (alphabetical) |\n|---|\n| ai-test, ai-debug |\n"
        names = _parse_skill_names(section)
        assert names == {"ai-test", "ai-debug"}

    def test_empty_section(self) -> None:
        assert _parse_skill_names("") == set()


class TestParseAgentNames:
    """Tests for _parse_agent_names from bullet and table formats."""

    def test_bullet_format(self) -> None:
        section = "- `.claude/agents/ai-build.md`\n- `.claude/agents/ai-plan.md`\n"
        names = _parse_agent_names(section)
        assert names == {"ai-build", "ai-plan"}

    def test_table_format(self) -> None:
        section = (
            "| Agent | Purpose |\n|---|---|\n| ai-build | writes code |\n| ai-plan | planning |\n"
        )
        names = _parse_agent_names(section)
        assert names == {"ai-build", "ai-plan"}

    def test_skips_header_row(self) -> None:
        section = "| Agent | Purpose |\n|---|---|\n"
        names = _parse_agent_names(section)
        assert names == set()

    def test_empty_cells_skipped(self) -> None:
        section = "| | Purpose |\n|---|---|\n"
        names = _parse_agent_names(section)
        assert names == set()


class TestExtractSubsection:
    """Tests for _extract_subsection (level-4 heading parser)."""

    def test_extracts_subsection(self) -> None:
        content = "#### Skills\n\nSkill content.\n\n#### Agents\n\nAgent content.\n"
        section = _extract_subsection(content, "Skills")
        assert "Skill content" in section
        assert "Agent content" not in section

    def test_missing_subsection_returns_empty(self) -> None:
        content = "#### Other\n\nSome content.\n"
        assert _extract_subsection(content, "Skills") == ""

    def test_stops_at_higher_heading(self) -> None:
        content = "#### Skills\n\nContent.\n\n### Higher\n\nOther.\n"
        section = _extract_subsection(content, "Skills")
        assert "Content." in section
        assert "Other." not in section

    def test_stops_at_same_level_heading(self) -> None:
        content = "#### Skills\n\nFirst.\n\n#### Next\n\nSecond.\n"
        section = _extract_subsection(content, "Skills")
        assert "First." in section
        assert "Second." not in section


class TestParseNamesFromSubsection:
    """Tests for _parse_skill_names_from_subsection and _parse_agent_names_from_subsection."""

    def test_skill_names_from_subsection(self) -> None:
        content = "#### Skills\n\n- `.claude/skills/ai-test/SKILL.md`\n\n#### Agents\n\n"
        names = _parse_skill_names_from_subsection(content, "Skills")
        assert names == {"ai-test"}

    def test_agent_names_from_subsection(self) -> None:
        content = "#### Skills\n\n\n#### Agents\n\n- `.codex/agents/ai-build.md`\n"
        names = _parse_agent_names_from_subsection(content, "Agents")
        assert names == {"ai-build"}

    def test_missing_subsection_returns_empty(self) -> None:
        assert _parse_skill_names_from_subsection("#### Other\n", "Skills") == set()
        assert _parse_agent_names_from_subsection("#### Other\n", "Agents") == set()


class TestExtractListings:
    """Tests for _extract_listings with fallback to subsection parsing."""

    def test_top_level_sections(self) -> None:
        content = (
            "## Skills\n\n"
            "- `.claude/skills/ai-test/SKILL.md`\n\n"
            "## Agents\n\n"
            "- `.claude/agents/ai-build.md`\n"
        )
        skills, agents = _extract_listings(content)
        assert skills == {"ai-test"}
        assert agents == {"ai-build"}

    def test_fallback_to_subsections(self) -> None:
        content = (
            "## Overview\n\nSome overview.\n\n"
            "#### Skills\n\n"
            "- `.claude/skills/ai-debug/SKILL.md`\n\n"
            "#### Agents\n\n"
            "- `.codex/agents/ai-plan.md`\n"
        )
        skills, agents = _extract_listings(content)
        assert skills == {"ai-debug"}
        assert agents == {"ai-plan"}

    def test_empty_content(self) -> None:
        skills, agents = _extract_listings("")
        assert skills == set()
        assert agents == set()


class TestFileCache:
    """Tests for FileCache utility."""

    def test_sha256_caching(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        cache = FileCache()
        h1 = cache.sha256(f)
        h2 = cache.sha256(f)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex digest length

    def test_rglob_caching(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text("a")
        (tmp_path / "b.md").write_text("b")
        cache = FileCache()
        r1 = cache.rglob(tmp_path, "*.md")
        r2 = cache.rglob(tmp_path, "*.md")
        assert r1 == r2
        assert len(r1) == 2

    def test_glob_files_via_cache(self, tmp_path: Path) -> None:
        (tmp_path / "x.md").write_text("x")
        (tmp_path / "y.yml").write_text("y: 1")
        cache = FileCache()
        result = cache.glob_files(tmp_path, ["*.md", "*.yml"])
        assert len(result) == 2


# -- Counter Accuracy: pointer format and manifest checks -----------------


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
        (ai / "manifest.yml").write_text(
            "name: test\nskills:\n  total: 99\nagents:\n  total: 0\n",
            encoding="utf-8",
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
        (ai / "manifest.yml").write_text(
            f"name: test\nskills:\n  total: {skill_count}\nagents:\n  total: 0\n",
            encoding="utf-8",
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
        (ai / "manifest.yml").write_text(
            "name: test\nskills:\n  total: 0\nagents:\n  total: 99\n",
            encoding="utf-8",
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
        (ai / "manifest.yml").write_text(
            f"name: test\nskills:\n  total: 0\nagents:\n  total: {agent_count}\n",
            encoding="utf-8",
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


# -- Skill Frontmatter: additional coverage --------------------------------


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
        assert "skipping" in ok_checks[0].message.lower()
