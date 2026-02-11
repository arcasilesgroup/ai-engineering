"""Tests for ai_engineering.validator.service -- content integrity validation."""

from __future__ import annotations

import shutil
from pathlib import Path

from ai_engineering.validator.service import (
    CheckStatus,
    IntegrityCategory,
    IntegrityCheckResult,
    IntegrityReport,
    validate_content_integrity,
)


# -- Helpers ----------------------------------------------------------------


_SKILL_PATHS = [
    "skills/workflows/commit.md",
    "skills/workflows/pr.md",
    "skills/workflows/acho.md",
    "skills/workflows/pre-implementation.md",
    "skills/swe/debug.md",
    "skills/swe/refactor.md",
    "skills/swe/changelog-documentation.md",
    "skills/swe/code-review.md",
    "skills/swe/test-strategy.md",
    "skills/swe/architecture-analysis.md",
    "skills/swe/pr-creation.md",
    "skills/swe/dependency-update.md",
    "skills/swe/performance-analysis.md",
    "skills/swe/security-review.md",
    "skills/swe/migration.md",
    "skills/swe/prompt-engineer.md",
    "skills/swe/python-mastery.md",
    "skills/swe/doc-writer.md",
    "skills/lifecycle/content-integrity.md",
    "skills/lifecycle/create-agent.md",
    "skills/lifecycle/create-skill.md",
    "skills/lifecycle/create-spec.md",
    "skills/lifecycle/delete-agent.md",
    "skills/lifecycle/delete-skill.md",
    "skills/lifecycle/accept-risk.md",
    "skills/lifecycle/resolve-risk.md",
    "skills/lifecycle/renew-risk.md",
    "skills/quality/audit-code.md",
    "skills/quality/audit-report.md",
    "skills/utils/git-helpers.md",
    "skills/utils/platform-detection.md",
    "skills/validation/install-readiness.md",
]

_AGENT_PATHS = [
    "agents/principal-engineer.md",
    "agents/debugger.md",
    "agents/architect.md",
    "agents/quality-auditor.md",
    "agents/security-reviewer.md",
    "agents/codebase-mapper.md",
    "agents/code-simplifier.md",
    "agents/verify-app.md",
]


def _make_governance(root: Path) -> Path:
    """Create a minimal .ai-engineering governance tree."""
    ai = root / ".ai-engineering"
    for d in [
        "skills/workflows", "skills/swe", "skills/lifecycle",
        "skills/quality", "skills/utils", "skills/validation",
        "agents", "standards/framework", "standards/team",
        "context/product", "context/specs", "state",
    ]:
        (ai / d).mkdir(parents=True, exist_ok=True)
    return ai


def _write_skill(ai: Path, rel: str) -> None:
    """Create a skill/agent markdown file."""
    path = ai / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {path.stem}\n", encoding="utf-8")


def _make_instruction_content(
    skills: list[str] | None = None,
    agents: list[str] | None = None,
) -> str:
    """Build instruction file content with skill/agent listings."""
    skill_list = skills if skills is not None else _SKILL_PATHS
    agent_list = agents if agents is not None else _AGENT_PATHS
    prefixes = {
        "Workflows": "skills/workflows/",
        "SWE Skills": "skills/swe/",
        "Lifecycle Skills": "skills/lifecycle/",
        "Quality Skills": "skills/quality/",
        "Utility Skills": "skills/utils/",
        "Validation Skills": "skills/validation/",
    }
    lines = ["# Instructions", "", "## Skills", ""]
    for heading, prefix in prefixes.items():
        lines.append(f"### {heading}")
        lines.append("")
        for s in skill_list:
            if s.startswith(prefix):
                lines.append(f"- `.ai-engineering/{s}`")
        lines.append("")
    lines.extend(["## Agents", ""])
    for a in agent_list:
        lines.append(f"- `.ai-engineering/{a}`")
    lines.append("")
    return "\n".join(lines)


def _write_all_instruction_files(
    root: Path, content: str | None = None,
) -> None:
    """Write identical instruction files to all 8 standard locations."""
    text = content if content is not None else _make_instruction_content()
    files = [
        root / ".github" / "copilot-instructions.md",
        root / "AGENTS.md",
        root / "CLAUDE.md",
        root / "codex.md",
        root / "src" / "ai_engineering" / "templates" / "project" / "copilot-instructions.md",
        root / "src" / "ai_engineering" / "templates" / "project" / "AGENTS.md",
        root / "src" / "ai_engineering" / "templates" / "project" / "CLAUDE.md",
        root / "src" / "ai_engineering" / "templates" / "project" / "codex.md",
    ]
    for f in files:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")


def _write_product_contract(
    ai: Path, *, skills: int = 32, agents: int = 8,
) -> None:
    """Write a minimal product-contract.md with counters."""
    pc = ai / "context" / "product" / "product-contract.md"
    pc.parent.mkdir(parents=True, exist_ok=True)
    pc.write_text(
        f"# Product\n\nShip {skills} skills, {agents} agents.\n\n"
        f"## KPIs\n\n{skills} skills + {agents} agents coverage.\n",
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
    ai: Path, spec_name: str = "006-test",
) -> Path:
    """Write _active.md and create the spec directory."""
    active = ai / "context" / "specs" / "_active.md"
    active.parent.mkdir(parents=True, exist_ok=True)
    active.write_text(
        f'---\nactive: "{spec_name}"\n---\n', encoding="utf-8",
    )
    spec_dir = ai / "context" / "specs" / spec_name
    spec_dir.mkdir(parents=True, exist_ok=True)
    for f in ("spec.md", "plan.md", "tasks.md"):
        (spec_dir / f).write_text(f"# {f}\n", encoding="utf-8")
    return spec_dir


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
    _write_active_spec(ai)
    return ai


# -- IntegrityReport model tests -------------------------------------------


class TestIntegrityReport:
    """Tests for IntegrityReport dataclass."""

    def test_empty_report_passes(self) -> None:
        report = IntegrityReport()
        assert report.passed is True
        assert report.summary == {}

    def test_report_with_ok_passes(self) -> None:
        report = IntegrityReport(checks=[
            IntegrityCheckResult(
                category=IntegrityCategory.FILE_EXISTENCE,
                name="test", status=CheckStatus.OK, message="all good",
            ),
        ])
        assert report.passed is True

    def test_report_with_fail_does_not_pass(self) -> None:
        report = IntegrityReport(checks=[
            IntegrityCheckResult(
                category=IntegrityCategory.FILE_EXISTENCE,
                name="test", status=CheckStatus.FAIL, message="broken",
            ),
        ])
        assert report.passed is False

    def test_report_with_warn_still_passes(self) -> None:
        report = IntegrityReport(checks=[
            IntegrityCheckResult(
                category=IntegrityCategory.FILE_EXISTENCE,
                name="test", status=CheckStatus.WARN, message="warning",
            ),
        ])
        assert report.passed is True

    def test_summary_counts(self) -> None:
        report = IntegrityReport(checks=[
            IntegrityCheckResult(
                category=IntegrityCategory.FILE_EXISTENCE,
                name="a", status=CheckStatus.OK, message="",
            ),
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="b", status=CheckStatus.FAIL, message="",
            ),
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="c", status=CheckStatus.FAIL, message="",
            ),
            IntegrityCheckResult(
                category=IntegrityCategory.COUNTER_ACCURACY,
                name="d", status=CheckStatus.WARN, message="",
            ),
        ])
        assert report.summary == {"ok": 1, "fail": 2, "warn": 1}

    def test_by_category(self) -> None:
        report = IntegrityReport(checks=[
            IntegrityCheckResult(
                category=IntegrityCategory.FILE_EXISTENCE,
                name="a", status=CheckStatus.OK, message="",
            ),
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="b", status=CheckStatus.FAIL, message="",
            ),
        ])
        cats = report.by_category()
        assert IntegrityCategory.FILE_EXISTENCE in cats
        assert IntegrityCategory.MIRROR_SYNC in cats
        assert len(cats[IntegrityCategory.FILE_EXISTENCE]) == 1

    def test_category_passed(self) -> None:
        report = IntegrityReport(checks=[
            IntegrityCheckResult(
                category=IntegrityCategory.FILE_EXISTENCE,
                name="a", status=CheckStatus.OK, message="",
            ),
            IntegrityCheckResult(
                category=IntegrityCategory.MIRROR_SYNC,
                name="b", status=CheckStatus.FAIL, message="",
            ),
        ])
        assert report.category_passed(IntegrityCategory.FILE_EXISTENCE) is True
        assert report.category_passed(IntegrityCategory.MIRROR_SYNC) is False

    def test_to_dict_structure(self) -> None:
        report = IntegrityReport(checks=[
            IntegrityCheckResult(
                category=IntegrityCategory.FILE_EXISTENCE,
                name="a", status=CheckStatus.OK, message="ok msg",
            ),
        ])
        d = report.to_dict()
        assert d["passed"] is True
        assert "summary" in d
        assert "categories" in d
        assert "file-existence" in d["categories"]

    def test_to_dict_includes_file_path(self) -> None:
        report = IntegrityReport(checks=[
            IntegrityCheckResult(
                category=IntegrityCategory.FILE_EXISTENCE,
                name="a", status=CheckStatus.FAIL, message="broken",
                file_path="some/file.md",
            ),
        ])
        d = report.to_dict()
        checks = d["categories"]["file-existence"]["checks"]
        assert checks[0]["file"] == "some/file.md"


# -- Category 1: File Existence -------------------------------------------


class TestFileExistence:
    """Tests for file-existence validation."""

    def test_missing_governance_directory(self, tmp_path: Path) -> None:
        report = validate_content_integrity(
            tmp_path, categories=[IntegrityCategory.FILE_EXISTENCE],
        )
        assert report.passed is False
        assert any(c.name == "governance-directory" for c in report.checks)

    def test_all_references_resolve(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        report = validate_content_integrity(
            tmp_path, categories=[IntegrityCategory.FILE_EXISTENCE],
        )
        assert report.category_passed(IntegrityCategory.FILE_EXISTENCE)

    def test_broken_reference_detected(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        skill = ai / "skills" / "workflows" / "commit.md"
        skill.write_text(
            "# Commit\n\nSee `skills/nonexistent/phantom.md` for details.\n",
            encoding="utf-8",
        )
        report = validate_content_integrity(
            tmp_path, categories=[IntegrityCategory.FILE_EXISTENCE],
        )
        fail_checks = [
            c for c in report.checks
            if c.category == IntegrityCategory.FILE_EXISTENCE
            and c.status == CheckStatus.FAIL
        ]
        assert len(fail_checks) >= 1

    def test_spec_directory_completeness(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        bad_spec = ai / "context" / "specs" / "007-incomplete"
        bad_spec.mkdir(parents=True)
        (bad_spec / "spec.md").write_text("# spec\n", encoding="utf-8")
        report = validate_content_integrity(
            tmp_path, categories=[IntegrityCategory.FILE_EXISTENCE],
        )
        fail_checks = [
            c for c in report.checks
            if c.name == "spec-007-incomplete" and c.status == CheckStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "plan.md" in fail_checks[0].message


# -- Category 2: Mirror Sync ----------------------------------------------


class TestMirrorSync:
    """Tests for mirror-sync validation."""

    def test_missing_canonical_root(self, tmp_path: Path) -> None:
        report = validate_content_integrity(
            tmp_path, categories=[IntegrityCategory.MIRROR_SYNC],
        )
        assert report.passed is False

    def test_synced_mirrors_pass(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        mirror_root = (
            tmp_path / "src" / "ai_engineering"
            / "templates" / ".ai-engineering"
        )
        for subdir in ("skills", "agents", "standards/framework"):
            src_dir = ai / subdir
            if not src_dir.is_dir():
                continue
            for f in sorted(src_dir.rglob("*.md")):
                rel = f.relative_to(ai)
                dest = mirror_root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(f.read_bytes())
        report = validate_content_integrity(
            tmp_path, categories=[IntegrityCategory.MIRROR_SYNC],
        )
        governance_fails = [
            c for c in report.checks
            if c.category == IntegrityCategory.MIRROR_SYNC
            and c.status == CheckStatus.FAIL
            and "claude" not in c.name
        ]
        assert len(governance_fails) == 0

    def test_desynced_mirror_detected(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        mirror_root = (
            tmp_path / "src" / "ai_engineering"
            / "templates" / ".ai-engineering"
        )
        for subdir in ("skills", "agents", "standards/framework"):
            src_dir = ai / subdir
            if not src_dir.is_dir():
                continue
            for f in sorted(src_dir.rglob("*.md")):
                rel = f.relative_to(ai)
                dest = mirror_root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(f.read_bytes())
        desynced = mirror_root / "skills" / "workflows" / "commit.md"
        desynced.write_text("DESYNCED CONTENT", encoding="utf-8")
        report = validate_content_integrity(
            tmp_path, categories=[IntegrityCategory.MIRROR_SYNC],
        )
        desync_checks = [
            c for c in report.checks
            if c.status == CheckStatus.FAIL and "desync" in c.name
        ]
        assert len(desync_checks) >= 1


# -- Category 3: Counter Accuracy -----------------------------------------


class TestCounterAccuracy:
    """Tests for counter-accuracy validation."""

    def test_consistent_counts_pass(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        report = validate_content_integrity(
            tmp_path, categories=[IntegrityCategory.COUNTER_ACCURACY],
        )
        assert report.category_passed(IntegrityCategory.COUNTER_ACCURACY)

    def test_mismatched_skill_counts_detected(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        shorter = _make_instruction_content(skills=_SKILL_PATHS[:-1])
        (tmp_path / "AGENTS.md").write_text(shorter, encoding="utf-8")
        report = validate_content_integrity(
            tmp_path, categories=[IntegrityCategory.COUNTER_ACCURACY],
        )
        fail_checks = [
            c for c in report.checks
            if c.category == IntegrityCategory.COUNTER_ACCURACY
            and c.status == CheckStatus.FAIL
        ]
        assert len(fail_checks) >= 1

    def test_product_contract_mismatch_detected(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        _write_product_contract(ai, skills=99, agents=99)
        report = validate_content_integrity(
            tmp_path, categories=[IntegrityCategory.COUNTER_ACCURACY],
        )
        fail_checks = [
            c for c in report.checks
            if c.name.startswith("product-contract-")
            and c.status == CheckStatus.FAIL
        ]
        assert len(fail_checks) >= 1

    def test_missing_instruction_file(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        (tmp_path / "CLAUDE.md").unlink()
        report = validate_content_integrity(
            tmp_path, categories=[IntegrityCategory.COUNTER_ACCURACY],
        )
        fail_checks = [
            c for c in report.checks
            if c.status == CheckStatus.FAIL and "missing" in c.name
        ]
        assert len(fail_checks) >= 1


# -- Category 4: Cross-Reference Integrity --------------------------------


class TestCrossReference:
    """Tests for cross-reference validation."""

    def test_valid_references_pass(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        skill = ai / "skills" / "swe" / "debug.md"
        skill.write_text(
            "# Debug\n\n## References\n\n- `skills/swe/refactor.md`\n",
            encoding="utf-8",
        )
        report = validate_content_integrity(
            tmp_path, categories=[IntegrityCategory.CROSS_REFERENCE],
        )
        assert report.category_passed(IntegrityCategory.CROSS_REFERENCE)

    def test_broken_reference_detected(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        skill = ai / "skills" / "swe" / "debug.md"
        skill.write_text(
            "# Debug\n\n## References\n\n- `skills/swe/nonexistent.md`\n",
            encoding="utf-8",
        )
        report = validate_content_integrity(
            tmp_path, categories=[IntegrityCategory.CROSS_REFERENCE],
        )
        assert report.category_passed(IntegrityCategory.CROSS_REFERENCE) is False

    def test_no_governance_dir_skips(self, tmp_path: Path) -> None:
        report = validate_content_integrity(
            tmp_path, categories=[IntegrityCategory.CROSS_REFERENCE],
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
        assert (
            report.category_passed(IntegrityCategory.INSTRUCTION_CONSISTENCY)
            is False
        )

    def test_missing_subsection_detected(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        lines = ["# Instructions", "", "## Skills", ""]
        for s in _SKILL_PATHS:
            lines.append(f"- `.ai-engineering/{s}`")
        lines.extend(["", "## Agents", ""])
        for a in _AGENT_PATHS:
            lines.append(f"- `.ai-engineering/{a}`")
        (tmp_path / "AGENTS.md").write_text("\n".join(lines), encoding="utf-8")
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.INSTRUCTION_CONSISTENCY],
        )
        fail_checks = [
            c for c in report.checks if "missing-subsections" in c.name
        ]
        assert len(fail_checks) >= 1


# -- Category 6: Manifest Coherence ---------------------------------------


class TestManifestCoherence:
    """Tests for manifest-coherence validation."""

    def test_complete_manifest_passes(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        report = validate_content_integrity(
            tmp_path, categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE)

    def test_missing_manifest_fails(self, tmp_path: Path) -> None:
        _make_governance(tmp_path)
        _write_active_spec(tmp_path / ".ai-engineering")
        report = validate_content_integrity(
            tmp_path, categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE) is False

    def test_active_spec_valid(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        report = validate_content_integrity(
            tmp_path, categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )
        ok_checks = [
            c for c in report.checks
            if c.name == "active-spec" and c.status == CheckStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_active_spec_missing_directory(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        active = ai / "context" / "specs" / "_active.md"
        active.write_text(
            '---\nactive: "999-nonexistent"\n---\n', encoding="utf-8",
        )
        report = validate_content_integrity(
            tmp_path, categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )
        fail_checks = [
            c for c in report.checks
            if c.name == "active-spec-dir" and c.status == CheckStatus.FAIL
        ]
        assert len(fail_checks) == 1

    def test_missing_ownership_directory(self, tmp_path: Path) -> None:
        ai = _make_governance(tmp_path)
        _write_manifest(ai)
        shutil.rmtree(ai / "agents")
        _write_active_spec(ai)
        report = validate_content_integrity(
            tmp_path, categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )
        fail_checks = [
            c for c in report.checks
            if c.status == CheckStatus.FAIL and "agents" in c.name
        ]
        assert len(fail_checks) >= 1


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
            tmp_path, categories=[IntegrityCategory.FILE_EXISTENCE],
        )
        cats = {c.category for c in report.checks}
        assert cats == {IntegrityCategory.FILE_EXISTENCE}

    def test_to_dict_roundtrip(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        report = validate_content_integrity(
            tmp_path, categories=[IntegrityCategory.FILE_EXISTENCE],
        )
        d = report.to_dict()
        assert isinstance(d, dict)
        assert "passed" in d
        assert "categories" in d
        assert isinstance(d["categories"], dict)
