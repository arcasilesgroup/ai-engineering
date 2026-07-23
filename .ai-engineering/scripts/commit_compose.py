#!/usr/bin/env python3
"""Compose conventional commit subject from spec.md frontmatter (brief §17).

No LLM unless ``--desc`` is omitted, in which case the script returns
the template with a ``<DESC>`` placeholder for the caller (the LLM
fills only the description clause).

Output shape:

* With active spec & ``--desc``:  ``feat(spec-127): Task 3.4 -- adopt rubric``
* With active spec, no ``--desc``: ``feat(spec-127): Task 3.4 -- <DESC>``
* No active spec, ``--desc``:     ``feat: adopt rubric``
* No active spec, no ``--desc``:  ``feat: <DESC>``

Frontmatter parsing is delegated to ``skill_scripts_lib.markdown_render``
(spec-129 T-14). ``--type`` overrides the default ``feat``. ``--task``
overrides the auto-extracted task identifier (``Task X.Y``).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add ``skill_scripts_lib`` parent dir to ``sys.path`` so this CLI runs
# standalone without the venv-only ``pythonpath`` entry in pyproject.
sys.path.insert(0, str(Path(__file__).resolve().parent / "skills"))

try:
    from skill_scripts_lib.markdown_render import (  # type: ignore[import-not-found]
        InvalidFrontmatterError,
        parse_frontmatter,
    )
except ImportError:  # pragma: no cover - lib missing
    parse_frontmatter = None  # type: ignore[assignment]
    InvalidFrontmatterError = Exception  # type: ignore[assignment,misc]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SPEC_PATH = _REPO_ROOT / ".ai-engineering" / "specs" / "spec.md"

VALID_TYPES = (
    "feat",
    "fix",
    "perf",
    "refactor",
    "style",
    "docs",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
)
DESC_PLACEHOLDER = "<DESC>"


def _read_frontmatter(spec_path: Path) -> dict | None:
    if not spec_path.is_file() or parse_frontmatter is None:
        return None
    try:
        fm = parse_frontmatter(spec_path.read_text(encoding="utf-8"))
    except (OSError, InvalidFrontmatterError):
        return None
    return fm or None


def compose_subject(
    *,
    commit_type: str,
    spec_id: str | None,
    task: str | None,
    desc: str | None,
) -> str:
    """Compose a conventional-commit subject line.

    The ``Task X.Y`` clause is included only when ``task`` is present.
    The description clause defaults to ``DESC_PLACEHOLDER`` so callers
    that need an LLM to fill it have a stable token to substitute.
    """
    if commit_type not in VALID_TYPES:
        raise ValueError(f"commit type {commit_type!r} not in {VALID_TYPES}")

    desc_clause = desc.strip() if isinstance(desc, str) and desc.strip() else DESC_PLACEHOLDER

    if spec_id:
        sid = spec_id if str(spec_id).startswith("spec-") else f"spec-{spec_id}"
        scope = f"({sid})"
        body = f"Task {task} -- {desc_clause}" if task else desc_clause
        return f"{commit_type}{scope}: {body}"
    return f"{commit_type}: {desc_clause}"


def _extract_spec_id(frontmatter: dict | None) -> str | None:
    if not frontmatter:
        return None
    val = frontmatter.get("id") or frontmatter.get("spec_id")
    return None if val is None else str(val).strip() or None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="commit_compose",
        description="Compose conventional commit subject from spec.md frontmatter.",
    )
    parser.add_argument(
        "--type",
        default="feat",
        choices=VALID_TYPES,
        dest="commit_type",
        help="Conventional commit type (default: feat).",
    )
    parser.add_argument(
        "--task",
        default=None,
        help='Task identifier (e.g., "3.4"). Omit to drop the Task clause.',
    )
    parser.add_argument(
        "--desc",
        default=None,
        help="Description clause. If omitted, output contains <DESC> for the LLM to fill.",
    )
    parser.add_argument(
        "--spec-path",
        type=Path,
        default=_SPEC_PATH,
        help="Path to spec.md.",
    )
    args = parser.parse_args(argv)

    fm = _read_frontmatter(args.spec_path)
    spec_id = _extract_spec_id(fm)
    subject = compose_subject(
        commit_type=args.commit_type,
        spec_id=spec_id,
        task=args.task,
        desc=args.desc,
    )
    sys.stdout.write(subject)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
