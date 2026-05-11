"""Plan check — enforces ``.ai-engineering/specs/plan.md`` contract.

Per `plan-schema.md`: every plan in an active lifecycle state must
carry checkbox tasks (``- [ ]`` / ``- [x]``). Plans in shipped states
are exempt because they legitimately rotate to an aggregate index.

Invoked by ``spec_lint.cli`` after the five spec checks. Operates on
the sibling ``plan.md`` of the supplied ``spec.md`` (same directory),
returning ``[]`` when no plan exists (skip silently — ``/ai-plan`` may
not have run yet).
"""

from __future__ import annotations

import re
from pathlib import Path

from spec_lint.checks.frontmatter import CheckResult

VALID_PLAN_STATUSES = frozenset(
    {
        "draft",
        "approved",
        "in-progress",
        "shipped-pending-pr-merge",
        "shipped",
    }
)

ACTIVE_PLAN_STATUSES = frozenset({"draft", "approved", "in-progress"})

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_TASK_RE = re.compile(r"^\s*-\s*\[([ xX])\]", re.MULTILINE)
_CHECKBOX_LIKE_RE = re.compile(r"^\s*-\s*\[([^\]]*)\]", re.MULTILINE)
_TASK_ID_RE = re.compile(r"\bT-(\d+)\.(\d+)\b")


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Lightweight YAML-frontmatter extractor (no PyYAML dep).

    Reads key: value pairs from the leading ``---`` fenced block.
    Quoted values strip the quotes; nested structures are out of scope
    (the plan schema only requires flat scalar fields).
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    out: dict[str, str] = {}
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        out[key.strip()] = value
    return out


def _resolve_plan_path(spec_path: Path) -> Path:
    return spec_path.parent / "plan.md"


def check_plan(spec_path: Path) -> list[CheckResult]:
    """Validate the sibling plan.md against `plan-schema.md`.

    Returns ``[]`` when no plan exists (skip silently). Returns one
    ``CheckResult`` per violation. The shipped-state exemption applies
    BEFORE the task-line existence rule.
    """
    plan_path = _resolve_plan_path(spec_path)
    if not plan_path.is_file():
        return []

    try:
        text = plan_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [
            CheckResult(
                "plan_unreadable",
                "BLOCKER",
                f"could not read sibling plan.md: {exc}",
            )
        ]

    results: list[CheckResult] = []
    fm = _parse_frontmatter(text)

    if not fm:
        results.append(
            CheckResult(
                "plan_frontmatter_missing",
                "BLOCKER",
                "plan.md has no YAML frontmatter fence (--- … ---)",
            )
        )
        return results

    status = fm.get("status") or fm.get("state") or ""
    if not status:
        results.append(
            CheckResult(
                "plan_status_missing",
                "BLOCKER",
                "plan.md frontmatter missing required 'status' field",
            )
        )
    elif status not in VALID_PLAN_STATUSES:
        results.append(
            CheckResult(
                "plan_status_invalid",
                "BLOCKER",
                f"plan.md status {status!r} not in {sorted(VALID_PLAN_STATUSES)}",
            )
        )

    for required in ("spec", "title"):
        if not fm.get(required):
            results.append(
                CheckResult(
                    "plan_frontmatter_missing_field",
                    "BLOCKER",
                    f"plan.md frontmatter missing required {required!r} field",
                )
            )

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        cb = _CHECKBOX_LIKE_RE.match(raw_line)
        if not cb:
            continue
        marker = cb.group(1)
        if marker not in (" ", "x", "X"):
            results.append(
                CheckResult(
                    "plan_task_marker_invalid",
                    "BLOCKER",
                    (
                        f"line {line_no}: checkbox marker '[{marker}]' "
                        "must be '[ ]', '[x]', or '[X]' (plan-schema.md "
                        "Task Line Format)"
                    ),
                    line=line_no,
                )
            )

    if status in ACTIVE_PLAN_STATUSES:
        tasks = _TASK_RE.findall(text)
        if not tasks:
            results.append(
                CheckResult(
                    "plan_tasks_missing",
                    "BLOCKER",
                    (
                        f"plan.md status={status!r} but no checkbox tasks "
                        "found (required by plan-schema.md rule 3)"
                    ),
                )
            )

    seen_ids: dict[str, int] = {}
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        if not _TASK_RE.match(raw_line):
            continue
        for match in _TASK_ID_RE.finditer(raw_line):
            tid = f"T-{match.group(1)}.{match.group(2)}"
            if tid in seen_ids:
                results.append(
                    CheckResult(
                        "plan_task_id_duplicate",
                        "ADVISORY",
                        (
                            f"task id {tid} repeats at line {line_no} "
                            f"(previously line {seen_ids[tid]})"
                        ),
                        line=line_no,
                    )
                )
            else:
                seen_ids[tid] = line_no

    return results
