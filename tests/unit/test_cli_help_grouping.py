"""spec-183 Phase 2: functional colour-grouped root --help.

Guards the taxonomy completeness (R-183-03) and the render contract: 4 panels
on bare + --help, and NO_COLOR / TERM=dumb / non-TTY / --json all unaffected.
"""

from __future__ import annotations

import click
import typer
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app
from ai_engineering.cli_help_render import CATEGORY_ORDER, COMMAND_CATEGORY, categorize
from ai_engineering.cli_ui import THEME

runner = CliRunner()
_PANELS = ("Lifecycle", "Governance", "Inspection", "Maintenance")


def _visible_top_level() -> list[str]:
    cmd = typer.main.get_command(create_app())
    ctx = click.Context(cmd, info_name="ai-eng")
    return [
        name
        for name in cmd.list_commands(ctx)
        if not getattr(cmd.get_command(ctx, name), "hidden", False)
    ]


# --- T-E1: palette ---------------------------------------------------------


def test_governance_token_added() -> None:
    assert "governance" in THEME
    assert THEME["governance"] == "#A78BFA"


# --- T-E2: taxonomy completeness (R-183-03) --------------------------------


def test_every_visible_command_is_categorized() -> None:
    """No visible top-level command falls into the 'Other' catch-all."""
    missing = [n for n in _visible_top_level() if n not in COMMAND_CATEGORY]
    assert missing == [], f"uncategorized visible commands (would render 'Other'): {missing}"


def test_no_phantom_map_entries() -> None:
    """Every mapped name is a real, currently-visible command."""
    visible = set(_visible_top_level())
    phantom = [n for n in COMMAND_CATEGORY if n not in visible]
    assert phantom == [], f"map names that are not visible commands: {phantom}"


def test_categories_are_within_taxonomy() -> None:
    for category in COMMAND_CATEGORY.values():
        assert category in CATEGORY_ORDER
    # 'release' is hidden -> must not be categorized as a visible command.
    assert "release" not in COMMAND_CATEGORY


def test_categorize_unmapped_is_other() -> None:
    assert categorize("definitely-not-a-command") == "Other"


# --- T-E4: render contract -------------------------------------------------


def test_help_renders_four_panels() -> None:
    result = runner.invoke(create_app(), ["--help"])
    assert result.exit_code == 0
    for panel in _PANELS:
        assert panel in result.output


def test_bare_invocation_renders_four_panels() -> None:
    result = runner.invoke(create_app(), [])
    for panel in _PANELS:
        assert panel in result.output


def test_release_absent_from_grouped_help() -> None:
    result = runner.invoke(create_app(), ["--help"])
    # hidden command must not surface in any panel.
    assert "release" not in result.output


def test_no_color_output_has_no_ansi(monkeypatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    result = runner.invoke(create_app(), ["--help"])
    assert "\x1b[" not in result.output
    for panel in _PANELS:
        assert panel in result.output


def test_dumb_terminal_has_no_ansi(monkeypatch) -> None:
    monkeypatch.setenv("TERM", "dumb")
    result = runner.invoke(create_app(), ["--help"])
    assert "\x1b[" not in result.output


def test_json_mode_returns_envelope_not_help() -> None:
    result = runner.invoke(create_app(), ["--json"])
    assert result.exit_code == 0
    # bare --json short-circuits to the JSON command list; no grouped help.
    for panel in _PANELS:
        assert panel not in result.stdout
    assert '"commands"' in result.stdout


def test_subcommand_help_is_not_grouped() -> None:
    """Non-Goal 1: subcommand --help keeps Typer's native rendering."""
    result = runner.invoke(create_app(), ["gate", "--help"])
    assert result.exit_code == 0
    for panel in _PANELS:
        assert panel not in result.output
