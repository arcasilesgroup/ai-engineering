"""CLI entrypoint for ai-engineering."""

from __future__ import annotations

from ai_engineering.cli_factory import create_app


app = create_app()


if __name__ == "__main__":
    app()
