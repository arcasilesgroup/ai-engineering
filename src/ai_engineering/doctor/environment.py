"""Shared environment failure classification for install and doctor flows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class FailureCategory(StrEnum):
    """Stable environment issue categories shared across the framework."""

    RUNTIME = "runtime"
    PACKAGING = "packaging"
    FEEDS = "feeds"
    TOOLS = "tools"
    PROVIDER_PREREQUISITES = "provider-prerequisites"


class RemediationPolicy(StrEnum):
    """Remediation policy selected for an environment failure category."""

    FAIL_FAST = "fail-fast"
    TRY_REPAIR = "try-repair"
    VALIDATE_THEN_BLOCK = "validate-then-block"
    REQUIRE_CAPABILITY_CHECK = "require-capability-check"
    SCOPE_CHECK_FIRST = "scope-check-first"


@dataclass(frozen=True)
class EnvironmentIssue:
    """Normalized environment issue contract for future install and doctor flows."""

    category: FailureCategory
    detail: str
    remediation_policy: RemediationPolicy


def classify_failure(
    exc: Exception,
    context: dict[str, Any] | None = None,
) -> FailureCategory:
    """Classify an exception into the shared spec-102 environment taxonomy."""
    details = str(exc).lower()
    ctx = context or {}

    if _is_provider_prerequisite(details, ctx):
        return FailureCategory.PROVIDER_PREREQUISITES

    if isinstance(exc, (ImportError, ModuleNotFoundError)):
        return FailureCategory.PACKAGING

    if isinstance(exc, FileNotFoundError) or _contains_any(
        details,
        (
            "executable not found",
            "not found on path",
            "command not found",
            "cli required",
            "cli not installed",
        ),
    ):
        return FailureCategory.TOOLS

    if isinstance(exc, ConnectionError) or _contains_any(
        details,
        (
            "feed",
            "index",
            "keyring",
            "auth failed",
            "authentication",
            "credential",
            "registry",
        ),
    ):
        return FailureCategory.FEEDS

    return FailureCategory.RUNTIME


def repair_strategy(category: FailureCategory) -> RemediationPolicy:
    """Return the remediation policy for a classified environment failure."""
    return {
        FailureCategory.RUNTIME: RemediationPolicy.FAIL_FAST,
        FailureCategory.PACKAGING: RemediationPolicy.TRY_REPAIR,
        FailureCategory.FEEDS: RemediationPolicy.VALIDATE_THEN_BLOCK,
        FailureCategory.TOOLS: RemediationPolicy.REQUIRE_CAPABILITY_CHECK,
        FailureCategory.PROVIDER_PREREQUISITES: RemediationPolicy.SCOPE_CHECK_FIRST,
    }[category]


def issue_from_failure(
    exc: Exception,
    context: dict[str, Any] | None = None,
) -> EnvironmentIssue:
    """Build a normalized environment issue from a raw exception."""
    category = classify_failure(exc, context=context)
    return EnvironmentIssue(
        category=category,
        detail=str(exc),
        remediation_policy=repair_strategy(category),
    )


def _contains_any(text: str, fragments: tuple[str, ...]) -> bool:
    return any(fragment in text for fragment in fragments)


def _is_provider_prerequisite(details: str, context: dict[str, Any]) -> bool:
    if not context.get("provider_scoped"):
        return False

    required_provider = _normalize_provider(context.get("required_provider"))
    active_provider = _normalize_provider(context.get("vcs_provider"))
    if required_provider and active_provider and required_provider != active_provider:
        return False

    return _contains_any(details, ("azure cli", "github cli", "gh cli", "az cli", "provider"))


def _normalize_provider(provider: Any) -> str:
    if provider is None:
        return ""
    return str(provider).replace("-", "_").lower()
