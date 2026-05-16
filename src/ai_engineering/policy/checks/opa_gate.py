"""Adapter between policy gates and the OPA runner (spec-122 Phase C, T-3.11).

Centralises the cold-start memoisation, fail-closed-with-message
contract, and decision-log emission so each policy gate (commit_msg,
branch_protection, risk) calls a single helper rather than re-deriving
the OPA invocation.

Fail-closed-with-message
------------------------

When the OPA binary is missing the gate check fails with a clear
"opa not installed; run 'ai-eng install'" message. This is technically
a fail-closed posture — the spec language about "fail-open" referred
to *not silently dropping* the gate. The user is forced to fix the
install rather than accidentally bypass governance.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_engineering.governance import opa_runner
from ai_engineering.governance.decision_log import emit_policy_decision

__all__ = [
    "OpaDecision",
    "evaluate_deny",
]


@dataclass(frozen=True)
class OpaDecision:
    """Result of an OPA deny-rule evaluation.

    ``passed`` is True when the deny set was empty (or OPA returned no
    deny rules); False when at least one deny fired or OPA failed to
    invoke. ``output`` carries either the joined deny messages or the
    runtime error string -- ready to feed straight into a
    ``GateCheckResult.output`` field.
    """

    passed: bool
    output: str
    deny_messages: list[str]


def evaluate_deny(
    *,
    project_root: Path,
    policy: str,
    input_data: dict[str, Any],
    bundle_path: Path | None = None,
    component: str = "gate-engine",
    source: str | None = None,
) -> OpaDecision:
    """Evaluate ``data.<policy>.deny`` and emit a policy_decision event.

    Parameters
    ----------
    project_root:
        Repository root for the decision log emit.
    policy:
        Policy package name (e.g. ``"commit_conventional"``).
    input_data:
        JSON-serialisable input dict piped to ``opa eval``.
    bundle_path:
        Optional override; defaults to ``opa_runner.DEFAULT_BUNDLE_PATH``
        resolved against ``project_root``.
    component:
        Logical component label for the decision log event.
    source:
        Source label (``"pre-commit"``, ``"pre-push"``, ``"risk-cmd"``).
    """
    query = f"data.{policy}.deny"
    bundle = (
        bundle_path if bundle_path is not None else (project_root / opa_runner.DEFAULT_BUNDLE_PATH)
    )

    try:
        result = opa_runner.evaluate(query, input_data, bundle_path=bundle)
    except opa_runner.OpaError as exc:
        # Fail-closed-with-message: the user sees an actionable hint.
        message = str(exc)
        emit_policy_decision(
            project_root=project_root,
            policy=policy,
            query=query,
            input_data=input_data,
            decision="blocked",
            deny_messages=[message],
            component=component,
            source=source,
        )
        return OpaDecision(passed=False, output=message, deny_messages=[message])

    deny = result.deny_messages
    passed = len(deny) == 0
    output = "\n".join(deny) if deny else "policy allow"

    emit_policy_decision(
        project_root=project_root,
        policy=policy,
        query=query,
        input_data=input_data,
        decision="allow" if passed else "blocked",
        deny_messages=deny,
        component=component,
        source=source,
    )

    return OpaDecision(passed=passed, output=output, deny_messages=deny)
