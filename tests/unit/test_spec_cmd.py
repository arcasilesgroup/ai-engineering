"""Unit tests for ai_engineering.cli_commands.spec_cmd (Working Buffer model).

Covers:
- spec_verify: drift detection, auto-fix, signal emission, placeholder handling.
- spec_list: title extraction, progress display, placeholder handling.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.cli_commands.spec_cmd import _auto_correct_frontmatter
from ai_engineering.lib.parsing import count_checkboxes, parse_frontmatter

pytestmark = pytest.mark.unit


def _create_plan_md(
    root: Path,
    *,
    total: int = 5,
    completed: int = 2,
    tasks_checkboxes: str | None = None,
    placeholder: bool = False,
) -> Path:
    """Create a plan.md in the Working Buffer model."""
    specs_dir = root / ".ai-engineering" / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    if placeholder:
        content = "# No active plan\n\nRun /ai-plan after brainstorm approval.\n"
    else:
        if tasks_checkboxes is None:
            checked_lines = "\n".join(f"- [x] {i}.1 Done" for i in range(completed))
            unchecked_lines = "\n".join(f"- [ ] {i}.1 Todo" for i in range(completed, total))
            tasks_checkboxes = f"{checked_lines}\n{unchecked_lines}"

        content = (
            f"---\ntotal: {total}\ncompleted: {completed}\n---\n\n# Plan\n\n{tasks_checkboxes}\n"
        )

    plan_path = specs_dir / "plan.md"
    plan_path.write_text(content)
    return plan_path


def _create_spec_md(
    root: Path,
    *,
    title: str = "Test Feature",
    placeholder: bool = False,
) -> Path:
    """Create a spec.md in the Working Buffer model."""
    specs_dir = root / ".ai-engineering" / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    if placeholder:
        content = "# No active spec\n\nRun /ai-brainstorm to start a new spec.\n"
    else:
        content = f'---\nid: "055"\n---\n\n# {title}\n\nSpec content here.\n'

    spec_path = specs_dir / "spec.md"
    spec_path.write_text(content)
    return spec_path


class TestAutoCorrectFrontmatter:
    """Tests for _auto_correct_frontmatter()."""

    def _write_plan(self, root: Path, content: str) -> Path:
        specs_dir = root / ".ai-engineering" / "specs"
        specs_dir.mkdir(parents=True, exist_ok=True)
        plan = specs_dir / "plan.md"
        plan.write_text(content)
        return plan

    def test_corrects_drifted_total(self, tmp_path: Path) -> None:
        """Drifted total is corrected."""
        plan = self._write_plan(
            tmp_path,
            "---\ntotal: 3\ncompleted: 1\n---\n\n"
            "- [x] Done\n- [ ] Todo\n- [ ] Todo\n- [ ] Todo\n- [ ] Todo\n",
        )

        result = _auto_correct_frontmatter(tmp_path, 5, 1)

        assert result is True
        fm = parse_frontmatter(plan.read_text())
        assert fm["total"] == "5"

    def test_corrects_drifted_completed(self, tmp_path: Path) -> None:
        """Drifted completed is corrected."""
        plan = self._write_plan(
            tmp_path,
            "---\ntotal: 3\ncompleted: 0\n---\n\n- [x] Done\n- [x] Done\n- [ ] Todo\n",
        )

        result = _auto_correct_frontmatter(tmp_path, 3, 2)

        assert result is True
        fm = parse_frontmatter(plan.read_text())
        assert fm["completed"] == "2"

    def test_no_correction_when_accurate(self, tmp_path: Path) -> None:
        """No changes when frontmatter matches reality."""
        self._write_plan(
            tmp_path,
            "---\ntotal: 3\ncompleted: 1\n---\n\n- [x] Done\n- [ ] Todo\n- [ ] Todo\n",
        )

        result = _auto_correct_frontmatter(tmp_path, 3, 1)

        assert result is False


class TestCountAndVerify:
    """Integration-style tests for verify logic."""

    def test_checkbox_count_matches_plan(self, tmp_path: Path) -> None:
        """Checkbox count should match the tasks in plan.md."""
        plan_path = _create_plan_md(tmp_path, total=5, completed=3)

        plan_text = plan_path.read_text()
        total, checked = count_checkboxes(plan_text)

        assert total == 5
        assert checked == 3

    def test_drift_detected_and_fixed(self, tmp_path: Path) -> None:
        """When frontmatter says 2/5 but checkboxes say 3/5, auto-fix corrects."""
        plan_path = _create_plan_md(tmp_path, total=5, completed=2)

        # Write content with 3 checked but frontmatter says 2
        plan_path.write_text(
            "---\ntotal: 5\ncompleted: 2\n---\n\n- [x] A\n- [x] B\n- [x] C\n- [ ] D\n- [ ] E\n"
        )

        real_total, real_completed = count_checkboxes(plan_path.read_text())
        corrected = _auto_correct_frontmatter(tmp_path, real_total, real_completed)

        assert real_total == 5
        assert real_completed == 3
        assert corrected is True
        fm = parse_frontmatter(plan_path.read_text())
        assert fm["completed"] == "3"
        assert fm["total"] == "5"


class TestSpecMdWorkingBuffer:
    """Tests for the Working Buffer spec.md model."""

    def test_placeholder_spec_detected(self, tmp_path: Path) -> None:
        """Placeholder content is recognized as no active spec."""
        spec_path = _create_spec_md(tmp_path, placeholder=True)
        content = spec_path.read_text()
        assert content.strip().startswith("# No active spec")

    def test_active_spec_title_extracted(self, tmp_path: Path) -> None:
        """Title is extracted from first H1 heading."""
        spec_path = _create_spec_md(tmp_path, title="Radical Simplification")
        content = spec_path.read_text()
        for line in content.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
        assert title == "Radical Simplification"

    def test_placeholder_plan_detected(self, tmp_path: Path) -> None:
        """Placeholder plan is recognized."""
        plan_path = _create_plan_md(tmp_path, placeholder=True)
        content = plan_path.read_text()
        assert content.strip().startswith("# No active plan")


class TestSpecVerifyCli:
    """Tests for spec_verify CLI function."""

    def test_verify_no_plan_exits(self, tmp_path: Path) -> None:
        from unittest.mock import patch

        import click

        from ai_engineering.cli_commands.spec_cmd import spec_verify

        with (
            patch("ai_engineering.cli_commands.spec_cmd.find_project_root", return_value=tmp_path),
            pytest.raises(click.exceptions.Exit),
        ):
            spec_verify()

    def test_verify_placeholder_plan(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        from unittest.mock import patch

        from ai_engineering.cli_commands.spec_cmd import spec_verify

        _create_plan_md(tmp_path, placeholder=True)
        with patch("ai_engineering.cli_commands.spec_cmd.find_project_root", return_value=tmp_path):
            spec_verify()
        assert "No active plan" in capsys.readouterr().out

    def test_verify_counters_match(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        from unittest.mock import patch

        from ai_engineering.cli_commands.spec_cmd import spec_verify

        _create_plan_md(tmp_path, total=3, completed=1)
        with patch("ai_engineering.cli_commands.spec_cmd.find_project_root", return_value=tmp_path):
            spec_verify()
        out = capsys.readouterr().out
        assert "Checkboxes: 1/3" in out
        assert "OK" in out

    def test_verify_drift_auto_fixed(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        from unittest.mock import patch

        from ai_engineering.cli_commands.spec_cmd import spec_verify

        plan_path = _create_plan_md(tmp_path, total=5, completed=2)
        plan_path.write_text(
            "---\ntotal: 5\ncompleted: 2\n---\n\n- [x] A\n- [x] B\n- [x] C\n- [ ] D\n- [ ] E\n"
        )
        with patch("ai_engineering.cli_commands.spec_cmd.find_project_root", return_value=tmp_path):
            spec_verify(fix=True)
        out = capsys.readouterr().out
        assert "DRIFT DETECTED" in out
        assert "AUTO-FIXED" in out


class TestSpecListCli:
    """Tests for spec_list CLI function."""

    def test_list_no_spec(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        from unittest.mock import patch

        from ai_engineering.cli_commands.spec_cmd import spec_list

        with patch("ai_engineering.cli_commands.spec_cmd.find_project_root", return_value=tmp_path):
            spec_list()
        assert "No specs/spec.md found" in capsys.readouterr().out

    def test_list_placeholder_spec(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        from unittest.mock import patch

        from ai_engineering.cli_commands.spec_cmd import spec_list

        _create_spec_md(tmp_path, placeholder=True)
        with patch("ai_engineering.cli_commands.spec_cmd.find_project_root", return_value=tmp_path):
            spec_list()
        assert "No active spec" in capsys.readouterr().out

    def test_list_active_spec_with_plan(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        from unittest.mock import patch

        from ai_engineering.cli_commands.spec_cmd import spec_list

        _create_spec_md(tmp_path, title="Radical Simplification")
        _create_plan_md(tmp_path, total=10, completed=7)
        with patch("ai_engineering.cli_commands.spec_cmd.find_project_root", return_value=tmp_path):
            spec_list()
        out = capsys.readouterr().out
        assert "Radical Simplification" in out
        assert "7/10" in out
