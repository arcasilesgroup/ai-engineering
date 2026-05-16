"""Test guard for D-133-02: `ai-eng guide` CLI command was DELETED.

Spec-133 D-133-02 hard-deleted the `ai-eng guide` Typer command. This
test enforces the deletion at the CLI-registry level so any accidental
reintroduction (via a revert, a bad merge, or a manual command
registration) is caught before merge.

Scope: this checks the CLI registry only. A separate guard
(`tests/unit/cli/test_no_guide_references.py`, spawned task) covers
user-facing messages that may still recommend the removed command.
"""

from __future__ import annotations

from ai_engineering.cli_factory import create_app


def _walk_command_names(app: object, prefix: str = "") -> list[str]:
    """Walk a Typer app tree and return every fully-qualified command name."""
    names: list[str] = []
    registered_commands = getattr(app, "registered_commands", []) or []
    for cmd in registered_commands:
        cmd_name = getattr(cmd, "name", None) or getattr(cmd.callback, "__name__", "")
        if cmd_name:
            full = f"{prefix} {cmd_name}".strip()
            names.append(full)
    registered_groups = getattr(app, "registered_groups", []) or []
    for grp in registered_groups:
        grp_name = getattr(grp, "name", None) or ""
        nested_prefix = f"{prefix} {grp_name}".strip() if grp_name else prefix
        names.extend(_walk_command_names(grp.typer_instance, nested_prefix))
    return names


def test_guide_command_absent_from_cli_registry() -> None:
    """`ai-eng guide` MUST NOT be registered (D-133-02)."""
    app = create_app()
    commands = _walk_command_names(app)
    assert "guide" not in commands, (
        f"D-133-02 violated — `ai-eng guide` was reintroduced. Found in command tree: {commands}"
    )


def test_no_guide_subcommand_anywhere() -> None:
    """No nested subcommand should end in `guide` either (e.g., `audit guide`)."""
    app = create_app()
    commands = _walk_command_names(app)
    matches = [c for c in commands if c.endswith(" guide") or c == "guide"]
    assert not matches, (
        f"D-133-02 violated — found {len(matches)} command(s) named 'guide': {matches}"
    )
