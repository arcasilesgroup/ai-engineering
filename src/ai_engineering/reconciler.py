"""Shared resource reconciliation core for local convergence flows.

The reconciler owns the generic lifecycle shared by installer, doctor, and
updater surfaces: inspect, plan, apply, verify. Domain-specific behavior stays
behind adapters so result models and ownership boundaries remain compatible.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ReconcileAction:
    """A single planned resource convergence action."""

    action_id: str
    action_type: str
    resource: str
    reason: str
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ReconcileInspection:
    """Side-effect-free snapshot collected before planning."""

    resource_name: str
    payload: object | None = None


@dataclass(frozen=True)
class ReconcilePlan:
    """Explicit action plan produced from an inspection snapshot."""

    resource_name: str
    actions: list[ReconcileAction] = field(default_factory=list)
    payload: object | None = None


@dataclass(frozen=True)
class ReconcileApplyResult:
    """Result of applying a reconcile plan."""

    resource_name: str
    applied_actions: list[str] = field(default_factory=list)
    skipped_actions: list[str] = field(default_factory=list)
    failed_actions: list[str] = field(default_factory=list)
    payload: object | None = None


@dataclass(frozen=True)
class ReconcileVerification:
    """Postcondition check result for applied resource changes."""

    resource_name: str
    passed: bool = True
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    payload: object | None = None


@dataclass(frozen=True)
class ReconcileRun:
    """Full lifecycle record for one resource adapter."""

    resource_name: str
    inspection: ReconcileInspection
    plan: ReconcilePlan
    apply_result: ReconcileApplyResult | None = None
    verification: ReconcileVerification | None = None
    preview: bool = False
    rolled_back: bool = False


class ResourceAdapter(Protocol):
    """Adapter contract implemented by each domain resource family."""

    @property
    def name(self) -> str: ...

    def inspect(self, context: object) -> ReconcileInspection: ...

    def plan(self, inspection: ReconcileInspection, context: object) -> ReconcilePlan: ...

    def apply(self, plan: ReconcilePlan, context: object) -> ReconcileApplyResult: ...

    def verify(
        self,
        apply_result: ReconcileApplyResult,
        context: object,
    ) -> ReconcileVerification: ...

    def rollback(
        self,
        plan: ReconcilePlan,
        context: object,
        reason: BaseException | ReconcileVerification,
    ) -> None: ...

    def finalize(
        self,
        plan: ReconcilePlan,
        apply_result: ReconcileApplyResult,
        verification: ReconcileVerification,
        context: object,
    ) -> None: ...


class ResourceReconciler:
    """Run one or more resource adapters through the reconcile lifecycle."""

    def run(
        self,
        adapter: ResourceAdapter,
        context: object,
        *,
        preview: bool = False,
    ) -> ReconcileRun:
        """Run inspect and plan, then optionally apply and verify."""
        inspection = adapter.inspect(context)
        plan = adapter.plan(inspection, context)

        if preview:
            return ReconcileRun(
                resource_name=adapter.name,
                inspection=inspection,
                plan=plan,
                preview=True,
            )

        try:
            apply_result = adapter.apply(plan, context)
            verification = adapter.verify(apply_result, context)
        except Exception as exc:
            adapter.rollback(plan, context, exc)
            raise

        if not verification.passed:
            adapter.rollback(plan, context, verification)
            return ReconcileRun(
                resource_name=adapter.name,
                inspection=inspection,
                plan=plan,
                apply_result=apply_result,
                verification=verification,
                rolled_back=True,
            )

        adapter.finalize(plan, apply_result, verification, context)
        return ReconcileRun(
            resource_name=adapter.name,
            inspection=inspection,
            plan=plan,
            apply_result=apply_result,
            verification=verification,
        )

    def run_all(
        self,
        adapters: list[ResourceAdapter],
        context: object,
        *,
        preview: bool = False,
    ) -> list[ReconcileRun]:
        """Run adapters in order and return their lifecycle records."""
        return [self.run(adapter, context, preview=preview) for adapter in adapters]
