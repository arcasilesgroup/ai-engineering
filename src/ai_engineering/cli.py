"""CLI entry point for ai-engineering.

This module creates the Typer app and serves as the console script
entry point registered in ``pyproject.toml`` as ``ai-eng``.
"""

from __future__ import annotations

from ai_engineering.cli_factory import create_app

app = create_app()

if __name__ == "__main__":
    app()
