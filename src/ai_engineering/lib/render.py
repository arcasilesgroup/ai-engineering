"""Rendering helpers for CLI markdown output.

Provides a small abstraction that renders markdown through ``rich`` when
available and falls back to plain stdout output when it is not.
"""

from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown


def render_markdown(content: str) -> None:
    """Render markdown content to stdout using rich formatting."""
    Console().print(Markdown(content))
