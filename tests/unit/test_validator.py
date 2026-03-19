"""Tests for ai_engineering.validator.service -- content integrity validation."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

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
# Canonical source is templates/.ai-engineering/ (used by sync script to generate
# IDE-adapted mirrors in .claude/, .agents/, .github/).
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TEMPLATES_AI_DIR = _PROJECT_ROOT / "src" / "ai_engineering" / "templates" / ".ai-engineering"

_SKILL_PATHS = sorted(
    f"skills/{d.name}/SKILL.md"
    for d in (_TEMPLATES_AI_DIR / "skills").iterdir()
    if d.is_dir() and (d / "SKILL.md").is_file()
)

_AGENT_PATHS = sorted(f"agents/{f.name}" for f in (_TEMPLATES_AI_DIR / "agents").glob("*.md"))


def _make_governance(root: Path) -> Path:
    """Create a minimal .ai-engineering governance tree."""
    ai = root / ".ai-engineering"
    for d in [
        "skills",
        "agents",
        "standards/framework",
        "standards/team",
        "context/product",
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


def _write_product_contract(
    ai: Path,
    *,
    skills: list[str] | None = None,
    agents: list[str] | None = None,
) -> None:
    """Write a minimal product-contract.md with skill/agent tables.

    Uses the canonical table format matching the actual product-contract.md.
    Defaults to the project's standard skill/agent lists.
    """
    skill_list = skills if skills is not None else [s.split("/")[1] for s in _SKILL_PATHS]
    agent_list = (
        agents
        if agents is not None
        else [a.split("/")[1].removesuffix(".md") for a in _AGENT_PATHS]
    )

    pc = ai / "context" / "product" / "product-contract.md"
    pc.parent.mkdir(parents=True, exist_ok=True)

    skill_row = "| " + ", ".join(skill_list) + " |"
    agent_rows = "\n".join(f"| {a} | purpose | scope |" for a in agent_list)
    pc.write_text(
        f"# Product\n\n"
        f"#### Skills ({len(skill_list)})\n\n"
        f"| Domain | Skills |\n|--------|--------|\n{skill_row}\n\n"
        f"#### Agents ({len(agent_list)})\n\n"
        f"| Agent | Purpose | Scope |\n|-------|---------|-------|\n{agent_rows}\n",
        encoding="utf-8",
    )


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
    """Write _active.md and create the spec directory."""
    active = ai / "specs" / "_active.md"
    active.parent.mkdir(parents=True, exist_ok=True)
    active.write_text(
        f'---\nactive: "{spec_name}"\n---\n',
        encoding="utf-8",
    )
    spec_dir = ai / "specs" / spec_name
    spec_dir.mkdir(parents=True, exist_ok=True)
    for f in ("spec.md", "plan.md", "tasks.md"):
        (spec_dir / f).write_text(f"# {f}\n", encoding="utf-8")
    return spec_dir


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
    _write_product_contract(ai)
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
        skill = ai / "skills" / "commit" / "SKILL.md"
        skill.write_text(
            "# Commit\n\nSee `skills/nonexistent/phantom.md` for details.\n",
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

    def test_spec_directory_completeness(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        bad_spec = ai / "specs" / "007-incomplete"
        bad_spec.mkdir(parents=True)
        (bad_spec / "spec.md").write_text("# spec\n", encoding="utf-8")
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.FILE_EXISTENCE],
        )
        fail_checks = [
            c
            for c in report.checks
            if c.name == "spec-007-incomplete" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "plan.md" in fail_checks[0].message

    def test_closed_spec_archives_skipped(self, tmp_path: Path) -> None:
        """Closed specs (with done.md) are historical archives; stale refs ignored."""
        ai = _setup_full_project(tmp_path)
        closed = ai / "specs" / "001-old"
        closed.mkdir(parents=True)
        (closed / "spec.md").write_text("# old\n", encoding="utf-8")
        (closed / "plan.md").write_text("# plan\n", encoding="utf-8")
        (closed / "tasks.md").write_text(
            "See `skills/nonexistent/phantom.md` for details.\n",
            encoding="utf-8",
        )
        (closed / "done.md").write_text("# done\n", encoding="utf-8")
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.FILE_EXISTENCE],
        )
        # The stale reference in the closed spec should NOT cause a failure
        broken = [
            c
            for c in report.checks
            if c.name == "broken-reference"
            and c.status == IntegrityStatus.FAIL
            and "phantom" in c.message
        ]
        assert len(broken) == 0


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
        # Only mirror governance files (standards, manifest, README) — not skills/agents
        for subdir in ("standards/framework",):
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
        # Ensure canonical has a standards file to compare against
        canonical_core = ai / "standards" / "framework" / "core.md"
        canonical_core.parent.mkdir(parents=True, exist_ok=True)
        canonical_core.write_text("CANONICAL CONTENT", encoding="utf-8")
        mirror_root = tmp_path / "src" / "ai_engineering" / "templates" / ".ai-engineering"
        # Only mirror governance files (standards, manifest, README) — not skills/agents
        for subdir in ("standards/framework",):
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
        desynced = mirror_root / "standards" / "framework" / "core.md"
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
    # Only mirror governance files (standards, manifest, README) — not skills/agents
    for subdir in ("standards/framework",):
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


class TestCopilotPromptsMirror:
    """Tests for Copilot prompts mirror-sync validation."""

    def test_copilot_prompts_mirror_sync_ok(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical = tmp_path / ".github" / "prompts"
        mirror = tmp_path / "src" / "ai_engineering" / "templates" / "project" / "prompts"
        canonical.mkdir(parents=True)
        mirror.mkdir(parents=True)
        content = "---\ndescription: test\nmode: agent\n---\nTest prompt.\n"
        (canonical / "test.prompt.md").write_text(content, encoding="utf-8")
        (mirror / "test.prompt.md").write_text(content, encoding="utf-8")
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MIRROR_SYNC],
        )
        ok_checks = [
            c
            for c in report.checks
            if c.name == "copilot-prompts-mirrors" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_copilot_prompts_mirror_desync(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical = tmp_path / ".github" / "prompts"
        mirror = tmp_path / "src" / "ai_engineering" / "templates" / "project" / "prompts"
        canonical.mkdir(parents=True)
        mirror.mkdir(parents=True)
        (canonical / "test.prompt.md").write_text("canonical", encoding="utf-8")
        (mirror / "test.prompt.md").write_text("different", encoding="utf-8")
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MIRROR_SYNC],
        )
        fail_checks = [
            c
            for c in report.checks
            if c.status == IntegrityStatus.FAIL and "copilot-prompt-desync" in c.name
        ]
        assert len(fail_checks) >= 1

    def test_copilot_prompts_mirror_missing_root(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        # Create canonical prompts but no mirror directory
        canonical = tmp_path / ".github" / "prompts"
        canonical.mkdir(parents=True)
        (canonical / "test.prompt.md").write_text("content", encoding="utf-8")
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MIRROR_SYNC],
        )
        fail_checks = [
            c
            for c in report.checks
            if c.name == "copilot-prompts-mirror-root" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1

    def test_copilot_prompts_missing_mirror_file(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical = tmp_path / ".github" / "prompts"
        mirror = tmp_path / "src" / "ai_engineering" / "templates" / "project" / "prompts"
        canonical.mkdir(parents=True)
        mirror.mkdir(parents=True)
        # File exists in canonical but not in mirror
        (canonical / "orphan.prompt.md").write_text("content", encoding="utf-8")
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MIRROR_SYNC],
        )
        fail_checks = [
            c
            for c in report.checks
            if c.status == IntegrityStatus.FAIL and "copilot-prompt-missing" in c.name
        ]
        assert len(fail_checks) >= 1


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
            if c.name == "copilot-agents-mirror-root" and c.status == IntegrityStatus.FAIL
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

    def test_product_contract_mismatch_detected(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        # Write product-contract with different skills/agents than instruction files
        _write_product_contract(
            ai, skills=["extra-skill-a", "extra-skill-b"], agents=["extra-agent"]
        )
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.COUNTER_ACCURACY],
        )
        fail_checks = [
            c
            for c in report.checks
            if c.name.startswith("product-contract-") and c.status == IntegrityStatus.FAIL
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
        skill_dir = tmp_path / ".claude" / "skills" / "debug"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            "# Debug\n\n## References\n\n- `skills/refactor/SKILL.md`\n",
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


# -- Category 5: Instruction Consistency -----------------------------------


class TestInstructionConsistency:
    """Tests for instruction-consistency validation."""

    def test_identical_files_pass(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.INSTRUCTION_CONSISTENCY],
        )
        assert report.category_passed(IntegrityCategory.INSTRUCTION_CONSISTENCY)

    def test_different_skills_detected(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        (tmp_path / "AGENTS.md").write_text(
            _make_instruction_content(skills=_SKILL_PATHS[:5]),
            encoding="utf-8",
        )
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.INSTRUCTION_CONSISTENCY],
        )
        assert report.category_passed(IntegrityCategory.INSTRUCTION_CONSISTENCY) is False

    def test_flat_layout_no_subsections_passes(self, tmp_path: Path) -> None:
        """Flat skill layout has no category subsections — should pass."""
        _setup_full_project(tmp_path)
        lines = ["# Instructions", "", "## Skills", ""]
        for s in _SKILL_PATHS:
            lines.append(f"- `.claude/{s}`")
        lines.extend(["", "## Agents", ""])
        for a in _AGENT_PATHS:
            lines.append(f"- `.claude/{a}`")
        (tmp_path / "AGENTS.md").write_text("\n".join(lines), encoding="utf-8")
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.INSTRUCTION_CONSISTENCY],
        )
        fail_checks = [c for c in report.checks if "missing-subsections" in c.name]
        assert len(fail_checks) == 0


# -- Category 6: Manifest Coherence ---------------------------------------


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

    def test_active_spec_missing_directory(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        active = ai / "specs" / "_active.md"
        active.write_text(
            '---\nactive: "999-nonexistent"\n---\n',
            encoding="utf-8",
        )
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )
        fail_checks = [
            c
            for c in report.checks
            if c.name == "active-spec-dir" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1

    def test_missing_ownership_directory(self, tmp_path: Path) -> None:
        ai = _make_governance(tmp_path)
        _write_manifest(ai)
        # skills/ and agents/ no longer live under .ai-engineering/ — remove a
        # directory that IS validated: standards/framework
        shutil.rmtree(ai / "standards" / "framework")
        _write_active_spec(ai)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )
        fail_checks = [
            c
            for c in report.checks
            if c.status == IntegrityStatus.FAIL and "standards/framework" in c.name
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
        assert IntegrityCategory.INSTRUCTION_CONSISTENCY in cats_found
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
