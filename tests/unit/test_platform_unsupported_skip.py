"""Unit tests for platform_unsupported skip behaviour (T-2.9 RED + T-2.10 GREEN).

Spec D-101-03 (tool-level) + D-101-13 (stack-level) define how the installer
treats tools and stacks declared incompatible with the current OS:

* **Tool-level** (``tool.platform_unsupported``): the named tool is skipped
  on listed OSes; the per-tool record carries
  ``state: skipped_platform_unsupported``.
* **Stack-level** (``stack.platform_unsupported_stack``): every tool in the
  stack is skipped on listed OSes; each tool's per-tool record carries
  ``state: skipped_platform_unsupported_stack``.

The tests in this file exercise :class:`ToolsPhase` directly so the behaviour
is verifiable independent of the higher-level pipeline. Each test mocks
``platform.system`` to drive the OS branch and asserts the resulting
``InstallState.required_tools_state`` map carries the correct enum values.

Layer 1 (``TestToolLevelSkip``) targets D-101-03 -- the canonical fixture
declares ``semgrep`` as ``platform_unsupported: [windows]``. On Windows the
phase MUST skip semgrep with ``state: skipped_platform_unsupported``; on
darwin/linux it MUST attempt the install (the install path is mocked).

Layer 2 (``TestStackLevelSkip``) targets D-101-13 -- the swift stack carries
``platform_unsupported_stack: [linux, windows]``. On those OSes every swift
tool MUST be recorded as ``skipped_platform_unsupported_stack``; on darwin
the phase MUST attempt the normal install.

Persistence layer: the tests assert the post-phase ``install-state.json``
on disk reflects the skip state. T-2.10 wires ``ToolsPhase.execute`` to
persist mutated state so doctor + downstream consumers see the records.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:  # pragma: no cover - typing only
    pass


FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "test_manifests"
    / "spec101_required_tools.yml"
)


# ``platform.system()`` returns proper-case names; the loader normalises to
# the lower-case :class:`Platform` enum keys.
_PLATFORM_SYSTEM: dict[str, str] = {
    "darwin": "Darwin",
    "linux": "Linux",
    "windows": "Windows",
}


@pytest.fixture()
def fixture_manifest_root(tmp_path: Path) -> Path:
    """Stage the canonical spec-101 manifest fixture into a temp project root."""
    ai_dir = tmp_path / ".ai-engineering"
    ai_dir.mkdir()
    (ai_dir / "state").mkdir()
    target = ai_dir / "manifest.yml"
    shutil.copyfile(FIXTURE_PATH, target)
    return tmp_path


def _read_install_state(project_root: Path) -> dict[str, object]:
    """Return the install_state payload as a dict.

    Spec-125 D-125-01: install_state moved from
    ``install-state.json`` to the ``install_state`` singleton row in
    state.db. Probe the canonical row via the repository reader.
    """
    from ai_engineering.state.repository import DurableStateRepository

    state = DurableStateRepository(project_root).load_install_state()
    return state.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Layer 1 -- tool-level platform_unsupported (D-101-03)
# ---------------------------------------------------------------------------


class TestToolLevelSkip:
    """A tool with ``platform_unsupported: [<current_os>]`` must be skipped."""

    def test_semgrep_skipped_on_windows(
        self,
        fixture_manifest_root: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """semgrep declares ``platform_unsupported: [windows]`` -> skip on win."""
        monkeypatch.setattr("platform.system", lambda: _PLATFORM_SYSTEM["windows"])

        from ai_engineering.installer.phases import InstallContext, InstallMode
        from ai_engineering.installer.phases.state import StatePhase
        from ai_engineering.installer.phases.tools import ToolsPhase

        ctx = InstallContext(
            target=fixture_manifest_root,
            mode=InstallMode.INSTALL,
            providers=["claude-code"],
            vcs_provider="github",
            stacks=["python"],
            ides=["terminal"],
        )

        # State phase must have run first so install-state.json exists.
        state_phase = StatePhase()
        state_phase.execute(state_phase.plan(ctx), ctx)

        tools_phase = ToolsPhase()
        tools_phase.execute(tools_phase.plan(ctx), ctx)

        state_payload = _read_install_state(fixture_manifest_root)
        required_tools_state = state_payload.get("required_tools_state", {})
        assert isinstance(required_tools_state, dict)

        record = required_tools_state.get("semgrep")
        assert record is not None, (
            "semgrep must appear in required_tools_state on windows; "
            f"got keys: {sorted(required_tools_state.keys())!r}"
        )
        assert record.get("state") == "skipped_platform_unsupported", (
            f"semgrep state must be 'skipped_platform_unsupported' on windows; "
            f"got {record.get('state')!r}"
        )

    @pytest.mark.parametrize(
        "current_os",
        [pytest.param("darwin", id="darwin"), pytest.param("linux", id="linux")],
    )
    def test_semgrep_not_skipped_on_supported_os(
        self,
        fixture_manifest_root: Path,
        monkeypatch: pytest.MonkeyPatch,
        current_os: str,
    ) -> None:
        """semgrep is supported on darwin/linux -> not recorded as skipped."""
        monkeypatch.setattr("platform.system", lambda: _PLATFORM_SYSTEM[current_os])

        from ai_engineering.installer.phases import InstallContext, InstallMode
        from ai_engineering.installer.phases.state import StatePhase
        from ai_engineering.installer.phases.tools import ToolsPhase

        ctx = InstallContext(
            target=fixture_manifest_root,
            mode=InstallMode.INSTALL,
            providers=["claude-code"],
            vcs_provider="github",
            stacks=["python"],
            ides=["terminal"],
        )
        state_phase = StatePhase()
        state_phase.execute(state_phase.plan(ctx), ctx)

        tools_phase = ToolsPhase()
        tools_phase.execute(tools_phase.plan(ctx), ctx)

        state_payload = _read_install_state(fixture_manifest_root)
        required_tools_state = state_payload.get("required_tools_state", {})
        assert isinstance(required_tools_state, dict)

        record = required_tools_state.get("semgrep")
        if record is not None:
            assert record.get("state") != "skipped_platform_unsupported", (
                f"semgrep must NOT be skipped on {current_os}; got state {record.get('state')!r}"
            )


# ---------------------------------------------------------------------------
# Layer 2 -- stack-level platform_unsupported_stack (D-101-13)
# ---------------------------------------------------------------------------


class TestStackLevelSkip:
    """All tools in a stack with ``platform_unsupported_stack`` are skipped."""

    @pytest.mark.parametrize(
        "current_os",
        [
            pytest.param("linux", id="linux"),
            pytest.param("windows", id="windows"),
        ],
    )
    def test_all_swift_tools_marked_skipped_stack(
        self,
        fixture_manifest_root: Path,
        monkeypatch: pytest.MonkeyPatch,
        current_os: str,
    ) -> None:
        """Each swift tool must record ``skipped_platform_unsupported_stack``."""
        monkeypatch.setattr("platform.system", lambda: _PLATFORM_SYSTEM[current_os])

        from ai_engineering.installer.phases import InstallContext, InstallMode
        from ai_engineering.installer.phases.state import StatePhase
        from ai_engineering.installer.phases.tools import ToolsPhase

        ctx = InstallContext(
            target=fixture_manifest_root,
            mode=InstallMode.INSTALL,
            providers=["claude-code"],
            vcs_provider="github",
            stacks=["swift"],
            ides=["terminal"],
        )
        state_phase = StatePhase()
        state_phase.execute(state_phase.plan(ctx), ctx)

        tools_phase = ToolsPhase()
        tools_phase.execute(tools_phase.plan(ctx), ctx)

        state_payload = _read_install_state(fixture_manifest_root)
        required_tools_state = state_payload.get("required_tools_state", {})
        assert isinstance(required_tools_state, dict)

        for tool in ("swiftlint", "swift-format"):
            record = required_tools_state.get(tool)
            assert record is not None, (
                f"swift tool {tool!r} must appear in required_tools_state on "
                f"{current_os}; got keys: {sorted(required_tools_state.keys())!r}"
            )
            assert record.get("state") == "skipped_platform_unsupported_stack", (
                f"swift tool {tool!r} state must be "
                "'skipped_platform_unsupported_stack' on "
                f"{current_os}; got {record.get('state')!r}"
            )

    def test_swift_tools_attempted_on_darwin(
        self,
        fixture_manifest_root: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """On darwin the swift stack runs the normal install path -- not skip."""
        monkeypatch.setattr("platform.system", lambda: _PLATFORM_SYSTEM["darwin"])

        from ai_engineering.installer.mechanisms import InstallResult as MechInstallResult
        from ai_engineering.installer.phases import InstallContext, InstallMode
        from ai_engineering.installer.phases.state import StatePhase
        from ai_engineering.installer.phases.tools import ToolsPhase

        # Patch every BrewMechanism.install call to return a happy outcome
        # without spawning a real subprocess.
        def _stub_install(self: object) -> object:
            return MechInstallResult(
                failed=False,
                stderr="",
                mechanism="BrewMechanism",
                version="1.0.0",
            )

        monkeypatch.setattr(
            "ai_engineering.installer.mechanisms.BrewMechanism.install",
            _stub_install,
        )

        ctx = InstallContext(
            target=fixture_manifest_root,
            mode=InstallMode.INSTALL,
            providers=["claude-code"],
            vcs_provider="github",
            stacks=["swift"],
            ides=["terminal"],
        )
        state_phase = StatePhase()
        state_phase.execute(state_phase.plan(ctx), ctx)

        tools_phase = ToolsPhase()
        tools_phase.execute(tools_phase.plan(ctx), ctx)

        state_payload = _read_install_state(fixture_manifest_root)
        required_tools_state = state_payload.get("required_tools_state", {})
        assert isinstance(required_tools_state, dict)

        for tool in ("swiftlint", "swift-format"):
            record = required_tools_state.get(tool)
            assert record is not None, (
                f"swift tool {tool!r} must appear on darwin; got keys "
                f"{sorted(required_tools_state.keys())!r}"
            )
            assert record.get("state") != "skipped_platform_unsupported_stack", (
                f"swift tool {tool!r} must NOT be skipped on darwin; "
                f"got state {record.get('state')!r}"
            )
            assert record.get("state") != "skipped_platform_unsupported", (
                f"swift tool {tool!r} must NOT be tool-skipped on darwin; "
                f"got state {record.get('state')!r}"
            )


# ---------------------------------------------------------------------------
# Layer 3 -- both levels coexist (mixed declaration on a multi-stack project)
# ---------------------------------------------------------------------------


class TestBothLevelsCoexist:
    """A project with both a tool-skip and a stack-skip records both kinds."""

    @pytest.mark.parametrize(
        "current_os",
        [pytest.param("linux", id="linux"), pytest.param("windows", id="windows")],
    )
    def test_swift_stack_skip_and_baseline_unaffected(
        self,
        fixture_manifest_root: Path,
        monkeypatch: pytest.MonkeyPatch,
        current_os: str,
    ) -> None:
        """Swift stack tools record stack-skip; baseline tools install normally.

        On windows, semgrep is tool-level skipped (D-101-03) AND swift is
        stack-level skipped (D-101-13). Both records coexist.
        """
        monkeypatch.setattr("platform.system", lambda: _PLATFORM_SYSTEM[current_os])

        from ai_engineering.installer.phases import InstallContext, InstallMode
        from ai_engineering.installer.phases.state import StatePhase
        from ai_engineering.installer.phases.tools import ToolsPhase

        ctx = InstallContext(
            target=fixture_manifest_root,
            mode=InstallMode.INSTALL,
            providers=["claude-code"],
            vcs_provider="github",
            stacks=["swift"],
            ides=["terminal"],
        )
        state_phase = StatePhase()
        state_phase.execute(state_phase.plan(ctx), ctx)

        tools_phase = ToolsPhase()
        tools_phase.execute(tools_phase.plan(ctx), ctx)

        state_payload = _read_install_state(fixture_manifest_root)
        required_tools_state = state_payload.get("required_tools_state", {})
        assert isinstance(required_tools_state, dict)

        # Stack-level skip records present.
        for tool in ("swiftlint", "swift-format"):
            record = required_tools_state.get(tool)
            assert record is not None, (
                f"swift tool {tool!r} missing on {current_os}; "
                f"keys: {sorted(required_tools_state.keys())!r}"
            )
            assert record.get("state") == "skipped_platform_unsupported_stack", (
                f"swift tool {tool!r} state must be "
                f"'skipped_platform_unsupported_stack' on {current_os}; "
                f"got {record.get('state')!r}"
            )

        # Tool-level skip on windows specifically: semgrep is unsupported.
        if current_os == "windows":
            semgrep_record = required_tools_state.get("semgrep")
            assert semgrep_record is not None
            assert semgrep_record.get("state") == "skipped_platform_unsupported"
