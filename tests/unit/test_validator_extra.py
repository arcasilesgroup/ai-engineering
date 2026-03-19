"""Additional branch coverage for validator.service."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.validator.service import IntegrityCategory, validate_content_integrity

pytestmark = pytest.mark.unit


def _mk(root: Path) -> Path:
    ai = root / ".ai-engineering"
    (ai / "skills").mkdir(parents=True, exist_ok=True)
    (ai / "agents").mkdir(parents=True, exist_ok=True)
    (ai / "contexts").mkdir(parents=True, exist_ok=True)
    (ai / "context" / "product").mkdir(parents=True, exist_ok=True)
    (ai / "specs").mkdir(parents=True, exist_ok=True)
    (ai / "state").mkdir(parents=True, exist_ok=True)
    (ai / "tasks").mkdir(parents=True, exist_ok=True)
    return ai


def _write_instruction_files(root: Path, content: str) -> None:
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
        f.write_text(content, encoding="utf-8")


def test_file_existence_skips_placeholders_and_prefix_cleanup(tmp_path: Path) -> None:
    ai = _mk(tmp_path)
    # Create Working Buffer spec files to pass spec-buffer check
    (ai / "specs" / "spec.md").write_text("# No active spec\n", encoding="utf-8")
    (ai / "specs" / "plan.md").write_text("# No active plan\n", encoding="utf-8")
    src = ai / "skills" / "debug.md"
    src.write_text(
        "---\nname: debug\nversion: 1.0.0\n---\n\n"
        "see `.ai-engineering/ai-engineering/skills/debug.md` "
        "and `.ai-engineering/skills/<name>.md`\n",
        encoding="utf-8",
    )
    report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.FILE_EXISTENCE])
    assert report.category_passed(IntegrityCategory.FILE_EXISTENCE)


def test_mirror_sync_missing_and_orphan(tmp_path: Path) -> None:
    ai = _mk(tmp_path)
    mirror = tmp_path / "src" / "ai_engineering" / "templates" / ".ai-engineering"
    # Governance mirror syncs contexts/**/*.md — use that pattern
    (mirror / "contexts").mkdir(parents=True, exist_ok=True)
    (ai / "contexts" / "debug.md").write_text("x", encoding="utf-8")
    (mirror / "contexts" / "orphan.md").write_text("y", encoding="utf-8")
    report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MIRROR_SYNC])
    checks = [c.name for c in report.by_category()[IntegrityCategory.MIRROR_SYNC]]
    assert any(name.startswith("missing-mirror-") for name in checks)
    assert any(name.startswith("orphan-mirror-") for name in checks)


def test_claude_commands_mirror_missing_root_and_mismatch(tmp_path: Path) -> None:
    _mk(tmp_path)
    # Mark as source repo so mirror checks actually run
    (tmp_path / "src" / "ai_engineering" / "templates").mkdir(parents=True, exist_ok=True)
    # add canonical .claude commands so checker runs
    cmd = tmp_path / ".claude" / "commands" / "a.md"
    cmd.parent.mkdir(parents=True, exist_ok=True)
    cmd.write_text("a", encoding="utf-8")

    report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MIRROR_SYNC])
    assert report.category_passed(IntegrityCategory.MIRROR_SYNC) is False

    mirror = tmp_path / "src" / "ai_engineering" / "templates" / "project" / ".claude" / "commands"
    mirror.mkdir(parents=True, exist_ok=True)
    (mirror / "a.md").write_text("different", encoding="utf-8")
    report2 = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MIRROR_SYNC])
    assert report2.category_passed(IntegrityCategory.MIRROR_SYNC) is False


def test_counter_accuracy_agent_mismatch(tmp_path: Path) -> None:
    ai = _mk(tmp_path)
    # manifest.yml lists 1 skill and 2 agents
    (ai / "manifest.yml").write_text(
        "skills:\n  total: 1\n  registry:\n    ai-debug: {type: workflow}\n\n"
        "agents:\n  total: 2\n  names: [a, b]\n",
        encoding="utf-8",
    )
    # Instruction files list only 1 agent
    content = (
        "## Skills\n"
        "| Domain | Skills |\n|--------|--------|\n| Build | debug |\n\n"
        "## Agents\n"
        "| Agent | Purpose | Scope |\n|-------|---------|-------|\n"
        "| a | purpose | scope |\n"
    )
    _write_instruction_files(tmp_path, content)
    report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.COUNTER_ACCURACY])
    assert report.category_passed(IntegrityCategory.COUNTER_ACCURACY) is False


def test_instruction_consistency_missing_file_and_differences(tmp_path: Path) -> None:
    # Parser expects IDE-specific paths (.claude/ or .agents/)
    base_content = """
## Skills
- `.claude/skills/a/SKILL.md`

## Agents
- `.claude/agents/a.md`
"""
    _write_instruction_files(tmp_path, base_content)
    # mutate one file to create difference
    (tmp_path / "CLAUDE.md").write_text(
        base_content + "- `.claude/agents/b.md`\n", encoding="utf-8"
    )
    # remove one file to hit missing-file branch
    (tmp_path / "CLAUDE.md").unlink()
    report = validate_content_integrity(
        tmp_path,
        categories=[IntegrityCategory.INSTRUCTION_CONSISTENCY],
    )
    assert report.category_passed(IntegrityCategory.INSTRUCTION_CONSISTENCY) is False


def test_instruction_consistency_single_file_returns_early(tmp_path: Path) -> None:
    content = "## Skills\n## Agents\n"
    only = tmp_path / "AGENTS.md"
    only.parent.mkdir(parents=True, exist_ok=True)
    only.write_text(content, encoding="utf-8")
    report = validate_content_integrity(
        tmp_path,
        categories=[IntegrityCategory.INSTRUCTION_CONSISTENCY],
    )
    assert report.category_passed(IntegrityCategory.INSTRUCTION_CONSISTENCY) is False


def test_manifest_coherence_active_spec_branches(tmp_path: Path) -> None:
    ai = _mk(tmp_path)
    (ai / "manifest.yml").write_text("name: x\n", encoding="utf-8")
    spec_path = ai / "specs" / "spec.md"

    # Placeholder spec passes
    spec_path.write_text(
        "# No active spec\n\nRun /ai-brainstorm to start a new spec.\n",
        encoding="utf-8",
    )
    r1 = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MANIFEST_COHERENCE])
    assert r1.category_passed(IntegrityCategory.MANIFEST_COHERENCE)

    # Active spec passes
    spec_path.write_text(
        '---\nid: "042"\n---\n\n# My Feature\n\nContent.\n',
        encoding="utf-8",
    )
    r2 = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MANIFEST_COHERENCE])
    assert r2.category_passed(IntegrityCategory.MANIFEST_COHERENCE)


def test_skill_frontmatter_additional_failure_paths(tmp_path: Path) -> None:
    _mk(tmp_path)
    # Frontmatter validator scans IDE-specific dirs (.claude/skills/)
    claude_skills = tmp_path / ".claude" / "skills"
    (claude_skills / "bad-type").mkdir(parents=True, exist_ok=True)
    s1 = claude_skills / "bad-type" / "SKILL.md"
    s1.write_text("---\n- x\n---\n", encoding="utf-8")
    (claude_skills / "bad-req").mkdir(parents=True, exist_ok=True)
    s2 = claude_skills / "bad-req" / "SKILL.md"
    s2.write_text(
        "---\nname: bad-req\nversion: 1.0.0\nrequires: bad\nos: nope\n---\n",
        encoding="utf-8",
    )
    (claude_skills / "bad-os").mkdir(parents=True, exist_ok=True)
    s3 = claude_skills / "bad-os" / "SKILL.md"
    s3.write_text(
        "---\nname: bad-os\nversion: 1.0.0\nos: [plan9]\n---\n",
        encoding="utf-8",
    )
    report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.SKILL_FRONTMATTER])
    assert report.category_passed(IntegrityCategory.SKILL_FRONTMATTER) is False


def test_skill_frontmatter_invalid_yaml_and_missing_dir(tmp_path: Path) -> None:
    # No IDE skill directories: validator returns OK (skip, not error)
    report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.SKILL_FRONTMATTER])
    assert report.category_passed(IntegrityCategory.SKILL_FRONTMATTER) is True

    # Frontmatter validator scans IDE-specific dirs (.claude/skills/)
    _mk(tmp_path)
    claude_skills = tmp_path / ".claude" / "skills"
    (claude_skills / "bad-yaml").mkdir(parents=True, exist_ok=True)
    bad = claude_skills / "bad-yaml" / "SKILL.md"
    bad.write_text("---\nname: [\n---\n", encoding="utf-8")
    report2 = validate_content_integrity(tmp_path, categories=[IntegrityCategory.SKILL_FRONTMATTER])
    assert report2.category_passed(IntegrityCategory.SKILL_FRONTMATTER) is False


def test_manifest_coherence_placeholder_spec_passes(tmp_path: Path) -> None:
    """Placeholder spec.md is treated as no active spec (passes)."""
    ai = _mk(tmp_path)
    (ai / "manifest.yml").write_text("name: x\n", encoding="utf-8")
    (ai / "specs" / "spec.md").write_text(
        "# No active spec\n\nRun /ai-brainstorm to start a new spec.\n",
        encoding="utf-8",
    )
    report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MANIFEST_COHERENCE])
    assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE)


def test_file_existence_resolves_via_ide_fallback(tmp_path: Path) -> None:
    """Refs to skills/ in .ai-engineering/ docs resolve via .claude/ fallback."""
    ai = _mk(tmp_path)
    # Write a governance doc referencing a skill that only exists in .claude/
    doc = ai / "standards" / "framework" / "core.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(
        "# Core\n\nSee `skills/code/SKILL.md` for details.\n",
        encoding="utf-8",
    )

    # Skill exists in .claude/ (IDE fallback), not in .ai-engineering/
    claude_skill = tmp_path / ".claude" / "skills" / "code"
    claude_skill.mkdir(parents=True, exist_ok=True)
    (claude_skill / "SKILL.md").write_text(
        "---\nname: code\nversion: 1.0.0\n---\n\n# Code\n",
        encoding="utf-8",
    )

    report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.FILE_EXISTENCE])
    # The ref should NOT be broken because .claude/ is a fallback root
    broken = [
        c
        for c in report.checks
        if c.name == "broken-reference" and c.status.value == "fail" and "skills/code" in c.message
    ]
    assert len(broken) == 0


def test_cross_reference_resolves_via_ai_engineering_prefix(tmp_path: Path) -> None:
    """Refs to standards/framework/core.md resolve via .ai-engineering/ fallback."""
    _mk(tmp_path)
    # Create the referenced governance file under .ai-engineering/
    core = tmp_path / ".ai-engineering" / "standards" / "framework" / "core.md"
    core.parent.mkdir(parents=True, exist_ok=True)
    core.write_text("# Core Standard\n", encoding="utf-8")

    # Skill in IDE dir references a governance path (no .ai-engineering/ prefix)
    skill_dir = tmp_path / ".claude" / "skills" / "code"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        "# Code\n\n## References\n\n- `standards/framework/core.md`\n",
        encoding="utf-8",
    )

    report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.CROSS_REFERENCE])
    assert report.category_passed(IntegrityCategory.CROSS_REFERENCE)


def test_cross_reference_resolves_via_template_fallback(tmp_path: Path) -> None:
    """Refs resolve via src/ai_engineering/templates/.ai-engineering/ fallback."""
    _mk(tmp_path)
    # Create the referenced file in the template canonical source
    tpl = (
        tmp_path
        / "src"
        / "ai_engineering"
        / "templates"
        / ".ai-engineering"
        / "standards"
        / "framework"
        / "core.md"
    )
    tpl.parent.mkdir(parents=True, exist_ok=True)
    tpl.write_text("# Core Standard\n", encoding="utf-8")

    skill_dir = tmp_path / ".claude" / "skills" / "code"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        "# Code\n\n## References\n\n- `standards/framework/core.md`\n",
        encoding="utf-8",
    )

    report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.CROSS_REFERENCE])
    assert report.category_passed(IntegrityCategory.CROSS_REFERENCE)


def test_manifest_coherence_missing_spec_md_warns(tmp_path: Path) -> None:
    """Missing specs/spec.md produces a warning."""
    ai = _mk(tmp_path)
    (ai / "manifest.yml").write_text("name: x\n", encoding="utf-8")
    # Remove spec.md to trigger warning
    spec_md = ai / "specs" / "spec.md"
    if spec_md.exists():
        spec_md.unlink()
    report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MANIFEST_COHERENCE])
    warn_checks = [
        c for c in report.checks if c.name == "active-spec-pointer" and c.status.value == "warn"
    ]
    assert len(warn_checks) == 1
