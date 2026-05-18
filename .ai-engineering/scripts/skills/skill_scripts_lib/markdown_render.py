"""GFM rendering and YAML frontmatter helpers (spec-129 T-6).

GREEN-phase implementation of the contract pinned in
``tests/unit/scripts/_lib/test_markdown_render.py`` (T-5). This module
backs the cleanup, standup, and resolve-classify scripts that emit
GitHub-Flavoured-Markdown to stdout and to PR bodies. The contract is
narrow and the implementation is intentionally allocation-cheap: no
state, no caching, no I/O. Stdlib plus ``yaml`` only.

Contract choices (documented here so callers can reason about edge
cases without re-reading the tests):

* **Pipe escape vs newline raise.** GFM tables encode column boundaries
  with ``|``, so a literal pipe inside a cell must be escaped as
  ``\\|``. We honour that escape rule — cells with embedded pipes are
  rendered safely. GFM has *no* spec-defined escape for a literal
  newline inside a table cell (line breaks must use ``<br>``), so a
  raw ``\\n`` inside a cell would corrupt the row count if inlined.
  We refuse silently-corrupting input by raising
  ``MarkdownRenderError`` — the caller must rewrite the value (e.g.
  pre-collapse whitespace) before re-attempting. The same rule
  applies to ``render_checklist`` items.

* **Leading-only fence recognition.** YAML frontmatter is recognised
  *only* when the document opens with ``---`` on line 1. A ``---``
  marker mid-document is treated as body content (it is a valid GFM
  horizontal rule), so ``strip_frontmatter`` leaves it alone and
  ``parse_frontmatter`` returns ``{}``. This matches Jekyll / Hugo /
  Astro conventions and keeps the parser O(n) — we never have to scan
  the whole document to disambiguate.

* **Empty frontmatter is a valid empty mapping.** ``---\\n---`` parses
  to ``{}`` rather than raising; the caller learns "frontmatter
  present but empty" by reading the body via ``strip_frontmatter``,
  which still drops the empty fence block.

* **Closing fence is mandatory.** A leading ``---`` with no closing
  fence raises ``InvalidFrontmatterError`` because the document
  structure is ambiguous — the parser cannot tell where the metadata
  ends and the body begins. We surface this loudly rather than
  guessing.
"""

from __future__ import annotations

import importlib.util
from typing import Any

_HAS_YAML = importlib.util.find_spec("yaml") is not None
if _HAS_YAML:
    import yaml

__all__ = [
    "InvalidFrontmatterError",
    "MarkdownRenderError",
    "parse_frontmatter",
    "render_checklist",
    "render_table",
    "strip_frontmatter",
]


class MarkdownRenderError(ValueError):
    """Raised when input cannot be rendered as valid GFM without corruption.

    Subclasses ``ValueError`` because the offending object is the
    input being validated (e.g. a row with a newline in a cell, or a
    row whose width does not match the header). Callers may catch
    this independently of ``InvalidFrontmatterError`` to surface
    table-specific or list-specific errors differently from parser
    errors.
    """


class InvalidFrontmatterError(ValueError):
    """Raised when leading ``---`` frontmatter cannot be parsed.

    Covers both malformed YAML inside the fence and an unclosed
    leading fence. Subclasses ``ValueError`` for the same reason as
    ``MarkdownRenderError`` and is intentionally distinct from it so
    callers can choose to handle frontmatter failures differently
    from rendering failures.
    """


def _escape_cell(value: str) -> str:
    """Return ``value`` with GFM table-cell escapes applied.

    GFM defines a single in-cell escape: ``\\|`` for a literal pipe.
    No spec-defined escape exists for a literal newline, so we raise
    ``MarkdownRenderError`` rather than silently corrupt the row.

    Args:
        value: Raw cell content from the caller.

    Returns:
        ``value`` with every ``|`` replaced by ``\\|``.

    Raises:
        MarkdownRenderError: ``value`` contains a literal ``\\n``.
    """
    if "\n" in value:
        raise MarkdownRenderError(
            "cell contains a literal newline — GFM has no in-cell escape; "
            "collapse whitespace before rendering"
        )
    return value.replace("|", "\\|")


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a GFM table from ``headers`` and ``rows``.

    The renderer emits the canonical wrapped form
    (``| a | b |\\n| --- | --- |\\n| 1 | 2 |``) so the pipe count is
    constant across rows and downstream linters that expect the
    wrapped form do not complain.

    Args:
        headers: Column headers, one string per column. Empty list
            means "no table" — the function returns ``""``.
        rows: Body rows. Each row must contain exactly
            ``len(headers)`` cells. Empty list means
            "header-only table" — the function emits header +
            separator and no body rows.

    Returns:
        The rendered table. Empty string when ``headers`` is empty.
        Lines are joined with ``\\n`` and the result has no trailing
        newline so the caller controls block separation.

    Raises:
        MarkdownRenderError: A row's width does not match the header
            width, or any cell contains a literal newline.
    """
    if not headers:
        return ""

    column_count = len(headers)
    escaped_headers = [_escape_cell(h) for h in headers]
    header_line = "| " + " | ".join(escaped_headers) + " |"
    separator_line = "| " + " | ".join(["---"] * column_count) + " |"

    body_lines: list[str] = []
    for index, row in enumerate(rows):
        if len(row) != column_count:
            raise MarkdownRenderError(
                f"row {index} has {len(row)} cells but header declares {column_count} columns"
            )
        escaped = [_escape_cell(cell) for cell in row]
        body_lines.append("| " + " | ".join(escaped) + " |")

    return "\n".join([header_line, separator_line, *body_lines])


def render_checklist(items: list[tuple[bool, str]]) -> str:
    """Render a GFM task list from ``items``.

    Each tuple ``(checked, text)`` maps to ``- [x] text`` when
    ``checked`` is true and ``- [ ] text`` (one space inside the
    brackets) when false. Order is preserved.

    Args:
        items: Sequence of ``(checked, label)`` tuples.

    Returns:
        The rendered list, lines joined with ``\\n``. Empty input
        returns ``""`` (no stray newline).

    Raises:
        MarkdownRenderError: A label contains a literal newline —
            GFM list items break on bare newlines and we refuse to
            silently spawn multiple list entries from one tuple.
    """
    if not items:
        return ""

    lines: list[str] = []
    for index, (checked, label) in enumerate(items):
        if "\n" in label:
            raise MarkdownRenderError(
                f"checklist item {index} label contains a literal newline; "
                "collapse whitespace before rendering"
            )
        marker = "[x]" if checked else "[ ]"
        lines.append(f"- {marker} {label}")

    return "\n".join(lines)


def _split_leading_frontmatter(md_text: str) -> tuple[str | None, str]:
    """Split ``md_text`` into ``(yaml_block, body)``.

    Returns ``(None, md_text)`` when there is no leading fence so the
    caller can short-circuit. Returns ``(yaml_block, body)`` when a
    leading ``---`` fence is closed by a matching ``---`` line. The
    ``yaml_block`` excludes both fence lines.

    Args:
        md_text: The full markdown document.

    Returns:
        Tuple of ``(yaml_block, body)`` — see above.

    Raises:
        InvalidFrontmatterError: A leading fence exists but no
            closing fence was found before EOF.
    """
    if not md_text.startswith("---"):
        return None, md_text

    lines = md_text.splitlines(keepends=True)
    # First line must be exactly "---" (allowing trailing newline) — a
    # line like "---x" is not a fence opener.
    first = lines[0].rstrip("\n").rstrip("\r")
    if first != "---":
        return None, md_text

    # Walk forward looking for the closing "---" fence.
    for closing_index in range(1, len(lines)):
        candidate = lines[closing_index].rstrip("\n").rstrip("\r")
        if candidate == "---":
            yaml_block = "".join(lines[1:closing_index])
            body = "".join(lines[closing_index + 1 :])
            return yaml_block, body

    raise InvalidFrontmatterError("leading '---' frontmatter fence has no closing '---' line")


def parse_frontmatter(md_text: str) -> dict[str, Any]:
    """Parse YAML frontmatter from the start of ``md_text``.

    Recognises only a leading ``---`` fence on line 1. Mid-document
    ``---`` markers are treated as body content.

    Args:
        md_text: The full markdown document. May be empty.

    Returns:
        The parsed YAML mapping. ``{}`` when ``md_text`` is empty,
        when there is no leading fence, or when the fence wraps no
        content (``---\\n---``).

    Raises:
        InvalidFrontmatterError: YAML inside the fence is malformed,
            the YAML payload is not a mapping, or the leading fence
            is not closed.
    """
    if not md_text:
        return {}

    yaml_block, _body = _split_leading_frontmatter(md_text)
    if yaml_block is None:
        return {}

    stripped = yaml_block.strip()
    if not stripped:
        return {}

    if not _HAS_YAML:
        raise InvalidFrontmatterError(
            "pyyaml is not installed — frontmatter cannot be parsed; "
            "run `uv pip install pyyaml` or add it to the project venv"
        )

    try:
        loaded = yaml.safe_load(yaml_block)
    except yaml.YAMLError as err:
        raise InvalidFrontmatterError(f"frontmatter YAML is malformed: {err}") from err

    if loaded is None:
        return {}

    if not isinstance(loaded, dict):
        raise InvalidFrontmatterError(
            f"frontmatter must be a YAML mapping, got {type(loaded).__name__}"
        )

    return loaded


def strip_frontmatter(md_text: str) -> str:
    """Return ``md_text`` with leading YAML frontmatter removed.

    A document that does not open with ``---`` is returned unchanged.
    A document whose closing fence is followed by a blank line keeps
    the blank line in the body (callers can ``lstrip`` if desired);
    we do not aggressively trim because the frontmatter contract is
    "remove the fence block", not "remove leading whitespace".

    Args:
        md_text: The full markdown document. May be empty.

    Returns:
        The body, with the leading ``---`` ... ``---`` block dropped
        when present. Empty input returns ``""``.

    Raises:
        InvalidFrontmatterError: A leading fence exists but no
            closing fence was found before EOF. We surface this
            failure rather than silently returning the full document
            because the caller has explicitly asked us to remove
            metadata that we cannot identify.
    """
    if not md_text:
        return ""

    _yaml_block, body = _split_leading_frontmatter(md_text)
    return body
