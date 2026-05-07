"""Unit tests for the shared resource reconciler core."""

from __future__ import annotations

import pytest

from ai_engineering.reconciler import (
    ReconcileAction,
    ReconcileApplyResult,
    ReconcileInspection,
    ReconcilePlan,
    ReconcileVerification,
    ResourceReconciler,
)


class _Adapter:
    def __init__(self, *, fail_apply: bool = False, fail_verify: bool = False) -> None:
        self.calls: list[str] = []
        self.fail_apply = fail_apply
        self.fail_verify = fail_verify

    @property
    def name(self) -> str:
        return "test-resource"

    def inspect(self, context: object) -> ReconcileInspection:
        self.calls.append("inspect")
        return ReconcileInspection(resource_name=self.name, payload={"exists": True})

    def plan(self, inspection: ReconcileInspection, context: object) -> ReconcilePlan:
        self.calls.append("plan")
        return ReconcilePlan(
            resource_name=self.name,
            actions=[
                ReconcileAction(
                    action_id="test-resource:1",
                    action_type="update",
                    resource="test-resource",
                    reason="drift detected",
                )
            ],
        )

    def apply(self, plan: ReconcilePlan, context: object) -> ReconcileApplyResult:
        self.calls.append("apply")
        if self.fail_apply:
            msg = "apply failed"
            raise OSError(msg)
        return ReconcileApplyResult(
            resource_name=self.name,
            applied_actions=[action.action_id for action in plan.actions],
        )

    def verify(
        self,
        apply_result: ReconcileApplyResult,
        context: object,
    ) -> ReconcileVerification:
        self.calls.append("verify")
        return ReconcileVerification(
            resource_name=self.name,
            passed=not self.fail_verify,
            errors=["postcondition failed"] if self.fail_verify else [],
        )

    def rollback(
        self,
        plan: ReconcilePlan,
        context: object,
        reason: BaseException | ReconcileVerification,
    ) -> None:
        self.calls.append("rollback")

    def finalize(
        self,
        plan: ReconcilePlan,
        apply_result: ReconcileApplyResult,
        verification: ReconcileVerification,
        context: object,
    ) -> None:
        self.calls.append("finalize")


def test_preview_is_inspect_and_plan_only() -> None:
    adapter = _Adapter()

    run = ResourceReconciler().run(adapter, object(), preview=True)

    assert run.preview is True
    assert run.apply_result is None
    assert run.verification is None
    assert adapter.calls == ["inspect", "plan"]


def test_apply_runs_postcondition_verification_and_finalize() -> None:
    adapter = _Adapter()

    run = ResourceReconciler().run(adapter, object())

    assert run.verification is not None
    assert run.verification.passed is True
    assert run.rolled_back is False
    assert adapter.calls == ["inspect", "plan", "apply", "verify", "finalize"]


def test_apply_exception_triggers_rollback() -> None:
    adapter = _Adapter(fail_apply=True)

    with pytest.raises(OSError, match="apply failed"):
        ResourceReconciler().run(adapter, object())

    assert adapter.calls == ["inspect", "plan", "apply", "rollback"]


def test_verification_failure_triggers_rollback_without_finalize() -> None:
    adapter = _Adapter(fail_verify=True)

    run = ResourceReconciler().run(adapter, object())

    assert run.rolled_back is True
    assert run.verification is not None
    assert run.verification.errors == ["postcondition failed"]
    assert adapter.calls == ["inspect", "plan", "apply", "verify", "rollback"]
