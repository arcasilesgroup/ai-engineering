#!/usr/bin/env python3
"""Sync plan.md frontmatter (``total`` / ``completed``) with checkbox counts.

Wired by ai-autopilot Phase 2 (deep-plan gate) and Phase 4 (implement
post-wave) handlers. Pure stdlib, deterministic, <50ms per file.

Canonical task line format (per ``ai-autopilot`` deep-plan handler):

    - [ ] T-N.K: title
    - [x] T-N.K: title

Sub-bullets (``  - **Files**: ...``) are indented and not counted.
Bullets without ``[ ]`` / ``[x]`` (``- **T-2.1** —``), section headers
(``### Task 1``), and empty placeholders (``[EMPTY — populated by
Phase 2]``) all count as zero canonical tasks. ``validate`` rejects
plans with fewer than two canonical checkboxes so the Phase 2 gate
fails fast instead of silently letting a malformed plan through.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Domain — pure counting
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Counts:
    total: int
    completed: int


_CHECKBOX_LINE = re.compile(r"^- \[([ xX])\]", re.MULTILINE)


def count_tasks(body: str) -> Counts:
    total = 0
    completed = 0
    for match in _CHECKBOX_LINE.finditer(body):
        total += 1
        if match.group(1).lower() == "x":
            completed += 1
    return Counts(total=total, completed=completed)


# ---------------------------------------------------------------------------
# Frontmatter — minimal YAML-ish parser (stdlib only)
# ---------------------------------------------------------------------------


_FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    fm: dict[str, str] = {}
    for line in match.group("body").splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip()
    return fm, text[match.end() :]


def render_frontmatter(fm: dict[str, object], body: str) -> str:
    lines = ["---"]
    for key, value in fm.items():
        lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n" + body


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------


def sync(path: Path) -> bool:
    """Rewrite ``path`` so frontmatter ``total`` / ``completed`` match the body.

    Returns ``True`` if the file changed, ``False`` if already in sync.
    Raises ``FileNotFoundError`` if ``path`` does not exist.
    """
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    counts = count_tasks(body)

    new_fm: dict[str, object] = {
        "total": counts.total,
        "completed": counts.completed,
    }
    for key, value in fm.items():
        if key in new_fm:
            continue
        new_fm[key] = value

    new_text = render_frontmatter(new_fm, body)
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def validate(path: Path) -> tuple[bool, str]:
    """Sync ``path`` and assert it has at least two canonical checkbox tasks.

    The sync runs unconditionally so the frontmatter is always honest after
    this call, even when the gate fails.
    """
    sync(path)
    text = path.read_text(encoding="utf-8")
    _, body = parse_frontmatter(text)
    counts = count_tasks(body)
    if counts.total >= 2:
        return True, f"ok: {counts.completed}/{counts.total} tasks"
    return False, (
        f"plan has {counts.total} canonical `- [ ]` checkbox tasks; "
        "gate requires >= 2 (see phase-deep-plan.md)"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="plan_tasks.py",
        description="Sync plan.md frontmatter with checkbox counts.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_sync = sub.add_parser("sync", help="rewrite frontmatter total/completed")
    p_sync.add_argument("path", type=Path)

    p_validate = sub.add_parser("validate", help="sync + assert plan has >= 2 canonical tasks")
    p_validate.add_argument("path", type=Path)

    args = parser.parse_args(argv)

    if args.cmd == "sync":
        try:
            changed = sync(args.path)
        except FileNotFoundError:
            print(f"plan not found: {args.path}", file=sys.stderr)
            return 1
        print("changed" if changed else "in-sync")
        return 0

    if args.cmd == "validate":
        try:
            ok, reason = validate(args.path)
        except FileNotFoundError:
            print(f"plan not found: {args.path}", file=sys.stderr)
            return 1
        print(reason)
        return 0 if ok else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(_main())
