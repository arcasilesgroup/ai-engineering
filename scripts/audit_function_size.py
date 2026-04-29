#!/usr/bin/env python3
"""Audit Python function body size against the 50-LOC clean-code target.

Scans `src/ai_engineering/` and `.ai-engineering/scripts/hooks/`
(excluding `src/ai_engineering/templates/`) and reports each function whose
body exceeds 50 LOC, where "body" excludes the function signature, leading
docstring, and decorator lines.

Output format: JSON list to stdout, one entry per offender::

    [
      {"file": "...", "function": "...", "loc": 73, "has_exempt": false},
      ...
    ]

A function is considered exempt when the line containing the `def` keyword
ends with `# audit:exempt:<reason>`.

Usage::

    python scripts/audit_function_size.py
    python scripts/audit_function_size.py --threshold 50

Exit code is always 0 — this is a reporting tool, not a gate.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_THRESHOLD = 50

INCLUDE_DIRS = (
    REPO_ROOT / "src" / "ai_engineering",
    REPO_ROOT / ".ai-engineering" / "scripts" / "hooks",
)
EXCLUDE_DIRS = (REPO_ROOT / "src" / "ai_engineering" / "templates",)


def _is_excluded(path: Path) -> bool:
    return any(excluded in path.parents or excluded == path for excluded in EXCLUDE_DIRS)


def _iter_python_files() -> list[Path]:
    files: list[Path] = []
    for root in INCLUDE_DIRS:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if _is_excluded(path):
                continue
            if "__pycache__" in path.parts:
                continue
            files.append(path)
    return sorted(files)


def _function_body_loc(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Compute body LOC excluding leading docstring."""
    body = list(node.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    if not body:
        return 0
    first = body[0]
    last = body[-1]
    end = getattr(last, "end_lineno", last.lineno) or last.lineno
    return max(0, end - first.lineno + 1)


def _has_exempt_marker(
    source_lines: list[str],
    def_line_idx: int,
    body_start_idx: int,
) -> bool:
    """Return True when the function signature span carries `# audit:exempt:<reason>`.

    Scans every line from the `def` keyword through (but not including) the
    first body line. Multi-line signatures reformatted by ruff/black may park
    the trailing comment on the closing-paren line rather than the `def`
    line itself, so the marker can appear anywhere in that span.
    """
    if def_line_idx < 0 or def_line_idx >= len(source_lines):
        return False
    end_idx = max(def_line_idx + 1, min(body_start_idx, len(source_lines)))
    return any("# audit:exempt:" in source_lines[i] for i in range(def_line_idx, end_idx))


def _scan_file(path: Path, threshold: int) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    source_lines = text.splitlines()
    offenders: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        loc = _function_body_loc(node)
        if loc <= threshold:
            continue
        def_line_idx = node.lineno - 1
        body_start_idx = node.body[0].lineno - 1 if node.body else def_line_idx + 1
        offenders.append(
            {
                "file": str(path.relative_to(REPO_ROOT)),
                "function": node.name,
                "loc": loc,
                "has_exempt": _has_exempt_marker(source_lines, def_line_idx, body_start_idx),
            }
        )
    return offenders


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    args = parser.parse_args(argv)

    offenders: list[dict] = []
    for path in _iter_python_files():
        offenders.extend(_scan_file(path, args.threshold))

    json.dump(offenders, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
