"""RED tests for spec-101 T-0.13.

Covers the upcoming extensions to ``state/models.py`` (delivered in T-0.14):

- ``ToolInstallState`` enum with five members:
  ``installed``, ``skipped_platform_unsupported``,
  ``skipped_platform_unsupported_stack``, ``not_installed_project_local``,
  ``failed_needs_manual``.
- ``ToolInstallRecord`` Pydantic model with fields ``state``, ``mechanism``,
  ``version``, ``verified_at``, ``os_release``.
- ``PythonEnvMode`` enum with ``uv-tool``, ``venv``, ``shared-parent``.
- ``InstallState.required_tools_state`` (default ``{}``) and
  ``InstallState.python_env_mode_recorded`` (default ``None``).
- JSON round-trip preserves all values (including the new fields).
- Loading legacy state JSON without ``required_tools_state`` defaults the
  field to ``{}`` (the file-rename migration is exercised separately by
  T-0.15/0.16).

These tests intentionally fail until T-0.14 lands. The carve-out behaviour
for ``not_installed_project_local`` is documented at spec-101 D-101-15 /
D-101-01: ``scope: project_local`` tools are catalogued in
``required_tools`` but never installed by the framework.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ai_engineering.state.models import (
    InstallState,
    PythonEnvMode,
    ToolInstallRecord,
    ToolInstallState,
)

# -- ToolInstallState enum ------------------------------------------------


class TestToolInstallStateEnum:
    """All five enum members exist and use the canonical string values."""

    def test_installed_member(self) -> None:
        assert ToolInstallState.INSTALLED.value == "installed"

    def test_skipped_platform_unsupported_member(self) -> None:
        assert ToolInstallState.SKIPPED_PLATFORM_UNSUPPORTED.value == "skipped_platform_unsupported"

    def test_skipped_platform_unsupported_stack_member(self) -> None:
        assert (
            ToolInstallState.SKIPPED_PLATFORM_UNSUPPORTED_STACK.value
            == "skipped_platform_unsupported_stack"
        )

    def test_not_installed_project_local_member(self) -> None:
        # D-101-15 / D-101-01 carve-out: scope=project_local tools are
        # catalogued but the framework never installs them.
        assert ToolInstallState.NOT_INSTALLED_PROJECT_LOCAL.value == "not_installed_project_local"

    def test_failed_needs_manual_member(self) -> None:
        assert ToolInstallState.FAILED_NEEDS_MANUAL.value == "failed_needs_manual"

    def test_enum_has_exactly_five_members(self) -> None:
        """Guard against accidentally adding/removing values."""
        assert len(list(ToolInstallState)) == 5

    def test_enum_member_set(self) -> None:
        """Exact set of canonical string values."""
        assert {member.value for member in ToolInstallState} == {
            "installed",
            "skipped_platform_unsupported",
            "skipped_platform_unsupported_stack",
            "not_installed_project_local",
            "failed_needs_manual",
        }


# -- ToolInstallRecord model ---------------------------------------------


class TestToolInstallRecordConstruction:
    """Field shape and validation for the new record model."""

    def test_full_record_constructs_successfully(self) -> None:
        # Arrange
        ts = datetime(2026, 4, 24, 9, 30, 0, tzinfo=UTC)

        # Act
        record = ToolInstallRecord(
            state="installed",
            mechanism="brew",
            version="8.18.4",
            verified_at=ts,
            os_release="14.4",
        )

        # Assert
        assert record.state == ToolInstallState.INSTALLED
        assert record.mechanism == "brew"
        assert record.version == "8.18.4"
        assert record.verified_at == ts
        assert record.os_release == "14.4"

    def test_record_accepts_enum_instance_for_state(self) -> None:
        record = ToolInstallRecord(
            state=ToolInstallState.FAILED_NEEDS_MANUAL,
            mechanism="manual",
            version=None,
            verified_at=datetime(2026, 4, 24, tzinfo=UTC),
            os_release="14.4",
        )
        assert record.state == ToolInstallState.FAILED_NEEDS_MANUAL

    def test_version_is_optional(self) -> None:
        """version may be None when the tool failed to install or was skipped."""
        record = ToolInstallRecord(
            state="skipped_platform_unsupported",
            mechanism="none",
            version=None,
            verified_at=datetime(2026, 4, 24, tzinfo=UTC),
            os_release="22.04",
        )
        assert record.version is None

    def test_os_release_is_optional(self) -> None:
        """os_release may be None on platforms where it cannot be resolved."""
        record = ToolInstallRecord(
            state="not_installed_project_local",
            mechanism="project_local",
            version=None,
            verified_at=datetime(2026, 4, 24, tzinfo=UTC),
            os_release=None,
        )
        assert record.os_release is None

    def test_invalid_state_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            ToolInstallRecord(
                state="totally_made_up_value",
                mechanism="brew",
                version="1.0.0",
                verified_at=datetime(2026, 4, 24, tzinfo=UTC),
                os_release="14.4",
            )

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            ToolInstallRecord(  # type: ignore[call-arg]
                state="installed",
                mechanism="brew",
                version="1.0.0",
                # verified_at intentionally missing
                os_release="14.4",
            )

    def test_record_roundtrips_through_json(self) -> None:
        """model_dump_json + model_validate_json preserves all fields."""
        ts = datetime(2026, 4, 24, 9, 30, 0, tzinfo=UTC)
        record = ToolInstallRecord(
            state="installed",
            mechanism="brew",
            version="8.18.4",
            verified_at=ts,
            os_release="14.4",
        )

        restored = ToolInstallRecord.model_validate_json(record.model_dump_json())

        assert restored == record


# -- PythonEnvMode enum --------------------------------------------------


class TestPythonEnvModeEnum:
    """python_env.mode values from manifest schema."""

    def test_uv_tool_member(self) -> None:
        assert PythonEnvMode.UV_TOOL.value == "uv-tool"

    def test_venv_member(self) -> None:
        assert PythonEnvMode.VENV.value == "venv"

    def test_shared_parent_member(self) -> None:
        assert PythonEnvMode.SHARED_PARENT.value == "shared-parent"

    def test_enum_has_exactly_three_members(self) -> None:
        assert len(list(PythonEnvMode)) == 3


# -- InstallState extensions ---------------------------------------------


class TestInstallStateNewFields:
    """The two new fields on InstallState."""

    def test_required_tools_state_defaults_to_empty_dict(self) -> None:
        state = InstallState(installed_at=datetime(2026, 4, 24, tzinfo=UTC))
        assert state.required_tools_state == {}

    def test_python_env_mode_recorded_defaults_to_none(self) -> None:
        state = InstallState(installed_at=datetime(2026, 4, 24, tzinfo=UTC))
        assert state.python_env_mode_recorded is None

    def test_required_tools_state_accepts_record_dict(self) -> None:
        # Arrange
        ts = datetime(2026, 4, 24, 9, 30, 0, tzinfo=UTC)
        record = ToolInstallRecord(
            state="installed",
            mechanism="brew",
            version="8.18.4",
            verified_at=ts,
            os_release="14.4",
        )

        # Act
        state = InstallState(
            installed_at=ts,
            required_tools_state={"gh": record},
        )

        # Assert
        assert "gh" in state.required_tools_state
        assert state.required_tools_state["gh"].mechanism == "brew"
        assert state.required_tools_state["gh"].state == ToolInstallState.INSTALLED

    def test_python_env_mode_recorded_accepts_enum(self) -> None:
        state = InstallState(
            installed_at=datetime(2026, 4, 24, tzinfo=UTC),
            python_env_mode_recorded=PythonEnvMode.UV_TOOL,
        )
        assert state.python_env_mode_recorded == PythonEnvMode.UV_TOOL

    def test_python_env_mode_recorded_accepts_string(self) -> None:
        """StrEnum values may be supplied as their string form."""
        state = InstallState(
            installed_at=datetime(2026, 4, 24, tzinfo=UTC),
            python_env_mode_recorded="shared-parent",
        )
        assert state.python_env_mode_recorded == PythonEnvMode.SHARED_PARENT

    def test_python_env_mode_recorded_rejects_invalid(self) -> None:
        with pytest.raises(ValidationError):
            InstallState(
                installed_at=datetime(2026, 4, 24, tzinfo=UTC),
                python_env_mode_recorded="conda",
            )


# -- Round-trip with new fields ------------------------------------------


class TestInstallStateRoundtripWithNewFields:
    """JSON round-trip preserves required_tools_state and python_env_mode_recorded."""

    def test_full_roundtrip_preserves_records_and_mode(self) -> None:
        # Arrange
        ts = datetime(2026, 4, 24, 9, 30, 0, tzinfo=UTC)
        records = {
            "gh": ToolInstallRecord(
                state="installed",
                mechanism="brew",
                version="2.62.0",
                verified_at=ts,
                os_release="14.4",
            ),
            "swift": ToolInstallRecord(
                state="skipped_platform_unsupported_stack",
                mechanism="none",
                version=None,
                verified_at=ts,
                os_release="22.04",
            ),
            "eslint": ToolInstallRecord(
                state="not_installed_project_local",
                mechanism="project_local",
                version=None,
                verified_at=ts,
                os_release=None,
            ),
            "semgrep": ToolInstallRecord(
                state="failed_needs_manual",
                mechanism="pip",
                version=None,
                verified_at=ts,
                os_release="14.4",
            ),
            "az": ToolInstallRecord(
                state="skipped_platform_unsupported",
                mechanism="none",
                version=None,
                verified_at=ts,
                os_release="14.4",
            ),
        }
        state = InstallState(
            installed_at=ts,
            required_tools_state=records,
            python_env_mode_recorded=PythonEnvMode.UV_TOOL,
        )

        # Act
        json_str = state.model_dump_json()
        restored = InstallState.model_validate_json(json_str)

        # Assert
        assert restored.python_env_mode_recorded == PythonEnvMode.UV_TOOL
        assert set(restored.required_tools_state.keys()) == set(records.keys())
        assert restored.required_tools_state["gh"].state == ToolInstallState.INSTALLED
        assert restored.required_tools_state["gh"].version == "2.62.0"
        assert (
            restored.required_tools_state["swift"].state
            == ToolInstallState.SKIPPED_PLATFORM_UNSUPPORTED_STACK
        )
        assert (
            restored.required_tools_state["eslint"].state
            == ToolInstallState.NOT_INSTALLED_PROJECT_LOCAL
        )
        assert restored.required_tools_state["eslint"].mechanism == "project_local"
        assert restored.required_tools_state["eslint"].os_release is None
        assert (
            restored.required_tools_state["semgrep"].state == ToolInstallState.FAILED_NEEDS_MANUAL
        )
        assert (
            restored.required_tools_state["az"].state
            == ToolInstallState.SKIPPED_PLATFORM_UNSUPPORTED
        )
        # Equality across the whole state
        assert restored == state

    def test_roundtrip_with_default_new_fields(self) -> None:
        """A state with no records or mode round-trips with defaults intact."""
        ts = datetime(2026, 4, 24, tzinfo=UTC)
        state = InstallState(installed_at=ts)

        restored = InstallState.model_validate_json(state.model_dump_json())

        assert restored.required_tools_state == {}
        assert restored.python_env_mode_recorded is None


# -- Legacy state without the new fields ---------------------------------


class TestInstallStateLegacyDefault:
    """Loading legacy JSON (pre T-0.14) defaults the new fields gracefully.

    The file-rename migration described in R-10 is owned by T-0.15/0.16
    (see ``state/service.py::load_install_state``); this test only covers
    Pydantic field defaults, exercised via ``model_validate``.
    """

    def test_legacy_json_missing_required_tools_state_defaults_empty(self) -> None:
        legacy_json = {
            "schema_version": "2.0",
            "installed_at": "2026-03-25T10:00:00Z",
            "vcs_provider": "github",
            "tooling": {},
            "platforms": {},
            "branch_policy": {"applied": False, "mode": "api"},
            "operational_readiness": {"status": "pending", "pending_steps": []},
            "release": {"last_version": "", "last_released_at": None},
        }

        state = InstallState.model_validate(legacy_json)

        assert state.required_tools_state == {}
        assert state.python_env_mode_recorded is None
