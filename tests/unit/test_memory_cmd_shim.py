"""Smoke tests for the `cli_commands/memory_cmd.py` shim.

The shim adds `.ai-engineering/scripts/` to sys.path and re-exports the
canonical Typer app. Earlier versions had no test coverage; a typo in the
sub-app wiring would ship undetected.
"""

from __future__ import annotations


def test_memory_app_resolves_to_typer_app() -> None:
    from ai_engineering.cli_commands import memory_cmd

    app = memory_cmd.memory_app
    # Typer instance, not the unavailable-fallback stub.
    assert app is not None
    assert app.info.name == "memory"


def test_memory_app_registers_expected_subcommands() -> None:
    from ai_engineering.cli_commands import memory_cmd

    app = memory_cmd.memory_app
    # Inspect Typer registered_commands. Names depend on the canonical app;
    # we only check that the surface is non-empty and contains the smoke set.
    names = {cmd.name or cmd.callback.__name__ for cmd in app.registered_commands}
    expected_subset = {"status", "stop"}
    assert expected_subset.issubset(names), f"missing expected commands: {expected_subset - names}"
