"""RED tests for spec-117 HX-04 T-3.1 -- adapter parity over the kernel.

These tests pin the first adapter-convergence contract for HX-04. The shared
kernel contract now exists in ``policy.orchestrator``, but the gate CLI hook
subcommands and workflow-helper entry points still route through the legacy
``policy.gates.run_gate`` engine.

T-3.1 captures the required RED state before T-3.2 moves the adapters:

1. Generated git hooks must keep targeting the ``ai-eng gate ...`` CLI adapter
   boundary (hook adapter parity invariant).
2. ``ai-eng gate pre-commit`` must route through the kernel-backed adapter, not
   the legacy gate engine.
3. ``ai-eng gate pre-push`` must route through the kernel-backed adapter, not
   the legacy gate engine.
4. ``ai-eng gate all`` must route its pre-commit and pre-push helper flow
   through the kernel-backed adapter, not the legacy gate engine.
5. ``policy.gates.run_gate`` must begin surfacing deprecation behaviour so the
   remaining legacy path is explicit rather than silent.

TDD CONSTRAINT: this file is IMMUTABLE after HX-04 T-3.1 lands. T-3.2 may only
introduce production behaviour that satisfies these assertions.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app
from ai_engineering.hooks.manager import generate_bash_hook
from ai_engineering.state.models import GateFindingsDocument, GateHook

runner = CliRunner()


def _seed_target(tmp_path: Path) -> Path:
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".ai-engineering" / "specs").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _make_document(*, produced_by: str = "ai-commit") -> GateFindingsDocument:
    return GateFindingsDocument.model_validate(
        {
            "schema": "ai-engineering/gate-findings/v1",
            "session_id": str(uuid.uuid4()),
            "produced_by": produced_by,
            "produced_at": datetime.now(UTC).isoformat(),
            "branch": "feature/hx04",
            "commit_sha": "0" * 40,
            "findings": [],
            "auto_fixed": [],
            "cache_hits": [],
            "cache_misses": [],
            "wall_clock_ms": {
                "wave1_fixers": 10,
                "wave2_checkers": 20,
                "total": 30,
            },
        }
    )


def test_generated_hooks_keep_targeting_gate_cli_adapter_boundary() -> None:
    pre_commit = generate_bash_hook(GateHook.PRE_COMMIT)
    pre_push = generate_bash_hook(GateHook.PRE_PUSH)

    assert "ai-eng gate pre-commit" in pre_commit
    assert "ai-eng gate pre-push" in pre_push


def test_gate_pre_commit_routes_through_kernel_adapter_not_legacy_engine(tmp_path: Path) -> None:
    target = _seed_target(tmp_path)
    document = _make_document(produced_by="ai-commit")

    with (
        patch(
            "ai_engineering.cli_commands.gate.run_orchestrator_gate", return_value=document
        ) as kernel_run,
        patch(
            "ai_engineering.policy.gates.run_gate",
            side_effect=AssertionError("legacy gate engine must not be used by gate pre-commit"),
        ),
    ):
        app = create_app()
        result = runner.invoke(app, ["gate", "pre-commit", "--target", str(target)])

    assert result.exit_code == 0, (
        "gate pre-commit must route through the kernel-backed adapter and exit 0 on a clean document; "
        f"got exit_code={result.exit_code} output={result.output!r}"
    )
    assert kernel_run.call_count == 1


def test_gate_pre_push_routes_through_kernel_adapter_not_legacy_engine(tmp_path: Path) -> None:
    target = _seed_target(tmp_path)
    document = _make_document(produced_by="ai-pr")

    with (
        patch(
            "ai_engineering.cli_commands.gate.run_orchestrator_gate", return_value=document
        ) as kernel_run,
        patch(
            "ai_engineering.policy.gates.run_gate",
            side_effect=AssertionError("legacy gate engine must not be used by gate pre-push"),
        ),
    ):
        app = create_app()
        result = runner.invoke(app, ["gate", "pre-push", "--target", str(target)])

    assert result.exit_code == 0, (
        "gate pre-push must route through the kernel-backed adapter and exit 0 on a clean document; "
        f"got exit_code={result.exit_code} output={result.output!r}"
    )
    assert kernel_run.call_count == 1


def test_gate_commit_msg_routes_through_thin_adapter_not_legacy_engine(tmp_path: Path) -> None:
    target = _seed_target(tmp_path)
    msg_file = target / ".git" / "COMMIT_EDITMSG"
    msg_file.parent.mkdir(parents=True, exist_ok=True)
    msg_file.write_text("fix: adapter cutover", encoding="utf-8")

    with (
        patch(
            "ai_engineering.policy.gates.run_gate",
            side_effect=AssertionError("legacy gate engine must not be used by gate commit-msg"),
        ),
        patch("ai_engineering.policy.checks.branch_protection.check_branch_protection"),
        patch("ai_engineering.policy.checks.branch_protection.check_hook_integrity"),
        patch("ai_engineering.policy.checks.branch_protection.check_version_deprecation"),
    ):
        app = create_app()
        result = runner.invoke(
            app,
            ["gate", "commit-msg", str(msg_file), "--target", str(target)],
        )

    assert result.exit_code == 0, (
        "gate commit-msg must route through a thin adapter and exit 0 on a valid message; "
        f"got exit_code={result.exit_code} output={result.output!r}"
    )


def test_gate_all_routes_workflow_helpers_through_kernel_adapter(tmp_path: Path) -> None:
    target = _seed_target(tmp_path)
    document = _make_document(produced_by="ai-commit")

    with (
        patch(
            "ai_engineering.cli_commands.gate.run_orchestrator_gate", return_value=document
        ) as kernel_run,
        patch(
            "ai_engineering.policy.gates.run_gate",
            side_effect=AssertionError("legacy gate engine must not be used by gate all"),
        ),
        patch("ai_engineering.cli_commands.gate._check_risk_inline", return_value=False),
    ):
        app = create_app()
        result = runner.invoke(app, ["gate", "all", "--target", str(target)])

    assert result.exit_code == 0, (
        "gate all must keep its helper flow on the kernel-backed adapter path; "
        f"got exit_code={result.exit_code} output={result.output!r}"
    )
    assert kernel_run.call_count >= 2, (
        "gate all should exercise the kernel-backed adapter for both pre-commit and pre-push parity"
    )


def test_legacy_policy_gates_run_gate_emits_deprecation_warning(tmp_path: Path) -> None:
    from ai_engineering.policy import gates as legacy_gates

    target = _seed_target(tmp_path)

    with (
        patch("ai_engineering.policy.checks.branch_protection.check_branch_protection"),
        patch("ai_engineering.policy.checks.branch_protection.check_hook_integrity"),
        patch("ai_engineering.policy.checks.branch_protection.check_version_deprecation"),
        patch("ai_engineering.policy.gates._run_pre_commit_checks"),
        patch("ai_engineering.policy.gates.emit_gate_event"),
        pytest.warns(DeprecationWarning, match="legacy gate engine|deprecated"),
    ):
        legacy_gates.run_gate(GateHook.PRE_COMMIT, target)
