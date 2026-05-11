"""RED-phase tests for ``skill_scripts_lib.markdown_render`` (spec-129 T-5).

Covers the public surface declared in spec-129 §14.1:

* ``render_table(headers, rows) -> str``       — GFM table renderer.
* ``render_checklist(items) -> str``           — GFM checklist renderer.
* ``parse_frontmatter(md_text) -> dict``       — YAML frontmatter parser.
* ``strip_frontmatter(md_text) -> str``        — body extractor.
* ``MarkdownRenderError``                       — raised on un-renderable input.
* ``InvalidFrontmatterError``                   — raised on malformed YAML.

The module under test does not exist yet — these tests MUST fail at
import time with ``ModuleNotFoundError`` per the TDD RED contract. The
T-6 dispatch implements the module to drive the suite GREEN; T-5 owns
the spec via tests only.
"""

from __future__ import annotations

import pytest
from skill_scripts_lib.markdown_render import (
    InvalidFrontmatterError,
    MarkdownRenderError,
    parse_frontmatter,
    render_checklist,
    render_table,
    strip_frontmatter,
)

# ---------------------------------------------------------------------------
# render_table
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_render_table_emits_three_row_gfm_structure() -> None:
    """Header, separator, and one body row — exactly three lines, N pipes each."""
    out = render_table(["spec", "task", "status"], [["129", "T-5", "RED"]])
    lines = out.splitlines()
    assert len(lines) == 3, f"expected header+sep+row=3 lines, got {len(lines)}"
    # GFM convention: a leading and trailing pipe is allowed but optional;
    # we require the pipe to appear N-1 times between cells minimum so the
    # renderer is stable regardless of leading/trailing pipe choice.
    for line in lines:
        assert line.count("|") >= 2, f"row has fewer than 2 pipes: {line!r}"
    # Separator row must contain ``---`` (GFM column-alignment marker).
    assert "---" in lines[1], f"separator row missing ---: {lines[1]!r}"


@pytest.mark.unit
def test_render_table_header_pipe_count_matches_columns() -> None:
    """N columns → N+1 pipes when the renderer wraps with leading/trailing pipes.

    The contract allows either the GFM canonical wrapped form (``| a | b |``)
    or the unwrapped form (``a | b``). Either way, the number of pipes in
    the header row must agree with the number of pipes in every body row.
    """
    headers = ["a", "b", "c"]
    rows = [["1", "2", "3"], ["4", "5", "6"]]
    out = render_table(headers, rows)
    lines = out.splitlines()
    header_pipes = lines[0].count("|")
    for body_line in lines[2:]:  # skip header + separator
        assert body_line.count("|") == header_pipes, (
            f"row pipe count {body_line.count('|')} != header {header_pipes}: {body_line!r}"
        )


@pytest.mark.unit
def test_render_table_separator_uses_dashes_per_column() -> None:
    """Separator row encodes alignment markers — one dash run per column."""
    out = render_table(["x", "y"], [["1", "2"]])
    separator = out.splitlines()[1]
    # At least 2 ``---`` dash runs (one per column). Allow longer runs.
    assert separator.count("---") >= 2, f"separator missing per-column dash runs: {separator!r}"


@pytest.mark.unit
def test_render_table_empty_headers_returns_empty_string() -> None:
    """Empty input → empty output. No partial table emitted."""
    assert render_table([], []) == ""


@pytest.mark.unit
def test_render_table_empty_rows_still_emits_header_and_separator() -> None:
    """Header-only table is valid GFM — emits header + separator, no body rows."""
    out = render_table(["col"], [])
    lines = out.splitlines()
    assert len(lines) == 2, f"header-only table should be 2 lines, got {len(lines)}"
    assert "col" in lines[0]
    assert "---" in lines[1]


@pytest.mark.unit
def test_render_table_pipe_in_cell_raises_or_escapes() -> None:
    """A literal ``|`` inside a cell breaks GFM tables — must escape or raise.

    Either contract is acceptable: (a) escape as ``\\|`` per GFM spec, or
    (b) raise ``MarkdownRenderError`` rejecting the input. We allow both
    so the implementation can choose; we just refuse silent corruption.
    """
    try:
        out = render_table(["col"], [["a|b"]])
    except MarkdownRenderError:
        return  # contract (b) — rejected, acceptable
    # contract (a) — must have escaped the pipe; the raw ``a|b`` MUST NOT
    # appear unescaped in the cell content.
    body = out.splitlines()[2]
    assert "a|b" not in body or "\\|" in body, f"unescaped pipe in body cell: {body!r}"


@pytest.mark.unit
def test_render_table_newline_in_cell_raises_or_escapes() -> None:
    """A literal newline inside a cell breaks GFM tables — must escape or raise."""
    try:
        out = render_table(["col"], [["line1\nline2"]])
    except MarkdownRenderError:
        return
    # If the renderer accepted the input, the row line count must stay at
    # 3 (header + sep + 1 body row). A naive renderer that inlined the
    # newline would emit 4+ lines and corrupt the table.
    assert len(out.splitlines()) == 3, f"newline in cell leaked into the rendered output: {out!r}"


@pytest.mark.unit
def test_render_table_row_column_mismatch_raises() -> None:
    """Row width ≠ header width → ``MarkdownRenderError`` (loud failure)."""
    with pytest.raises(MarkdownRenderError):
        render_table(["a", "b", "c"], [["1", "2"]])  # 3 headers, 2 cells


# ---------------------------------------------------------------------------
# render_checklist
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_render_checklist_renders_checked_item_as_x() -> None:
    """``(True, "text")`` → ``- [x] text`` exact format."""
    out = render_checklist([(True, "done thing")])
    assert out.strip() == "- [x] done thing"


@pytest.mark.unit
def test_render_checklist_renders_unchecked_item_as_space() -> None:
    """``(False, "text")`` → ``- [ ] text`` exact format (single space inside brackets)."""
    out = render_checklist([(False, "pending thing")])
    assert out.strip() == "- [ ] pending thing"


@pytest.mark.unit
def test_render_checklist_preserves_order() -> None:
    """List order is significant — render in the order supplied."""
    items = [(True, "first"), (False, "second"), (True, "third")]
    out = render_checklist(items)
    lines = out.splitlines()
    assert len(lines) == 3, f"expected 3 checklist items, got {len(lines)}"
    assert "first" in lines[0]
    assert "second" in lines[1]
    assert "third" in lines[2]
    # Checkmark glyphs flow with order too.
    assert "[x]" in lines[0]
    assert "[ ]" in lines[1]
    assert "[x]" in lines[2]


@pytest.mark.unit
def test_render_checklist_empty_input_returns_empty_string() -> None:
    """Empty list → empty string. No stray newline."""
    assert render_checklist([]) == ""


@pytest.mark.unit
def test_render_checklist_handles_multiline_label_safely() -> None:
    """A label containing ``\\n`` must not break the list structure."""
    try:
        out = render_checklist([(True, "line1\nline2")])
    except MarkdownRenderError:
        return  # rejection is acceptable per the same contract as tables
    # Accepted path: the resulting markdown must still be exactly one
    # list item (one leading ``- [x]`` marker). Any embedded newline must
    # have been escaped to keep GFM intact.
    leading_markers = sum(1 for ln in out.splitlines() if ln.lstrip().startswith("- ["))
    assert leading_markers == 1, f"multiline label spawned {leading_markers} list items: {out!r}"


# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_parse_frontmatter_returns_yaml_mapping_between_fences() -> None:
    """Fenced YAML at the top of a doc parses into a dict."""
    md = "---\nspec: 129\ntitle: T-5\n---\n\n# Body heading\n\nBody text.\n"
    meta = parse_frontmatter(md)
    assert isinstance(meta, dict)
    assert meta.get("spec") == 129
    assert meta.get("title") == "T-5"


@pytest.mark.unit
def test_parse_frontmatter_returns_empty_dict_when_absent() -> None:
    """No leading fence → ``{}``. Body is left for ``strip_frontmatter``."""
    md = "# Heading\n\nBody.\n"
    assert parse_frontmatter(md) == {}


@pytest.mark.unit
def test_parse_frontmatter_empty_string_returns_empty_dict() -> None:
    """Empty input → ``{}``; no crash, no exception."""
    assert parse_frontmatter("") == {}


@pytest.mark.unit
def test_parse_frontmatter_only_recognises_leading_fence() -> None:
    """A ``---`` block in the middle of a doc is NOT frontmatter."""
    md = "# Heading\n\n---\nspec: 129\n---\n\nBody.\n"
    assert parse_frontmatter(md) == {}


@pytest.mark.unit
def test_parse_frontmatter_malformed_yaml_raises() -> None:
    """Invalid YAML inside the fence raises ``InvalidFrontmatterError``."""
    # Unbalanced bracket — yaml.safe_load will reject this.
    md = "---\nspec: [129\ntitle: bad\n---\n\nBody.\n"
    with pytest.raises(InvalidFrontmatterError):
        parse_frontmatter(md)


@pytest.mark.unit
def test_parse_frontmatter_unclosed_fence_raises() -> None:
    """A leading fence with no closing fence is malformed."""
    md = "---\nspec: 129\ntitle: still going\n\nNo closing fence."
    with pytest.raises(InvalidFrontmatterError):
        parse_frontmatter(md)


@pytest.mark.unit
def test_parse_frontmatter_empty_fence_returns_empty_dict() -> None:
    """``---\\n---`` is a valid (empty) frontmatter block → ``{}``."""
    md = "---\n---\n\nBody.\n"
    assert parse_frontmatter(md) == {}


# ---------------------------------------------------------------------------
# strip_frontmatter
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_strip_frontmatter_removes_leading_fenced_block() -> None:
    """Body is everything after the closing fence (with leading blank line consumed)."""
    md = "---\nspec: 129\n---\n\n# Heading\n\nBody.\n"
    body = strip_frontmatter(md)
    assert body.lstrip().startswith("# Heading")
    assert "spec: 129" not in body


@pytest.mark.unit
def test_strip_frontmatter_passthrough_when_no_frontmatter() -> None:
    """Input without a leading fence is returned unchanged."""
    md = "# Heading\n\nBody.\n"
    assert strip_frontmatter(md) == md


@pytest.mark.unit
def test_strip_frontmatter_empty_string_returns_empty_string() -> None:
    """Edge case: empty input → empty output."""
    assert strip_frontmatter("") == ""


@pytest.mark.unit
def test_strip_frontmatter_leaves_mid_doc_fences_alone() -> None:
    """``---`` horizontal-rule markers mid-doc are body content, not frontmatter."""
    md = "# Heading\n\n---\n\nFoot section.\n"
    assert strip_frontmatter(md) == md


@pytest.mark.unit
def test_strip_frontmatter_handles_empty_frontmatter_block() -> None:
    """``---\\n---\\nBody`` strips the empty fence and returns the body."""
    md = "---\n---\n\n# Heading\n\nBody.\n"
    body = strip_frontmatter(md)
    assert body.lstrip().startswith("# Heading")
    assert "---" not in body.splitlines()[0:2]  # no residual fence at top


# ---------------------------------------------------------------------------
# Cross-cutting: error type identity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_invalid_frontmatter_error_is_distinct_from_markdown_render_error() -> None:
    """``InvalidFrontmatterError`` is its own type — callers may catch separately."""
    assert InvalidFrontmatterError is not MarkdownRenderError


@pytest.mark.unit
def test_error_types_are_exception_subclasses() -> None:
    """Both errors are catchable via ``except Exception:`` (sanity)."""
    assert issubclass(MarkdownRenderError, Exception)
    assert issubclass(InvalidFrontmatterError, Exception)
