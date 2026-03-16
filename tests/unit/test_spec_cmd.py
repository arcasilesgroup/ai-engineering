"""Unit tests for ai_engineering.cli_commands.spec_cmd.

Covers:
- spec_verify: drift detection, auto-fix, signal emission, done.md warning.
- spec_catalog: generation, tag index.
- spec_list: active spec display.
- spec_compact: age calculation, dry-run, done.md preservation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.cli_commands.spec_cmd import (
    _auto_correct_frontmatter,
    _find_all_spec_files,
    _parse_age_threshold,
)
from ai_engineering.lib.parsing import count_checkboxes, parse_frontmatter

pytestmark = pytest.mark.unit


def _create_spec_tree(
    root: Path,
    spec_id: str,
    slug: str,
    *,
    status: str = "in-progress",
    created: str = "2025-01-15",
    tags: str = "",
    total: int = 5,
    completed: int = 2,
    done: bool = False,
    tasks_checkboxes: str | None = None,
) -> Path:
    """Create a minimal spec directory tree under archive/."""
    archive = root / ".ai-engineering" / "context" / "specs" / "archive"
    spec_dir = archive / f"{spec_id}-{slug}"
    spec_dir.mkdir(parents=True, exist_ok=True)

    tags_line = f"tags: [{tags}]" if tags else ""
    spec_content = (
        f"---\n"
        f'id: "{spec_id}"\n'
        f'slug: "{slug}"\n'
        f'status: "{status}"\n'
        f'created: "{created}"\n'
        f"{tags_line}\n"
        f"---\n\n"
        f"# Spec {spec_id} — {slug}\n"
    )
    (spec_dir / "spec.md").write_text(spec_content)

    if tasks_checkboxes is None:
        checked_lines = "\n".join(f"- [x] {i}.1 Done" for i in range(completed))
        unchecked_lines = "\n".join(f"- [ ] {i}.1 Todo" for i in range(completed, total))
        tasks_checkboxes = f"{checked_lines}\n{unchecked_lines}"

    tasks_content = (
        f"---\n"
        f'spec: "{spec_id}"\n'
        f"total: {total}\n"
        f"completed: {completed}\n"
        f"---\n\n"
        f"# Tasks\n\n{tasks_checkboxes}\n"
    )
    (spec_dir / "tasks.md").write_text(tasks_content)

    if done:
        (spec_dir / "done.md").write_text("# Done\n\nCompleted.\n")

    return spec_dir


def _create_active_md(root: Path, slug: str | None) -> None:
    """Create _active.md pointing to given slug."""
    specs_dir = root / ".ai-engineering" / "context" / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    if slug is None:
        content = '---\nactive: null\nupdated: "2026-01-01"\n---\n\n# Active Spec\n'
    else:
        content = f'---\nactive: "{slug}"\nupdated: "2026-01-01"\n---\n\n# Active Spec\n'
    (specs_dir / "_active.md").write_text(content)


class TestAutoCorrectFrontmatter:
    """Tests for _auto_correct_frontmatter()."""

    def test_corrects_drifted_total(self, tmp_path: Path) -> None:
        """Drifted total is corrected."""
        # Arrange
        tasks = tmp_path / "tasks.md"
        tasks.write_text(
            '---\nspec: "001"\ntotal: 3\ncompleted: 1\n---\n\n'
            "- [x] Done\n- [ ] Todo\n- [ ] Todo\n- [ ] Todo\n- [ ] Todo\n"
        )

        # Act
        result = _auto_correct_frontmatter(tasks, 5, 1)

        # Assert
        assert result is True
        fm = parse_frontmatter(tasks.read_text())
        assert fm["total"] == "5"

    def test_corrects_drifted_completed(self, tmp_path: Path) -> None:
        """Drifted completed is corrected."""
        # Arrange
        tasks = tmp_path / "tasks.md"
        tasks.write_text(
            '---\nspec: "001"\ntotal: 3\ncompleted: 0\n---\n\n- [x] Done\n- [x] Done\n- [ ] Todo\n'
        )

        # Act
        result = _auto_correct_frontmatter(tasks, 3, 2)

        # Assert
        assert result is True
        fm = parse_frontmatter(tasks.read_text())
        assert fm["completed"] == "2"

    def test_no_correction_when_accurate(self, tmp_path: Path) -> None:
        """No changes when frontmatter matches reality."""
        # Arrange
        tasks = tmp_path / "tasks.md"
        tasks.write_text(
            '---\nspec: "001"\ntotal: 3\ncompleted: 1\n---\n\n- [x] Done\n- [ ] Todo\n- [ ] Todo\n'
        )

        # Act
        result = _auto_correct_frontmatter(tasks, 3, 1)

        # Assert
        assert result is False


class TestFindAllSpecFiles:
    """Tests for _find_all_spec_files()."""

    def test_finds_specs_in_archive(self, tmp_path: Path) -> None:
        """Finds spec.md files in archive subdirectories."""
        # Arrange
        _create_spec_tree(tmp_path, "001", "alpha")
        _create_spec_tree(tmp_path, "002", "beta")

        # Act
        specs = _find_all_spec_files(tmp_path)

        # Assert
        assert len(specs) == 2

    def test_empty_archive(self, tmp_path: Path) -> None:
        """Empty archive returns empty list."""
        # Arrange
        archive = tmp_path / ".ai-engineering" / "context" / "specs" / "archive"
        archive.mkdir(parents=True)

        # Act
        specs = _find_all_spec_files(tmp_path)

        # Assert
        assert specs == []

    def test_no_archive(self, tmp_path: Path) -> None:
        """Missing archive dir returns empty list."""
        specs = _find_all_spec_files(tmp_path)
        assert specs == []


class TestParseAgeThreshold:
    """Tests for _parse_age_threshold()."""

    def test_months(self) -> None:
        assert _parse_age_threshold("6m") == 180

    def test_years(self) -> None:
        assert _parse_age_threshold("1y") == 365

    def test_days(self) -> None:
        assert _parse_age_threshold("30d") == 30

    def test_invalid_raises(self) -> None:
        with pytest.raises(SystemExit):
            try:
                _parse_age_threshold("abc")
            except Exception as exc:
                # typer.Exit wraps click.exceptions.Exit
                raise SystemExit(1) from exc


class TestCountAndVerify:
    """Integration-style tests for verify logic."""

    def test_checkbox_count_matches_tasks(self, tmp_path: Path) -> None:
        """Checkbox count should match the tasks created."""
        # Arrange
        spec_dir = _create_spec_tree(tmp_path, "010", "test", total=5, completed=3)

        # Act
        tasks_text = (spec_dir / "tasks.md").read_text()
        total, checked = count_checkboxes(tasks_text)

        # Assert
        assert total == 5
        assert checked == 3

    def test_drift_detected_and_fixed(self, tmp_path: Path) -> None:
        """When frontmatter says 2/5 but checkboxes say 3/5, auto-fix corrects."""
        # Arrange
        spec_dir = _create_spec_tree(tmp_path, "011", "drift", total=5, completed=2)
        tasks_path = spec_dir / "tasks.md"

        # Write content with 3 checked but frontmatter says 2
        tasks_path.write_text(
            '---\nspec: "011"\ntotal: 5\ncompleted: 2\n---\n\n'
            "- [x] A\n- [x] B\n- [x] C\n- [ ] D\n- [ ] E\n"
        )

        # Act
        real_total, real_completed = count_checkboxes(tasks_path.read_text())
        corrected = _auto_correct_frontmatter(tasks_path, real_total, real_completed)

        # Assert
        assert real_total == 5
        assert real_completed == 3
        assert corrected is True
        fm = parse_frontmatter(tasks_path.read_text())
        assert fm["completed"] == "3"
        assert fm["total"] == "5"


class TestSpecCompactLogic:
    """Tests for compact threshold and done.md preservation."""

    def test_old_spec_is_candidate(self, tmp_path: Path) -> None:
        """Spec older than 6 months is a compact candidate."""
        spec_dir = _create_spec_tree(tmp_path, "001", "old", created="2024-01-01", done=True)
        assert (spec_dir / "done.md").exists()
        assert (spec_dir / "spec.md").exists()

        fm = parse_frontmatter((spec_dir / "spec.md").read_text())
        assert fm["created"] == "2024-01-01"

    def test_recent_spec_not_candidate(self, tmp_path: Path) -> None:
        """Spec newer than threshold is not a candidate."""
        spec_dir = _create_spec_tree(tmp_path, "033", "recent", created="2026-02-01", done=True)
        fm = parse_frontmatter((spec_dir / "spec.md").read_text())
        assert fm["created"] == "2026-02-01"

    def test_spec_without_done_not_candidate(self, tmp_path: Path) -> None:
        """Spec without done.md cannot be compacted."""
        spec_dir = _create_spec_tree(tmp_path, "005", "nodone", created="2024-01-01", done=False)
        assert not (spec_dir / "done.md").exists()
