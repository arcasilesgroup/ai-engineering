"""Tests for ai_engineering.validator.service -- content integrity validation."""

from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_engineering.config.mirror_inventory import get_generated_provenance_fields
from ai_engineering.state.context_packs import write_context_pack
from ai_engineering.state.defaults import default_ownership_map
from ai_engineering.state.io import write_json_model
from ai_engineering.state.models import (
    EvidenceRef,
    HandoffRef,
    TaskLedger,
    TaskLedgerTask,
    TaskLifecycleState,
)
from ai_engineering.state.observability import (
    framework_capabilities_path,
    write_framework_capabilities,
)
from ai_engineering.state.work_plane import write_active_work_plane_pointer
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


def _write_manifest(
    ai: Path,
    *,
    providers: tuple[str, ...] = ("claude_code", "github_copilot"),
    skills_total: int | None = None,
    agents_total: int | None = None,
) -> None:
    """Write a minimal manifest.yml."""
    m = ai / "manifest.yml"
    skills_block = f"skills:\n  total: {skills_total}\n" if skills_total is not None else ""
    agents_block = f"agents:\n  total: {agents_total}\n" if agents_total is not None else ""
    m.write_text(
        "name: test-project\nversion: 1.0.0\n"
        f"{skills_block}{agents_block}"
        f"ai_providers:\n  enabled: [{', '.join(providers)}]\n  primary: {providers[0]}\n"
        "ownership:\n"
        '  framework: [".ai-engineering/**"]\n'
        "  root_entry_points:\n"
        "    CLAUDE.md:\n"
        "      owner: framework\n"
        "      canonical_source: CLAUDE.md\n"
        "      runtime_role: ide-overlay\n"
        "      sync:\n"
        "        mode: copy\n"
        "        template_path: src/ai_engineering/templates/project/CLAUDE.md\n"
        "        mirror_paths: []\n"
        "    AGENTS.md:\n"
        "      owner: framework\n"
        "      canonical_source: scripts/sync_command_mirrors.py:generate_agents_md\n"
        "      runtime_role: shared-runtime-contract\n"
        "      sync:\n"
        "        mode: generate\n"
        "        template_path: src/ai_engineering/templates/project/AGENTS.md\n"
        "        mirror_paths: []\n"
        '    ".github/copilot-instructions.md":\n'
        "      owner: framework\n"
        "      canonical_source: CLAUDE.md\n"
        "      runtime_role: ide-overlay\n"
        "      sync:\n"
        "        mode: generate\n"
        "        template_path: src/ai_engineering/templates/project/copilot-instructions.md\n"
        "        mirror_paths: []\n"
        '  team: [".ai-engineering/contexts/team/**"]\n'
        '  system: [".ai-engineering/state/**"]\n',
        encoding="utf-8",
    )


def _write_manifest_with_capabilities(ai: Path) -> None:
    """Write a manifest fixture with enough registry data for capability cards."""
    _write_manifest(ai)
    manifest = ai / "manifest.yml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8")
        + "skills:\n"
        + "  total: 2\n"
        + "  registry:\n"
        + "    ai-code:\n"
        + "      type: workflow\n"
        + "      tags: [implementation]\n"
        + "    ai-analyze-permissions:\n"
        + "      type: meta\n"
        + "      tags: [permissions]\n"
        + "agents:\n"
        + "  total: 3\n"
        + "  names: [plan, build, explore]\n",
        encoding="utf-8",
    )


def _source_repo_manifest_text(version: str = "1.2.3") -> str:
    return (
        f'framework_version: "{version}"\n'
        "session:\n"
        "  context_files:\n"
        "    - .ai-engineering/LESSONS.md\n"
        "    - CONSTITUTION.md\n"
        "    - .ai-engineering/manifest.yml\n"
        "    - .ai-engineering/state/decision-store.json\n"
        "control_plane:\n"
        "  constitutional_authority:\n"
        "    primary: CONSTITUTION.md\n"
        "  manifest_field_roles:\n"
        "    canonical_input:\n"
        "      - providers\n"
        "      - ai_providers\n"
        "      - artifact_feeds\n"
        "      - work_items\n"
        "      - quality\n"
        "      - documentation\n"
        "      - cicd\n"
        "      - contexts.precedence\n"
        "      - session.context_files\n"
        "      - ownership.framework\n"
        "      - ownership.root_entry_points\n"
        "      - telemetry\n"
        "      - gates\n"
        "      - hot_path_slos\n"
        "    generated_projection:\n"
        "      - skills\n"
        "      - agents\n"
        "    descriptive_metadata:\n"
        "      - schema_version\n"
        "      - framework_version\n"
        "      - name\n"
        "      - version\n"
    )


def _write_source_repo_markers(root: Path, ai: Path, *, version: str = "1.2.3") -> None:
    """Add the minimal source-repo files that enable source-only validator checks."""
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "test-project"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    (ai / "manifest.yml").write_text(_source_repo_manifest_text(version), encoding="utf-8")
    template_manifest = (
        root / "src" / "ai_engineering" / "templates" / ".ai-engineering" / "manifest.yml"
    )
    template_manifest.parent.mkdir(parents=True, exist_ok=True)
    template_manifest.write_text(_source_repo_manifest_text(version), encoding="utf-8")


def _write_source_repo_control_plane_files(root: Path, ai: Path) -> None:
    (root / "CONSTITUTION.md").write_text("# Root Constitution\n", encoding="utf-8")

    project_template_constitution = (
        root / "src" / "ai_engineering" / "templates" / "project" / "CONSTITUTION.md"
    )
    project_template_constitution.parent.mkdir(parents=True, exist_ok=True)
    project_template_constitution.write_text("# Template Constitution\n", encoding="utf-8")


def _write_work_plane(
    specs_dir: Path,
    spec_name: str = "006-test",
) -> Path:
    """Write compatibility files and seeded work-plane assets at a specs root."""
    specs_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / "spec.md").write_text(
        f'---\nid: "006"\n---\n\n# {spec_name}\n\nTest spec.\n',
        encoding="utf-8",
    )
    (specs_dir / "plan.md").write_text(
        "---\ntotal: 3\ncompleted: 1\n---\n\n# Plan\n\n- [x] Done\n- [ ] Todo\n- [ ] Todo\n",
        encoding="utf-8",
    )
    (specs_dir / "_history.md").write_text(
        "# Spec History\n\nNo lifecycle entries yet.\n",
        encoding="utf-8",
    )
    # Spec-123: dead HX-02 work-plane artifacts no longer required, but the
    # fixture continues to seed them for tests that exercise legacy paths.
    (specs_dir / "current-summary.md").write_text(
        "# Current Summary\n\nNo active current summary yet.\n",
        encoding="utf-8",
    )
    (specs_dir / "history-summary.md").write_text(
        "# History Summary\n\nNo history summary yet.\n",
        encoding="utf-8",
    )
    (specs_dir / "task-ledger.json").write_text(
        '{\n  "schemaVersion": "1.0",\n  "tasks": []\n}\n',
        encoding="utf-8",
    )
    (specs_dir / "handoffs").mkdir(exist_ok=True)
    (specs_dir / "evidence").mkdir(exist_ok=True)
    return specs_dir


def _write_task_artifacts(
    specs_dir: Path,
    task_id: str,
) -> tuple[HandoffRef, EvidenceRef]:
    """Write handoff and evidence files for a task-ledger test task."""
    handoff_path = specs_dir / "handoffs" / f"{task_id}.md"
    evidence_path = specs_dir / "evidence" / f"{task_id}.log"
    handoff_path.write_text(f"# Handoff {task_id}\n", encoding="utf-8")
    evidence_path.write_text(f"evidence for {task_id}\n", encoding="utf-8")
    return (
        HandoffRef(kind="build", path=f"handoffs/{task_id}.md"),
        EvidenceRef(kind="pytest", path=f"evidence/{task_id}.log"),
    )


def _write_active_spec(
    ai: Path,
    spec_name: str = "006-test",
) -> Path:
    """Write Working Buffer compatibility files and seeded work-plane assets."""
    return _write_work_plane(ai / "specs", spec_name)


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
    _write_source_repo_control_plane_files(root, ai)
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

    def test_legacy_state_plane_reference_requires_canonical_path(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        legacy_path = ai / "state" / "spec-116-t31-audit-classification.json"
        canonical_path = (
            ai / "specs" / "evidence" / "spec-116" / "spec-116-t31-audit-classification.json"
        )
        legacy_path.parent.mkdir(parents=True, exist_ok=True)
        canonical_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_path.write_text('{"source": "legacy"}\n', encoding="utf-8")
        canonical_path.write_text('{"source": "canonical"}\n', encoding="utf-8")

        doc = ai / "contexts" / "languages" / "legacy-state-plane.md"
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text(
            "# Legacy State Plane\n\n"
            "See `state/spec-116-t31-audit-classification.json` for details.\n",
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
        assert any(
            c.name == "legacy-state-plane-reference"
            and "state/spec-116-t31-audit-classification.json" in c.message
            and "specs/evidence/spec-116/spec-116-t31-audit-classification.json" in c.message
            for c in fail_checks
        )

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

    def test_spec_buffer_uses_resolved_work_plane_paths(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Spec-123: dead work-plane artifacts (task-ledger.json,
        # current-summary.md, history-summary.md, handoffs/, evidence/)
        # were removed. Spec buffer is now the canonical three-file
        # contract: spec.md, plan.md, _history.md.
        ai = _setup_full_project(tmp_path)
        (ai / "specs" / "spec.md").unlink()
        (ai / "specs" / "plan.md").unlink()
        (ai / "specs" / "_history.md").unlink()

        resolved_specs_dir = tmp_path / "resolved-work-plane"
        resolved_specs_dir.mkdir()
        resolved_spec = resolved_specs_dir / "spec.md"
        resolved_plan = resolved_specs_dir / "plan.md"
        resolved_history = resolved_specs_dir / "_history.md"
        resolved_spec.write_text("# Spec\n", encoding="utf-8")
        resolved_plan.write_text("# Plan\n", encoding="utf-8")
        resolved_history.write_text("# History\n", encoding="utf-8")

        monkeypatch.setattr(
            "ai_engineering.validator.categories.file_existence.resolve_active_work_plane",
            lambda _root: SimpleNamespace(
                specs_dir=resolved_specs_dir,
                spec_path=resolved_spec,
                plan_path=resolved_plan,
                history_path=resolved_history,
            ),
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.FILE_EXISTENCE],
        )

        ok_checks = [
            c for c in report.checks if c.name == "spec-buffer" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_source_repo_control_plane_paths_present_pass(self, tmp_path: Path) -> None:
        ai = _make_governance(tmp_path)
        _write_source_repo_markers(tmp_path, ai)
        _write_source_repo_control_plane_files(tmp_path, ai)
        _write_active_spec(ai)

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.FILE_EXISTENCE],
        )

        ok_checks = [
            c
            for c in report.checks
            if c.name == "control-plane-paths" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_source_repo_missing_project_constitution_template_fails(self, tmp_path: Path) -> None:
        ai = _make_governance(tmp_path)
        _write_source_repo_markers(tmp_path, ai)
        _write_source_repo_control_plane_files(tmp_path, ai)
        _write_active_spec(ai)
        (tmp_path / "src" / "ai_engineering" / "templates" / "project" / "CONSTITUTION.md").unlink()

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.FILE_EXISTENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "control-plane-paths" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "src/ai_engineering/templates/project/CONSTITUTION.md" in fail_checks[0].message


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


def _frontmatter_with_provenance(
    base_fields: list[tuple[str, str]],
    *,
    family_id: str,
    canonical_source: str,
    body: str,
) -> str:
    """Build a markdown document with generated provenance frontmatter."""
    frontmatter_lines = [f"{key}: {value}" for key, value in base_fields]
    for key, value in get_generated_provenance_fields(family_id, canonical_source).items():
        frontmatter_lines.append(f"{key}: {value}")
    return "---\n" + "\n".join(frontmatter_lines) + f"\n---\n\n{body}"


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
        content = _frontmatter_with_provenance(
            [("name", "ai-test"), ("mode", "agent")],
            family_id="copilot-skills",
            canonical_source=".claude/skills/ai-test/SKILL.md",
            body="Test skill.\n",
        )
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


class TestClaudeSpecialistAgentsMirror:
    """Tests for generated Claude specialist agent mirror-sync validation."""

    def test_claude_specialist_agents_mirror_sync_ok(self, tmp_path: Path) -> None:
        from scripts.sync_command_mirrors import generate_specialist_agent

        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical = tmp_path / ".claude" / "agents"
        mirror = (
            tmp_path / "src" / "ai_engineering" / "templates" / "project" / ".claude" / "agents"
        )
        canonical.mkdir(parents=True)
        mirror.mkdir(parents=True)

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

        report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MIRROR_SYNC])
        ok_checks = [
            c
            for c in report.checks
            if c.name == "claude-specialist-agents-mirrors" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_claude_specialist_agents_mirror_desync(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical = tmp_path / ".claude" / "agents"
        mirror = (
            tmp_path / "src" / "ai_engineering" / "templates" / "project" / ".claude" / "agents"
        )
        canonical.mkdir(parents=True)
        mirror.mkdir(parents=True)

        specialist = canonical / "reviewer-correctness.md"
        specialist.write_text(
            "---\nname: reviewer-correctness\ndescription: test\nmodel: opus\n"
            "color: cyan\ntools: [Read]\n---\n\nBody\n",
            encoding="utf-8",
        )
        (mirror / specialist.name).write_text("different", encoding="utf-8")

        report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MIRROR_SYNC])
        fail_checks = [
            c
            for c in report.checks
            if c.status == IntegrityStatus.FAIL
            and "claude-specialist-agent-desync-reviewer-correctness.md" in c.name
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
        content = _frontmatter_with_provenance(
            [("name", "ai-test"), ("mode", "agent")],
            family_id="codex-skills",
            canonical_source=".claude/skills/ai-test/SKILL.md",
            body="Skill.\n",
        )
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
        content = _frontmatter_with_provenance(
            [("name", "ai-test"), ("description", "test")],
            family_id="codex-agents",
            canonical_source=".claude/agents/ai-test.md",
            body="Agent.\n",
        )
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
        content = _frontmatter_with_provenance(
            [("name", "Test"), ("description", "test")],
            family_id="copilot-agents",
            canonical_source=".claude/agents/ai-test.md",
            body="Test agent.\n",
        )
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


class TestGeneratedMirrorProvenance:
    """Tests for negative provenance validation on generated mirrors."""

    def test_generated_codex_skill_missing_provenance_fails_even_when_pair_matches(
        self, tmp_path: Path
    ) -> None:
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

        content = "---\nname: ai-test\nmode: agent\n---\n\nSkill.\n"
        (canonical / "SKILL.md").write_text(content, encoding="utf-8")
        (mirror / "SKILL.md").write_text(content, encoding="utf-8")

        report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MIRROR_SYNC])

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
        canonical = tmp_path / ".github" / "agents"
        mirror = tmp_path / "src" / "ai_engineering" / "templates" / "project" / "agents"
        canonical.mkdir(parents=True)
        mirror.mkdir(parents=True)

        content = "---\nname: reviewer-bad\ndescription: test\n---\n\nBad peer.\n"
        (canonical / "reviewer-bad.md").write_text(content, encoding="utf-8")
        (mirror / "reviewer-bad.md").write_text(content, encoding="utf-8")

        report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MIRROR_SYNC])

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
        canonical = tmp_path / ".github" / "skills" / "reviewer-bad"
        mirror = (
            tmp_path
            / "src"
            / "ai_engineering"
            / "templates"
            / "project"
            / ".github"
            / "skills"
            / "reviewer-bad"
        )
        canonical.mkdir(parents=True)
        mirror.mkdir(parents=True)
        (canonical / "SKILL.md").write_text("# Bad skill\n", encoding="utf-8")
        (mirror / "SKILL.md").write_text("# Bad skill\n", encoding="utf-8")

        report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MIRROR_SYNC])

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
        canonical = tmp_path / ".github" / "skills" / "ai-test" / "scripts"
        mirror = (
            tmp_path
            / "src"
            / "ai_engineering"
            / "templates"
            / "project"
            / ".github"
            / "skills"
            / "ai-test"
            / "scripts"
        )
        canonical.mkdir(parents=True)
        mirror.mkdir(parents=True)

        content = 'SKILL_DIR=".claude/skills/ai-${SKILL_NAME}"\n'
        (canonical / "scaffold-skill.sh").write_text(content, encoding="utf-8")
        (mirror / "scaffold-skill.sh").write_text(content, encoding="utf-8")

        report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MIRROR_SYNC])

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
        canonical = tmp_path / ".github" / "agents"
        mirror = tmp_path / "src" / "ai_engineering" / "templates" / "project" / "agents"
        canonical.mkdir(parents=True)
        mirror.mkdir(parents=True)

        content = _frontmatter_with_provenance(
            [("name", "Test"), ("description", "test")],
            family_id="copilot-agents",
            canonical_source=".claude/agents/build.md",
            body="Test agent.\n",
        )
        (canonical / "test.agent.md").write_text(content, encoding="utf-8")
        (mirror / "test.agent.md").write_text(content, encoding="utf-8")

        report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MIRROR_SYNC])

        fail_checks = [
            c
            for c in report.checks
            if c.status == IntegrityStatus.FAIL
            and c.name.startswith("generated-provenance-copilot-agents")
        ]
        assert len(fail_checks) >= 1
        assert report.category_passed(IntegrityCategory.MIRROR_SYNC) is False


class TestGeneratedInstructionsMirror:
    """Tests for generated Copilot instruction mirror-sync validation."""

    def test_generated_instructions_mirror_sync_ok_excludes_manual_files(
        self, tmp_path: Path
    ) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical = tmp_path / ".github" / "instructions"
        mirror = tmp_path / "src" / "ai_engineering" / "templates" / "project" / "instructions"
        canonical.mkdir(parents=True)
        mirror.mkdir(parents=True)

        content = '---\napplyTo: "**/*.py"\n---\n\n# Python Instructions\n'
        (canonical / "python.instructions.md").write_text(content, encoding="utf-8")
        (mirror / "python.instructions.md").write_text(content, encoding="utf-8")
        (canonical / "testing.instructions.md").write_text("manual", encoding="utf-8")

        report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MIRROR_SYNC])
        ok_checks = [
            c
            for c in report.checks
            if c.name == "copilot-generated-instructions-mirrors" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_generated_instructions_mirror_desync(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        _setup_governance_mirror(tmp_path)
        canonical = tmp_path / ".github" / "instructions"
        mirror = tmp_path / "src" / "ai_engineering" / "templates" / "project" / "instructions"
        canonical.mkdir(parents=True)
        mirror.mkdir(parents=True)

        (canonical / "python.instructions.md").write_text("canonical", encoding="utf-8")
        (mirror / "python.instructions.md").write_text("different", encoding="utf-8")

        report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MIRROR_SYNC])
        fail_checks = [
            c
            for c in report.checks
            if c.status == IntegrityStatus.FAIL
            and "copilot-generated-instruction-desync-python.instructions.md" in c.name
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
        # Spec-123: task-ledger validation no longer emits checks; only the
        # active-spec OK signal remains for valid spec.md/plan.md content.
        _setup_full_project(tmp_path)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )
        ok_checks = [
            c for c in report.checks if c.name == "active-spec" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

        # Task-ledger checks are no longer emitted post-spec-123.
        ledger_checks = [c for c in report.checks if c.name == "active-task-ledger"]
        assert ledger_checks == []

    def test_active_spec_plan_declared_identity_mismatch_fails(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        (ai / "specs" / "spec.md").write_text(
            "---\nspec: spec-117-hx-02\n---\n\n# HX-02 Work Plane\n",
            encoding="utf-8",
        )
        (ai / "specs" / "plan.md").write_text(
            "---\ntotal: 1\ncompleted: 0\n---\n\n# Plan: spec-117-hx-06 Other Work\n",
            encoding="utf-8",
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "active-spec-plan-coherence" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "spec-117-hx-02" in fail_checks[0].message
        assert "spec-117-hx-06" in fail_checks[0].message
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE) is False

    def test_active_spec_missing_plan_fails(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        (ai / "specs" / "plan.md").unlink()

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "active-spec-plan-coherence" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "without specs/plan.md" in fail_checks[0].message

    def test_active_spec_idle_plan_placeholder_fails(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        (ai / "specs" / "plan.md").write_text(
            "# No active plan\n\nRun /ai-plan.\n",
            encoding="utf-8",
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "active-spec-plan-coherence" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "idle placeholder" in fail_checks[0].message

    def test_active_spec_plan_declared_identity_match_passes(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        (ai / "specs" / "spec.md").write_text(
            "---\nspec: spec-117-hx-02\n---\n\n# HX-02 Work Plane\n",
            encoding="utf-8",
        )
        (ai / "specs" / "plan.md").write_text(
            "---\ntotal: 1\ncompleted: 0\n---\n\n# Plan: spec-117-hx-02 Work Plane\n",
            encoding="utf-8",
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        ok_checks = [
            c
            for c in report.checks
            if c.name == "active-spec-plan-coherence" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE)

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
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

        ledger_checks = [c for c in report.checks if c.name == "active-task-ledger"]
        assert ledger_checks == []
        coherence_checks = [c for c in report.checks if c.name == "active-spec-ledger-coherence"]
        assert coherence_checks == []
        artifact_checks = [
            c for c in report.checks if c.name == "task-artifact-reference-validation"
        ]
        assert artifact_checks == []
        write_scope_checks = [
            c for c in report.checks if c.name == "task-write-scope-duplicate-validation"
        ]
        assert write_scope_checks == []

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_active_spec_placeholder_with_non_done_task_in_resolved_ledger_fails(
        self, tmp_path: Path
    ) -> None:
        ai = _setup_full_project(tmp_path)
        (ai / "specs" / "spec.md").write_text(
            "---\nid: legacy-spec\n---\n\n# Legacy Active Spec\n",
            encoding="utf-8",
        )
        pointed_specs_dir = _write_work_plane(
            ai / "specs" / "spec-fixture-progress", "fixture-progress"
        )
        (pointed_specs_dir / "spec.md").write_text(
            "# No active spec\n\nRun /ai-brainstorm to start a new spec.\n",
            encoding="utf-8",
        )
        write_json_model(
            pointed_specs_dir / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-1",
                        title="Active task",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="Build",
                        write_scope=["src/**"],
                    )
                ]
            ),
        )
        write_active_work_plane_pointer(tmp_path, pointed_specs_dir)

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "active-spec-ledger-coherence" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1

        ledger_checks = [c for c in report.checks if c.name == "active-task-ledger"]
        assert ledger_checks == []
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE) is False

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_active_spec_placeholder_with_malformed_task_ledger_warns(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        (ai / "specs" / "spec.md").write_text(
            "# No active spec\n\nRun /ai-brainstorm to start a new spec.\n",
            encoding="utf-8",
        )
        (ai / "specs" / "task-ledger.json").write_text(
            '{"schemaVersion": "1.0", "tasks": [}\n',
            encoding="utf-8",
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        ledger_checks = [
            c
            for c in report.checks
            if c.name == "active-task-ledger" and c.status == IntegrityStatus.WARN
        ]
        assert len(ledger_checks) == 1

        coherence_checks = [c for c in report.checks if c.name == "active-spec-ledger-coherence"]
        assert coherence_checks == []
        dependency_checks = [c for c in report.checks if c.name == "task-dependency-validation"]
        assert dependency_checks == []
        artifact_checks = [
            c for c in report.checks if c.name == "task-artifact-reference-validation"
        ]
        assert artifact_checks == []
        write_scope_checks = [
            c for c in report.checks if c.name == "task-write-scope-duplicate-validation"
        ]
        assert write_scope_checks == []
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE)

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_active_spec_with_non_done_task_in_ledger_passes(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        write_json_model(
            ai / "specs" / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-1",
                        title="Active task",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="Build",
                        write_scope=["src/**"],
                    )
                ]
            ),
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        ok_checks = [
            c
            for c in report.checks
            if c.name == "active-task-ledger" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1
        artifact_checks = [
            c
            for c in report.checks
            if c.name == "task-artifact-reference-validation" and c.status == IntegrityStatus.OK
        ]
        assert len(artifact_checks) == 1

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_task_capability_acceptance_passes_for_build_source_write(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        _write_manifest_with_capabilities(ai)
        write_json_model(
            ai / "specs" / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-build",
                        title="Build source change",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="Build",
                        write_scope=["src/ai_engineering/state/models.py"],
                    )
                ]
            ),
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        ok_checks = [
            c
            for c in report.checks
            if c.name == "task-capability-acceptance-validation" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE)

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_context_pack_manifest_contract_passes_for_generated_pack(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        write_json_model(
            ai / "specs" / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-pack",
                        title="Build context pack",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="Build",
                    )
                ]
            ),
        )
        write_context_pack(tmp_path, task_id="T-pack")

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        ok_checks = [
            c
            for c in report.checks
            if c.name == "context-pack-manifest-contract" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE)

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_context_pack_manifest_contract_fails_when_pack_drifts(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        write_json_model(
            ai / "specs" / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-pack",
                        title="Build context pack",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="Build",
                    )
                ]
            ),
        )
        pack_path = tmp_path / ".ai-engineering" / "specs" / "context-packs" / "T-pack.json"
        write_context_pack(tmp_path, task_id="T-pack")
        pack_path.write_text(
            pack_path.read_text(encoding="utf-8").replace(
                '"taskId": "T-pack"', '"taskId": "wrong"'
            ),
            encoding="utf-8",
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "context-pack-manifest-contract" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "does not match deterministic pack output" in fail_checks[0].message
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE) is False

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_task_capability_acceptance_rejects_illegal_source_writer(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        _write_manifest_with_capabilities(ai)
        write_json_model(
            ai / "specs" / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-plan",
                        title="Plan source change",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="Plan",
                        write_scope=["src/ai_engineering/state/models.py"],
                    )
                ]
            ),
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "task-capability-acceptance-validation"
            and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "cannot perform mutation classes: code-write" in fail_checks[0].message
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE) is False

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_task_capability_acceptance_rejects_illegal_tool_request(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        _write_manifest_with_capabilities(ai)
        write_json_model(
            ai / "specs" / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-explore",
                        title="Explore cannot edit",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="Explore",
                        toolRequests=["edit"],
                    )
                ]
            ),
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "task-capability-acceptance-validation"
            and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "cannot request tool scopes: edit" in fail_checks[0].message
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE) is False

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_task_capability_acceptance_rejects_provider_incompatible_packet(
        self, tmp_path: Path
    ) -> None:
        ai = _setup_full_project(tmp_path)
        _write_manifest_with_capabilities(ai)
        write_json_model(
            ai / "specs" / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-provider",
                        title="Provider-specific skill",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="ai-analyze-permissions",
                        provider="github_copilot",
                    )
                ]
            ),
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "task-capability-acceptance-validation"
            and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "incompatible with provider github_copilot" in fail_checks[0].message
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE) is False

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_duplicate_write_scope_across_in_progress_tasks_fails(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        write_json_model(
            ai / "specs" / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-1",
                        title="First active task",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="Build",
                        write_scope=["src/**"],
                    ),
                    TaskLedgerTask(
                        id="T-2",
                        title="Second active task",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="Build",
                        write_scope=["src/**"],
                    ),
                ]
            ),
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "task-write-scope-duplicate-validation"
            and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "src/**" in fail_checks[0].message
        assert "T-1" in fail_checks[0].message
        assert "T-2" in fail_checks[0].message
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE) is False

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_distinct_write_scope_across_in_progress_tasks_passes(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        write_json_model(
            ai / "specs" / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-1",
                        title="Source task",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="Build",
                        write_scope=["src/**"],
                    ),
                    TaskLedgerTask(
                        id="T-2",
                        title="Test task",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="Build",
                        write_scope=["tests/**"],
                    ),
                ]
            ),
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        ok_checks = [
            c
            for c in report.checks
            if c.name == "task-write-scope-duplicate-validation" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE)

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_overlapping_but_non_identical_write_scope_strings_fail(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        write_json_model(
            ai / "specs" / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-1",
                        title="Broad source task",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="Build",
                        write_scope=["src/**"],
                    ),
                    TaskLedgerTask(
                        id="T-2",
                        title="Nested source task",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="Build",
                        write_scope=["src/ai_engineering/**"],
                    ),
                ]
            ),
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "task-write-scope-duplicate-validation"
            and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "src/**" in fail_checks[0].message
        assert "src/ai_engineering/**" in fail_checks[0].message
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE) is False

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_duplicate_write_scope_with_fewer_than_two_in_progress_tasks_passes(
        self, tmp_path: Path
    ) -> None:
        ai = _setup_full_project(tmp_path)
        write_json_model(
            ai / "specs" / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-1",
                        title="Active task",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="Build",
                        write_scope=["src/**"],
                    ),
                    TaskLedgerTask(
                        id="T-2",
                        title="Planned task",
                        status=TaskLifecycleState.PLANNED,
                        owner_role="Build",
                        write_scope=["src/**"],
                    ),
                ]
            ),
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        ok_checks = [
            c
            for c in report.checks
            if c.name == "task-write-scope-duplicate-validation" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE)

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_malformed_task_ledger_warns_and_skips_dependency_validation(
        self, tmp_path: Path
    ) -> None:
        ai = _setup_full_project(tmp_path)
        (ai / "specs" / "task-ledger.json").write_text(
            '{"schemaVersion": "1.0", "tasks": [}\n',
            encoding="utf-8",
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        ledger_checks = [
            c
            for c in report.checks
            if c.name == "active-task-ledger" and c.status == IntegrityStatus.WARN
        ]
        assert len(ledger_checks) == 1

        dependency_checks = [c for c in report.checks if c.name == "task-dependency-validation"]
        assert dependency_checks == []
        artifact_checks = [
            c for c in report.checks if c.name == "task-artifact-reference-validation"
        ]
        assert artifact_checks == []
        write_scope_checks = [
            c for c in report.checks if c.name == "task-write-scope-duplicate-validation"
        ]
        assert write_scope_checks == []
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE)

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_task_ledger_with_missing_dependency_fails(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        write_json_model(
            ai / "specs" / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-1",
                        title="Active task",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="Build",
                        dependencies=["T-2"],
                        write_scope=["src/**"],
                    )
                ]
            ),
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "task-dependency-validation" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE) is False

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_task_ledger_with_valid_dependencies_passes(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        handoff_ref, evidence_ref = _write_task_artifacts(ai / "specs", "T-1")
        write_json_model(
            ai / "specs" / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-1",
                        title="Dependency task",
                        status=TaskLifecycleState.DONE,
                        owner_role="Build",
                        write_scope=["src/**"],
                        handoffs=[handoff_ref],
                        evidence=[evidence_ref],
                    ),
                    TaskLedgerTask(
                        id="T-2",
                        title="Active task",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="Build",
                        dependencies=["T-1"],
                        write_scope=["tests/**"],
                    ),
                ]
            ),
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        ok_checks = [
            c
            for c in report.checks
            if c.name == "task-dependency-validation" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE)

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_done_task_with_missing_dependency_stays_in_dependency_validation(
        self, tmp_path: Path
    ) -> None:
        ai = _setup_full_project(tmp_path)
        write_json_model(
            ai / "specs" / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-1",
                        title="Completed task",
                        status=TaskLifecycleState.DONE,
                        owner_role="Build",
                        dependencies=["T-2"],
                        write_scope=["tests/**"],
                    )
                ]
            ),
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        dependency_checks = [c for c in report.checks if c.name == "task-dependency-validation"]
        state_checks = [c for c in report.checks if c.name == "task-state-consistency"]

        assert len(dependency_checks) == 1
        assert dependency_checks[0].status == IntegrityStatus.FAIL
        assert state_checks == []
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE) is False

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_done_task_with_incomplete_dependency_fails(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        write_json_model(
            ai / "specs" / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-1",
                        title="Dependency task",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="Build",
                        write_scope=["src/**"],
                    ),
                    TaskLedgerTask(
                        id="T-2",
                        title="Completed task",
                        status=TaskLifecycleState.DONE,
                        owner_role="Build",
                        dependencies=["T-1"],
                        write_scope=["tests/**"],
                    ),
                ]
            ),
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "task-state-consistency" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE) is False

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_done_task_with_done_dependency_passes(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        first_handoff_ref, first_evidence_ref = _write_task_artifacts(ai / "specs", "T-1")
        second_handoff_ref, second_evidence_ref = _write_task_artifacts(ai / "specs", "T-2")
        write_json_model(
            ai / "specs" / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-1",
                        title="Dependency task",
                        status=TaskLifecycleState.DONE,
                        owner_role="Build",
                        write_scope=["src/**"],
                        handoffs=[first_handoff_ref],
                        evidence=[first_evidence_ref],
                    ),
                    TaskLedgerTask(
                        id="T-2",
                        title="Completed task",
                        status=TaskLifecycleState.DONE,
                        owner_role="Build",
                        dependencies=["T-1"],
                        write_scope=["tests/**"],
                        handoffs=[second_handoff_ref],
                        evidence=[second_evidence_ref],
                    ),
                ]
            ),
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        ok_checks = [
            c
            for c in report.checks
            if c.name == "task-state-consistency" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE)

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_review_task_without_handoff_ref_fails(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        write_json_model(
            ai / "specs" / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-1",
                        title="Ready for review",
                        status=TaskLifecycleState.REVIEW,
                        owner_role="Build",
                        write_scope=["src/**"],
                    )
                ]
            ),
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "task-lifecycle-artifact-validation" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "T-1" in fail_checks[0].message
        assert "handoff" in fail_checks[0].message
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE) is False

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_verify_task_without_evidence_ref_fails(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        handoff_ref, _evidence_ref = _write_task_artifacts(ai / "specs", "T-1")
        write_json_model(
            ai / "specs" / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-1",
                        title="Ready for verify",
                        status=TaskLifecycleState.VERIFY,
                        owner_role="Build",
                        write_scope=["src/**"],
                        handoffs=[handoff_ref],
                    )
                ]
            ),
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "task-lifecycle-artifact-validation" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "T-1" in fail_checks[0].message
        assert "evidence" in fail_checks[0].message
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE) is False

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_task_with_missing_handoff_ref_fails(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        write_json_model(
            ai / "specs" / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-1",
                        title="Produce handoff",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="Build",
                        write_scope=["src/**"],
                        handoffs=[
                            HandoffRef(
                                kind="build",
                                path=".ai-engineering/state/archive/delivery-logs/spec-117/missing-handoff.md",
                            )
                        ],
                    )
                ]
            ),
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "task-artifact-reference-validation" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE) is False

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_task_with_missing_evidence_ref_fails(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        write_json_model(
            ai / "specs" / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-1",
                        title="Collect evidence",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="Build",
                        write_scope=["tests/**"],
                        evidence=[EvidenceRef(kind="pytest", path="evidence/missing-verify.log")],
                    )
                ]
            ),
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "task-artifact-reference-validation" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE) is False

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_task_with_absolute_artifact_ref_fails(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        write_json_model(
            ai / "specs" / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-1",
                        title="Absolute handoff path",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="Build",
                        write_scope=["src/**"],
                        handoffs=[
                            HandoffRef(
                                kind="build",
                                path=str(tmp_path / "outside.md"),
                            )
                        ],
                    )
                ]
            ),
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "task-artifact-reference-validation" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "is absolute" in fail_checks[0].message
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE) is False

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_task_with_escaping_relative_artifact_ref_fails(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        write_json_model(
            ai / "specs" / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-1",
                        title="Escaping evidence path",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="Build",
                        write_scope=["tests/**"],
                        evidence=[EvidenceRef(kind="pytest", path="../outside.md")],
                    )
                ]
            ),
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "task-artifact-reference-validation" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "escapes the active work plane" in fail_checks[0].message
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE) is False

    @pytest.mark.skip(reason="Spec-123 removed task-ledger validation surface")
    def test_task_artifact_refs_use_resolved_active_work_plane(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        write_json_model(
            ai / "specs" / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-legacy",
                        title="Legacy work plane task",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="Build",
                        write_scope=["src/**"],
                        handoffs=[HandoffRef(kind="build", path="handoffs/legacy-missing.md")],
                    )
                ]
            ),
        )

        pointed_specs_dir = _write_work_plane(
            tmp_path / ".ai-engineering" / "specs" / "spec-117-hx-02",
            spec_name="006-pointed",
        )
        (pointed_specs_dir / "build-note.md").write_text("Build handoff\n", encoding="utf-8")
        (pointed_specs_dir / "evidence" / "verify.log").write_text(
            "verify output\n",
            encoding="utf-8",
        )
        write_json_model(
            pointed_specs_dir / "task-ledger.json",
            TaskLedger(
                tasks=[
                    TaskLedgerTask(
                        id="T-pointed",
                        title="Pointed work plane task",
                        status=TaskLifecycleState.IN_PROGRESS,
                        owner_role="Build",
                        write_scope=["src/**"],
                        handoffs=[
                            HandoffRef(
                                kind="build",
                                path=".ai-engineering/specs/spec-117-hx-02/build-note.md",
                            )
                        ],
                        evidence=[EvidenceRef(kind="pytest", path="evidence/verify.log")],
                    )
                ]
            ),
        )
        write_active_work_plane_pointer(tmp_path, pointed_specs_dir)

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        ok_checks = [
            c
            for c in report.checks
            if c.name == "task-artifact-reference-validation" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE)

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

    def test_source_repo_ownership_snapshot_matches_default_contract(self, tmp_path: Path) -> None:
        ai = _make_governance(tmp_path)
        _write_source_repo_markers(tmp_path, ai)
        _write_active_spec(ai)
        write_json_model(ai / "state" / "ownership-map.json", default_ownership_map())

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        ok_checks = [
            c
            for c in report.checks
            if c.name == "ownership-map-snapshot" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_source_repo_ownership_snapshot_drift_fails(self, tmp_path: Path) -> None:
        ai = _make_governance(tmp_path)
        _write_source_repo_markers(tmp_path, ai)
        _write_active_spec(ai)
        drifted = default_ownership_map()
        drifted.paths = []
        write_json_model(ai / "state" / "ownership-map.json", drifted)

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "ownership-map-snapshot" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1

    def test_source_repo_framework_capabilities_snapshot_matches_builder(
        self, tmp_path: Path
    ) -> None:
        ai = _make_governance(tmp_path)
        _write_source_repo_markers(tmp_path, ai)
        _write_active_spec(ai)
        write_framework_capabilities(tmp_path)

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        ok_checks = [
            c
            for c in report.checks
            if c.name == "framework-capabilities-snapshot" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_source_repo_framework_capabilities_snapshot_drift_fails(self, tmp_path: Path) -> None:
        ai = _make_governance(tmp_path)
        _write_source_repo_markers(tmp_path, ai)
        _write_active_spec(ai)
        drifted = write_framework_capabilities(tmp_path)
        drifted.context_classes = drifted.context_classes[:-1]
        write_json_model(framework_capabilities_path(tmp_path), drifted)

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "framework-capabilities-snapshot" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1

    def test_source_repo_control_plane_authority_contract_passes(self, tmp_path: Path) -> None:
        ai = _make_governance(tmp_path)
        _write_source_repo_markers(tmp_path, ai)
        _write_active_spec(ai)
        write_json_model(ai / "state" / "ownership-map.json", default_ownership_map())
        write_framework_capabilities(tmp_path)

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        ok_checks = [
            c
            for c in report.checks
            if c.name == "control-plane-authority-contract" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_source_repo_control_plane_authority_contract_drift_fails(self, tmp_path: Path) -> None:
        ai = _make_governance(tmp_path)
        _write_source_repo_markers(tmp_path, ai)
        _write_active_spec(ai)
        write_json_model(ai / "state" / "ownership-map.json", default_ownership_map())
        write_framework_capabilities(tmp_path)

        template_manifest = (
            tmp_path / "src" / "ai_engineering" / "templates" / ".ai-engineering" / "manifest.yml"
        )
        template_manifest.write_text(
            _source_repo_manifest_text().replace(
                "    - CONSTITUTION.md\n",
                "    - .ai-engineering/CONSTITUTION.md\n",
            ),
            encoding="utf-8",
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "control-plane-authority-contract" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1


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
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        (tmp_path / ".ai-engineering" / "manifest.yml").write_text(
            "name: test-project\n"
            "version: 1.0.0\n"
            "ai_providers:\n"
            "  enabled: [claude_code, github_copilot]\n"
            "  primary: claude_code\n"
            "ownership:\n"
            "  root_entry_points:\n"
            "    CLAUDE.md:\n"
            "      owner: framework\n"
            "      canonical_source: CLAUDE.md\n"
            "      runtime_role: ide-overlay\n"
            "      sync:\n"
            "        mode: copy\n"
            "        template_path: src/ai_engineering/templates/project/CLAUDE.md\n"
            "        mirror_paths: []\n"
            "    AGENTS.md:\n"
            "      owner: framework\n"
            "      canonical_source: scripts/sync_command_mirrors.py:generate_agents_md\n"
            "      runtime_role: shared-runtime-contract\n"
            "      sync:\n"
            "        mode: generate\n"
            "        template_path: src/ai_engineering/templates/project/AGENTS.md\n"
            "        mirror_paths: []\n"
            "    .github/copilot-instructions.md:\n"
            "      owner: framework\n"
            "      canonical_source: src/ai_engineering/templates/project/copilot-instructions.md\n"
            "      runtime_role: ide-overlay\n"
            "      sync:\n"
            "        mode: generate\n"
            "        template_path: src/ai_engineering/templates/project/copilot-instructions.md\n"
            "        mirror_paths: []\n",
            encoding="utf-8",
        )
        (tmp_path / "src" / "ai_engineering" / "templates").mkdir(parents=True)
        files = _instruction_files(tmp_path)
        assert any("templates" in f for f in files)
        assert len(files) == 6  # 3 base + 3 template

    def test_non_source_repo_without_manifest_uses_base_instruction_fallback(
        self, tmp_path: Path
    ) -> None:
        assert _instruction_files(tmp_path) == [
            ".github/copilot-instructions.md",
            "AGENTS.md",
            "CLAUDE.md",
        ]


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
        _write_manifest(
            ai,
            providers=("claude_code",),
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
            providers=("claude_code",),
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
            providers=("claude_code",),
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
            providers=("claude_code",),
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
