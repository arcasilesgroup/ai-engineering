#!/usr/bin/env python3
"""Compose Markdown PR body from spec.md + plan.md frontmatter (brief §17).

80% of the PR body is deterministic data shuffling: the Summary section
takes its bullets from spec.md frontmatter ``summary``, the Test Plan
checklist comes from plan.md ``[ ]`` rows, and the Work Items section
joins ``refs.user_stories`` / ``refs.tasks`` with ``Closes #N`` lines.

LLM extension point: the ``--bullets-prompt`` flag accepts free-form
Summary bullets when the operator wants a hand-written narrative. The
SKILL.md fills this via Claude on demand.

Output: Markdown to stdout. Stdlib + pyyaml. No external HTTP.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SPEC_PATH = _REPO_ROOT / ".ai-engineering" / "specs" / "spec.md"
_PLAN_PATH = _REPO_ROOT / ".ai-engineering" / "specs" / "plan.md"
_MANIFEST_PATH = _REPO_ROOT / ".ai-engineering" / "manifest.yml"

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
_TASK_RE = re.compile(r"^\s*-\s*\[([ xX])\]\s*(.+?)$", re.MULTILINE)


def _load_frontmatter(path: Path) -> dict | None:
    if not path.is_file() or yaml is None:
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = _FRONTMATTER_RE.search(text)
    if not match:
        return None
    try:
        fm = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return None
    return fm if isinstance(fm, dict) else None


def _extract_tasks(plan_path: Path, *, only_unchecked: bool = True) -> list[str]:
    """Extract ``[ ]`` task lines from plan.md (text after the bracket)."""
    if not plan_path.is_file():
        return []
    try:
        text = plan_path.read_text(encoding="utf-8")
    except OSError:
        return []
    tasks: list[str] = []
    for state, body in _TASK_RE.findall(text):
        is_done = state in ("x", "X")
        if only_unchecked and is_done:
            continue
        tasks.append(body.strip())
    return tasks


def _format_summary(spec_fm: dict | None, override: str | None) -> str:
    if override:
        body = override.strip()
        return f"## Summary\n\n{body}\n"

    bullets: list[str] = []
    if spec_fm:
        # Multiple shapes accepted: ``summary`` as list, string, or
        # ``description`` fallback.
        summary = spec_fm.get("summary") or spec_fm.get("description")
        if isinstance(summary, list):
            bullets = [str(b).strip() for b in summary if str(b).strip()]
        elif isinstance(summary, str):
            # Split on newlines or `;` separators.
            bullets = [s.strip() for s in re.split(r"[\n;]+", summary) if s.strip()]

    if not bullets:
        bullets = ["<fill in 1-3 bullets>"]
    rendered = "\n".join(f"- {b}" for b in bullets)
    return f"## Summary\n\n{rendered}\n"


def _format_test_plan(tasks: list[str]) -> str:
    # Cap at 10 to keep PR bodies focused; default minimal checklist when
    # plan.md has no unchecked tasks (e.g., docs-only PRs).
    items = tasks[:10] if tasks else ["Lint clean (`ruff check`)", "Tests green (`pytest`)"]
    rendered = "\n".join(f"- [ ] {item}" for item in items)
    return f"## Test Plan\n\n{rendered}\n"


def _format_work_items(spec_fm: dict | None) -> str:
    if not spec_fm:
        return "## Work Items\n\n- _none_\n"
    refs = spec_fm.get("refs") or {}
    if not isinstance(refs, dict):
        return "## Work Items\n\n- _none_\n"

    closes: list[str] = []
    related: list[str] = []
    for closing_key in ("user_stories", "tasks", "issues", "bugs"):
        items = refs.get(closing_key) or []
        if isinstance(items, list):
            for item in items:
                ref = str(item).strip()
                if ref:
                    closes.append(ref)
    for related_key in ("features",):
        items = refs.get(related_key) or []
        if isinstance(items, list):
            for item in items:
                ref = str(item).strip()
                if ref:
                    related.append(ref)

    lines: list[str] = []
    # Both GitHub (``#45``) and Azure DevOps (``AB#102``) refs use the
    # ``Closes`` keyword; the suffix encodes the platform.
    for ref in closes:
        lines.append(f"- Closes {ref}")
    for ref in related:
        lines.append(f"- Related: {ref} (never closed)")

    if not lines:
        lines.append("- _none_")
    return "## Work Items\n\n" + "\n".join(lines) + "\n"


def _format_checklist() -> str:
    items = (
        "Lint clean",
        "Secret scan clean",
        "Tests green",
        "CHANGELOG updated (if user-visible)",
        "No breaking changes (or documented)",
    )
    rendered = "\n".join(f"- [ ] {it}" for it in items)
    return f"## Checklist\n\n{rendered}\n"


def compose_body(
    *,
    spec_path: Path = _SPEC_PATH,
    plan_path: Path = _PLAN_PATH,
    bullets_prompt: str | None = None,
) -> str:
    spec_fm = _load_frontmatter(spec_path)
    tasks = _extract_tasks(plan_path)

    parts = [
        _format_summary(spec_fm, bullets_prompt),
        _format_test_plan(tasks),
        _format_work_items(spec_fm),
        _format_checklist(),
    ]
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pr_body_compose",
        description="Compose Markdown PR body from spec.md + plan.md frontmatter.",
    )
    parser.add_argument(
        "--spec-path",
        type=Path,
        default=_SPEC_PATH,
        help="Path to spec.md.",
    )
    parser.add_argument(
        "--plan-path",
        type=Path,
        default=_PLAN_PATH,
        help="Path to plan.md.",
    )
    parser.add_argument(
        "--bullets-prompt",
        default=None,
        help="LLM-supplied Summary bullets (multi-line). Overrides frontmatter summary.",
    )
    args = parser.parse_args(argv)

    body = compose_body(
        spec_path=args.spec_path,
        plan_path=args.plan_path,
        bullets_prompt=args.bullets_prompt,
    )
    sys.stdout.write(body)
    if not body.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
