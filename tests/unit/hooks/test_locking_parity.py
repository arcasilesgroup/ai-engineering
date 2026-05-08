"""Byte-level parity test between hook-side and pkg-side locking primitives.

spec-126 D-126-01 mitigates silent drift on the duplicated lock primitive by
asserting byte-level equality between

  .ai-engineering/scripts/hooks/_lib/locking.py     (hook-side, standalone)
  src/ai_engineering/state/locking.py               (pkg-side, canonical)

Tolerated divergence: the module docstring (first triple-quoted string after
any ``from __future__`` line) and the import block (everything from line 1
up to and including the last top-level ``import`` / ``from ... import``
statement). Any other byte-level difference fails CI with a unified diff.
"""

from __future__ import annotations

import ast
import difflib
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOK_LOCKING = _REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "locking.py"
_PKG_LOCKING = _REPO_ROOT / "src" / "ai_engineering" / "state" / "locking.py"


def _last_import_lineno(source: str) -> int:
    """Return the 1-based line number of the last top-level import statement.

    Walks only top-level nodes so an ``import`` nested inside an ``if`` block
    is treated as a regular statement (not a header import). The
    ``if os.name == "nt": import msvcrt`` block in locking.py contains
    nested imports — we want those preserved on the body side of the diff,
    not stripped as part of the header.
    """
    tree = ast.parse(source)
    last = 0
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            last = max(last, node.end_lineno or node.lineno)
    return last


def _strip_module_docstring(source: str) -> str:
    """Remove the leading module docstring if present, preserving line layout."""
    tree = ast.parse(source)
    if not tree.body:
        return source
    first = tree.body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        lines = source.splitlines(keepends=True)
        start = (first.lineno or 1) - 1
        end = first.end_lineno or first.lineno
        del lines[start:end]
        return "".join(lines)
    return source


def _normalize(source: str) -> str:
    """Strip module docstring and import block; return the remaining body."""
    without_doc = _strip_module_docstring(source)
    last_import = _last_import_lineno(without_doc)
    if last_import == 0:
        return without_doc
    lines = without_doc.splitlines(keepends=True)
    return "".join(lines[last_import:])


def test_locking_files_are_byte_identical_after_normalization() -> None:
    """Hook-side and pkg-side locking.py must be byte-identical after stripping
    the module docstring and the top-level import block. Any other divergence
    indicates silent drift on a security-relevant primitive (D-126-01).
    """
    assert _HOOK_LOCKING.exists(), f"missing hook-side lock primitive: {_HOOK_LOCKING}"
    assert _PKG_LOCKING.exists(), f"missing pkg-side lock primitive: {_PKG_LOCKING}"

    hook_src = _HOOK_LOCKING.read_text(encoding="utf-8")
    pkg_src = _PKG_LOCKING.read_text(encoding="utf-8")

    hook_body = _normalize(hook_src)
    pkg_body = _normalize(pkg_src)

    if hook_body != pkg_body:
        diff = "".join(
            difflib.unified_diff(
                pkg_body.splitlines(keepends=True),
                hook_body.splitlines(keepends=True),
                fromfile=str(_PKG_LOCKING),
                tofile=str(_HOOK_LOCKING),
                lineterm="",
            )
        )
        raise AssertionError(
            "hook-side and pkg-side locking.py diverged outside the tolerated "
            "module-docstring / import-block region (spec-126 D-126-01):\n" + diff
        )
