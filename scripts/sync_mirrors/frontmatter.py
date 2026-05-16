"""YAML frontmatter parsing helpers.

Thin facade over `core` -- centralizes the symbols downstream readers
expect to find in a `frontmatter` module without duplicating logic.
"""

from __future__ import annotations

from scripts.sync_mirrors.core import (
    _format_yaml_field,
    _serialize_frontmatter,
    parse_frontmatter_simple,
    read_body,
    read_frontmatter,
)

__all__ = [
    "_format_yaml_field",
    "_serialize_frontmatter",
    "parse_frontmatter_simple",
    "read_body",
    "read_frontmatter",
]
