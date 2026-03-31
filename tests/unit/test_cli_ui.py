"""Unit tests for cli_ui module."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.cli_ui import (
    BRAND_TEAL,
    THEME,
    _is_no_color,
    file_count,
    get_console,
    get_stdout_console,
    header,
    info,
    kv,
    print_stdout,
    render_update_tree,
    result_header,
    show_logo,
    status_line,
    success,
    suggest_next,
    warning,
)
from ai_engineering.updater.service import FileChange


class TestNoColorDetection:
    """Tests for NO_COLOR / TERM=dumb detection."""

    def test_no_color_env_var(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            assert _is_no_color() is True

    def test_term_dumb(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "NO_COLOR"}
        env["TERM"] = "dumb"
        with patch.dict(os.environ, env, clear=True):
            assert _is_no_color() is True

    def test_normal_env(self) -> None:
        env = {k: v for k, v in os.environ.items() if k not in ("NO_COLOR", "TERM")}
        with patch.dict(os.environ, env, clear=True):
            assert _is_no_color() is False


class TestConsoleCreation:
    """Tests for console factory functions."""

    def test_get_console_returns_console(self) -> None:
        get_console.cache_clear()
        con = get_console()
        # Console writes to stderr
        assert con.file is not None

    def test_get_stdout_console_returns_console(self) -> None:
        con = get_stdout_console()
        assert con is not None


class TestTheme:
    """Tests for the brand theme."""

    def test_brand_teal_is_hex(self) -> None:
        assert BRAND_TEAL.startswith("#")

    def test_theme_has_required_keys(self) -> None:
        required = {"brand", "success", "warning", "error", "info", "muted", "key"}
        assert required.issubset(set(THEME))


class TestLogoOutput:
    """Tests for the logo display."""

    def test_logo_noop_on_non_tty(self) -> None:
        get_console.cache_clear()
        # In test environment, console is not a TTY, so show_logo should be a no-op
        show_logo()  # Should not raise


class TestMessageHelpers:
    """Tests for success/warning/error/info helpers."""

    def test_success_writes_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()

        # Act
        success("done")
        err = capsys.readouterr().err

        # Assert
        assert "done" in err

    def test_warning_writes_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()

        # Act
        warning("caution")
        err = capsys.readouterr().err

        # Assert
        assert "caution" in err

    def test_info_writes_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()

        # Act
        info("note")
        err = capsys.readouterr().err

        # Assert
        assert "note" in err

    def test_kv_writes_pair(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()

        # Act
        kv("Name", "value")
        err = capsys.readouterr().err

        # Assert
        assert "Name" in err
        assert "value" in err

    def test_status_line_ok(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()

        # Act
        status_line("ok", "ruff", "passed")
        err = capsys.readouterr().err

        # Assert
        assert "ruff" in err
        assert "passed" in err

    def test_result_header_pass(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()

        # Act
        result_header("Doctor", "PASS", "/tmp/test")
        err = capsys.readouterr().err

        # Assert
        assert "Doctor" in err
        assert "PASS" in err

    def test_result_header_fail(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()

        # Act
        result_header("Doctor", "FAIL")
        err = capsys.readouterr().err

        # Assert
        assert "FAIL" in err

    def test_suggest_next_lists_steps(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()

        # Act
        suggest_next(
            [
                ("ai-eng doctor", "Run health diagnostics"),
                ("ai-eng setup", "Configure platforms"),
            ]
        )
        err = capsys.readouterr().err

        # Assert
        assert "ai-eng doctor" in err
        assert "Run health diagnostics" in err
        assert "ai-eng setup" in err

    def test_file_count_formats(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()

        # Act
        file_count("Governance", 42)
        err = capsys.readouterr().err

        # Assert
        assert "42 files" in err

    def test_header_prints_rule(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()

        # Act
        header("Section")
        err = capsys.readouterr().err

        # Assert
        assert "Section" in err


class TestSafePrintFallback:
    """Tests for _safe_print ImportError fallback."""

    def test_safe_print_falls_back_on_import_error(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # Arrange
        from ai_engineering.cli_ui import _safe_print

        get_console.cache_clear()

        # Act
        with patch.object(get_console(), "print", side_effect=ImportError("fake")):
            _safe_print("[bold]hello[/bold]")
        err = capsys.readouterr().err

        # Assert
        assert "hello" in err
        # Markup should be stripped
        assert "[bold]" not in err

    def test_safe_print_strips_nested_markup(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        from ai_engineering.cli_ui import _safe_print

        get_console.cache_clear()

        # Act
        with patch.object(get_console(), "print", side_effect=ModuleNotFoundError("fake")):
            _safe_print("[success]done[/success]")
        err = capsys.readouterr().err

        # Assert
        assert "done" in err
        assert "[success]" not in err


class TestShowLogoTty:
    """Tests for show_logo on TTY-like console."""

    def test_show_logo_prints_on_tty(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()
        con = get_console()

        # Act
        with patch.object(type(con), "is_terminal", new_callable=lambda: property(lambda s: True)):
            show_logo()
        err = capsys.readouterr().err

        # Assert
        assert "ai" in err or "engineering" in err


class TestUpdateTreeRendering:
    def test_render_update_tree_relative_path_unchanged_goes_to_footer(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Relative paths with skip-unchanged action appear only in the footer count."""
        # Arrange
        get_console.cache_clear()
        changes = [
            FileChange(
                path=Path("docs/README.md"),
                action="skip-unchanged",
                reason_code="already-current",
                explanation="Up to date.",
            )
        ]

        # Act
        render_update_tree(changes, root=Path("/repo"), dry_run=True)
        err = capsys.readouterr().err

        # Assert -- unchanged files go to the footer, not the tree
        assert "1 files unchanged" in err
        assert "├" not in err, "No tree structure expected for unchanged-only changes"
        assert "└" not in err, "No tree structure expected for unchanged-only changes"

    def test_show_logo_handles_import_error(self) -> None:
        get_console.cache_clear()
        con = get_console()
        with (
            patch.object(type(con), "is_terminal", new_callable=lambda: property(lambda s: True)),
            patch.object(con, "print", side_effect=ImportError("fake")),
        ):
            show_logo()  # Should not raise


class TestUnifiedTreeRenderer:
    """Tests for the unified tree renderer (single tree, per-file state labels, no detail lines)."""

    def test_unified_tree_single_tree_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Mixed outcomes produce ONE tree -- no bucket headings like 'Available (3)'."""
        # Arrange
        get_console.cache_clear()
        changes = [
            FileChange(
                path=Path("/repo/.claude/skills/ai-start/SKILL.md"),
                action="create",
                reason_code="new-file",
                explanation="New skill file.",
            ),
            FileChange(
                path=Path("/repo/.claude/skills/ai-guide/SKILL.md"),
                action="update",
                reason_code="template-drift",
                explanation="Framework update.",
            ),
            FileChange(
                path=Path("/repo/.ai-engineering/LESSONS.md"),
                action="skip-denied",
                reason_code="team-managed-update-protected",
                explanation="Protected by ownership.",
            ),
            FileChange(
                path=Path("/repo/docs/README.md"),
                action="skip-unchanged",
                reason_code="already-current",
                explanation="Up to date.",
            ),
        ]

        # Act
        render_update_tree(changes, root=Path("/repo"), dry_run=True)
        err = capsys.readouterr().err

        # Assert -- no bucket headings anywhere in the output
        assert "Available" not in err, "Should not contain bucket heading 'Available'"
        assert "Protected" not in err, "Should not contain bucket heading 'Protected'"
        assert "Unchanged" not in err, "Should not contain bucket heading 'Unchanged'"
        # Files from different buckets must still appear
        assert "SKILL.md" in err
        assert "LESSONS.md" in err

    def test_unified_tree_directory_grouping(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Files from different directories are grouped under their parent directory."""
        # Arrange
        get_console.cache_clear()
        changes = [
            FileChange(
                path=Path("/repo/.claude/skills/ai-start/SKILL.md"),
                action="create",
                reason_code="new-file",
            ),
            FileChange(
                path=Path("/repo/.claude/skills/ai-guide/SKILL.md"),
                action="update",
                reason_code="template-drift",
            ),
            FileChange(
                path=Path("/repo/.ai-engineering/contexts/stack.md"),
                action="update",
                reason_code="template-drift",
            ),
        ]

        # Act
        render_update_tree(changes, root=Path("/repo"), dry_run=True)
        err = capsys.readouterr().err

        # Assert -- both top-level directories appear as tree groups in a single tree
        assert ".claude" in err
        assert ".ai-engineering" in err
        assert "ai-start" in err
        assert "ai-guide" in err
        assert "stack.md" in err
        # Single unified tree -- no bucket headings separating the directories
        assert "Available" not in err, "Should not contain bucket heading 'Available'"
        # Both directories appear under one tree -- verify the first tree connector
        # appears before both directory names (no heading resets the tree)
        lines_with_connectors = [ln for ln in err.splitlines() if ("├" in ln or "└" in ln)]
        # A unified tree has one root-level set of connectors; the current bucket
        # renderer produces separate trees per outcome, so .claude and .ai-engineering
        # each start a new root. In a unified tree they share the same root.
        root_branches = [
            ln for ln in lines_with_connectors if ln.lstrip().startswith(("├──", "└──"))
        ]
        # Both top-level dirs must appear as root-level branches of the same tree
        root_text = " ".join(root_branches)
        assert ".claude" in root_text, ".claude should be a root branch"
        assert ".ai-engineering" in root_text, ".ai-engineering should be a root branch"

    def test_unified_tree_per_file_state_labels(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Each leaf file shows its state label inline (e.g., 'SKILL.md  new')."""
        # Arrange
        get_console.cache_clear()
        changes = [
            FileChange(
                path=Path("/repo/.claude/skills/ai-start/SKILL.md"),
                action="create",
                reason_code="new-file",
            ),
            FileChange(
                path=Path("/repo/.claude/skills/ai-guide/SKILL.md"),
                action="update",
                reason_code="template-drift",
            ),
            FileChange(
                path=Path("/repo/.ai-engineering/LESSONS.md"),
                action="skip-denied",
                reason_code="team-managed-update-protected",
            ),
        ]

        # Act
        render_update_tree(changes, root=Path("/repo"), dry_run=True)
        err = capsys.readouterr().err

        # Assert -- state labels appear inline on the same line as the filename
        lines = err.splitlines()
        skill_start_lines = [ln for ln in lines if "ai-start" in ln and "SKILL.md" in ln]
        assert skill_start_lines, "Should find a line with ai-start/SKILL.md"
        assert any("new" in ln for ln in skill_start_lines), (
            "State label 'new' should appear on the same line as the file"
        )

        skill_guide_lines = [ln for ln in lines if "ai-guide" in ln and "SKILL.md" in ln]
        assert skill_guide_lines, "Should find a line with ai-guide/SKILL.md"
        assert any("updated" in ln for ln in skill_guide_lines), (
            "State label 'updated' should appear on the same line as the file"
        )

        lessons_lines = [ln for ln in lines if "LESSONS.md" in ln]
        assert lessons_lines, "Should find a line with LESSONS.md"
        assert any("removed" in ln or "protected" in ln for ln in lessons_lines), (
            "State label should appear on the same line as the file"
        )

    def test_unified_tree_no_detail_lines(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Tree does NOT produce 'Reason:', 'Next:', or 'Why:' detail lines."""
        # Arrange
        get_console.cache_clear()
        changes = [
            FileChange(
                path=Path("/repo/.claude/skills/ai-start/SKILL.md"),
                action="create",
                reason_code="new-file",
                explanation="New skill file.",
                recommended_action="Review the file.",
            ),
            FileChange(
                path=Path("/repo/.ai-engineering/LESSONS.md"),
                action="skip-denied",
                reason_code="team-managed-update-protected",
                explanation="Protected by ownership.",
                recommended_action="No action required.",
            ),
        ]

        # Act
        render_update_tree(changes, root=Path("/repo"), dry_run=True)
        err = capsys.readouterr().err

        # Assert -- none of the detail prefixes should appear
        assert "Reason:" not in err, "Should not contain 'Reason:' detail lines"
        assert "Next:" not in err, "Should not contain 'Next:' detail lines"
        assert "Why:" not in err, "Should not contain 'Why:' detail lines"

    def test_unified_tree_unchanged_footer(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Unchanged files appear as a footer count, not individually in the tree."""
        # Arrange
        get_console.cache_clear()
        changes = [
            FileChange(
                path=Path("/repo/.claude/skills/ai-start/SKILL.md"),
                action="create",
                reason_code="new-file",
            ),
            FileChange(
                path=Path("/repo/docs/README.md"),
                action="skip-unchanged",
                reason_code="already-current",
            ),
            FileChange(
                path=Path("/repo/docs/GUIDE.md"),
                action="skip-unchanged",
                reason_code="already-current",
            ),
        ]

        # Act
        render_update_tree(changes, root=Path("/repo"), dry_run=True)
        err = capsys.readouterr().err

        # Assert -- unchanged files should NOT be in the tree
        assert "README.md" not in err, "Unchanged file should not appear individually"
        assert "GUIDE.md" not in err, "Unchanged file should not appear individually"
        # Footer must summarise the count
        assert "2 files unchanged" in err, "Footer should say '2 files unchanged'"

    def test_unified_tree_empty_changes(self, capsys: pytest.CaptureFixture[str]) -> None:
        """When all changes are unchanged, only the footer counter is shown."""
        # Arrange
        get_console.cache_clear()
        changes = [
            FileChange(
                path=Path("/repo/docs/README.md"),
                action="skip-unchanged",
                reason_code="already-current",
            ),
            FileChange(
                path=Path("/repo/docs/GUIDE.md"),
                action="skip-unchanged",
                reason_code="already-current",
            ),
            FileChange(
                path=Path("/repo/docs/SETUP.md"),
                action="skip-unchanged",
                reason_code="already-current",
            ),
        ]

        # Act
        render_update_tree(changes, root=Path("/repo"), dry_run=True)
        err = capsys.readouterr().err

        # Assert -- no tree connectors should appear
        assert "├" not in err, "No tree structure expected when all files are unchanged"
        assert "└" not in err, "No tree structure expected when all files are unchanged"
        # Only the footer
        assert "3 files unchanged" in err, "Footer should say '3 files unchanged'"


class TestHeaderFallback:
    """Tests for header() ImportError fallback."""

    def test_header_fallback_on_import_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()

        # Act
        with patch.object(get_console(), "print", side_effect=ImportError("fake")):
            header("MySection")
        err = capsys.readouterr().err

        # Assert
        assert "MySection" in err


class TestErrorHelper:
    """Tests for the error() helper."""

    def test_error_writes_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        from ai_engineering.cli_ui import error

        get_console.cache_clear()

        # Act
        error("something broke")
        err = capsys.readouterr().err

        # Assert
        assert "something broke" in err


class TestPrintStdout:
    """Tests for stdout data output."""

    def test_print_stdout_goes_to_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_stdout("data line")
        out = capsys.readouterr().out
        assert "data line" in out
