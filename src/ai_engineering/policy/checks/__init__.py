"""Gate check modules for ai-engineering quality gates."""

from __future__ import annotations

from ai_engineering.policy.checks.branch_protection import (
    check_branch_protection,
    check_hook_integrity,
    check_version_deprecation,
)
from ai_engineering.policy.checks.commit_msg import inject_gate_trailer, validate_commit_message
from ai_engineering.policy.checks.risk import (
    check_expired_risk_acceptances,
    check_expiring_risk_acceptances,
    load_decision_store,
)
from ai_engineering.policy.checks.sonar import check_sonar_gate
from ai_engineering.policy.checks.stack_runner import (
    CheckConfig,
    run_checks_for_stacks,
    run_tool_check,
)

__all__ = [
    "CheckConfig",
    "check_branch_protection",
    "check_expired_risk_acceptances",
    "check_expiring_risk_acceptances",
    "check_hook_integrity",
    "check_sonar_gate",
    "check_version_deprecation",
    "inject_gate_trailer",
    "load_decision_store",
    "run_checks_for_stacks",
    "run_tool_check",
    "validate_commit_message",
]
