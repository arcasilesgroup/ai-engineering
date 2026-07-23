"""Deterministic session ticket generator (spec-196 D-196-01).

Generates a bounded, task-specific context index. No full references
are loaded unless an invoked workflow requests them.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SessionTicket:
    """Deterministic session ticket with bounded pointers."""

    task_type: str
    risk_level: str  # low, medium, high
    changed_paths: list[str]
    stack: str
    ticket_hash: str  # deterministic hash of inputs
    recommended_workflow: str  # which /ai-* to invoke
    context_budget_tokens: int = 500
    includes: list[str] | None = None  # only what's needed

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)

    def truncate_to_budget(self, max_bytes: int = 2048) -> str:
        """Ensure ticket stays within budget."""
        full = self.to_json()
        if len(full.encode("utf-8")) <= max_bytes:
            return full
        minimal = {
            "task_type": self.task_type,
            "risk_level": self.risk_level,
            "ticket_hash": self.ticket_hash,
            "recommended_workflow": self.recommended_workflow,
            "truncated": True,
        }
        return json.dumps(minimal, indent=2, sort_keys=True)


def _compute_hash(task_type: str, risk_level: str, stack: str, paths: list[str]) -> str:
    """Deterministic hash of ticket inputs."""
    payload = f"{task_type}:{risk_level}:{stack}:{':'.join(sorted(paths))}"
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


def _classify_risk(changed_paths: list[str]) -> str:
    """Classify risk from changed paths."""
    high_risk_patterns = ["security", "credential", "secret", "auth", "migration"]
    medium_risk_patterns = ["schema", "config", "manifest", "hook"]

    all_paths = " ".join(changed_paths).lower()
    for pattern in high_risk_patterns:
        if pattern in all_paths:
            return "high"
    for pattern in medium_risk_patterns:
        if pattern in all_paths:
            return "medium"
    return "low"


def _recommend_workflow(task_type: str, risk_level: str) -> str:
    """Recommend which /ai-* workflow to invoke."""
    workflow_map = {
        ("bug", "low"): "/ai-debug",
        ("bug", "medium"): "/ai-debug",
        ("bug", "high"): "/ai-debug",
        ("feature", "low"): "/ai-code",
        ("feature", "medium"): "/ai-build",
        ("feature", "high"): "/ai-build",
        ("test", "low"): "/ai-test",
        ("test", "medium"): "/ai-test",
        ("refactor", "low"): "/ai-simplify",
        ("refactor", "medium"): "/ai-simplify",
        ("refactor", "high"): "/ai-build",
        ("review", "low"): "/ai-review",
        ("review", "medium"): "/ai-review",
        ("review", "high"): "/ai-verify",
        ("security", "low"): "/ai-security",
        ("security", "medium"): "/ai-security",
        ("security", "high"): "/ai-security",
    }
    return workflow_map.get((task_type, risk_level), "/ai-brainstorm")


def generate_ticket(
    task_type: str = "general",
    changed_paths: list[str] | None = None,
    stack: str = "python",
) -> SessionTicket:
    """Generate a deterministic session ticket.

    Args:
        task_type: Type of task (bug, feature, test, refactor, review, security, general)
        changed_paths: Files that were changed or will be changed
        stack: Programming stack

    Returns:
        Bounded SessionTicket with deterministic hash
    """
    paths = changed_paths or []
    risk_level = _classify_risk(paths)
    ticket_hash = _compute_hash(task_type, risk_level, stack, paths)
    workflow = _recommend_workflow(task_type, risk_level)

    # Determine what context to include based on risk
    includes = []
    if risk_level == "high":
        includes.append("SECURITY.md")
    if risk_level in ("medium", "high"):
        includes.append("CONSTITUTION.md")

    return SessionTicket(
        task_type=task_type,
        risk_level=risk_level,
        changed_paths=paths,
        stack=stack,
        ticket_hash=ticket_hash,
        recommended_workflow=workflow,
        context_budget_tokens=500,
        includes=includes if includes else None,
    )
