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
    (ai / "standards" / "framework").mkdir(parents=True, exist_ok=True)
    (ai / "context" / "product").mkdir(parents=True, exist_ok=True)
    (ai / "context" / "specs").mkdir(parents=True, exist_ok=True)
    (ai / "state").mkdir(parents=True, exist_ok=True)
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
    (mirror / "skills").mkdir(parents=True, exist_ok=True)
    (ai / "skills" / "debug.md").write_text("x", encoding="utf-8")
    (mirror / "skills" / "orphan.md").write_text("y", encoding="utf-8")
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
    (ai / "context" / "product" / "product-contract.md").write_text(
        "Ship 1 skills, 2 agents.\n\n1 skills + 2 agents coverage.", encoding="utf-8"
    )
    content = (
        "## Skills\n"
        "- `.ai-engineering/skills/debug.md`\n\n"
        "## Agents\n"
        "- `.ai-engineering/agents/a.md`\n"
    )
    _write_instruction_files(tmp_path, content)
    report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.COUNTER_ACCURACY])
    assert report.category_passed(IntegrityCategory.COUNTER_ACCURACY) is False


def test_instruction_consistency_missing_file_and_differences(tmp_path: Path) -> None:
    base_content = """
## Skills
- `.ai-engineering/skills/a.md`

## Agents
- `.ai-engineering/agents/a.md`
"""
    _write_instruction_files(tmp_path, base_content)
    # mutate one file to create difference
    (tmp_path / "CLAUDE.md").write_text(
        base_content + "- `.ai-engineering/agents/b.md`\n", encoding="utf-8"
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
    active = ai / "context" / "specs" / "_active.md"

    active.write_text('active: "none"\n', encoding="utf-8")
    r1 = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MANIFEST_COHERENCE])
    assert r1.category_passed(IntegrityCategory.MANIFEST_COHERENCE)

    active.write_text('active: "999-missing"\n', encoding="utf-8")
    r2 = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MANIFEST_COHERENCE])
    assert r2.category_passed(IntegrityCategory.MANIFEST_COHERENCE) is False

    spec = ai / "context" / "specs" / "abc"
    spec.mkdir(parents=True, exist_ok=True)
    active.write_text('active: "abc"\n', encoding="utf-8")
    r3 = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MANIFEST_COHERENCE])
    assert r3.category_passed(IntegrityCategory.MANIFEST_COHERENCE) is False


def test_skill_frontmatter_additional_failure_paths(tmp_path: Path) -> None:
    ai = _mk(tmp_path)
    (ai / "skills" / "bad-type").mkdir(parents=True, exist_ok=True)
    s1 = ai / "skills" / "bad-type" / "SKILL.md"
    s1.write_text("---\n- x\n---\n", encoding="utf-8")
    (ai / "skills" / "bad-req").mkdir(parents=True, exist_ok=True)
    s2 = ai / "skills" / "bad-req" / "SKILL.md"
    s2.write_text(
        "---\nname: bad-req\nversion: 1.0.0\nrequires: bad\nos: nope\n---\n",
        encoding="utf-8",
    )
    (ai / "skills" / "bad-os").mkdir(parents=True, exist_ok=True)
    s3 = ai / "skills" / "bad-os" / "SKILL.md"
    s3.write_text(
        "---\nname: bad-os\nversion: 1.0.0\nos: [plan9]\n---\n",
        encoding="utf-8",
    )
    report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.SKILL_FRONTMATTER])
    assert report.category_passed(IntegrityCategory.SKILL_FRONTMATTER) is False


def test_skill_frontmatter_invalid_yaml_and_missing_dir(tmp_path: Path) -> None:
    report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.SKILL_FRONTMATTER])
    assert report.category_passed(IntegrityCategory.SKILL_FRONTMATTER) is False

    ai = _mk(tmp_path)
    (ai / "skills" / "bad-yaml").mkdir(parents=True, exist_ok=True)
    bad = ai / "skills" / "bad-yaml" / "SKILL.md"
    bad.write_text("---\nname: [\n---\n", encoding="utf-8")
    report2 = validate_content_integrity(tmp_path, categories=[IntegrityCategory.SKILL_FRONTMATTER])
    assert report2.category_passed(IntegrityCategory.SKILL_FRONTMATTER) is False


def test_manifest_coherence_active_null_unquoted(tmp_path: Path) -> None:
    """Unquoted `active: null` is treated as no active spec (passes)."""
    ai = _mk(tmp_path)
    (ai / "manifest.yml").write_text("name: x\n", encoding="utf-8")
    active = ai / "context" / "specs" / "_active.md"
    active.write_text("active: null\n", encoding="utf-8")
    report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MANIFEST_COHERENCE])
    assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE)


def test_manifest_coherence_active_tilde(tmp_path: Path) -> None:
    """YAML tilde `~` is a null alias and should pass."""
    ai = _mk(tmp_path)
    (ai / "manifest.yml").write_text("name: x\n", encoding="utf-8")
    active = ai / "context" / "specs" / "_active.md"
    active.write_text("active: ~\n", encoding="utf-8")
    report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MANIFEST_COHERENCE])
    assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE)


def test_manifest_coherence_archive_spec_found(tmp_path: Path) -> None:
    """Active spec pointing to archive/ directory passes validation."""
    ai = _mk(tmp_path)
    (ai / "manifest.yml").write_text("name: x\n", encoding="utf-8")
    # Create spec in archive dir
    spec_dir = ai / "context" / "specs" / "archive" / "033-archived"
    spec_dir.mkdir(parents=True, exist_ok=True)
    for f in ("spec.md", "plan.md", "tasks.md"):
        (spec_dir / f).write_text(f"# {f}\n", encoding="utf-8")
    active = ai / "context" / "specs" / "_active.md"
    active.write_text('active: "033-archived"\n', encoding="utf-8")
    report = validate_content_integrity(tmp_path, categories=[IntegrityCategory.MANIFEST_COHERENCE])
    assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE)
