"""Integration test for spec-113 G-12 / D-113-10: doctor recovers external installs.

When the operator manually installs a tool (e.g. ``apk add jq`` on Alpine)
after the framework recorded ``failed_needs_manual``, the doctor must
re-evaluate, recognise the tool is now present, AND graduate the install-
state record to ``INSTALLED`` with ``mechanism="external"``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from ai_engineering.doctor.models import DoctorContext
from ai_engineering.doctor.phases import tools as doctor_tools
from ai_engineering.state.models import (
    InstallState,
    ToolInstallRecord,
    ToolInstallState,
    ToolScope,
    ToolSpec,
)


def _ctx(tmp_path: Path, install_state: InstallState) -> DoctorContext:
    state_dir = tmp_path / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return DoctorContext(
        target=tmp_path,
        install_state=install_state,
        manifest_config=None,
    )


def test_doctor_recovers_failed_needs_manual_to_installed_external(
    tmp_path: Path,
) -> None:
    """jq pre-recorded as failed_needs_manual + on-PATH + verifies => upgraded to INSTALLED."""
    state = InstallState(
        vcs_provider="github",
        required_tools_state={
            "jq": ToolInstallRecord(
                state=ToolInstallState.FAILED_NEEDS_MANUAL,
                mechanism="GitHubReleaseBinaryMechanism",
                version=None,
                verified_at=datetime.now(tz=UTC),
                os_release="alpine.3",
            )
        },
    )
    ctx = _ctx(tmp_path, state)

    # Probe: jq is on PATH and verify passes.
    with (
        patch.object(
            doctor_tools,
            "_probe_one_required_tool",
            return_value=True,
        ),
        patch.object(
            doctor_tools,
            "load_required_tools",
            return_value=[ToolSpec(name="jq", scope=ToolScope.USER_GLOBAL)],
        ),
    ):
        result = doctor_tools._check_required_tools(ctx)

    # No tools missing AND record upgraded.
    assert (
        "missing" not in result.message.lower()
        or "all required tools available" in result.message.lower()
    )
    record = state.required_tools_state["jq"]
    assert record.state == ToolInstallState.INSTALLED
    assert record.mechanism == "external"


def test_doctor_does_not_overwrite_already_installed_record(tmp_path: Path) -> None:
    """When the state already records INSTALLED, the doctor leaves it alone."""
    state = InstallState(
        required_tools_state={
            "ruff": ToolInstallRecord(
                state=ToolInstallState.INSTALLED,
                mechanism="UvToolMechanism",
                version="0.5.0",
                verified_at=datetime.now(tz=UTC),
                os_release="darwin.15",
            )
        }
    )
    ctx = _ctx(tmp_path, state)
    with (
        patch.object(doctor_tools, "_probe_one_required_tool", return_value=True),
        patch.object(
            doctor_tools,
            "load_required_tools",
            return_value=[ToolSpec(name="ruff", scope=ToolScope.USER_GLOBAL)],
        ),
    ):
        doctor_tools._check_required_tools(ctx)
    record = state.required_tools_state["ruff"]
    assert record.state == ToolInstallState.INSTALLED
    assert record.mechanism == "UvToolMechanism"  # unchanged


def test_doctor_keeps_missing_when_probe_fails(tmp_path: Path) -> None:
    """If the tool is still missing on PATH, the record stays as failed_needs_manual."""
    state = InstallState(
        required_tools_state={
            "jq": ToolInstallRecord(
                state=ToolInstallState.FAILED_NEEDS_MANUAL,
                mechanism="GitHubReleaseBinaryMechanism",
                version=None,
                verified_at=datetime.now(tz=UTC),
                os_release="alpine.3",
            )
        }
    )
    ctx = _ctx(tmp_path, state)
    with (
        patch.object(doctor_tools, "_probe_one_required_tool", return_value=False),
        patch.object(
            doctor_tools,
            "load_required_tools",
            return_value=[ToolSpec(name="jq", scope=ToolScope.USER_GLOBAL)],
        ),
    ):
        result = doctor_tools._check_required_tools(ctx)
    assert "jq" in result.message
    assert state.required_tools_state["jq"].state == ToolInstallState.FAILED_NEEDS_MANUAL


def test_doctor_persists_recovery_to_disk(tmp_path: Path) -> None:
    """The state.required_tools_state update is written back to install-state.json."""
    state = InstallState(
        required_tools_state={
            "jq": ToolInstallRecord(
                state=ToolInstallState.FAILED_NEEDS_MANUAL,
                mechanism="GitHubReleaseBinaryMechanism",
                version=None,
                verified_at=datetime.now(tz=UTC),
                os_release="alpine.3",
            )
        }
    )
    ctx = _ctx(tmp_path, state)

    with (
        patch.object(doctor_tools, "_probe_one_required_tool", return_value=True),
        patch.object(
            doctor_tools,
            "load_required_tools",
            return_value=[ToolSpec(name="jq", scope=ToolScope.USER_GLOBAL)],
        ),
    ):
        doctor_tools._check_required_tools(ctx)

    state_path = tmp_path / ".ai-engineering" / "state" / "install-state.json"
    assert state_path.exists(), "doctor must persist external-recovery to install-state.json"
    on_disk = json.loads(state_path.read_text(encoding="utf-8"))
    record = on_disk["required_tools_state"]["jq"]
    assert record["state"] == ToolInstallState.INSTALLED.value
    assert record["mechanism"] == "external"
