"""Pure executor-route classifier for the governed skill chain.

The classifier answers one question only: once a plan exists, which
framework executor should the operator invoke next, ``/ai-build`` or
``/ai-autopilot``?  It deliberately does not import host telemetry or
admission-control data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Executor = Literal["build", "autopilot"]

_AUTOPILOT_CONCERN_THRESHOLD = 3
_AUTOPILOT_FILE_THRESHOLD = 10


@dataclass(frozen=True)
class ExecutionRoute:
    """Reviewable plan-frontmatter route recommendation."""

    spec: str
    executor: Executor
    automation: str
    concern_count: int
    estimated_files: int
    reason: str
    safe_next_command: str
    executable: bool


def classify_execution_route(
    *,
    spec: str,
    status: str,
    concern_count: int,
    estimated_files: int,
    automation: str = "hitl",
) -> ExecutionRoute:
    """Classify a plan into the next framework executor.

    ``status`` controls executability only.  Draft plans still get a
    route recommendation so the operator can review it, but execution is
    not allowed until the plan lifecycle state becomes ``approved``.
    """

    if concern_count >= _AUTOPILOT_CONCERN_THRESHOLD:
        executor: Executor = "autopilot"
        reason = (
            f"{concern_count} independent concerns meets the "
            f"/ai-autopilot threshold of {_AUTOPILOT_CONCERN_THRESHOLD}."
        )
    elif estimated_files >= _AUTOPILOT_FILE_THRESHOLD:
        executor = "autopilot"
        reason = (
            f"{estimated_files} estimated files meets the "
            f"/ai-autopilot threshold of {_AUTOPILOT_FILE_THRESHOLD}."
        )
    else:
        executor = "build"
        reason = "Single-concern plan below the /ai-autopilot file threshold."

    executable = status == "approved"
    if not executable:
        reason = f"Plan status {status!r} is not approved; recommendation only. {reason}"

    safe_next_command = "/ai-build" if executor == "build" else "/ai-autopilot"
    return ExecutionRoute(
        spec=spec,
        executor=executor,
        automation=automation,
        concern_count=concern_count,
        estimated_files=estimated_files,
        reason=reason,
        safe_next_command=safe_next_command,
        executable=executable,
    )
