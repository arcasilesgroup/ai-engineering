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
VALID_EXECUTION_ROUTE_EXECUTORS = frozenset({"build", "autopilot"})
EXECUTION_ROUTE_REQUIRED_FIELDS = frozenset(
    {
        "automation",
        "concern_count",
        "estimated_files",
        "executor",
        "reason",
        "safe_next_command",
        "spec",
        "version",
    }
)
EXECUTION_ROUTE_COMMANDS = {
    "build": "/ai-build",
    "autopilot": "/ai-autopilot",
}
EXECUTION_ROUTE_FORBIDDEN_APPROVAL_FIELDS = frozenset(
    {
        "approval",
        "approved",
        "approved_at",
        "approved_by",
        "is_approved",
        "plan_approved",
    }
)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_TASK_RE = re.compile(r"^\s*-\s*\[([ xX])\]", re.MULTILINE)
_CHECKBOX_LIKE_RE = re.compile(r"^\s*-\s*\[([^\]]*)\]", re.MULTILINE)
_TASK_ID_RE = re.compile(r"\bT-(\d+)\.(\d+)\b")


def _strip_scalar_quotes(value: str) -> str:
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Lightweight YAML-frontmatter extractor (no PyYAML dep).

    Reads key: value pairs from the leading ``---`` fenced block and
    the ``execution_route:`` one-level nested map used by spec-145.
    Quoted values strip the quotes; arbitrary YAML remains out of
    scope so this lint path stays dependency-free.
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    out: dict[str, str] = {}
    nested_key: str | None = None
    for raw_line in match.group(1).splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))

        if indent == 0:
            nested_key = None
        elif nested_key:
            if ":" not in stripped:
                continue
            key, _, value = stripped.partition(":")
            out[f"{nested_key}.{key.strip()}"] = _strip_scalar_quotes(value.strip())
            continue
        else:
            continue

        line = stripped
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        key = key.strip()
        out[key] = _strip_scalar_quotes(value)
        if key == "execution_route" and not value:
            nested_key = key
    return out


def _execution_route_fields(fm: dict[str, str]) -> dict[str, str]:
    prefix = "execution_route."
    return {key.removeprefix(prefix): value for key, value in fm.items() if key.startswith(prefix)}


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

    route = _execution_route_fields(fm)
    if route:
        missing = sorted(EXECUTION_ROUTE_REQUIRED_FIELDS - route.keys())
        for field in missing:
            results.append(
                CheckResult(
                    "plan_execution_route_missing_field",
                    "BLOCKER",
                    f"execution_route missing required {field!r} field",
                )
            )

        forbidden = sorted(EXECUTION_ROUTE_FORBIDDEN_APPROVAL_FIELDS & route.keys())
        for field in forbidden:
            results.append(
                CheckResult(
                    "plan_execution_route_approval_duplicate",
                    "BLOCKER",
                    (
                        f"execution_route field {field!r} duplicates approval state; "
                        "plan frontmatter 'status' is the approval source of truth"
                    ),
                )
            )

        route_spec = route.get("spec")
        if route_spec and route_spec != fm.get("spec"):
            results.append(
                CheckResult(
                    "plan_execution_route_spec_mismatch",
                    "BLOCKER",
                    (
                        f"execution_route.spec {route_spec!r} does not match "
                        f"plan spec {fm.get('spec')!r}"
                    ),
                )
            )

        executor = route.get("executor", "")
        if executor and executor not in VALID_EXECUTION_ROUTE_EXECUTORS:
            results.append(
                CheckResult(
                    "plan_execution_route_executor_invalid",
                    "BLOCKER",
                    (
                        f"execution_route.executor {executor!r} not in "
                        f"{sorted(VALID_EXECUTION_ROUTE_EXECUTORS)}"
                    ),
                )
            )

        expected_command = EXECUTION_ROUTE_COMMANDS.get(executor)
        command = route.get("safe_next_command")
        if expected_command and command and command != expected_command:
            results.append(
                CheckResult(
                    "plan_execution_route_command_mismatch",
                    "BLOCKER",
                    (
                        f"execution_route.safe_next_command {command!r} must be "
                        f"{expected_command!r} when executor is {executor!r}"
                    ),
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
