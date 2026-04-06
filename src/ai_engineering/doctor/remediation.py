"""Shared remediation contract for install and doctor fix flows."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from ai_engineering.doctor.environment import FailureCategory


class RemediationStatus(StrEnum):
    """Stable remediation outcomes shared by install and doctor."""

    REPAIRED = "repaired"
    MANUAL = "manual"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not-applicable"


@dataclass
class RemediationResult:
    """Normalized remediation result for a single shared failure class."""

    category: FailureCategory
    status: RemediationStatus
    source: str
    summary: str
    detail: str = ""
    repaired_items: list[str] = field(default_factory=list)
    remaining_items: list[str] = field(default_factory=list)
    manual_steps: list[str] = field(default_factory=list)


class PackagingRepairer(Protocol):
    """Repair callback for framework-owned packaging drift."""

    def __call__(self, detail: str, *, source: str) -> bool: ...


class ToolCapabilityChecker(Protocol):
    """Capability callback for OS/provider-specific tool installation support."""

    def __call__(self, tool: str) -> bool: ...


class ToolInstaller(Protocol):
    """Installer callback for an individual missing tool."""

    def __call__(self, tool: str) -> bool: ...


class ToolManualStepFactory(Protocol):
    """Manual guidance callback for tools that cannot be auto-installed."""

    def __call__(self, tool: str) -> str: ...


@dataclass
class RemediationEngine:
    """Small shared engine for remediation outcomes introduced in spec-102."""

    packaging_repair: PackagingRepairer | None = None
    tool_capability: ToolCapabilityChecker | None = None
    tool_installer: ToolInstaller | None = None
    tool_manual_step: ToolManualStepFactory | None = None

    def remediate_packaging_drift(self, detail: str, *, source: str) -> RemediationResult:
        """Attempt repair for framework-owned packaging drift."""
        normalized_detail = detail.strip()
        if not normalized_detail:
            return RemediationResult(
                category=FailureCategory.PACKAGING,
                status=RemediationStatus.NOT_APPLICABLE,
                source=source,
                summary="No packaging drift detected.",
            )

        if self.packaging_repair is None:
            return RemediationResult(
                category=FailureCategory.PACKAGING,
                status=RemediationStatus.BLOCKED,
                source=source,
                summary="Packaging drift repair is not configured.",
                detail=normalized_detail,
                remaining_items=["framework-runtime"],
            )

        try:
            repaired = self.packaging_repair(normalized_detail, source=source)
        except Exception as exc:
            return RemediationResult(
                category=FailureCategory.PACKAGING,
                status=RemediationStatus.BLOCKED,
                source=source,
                summary="Packaging drift repair failed.",
                detail=str(exc),
                remaining_items=["framework-runtime"],
            )

        if repaired:
            return RemediationResult(
                category=FailureCategory.PACKAGING,
                status=RemediationStatus.REPAIRED,
                source=source,
                summary="Framework packaging drift repaired.",
                detail=normalized_detail,
                repaired_items=["framework-runtime"],
            )

        return RemediationResult(
            category=FailureCategory.PACKAGING,
            status=RemediationStatus.BLOCKED,
            source=source,
            summary="Packaging drift could not be repaired automatically.",
            detail=normalized_detail,
            remaining_items=["framework-runtime"],
        )

    def remediate_missing_tools(
        self,
        missing_tools: Sequence[str],
        *,
        source: str,
    ) -> RemediationResult:
        """Attempt repair or manual guidance for missing CLI tools."""
        normalized_tools = [tool.strip() for tool in missing_tools if tool.strip()]
        if not normalized_tools:
            return RemediationResult(
                category=FailureCategory.TOOLS,
                status=RemediationStatus.NOT_APPLICABLE,
                source=source,
                summary="No missing tools detected.",
            )

        repaired_items: list[str] = []
        remaining_items: list[str] = []
        manual_steps: list[str] = []

        for index, tool in enumerate(normalized_tools):
            try:
                if self.tool_capability is not None and not self.tool_capability(tool):
                    remaining_items.append(tool)
                    manual_steps.append(self._manual_step(tool))
                    continue

                if self.tool_installer is None:
                    remaining_items.append(tool)
                    manual_steps.append(self._manual_step(tool))
                    continue

                if self.tool_installer(tool):
                    repaired_items.append(tool)
                    continue

                remaining_items.append(tool)
                manual_steps.append(self._manual_step(tool))
            except Exception as exc:
                remaining_items.extend(
                    tool for tool in normalized_tools[index:] if tool not in remaining_items
                )
                return RemediationResult(
                    category=FailureCategory.TOOLS,
                    status=RemediationStatus.BLOCKED,
                    source=source,
                    summary="Missing tool remediation failed.",
                    detail=str(exc),
                    repaired_items=repaired_items,
                    remaining_items=remaining_items,
                    manual_steps=manual_steps,
                )

        if remaining_items:
            return RemediationResult(
                category=FailureCategory.TOOLS,
                status=RemediationStatus.MANUAL,
                source=source,
                summary="Some tools require manual follow-up.",
                repaired_items=repaired_items,
                remaining_items=remaining_items,
                manual_steps=manual_steps,
            )

        return RemediationResult(
            category=FailureCategory.TOOLS,
            status=RemediationStatus.REPAIRED,
            source=source,
            summary="Missing tools repaired.",
            repaired_items=repaired_items,
        )

    def _manual_step(self, tool: str) -> str:
        if self.tool_manual_step is not None:
            return self.tool_manual_step(tool)
        return f"Install `{tool}` manually."
