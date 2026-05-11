"""Regression guard for the canonical Engram MCP tool prefix.

spec-131 sub-004 T-4.H: the canonical prefix is ``mcp__plugin_engram_engram__*``.
Earlier docs that used ``mcp__engram__*`` are historical. This test scans
the load-bearing surface (markdown / Python / JSON under the framework
root) and fails on any non-canonical occurrence.

Exclusions:
- ``.ai-engineering/runtime/`` — transient tool outputs (gitignored anyway).
- ``.ai-engineering/state/observation-events.ndjson`` — write-once audit.
- ``.ai-engineering/state/framework-events.ndjson`` — write-once audit.
- ``.ai-engineering/specs/drafts/dx-excellence-refactor-brief.md`` — historical.
- ``.git/`` — git internals (in case packed refs reference old text).
- ``node_modules/`` / ``.venv/`` — third-party.
- ``.ai-engineering/runtime/autopilot/`` — wave plans / specs (transient).
- the test file itself (must mention the non-canonical form to assert it).

The intent is *defensive*: at HEAD live drift is zero. The lint exists to
prevent regression.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
NON_CANONICAL = "mcp__engram__"
CANONICAL = "mcp__plugin_engram_engram__"

# Surface scanned by the regression guard. Limited to the live surface
# so the test runs fast (≤200 ms target per pre-commit budget) — the
# audit doesn't need to walk node_modules.
SCAN_ROOTS = (
    Path("CLAUDE.md"),
    Path("AGENTS.md"),
    Path("GEMINI.md"),
    Path(".github/copilot-instructions.md"),
    Path(".ai-engineering/scripts"),
    Path(".ai-engineering/contexts"),
    Path("tools"),
    Path(".claude/skills"),
    Path(".claude/agents"),
)

EXTENSIONS = {".md", ".py", ".json"}

EXCLUDE_DIRS = {
    ".ai-engineering/runtime",
    ".git",
    "node_modules",
    ".venv",
    ".pytest_cache",
    "__pycache__",
}

EXCLUDE_FILES = {
    ".ai-engineering/state/observation-events.ndjson",
    ".ai-engineering/state/framework-events.ndjson",
    ".ai-engineering/specs/drafts/dx-excellence-refactor-brief.md",
    # The test file itself names the non-canonical form to assert it.
    "tests/unit/hooks/test_engram_prefix_canonical.py",
}


def _iter_candidate_files() -> list[Path]:
    candidates: list[Path] = []
    for root_rel in SCAN_ROOTS:
        root = REPO / root_rel
        if root.is_file():
            candidates.append(root)
            continue
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in EXTENSIONS:
                continue
            rel = str(path.relative_to(REPO))
            if any(ex in rel for ex in EXCLUDE_DIRS):
                continue
            if rel in EXCLUDE_FILES:
                continue
            candidates.append(path)
    return candidates


def _is_non_canonical(line: str) -> bool:
    """``mcp__engram__`` is non-canonical only when NOT preceded by ``plugin_``.

    ``mcp__plugin_engram_engram__`` is the canonical form. Naive substring
    match for ``mcp__engram__`` flags both forms, so the helper enforces
    the negative lookahead-equivalent constraint.
    """
    return NON_CANONICAL in line and CANONICAL not in line


def test_synthetic_non_canonical_line_is_flagged() -> None:
    """Smoke test: the helper flags a hand-rolled non-canonical line."""
    assert _is_non_canonical("call mcp__engram__mem_save here")


def test_synthetic_canonical_line_is_not_flagged() -> None:
    """Canonical form must not register as a violation."""
    assert not _is_non_canonical("call mcp__plugin_engram_engram__mem_save here")


def test_canonical_substring_in_longer_line_is_not_flagged() -> None:
    """A line that names BOTH forms must not flag (e.g. doc explaining the change)."""
    assert not _is_non_canonical(
        "the canonical form is mcp__plugin_engram_engram__mem_save (was mcp__engram__mem_save)"
    )


def test_no_non_canonical_engram_prefix_on_live_surface() -> None:
    """Defensive lint: zero non-canonical occurrences in the scanned surface.

    Any single non-canonical occurrence on the live surface MUST be
    rewritten to ``mcp__plugin_engram_engram__*`` or moved under one of
    the documented exclusions.
    """
    offenders: list[str] = []
    for path in _iter_candidate_files():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _is_non_canonical(line):
                rel = str(path.relative_to(REPO))
                offenders.append(f"{rel}:{lineno}: {line.strip()[:120]}")
    assert not offenders, (
        "non-canonical engram prefix found on live surface; rewrite to "
        f"{CANONICAL}*: {offenders[:10]}"
    )
