"""RED-phase tests for spec-101 T-1.15 -- swift stack skip on linux/windows.

Verifies the contract described in spec D-101-13:

* On linux/windows, the swift stack contributes ZERO tools and surfaces a
  ``skipped_platform_unsupported_stack`` marker (loader-level -- this is the
  Wave-4 ``state.manifest.load_required_tools`` mechanism, already in place).
* End-to-end: when ``PHASE_TOOLS`` runs against a project that declares the
  swift stack on linux/windows, the resulting ``install-state.json`` records
  per-tool ``ToolInstallRecord`` entries for ``swiftlint`` and ``swift-format``
  with ``state == "skipped_platform_unsupported_stack"``. (THIS path will fail
  RED until T-2.10 lands.)
* On darwin, swift IS supported -- the installer must invoke its normal
  per-tool install path rather than recording a skip.

Two layers of assertions:

1. ``TestLoaderLevelSkip`` -- already-passing (Wave-4) coverage of
   ``load_required_tools`` on linux/windows/darwin.
2. ``TestInstallerPhaseEndToEnd`` -- pending (Wave-2 / T-2.10) coverage that
   exercises ``ToolsPhase.execute`` and asserts ``install-state.json`` rows.

Per spec scope: this file MUST NOT modify ``state/manifest.py`` and MUST NOT
introduce installer-phase logic. Failure during RED is the intended outcome
for the end-to-end layer.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:  # pragma: no cover - typing only
    from collections.abc import Iterable

# ---------------------------------------------------------------------------
# Fixture wiring -- reuse the canonical spec-101 manifest fixture
# ---------------------------------------------------------------------------

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "test_manifests"
    / "spec101_required_tools.yml"
)

# Per spec.md D-101-01: swift stack tools (kept in sync with the canonical
# fixture). Importing from the fixture loader test module would create a
# cross-test coupling we explicitly avoid.
SWIFT_TOOLS: tuple[str, ...] = ("swiftlint", "swift-format")

# Baseline tools that MUST remain present even when swift is skipped (the
# skip is per-stack, not global).
BASELINE_TOOLS: tuple[str, ...] = ("gitleaks", "semgrep", "jq")

# Mapping from the parametric ``current_os`` value (lower-case, matching
# ``state.models.Platform``) onto the ``platform.system()`` style value used
# by ``platform.system`` (proper-case as returned by Python).
_PLATFORM_SYSTEM: dict[str, str] = {
    "darwin": "Darwin",
    "linux": "Linux",
    "windows": "Windows",
}

# OSes where swift is unsupported per the manifest fixture
# (``platform_unsupported_stack: [linux, windows]``).
SWIFT_UNSUPPORTED_OSES: tuple[str, ...] = ("linux", "windows")


@pytest.fixture()
def fixture_manifest_root(tmp_path: Path) -> Path:
    """Stage the canonical spec-101 manifest fixture into a temp project root.

    Returns the project root containing ``.ai-engineering/manifest.yml`` plus
    a fresh ``.ai-engineering/state/`` directory ready for install-state.json.
    """
    ai_dir = tmp_path / ".ai-engineering"
    ai_dir.mkdir()
    (ai_dir / "state").mkdir()
    target = ai_dir / "manifest.yml"
    shutil.copyfile(FIXTURE_PATH, target)
    return tmp_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _names(specs: Iterable[object]) -> list[str]:
    """Project a list of ``ToolSpec`` instances onto their ``.name`` field."""
    return [spec.name for spec in specs]  # type: ignore[attr-defined]


def _read_install_state_dict(project_root: Path) -> dict[str, object]:
    """Return the install_state payload as a dict.

    Spec-125 D-125-01: install_state moved from JSON to the
    ``install_state`` singleton row in state.db.
    """
    from ai_engineering.state.repository import DurableStateRepository

    state = DurableStateRepository(project_root).load_install_state()
    return state.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Layer 1 -- loader-level skip (Wave 4 -- already implemented)
# ---------------------------------------------------------------------------


class TestLoaderLevelSkip:
    """``load_required_tools`` correctly applies stack-level platform skip."""

    @pytest.mark.parametrize("current_os", SWIFT_UNSUPPORTED_OSES)
    def test_swift_on_unsupported_os_yields_no_swift_tools(
        self,
        fixture_manifest_root: Path,
        current_os: str,
    ) -> None:
        from ai_engineering.state.manifest import load_required_tools

        result = load_required_tools(
            ["swift"],
            root=fixture_manifest_root,
            current_os=current_os,
        )
        names = _names(result)

        for tool in SWIFT_TOOLS:
            assert tool not in names, (
                f"swift tool {tool!r} unexpectedly present on {current_os}; "
                "stack-level platform_unsupported_stack must filter it out"
            )

    @pytest.mark.parametrize("current_os", SWIFT_UNSUPPORTED_OSES)
    def test_swift_on_unsupported_os_keeps_baseline(
        self,
        fixture_manifest_root: Path,
        current_os: str,
    ) -> None:
        from ai_engineering.state.manifest import load_required_tools

        result = load_required_tools(
            ["swift"],
            root=fixture_manifest_root,
            current_os=current_os,
        )
        names = _names(result)

        for tool in BASELINE_TOOLS:
            assert tool in names, (
                f"baseline tool {tool!r} unexpectedly missing on {current_os}; "
                "stack skip must NOT drop baseline tools"
            )

    @pytest.mark.parametrize("current_os", SWIFT_UNSUPPORTED_OSES)
    def test_swift_skip_marker_surfaced(
        self,
        fixture_manifest_root: Path,
        current_os: str,
    ) -> None:
        from ai_engineering.state.manifest import load_required_tools

        result = load_required_tools(
            ["swift"],
            root=fixture_manifest_root,
            current_os=current_os,
        )

        # ``LoadResult.skipped_stacks`` is the Wave-4 surface for skip markers.
        assert hasattr(result, "skipped_stacks"), (
            "LoadResult must expose ``skipped_stacks`` for stacks dropped via "
            "platform_unsupported_stack"
        )
        skipped = list(result.skipped_stacks)
        assert len(skipped) == 1, (
            f"expected exactly one skip marker on {current_os}; got {skipped!r}"
        )
        marker = skipped[0]
        assert marker.stack == "swift", (
            f"skip marker must name the swift stack; got {marker.stack!r}"
        )
        assert marker.reason, "skip marker must carry the unsupported_reason from the manifest"

    def test_swift_on_darwin_includes_swift_tools(self, fixture_manifest_root: Path) -> None:
        from ai_engineering.state.manifest import load_required_tools

        result = load_required_tools(
            ["swift"],
            root=fixture_manifest_root,
            current_os="darwin",
        )
        names = _names(result)

        for tool in SWIFT_TOOLS:
            assert tool in names, (
                f"swift tool {tool!r} should be present on darwin where the stack is supported"
            )
        # No skip markers on the supported OS.
        assert list(result.skipped_stacks) == [], (
            "darwin must NOT produce any skip markers for the swift stack"
        )


# ---------------------------------------------------------------------------
# Layer 2 -- end-to-end installer phase (T-2.10 GREEN -- pending)
# ---------------------------------------------------------------------------


class TestInstallerPhaseEndToEnd:
    """``PHASE_TOOLS`` records swiftlint+swift-format skip on linux/windows.

    These tests fail RED until T-2.10 wires ``installer/phases/tools.py`` to
    the ``load_required_tools`` skip surface and persists per-tool
    ``ToolInstallRecord`` entries with state
    ``skipped_platform_unsupported_stack`` for the swift stack on
    unsupported OSes.
    """

    @pytest.mark.parametrize("current_os", SWIFT_UNSUPPORTED_OSES)
    def test_phase_tools_records_swift_tools_as_skipped_stack(
        self,
        fixture_manifest_root: Path,
        current_os: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Force Python's platform.system() to report the target OS so that the
        # ToolsPhase implementation observes the expected current_os. The
        # actual RED reason is that the phase does not yet read swift-stack
        # skip markers from load_required_tools and propagate them into
        # install-state.json.
        monkeypatch.setattr("platform.system", lambda: _PLATFORM_SYSTEM[current_os])

        # Defer imports to inside the test so the module-level pytest collect
        # does not fail if the implementation later tightens its imports.
        from ai_engineering.installer.phases import (
            InstallContext,
            InstallMode,
        )
        from ai_engineering.installer.phases.state import StatePhase
        from ai_engineering.installer.phases.tools import ToolsPhase

        # Stage state files via StatePhase so install-state.json exists before
        # the tools phase runs (canonical pipeline ordering -- state runs
        # before tools in PHASE_ORDER).
        ctx = InstallContext(
            target=fixture_manifest_root,
            mode=InstallMode.INSTALL,
            providers=["claude-code"],
            vcs_provider="github",
            stacks=["swift"],
            ides=["terminal"],
        )
        state_phase = StatePhase()
        state_plan = state_phase.plan(ctx)
        state_phase.execute(state_plan, ctx)

        tools_phase = ToolsPhase()
        plan = tools_phase.plan(ctx)
        tools_phase.execute(plan, ctx)

        # The per-tool ``required_tools_state`` block must contain entries for
        # each swift tool, each marked ``skipped_platform_unsupported_stack``.
        state_payload = _read_install_state_dict(fixture_manifest_root)
        required_tools_state = state_payload.get("required_tools_state")
        assert isinstance(required_tools_state, dict), (
            "install-state.json must carry a ``required_tools_state`` dict; "
            f"got {type(required_tools_state).__name__}"
        )

        for tool in SWIFT_TOOLS:
            assert tool in required_tools_state, (
                f"swift tool {tool!r} missing from required_tools_state on "
                f"{current_os}; the installer must record a skip entry per "
                "declared swift tool when the stack is platform-unsupported"
            )
            record = required_tools_state[tool]
            assert isinstance(record, dict), (
                f"required_tools_state[{tool!r}] must be a dict; got {type(record).__name__}"
            )
            assert record.get("state") == "skipped_platform_unsupported_stack", (
                f"required_tools_state[{tool!r}].state must be "
                "'skipped_platform_unsupported_stack' on "
                f"{current_os}; got {record.get('state')!r}"
            )

    def test_phase_tools_attempts_install_on_darwin(
        self,
        fixture_manifest_root: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # On macOS the swift stack is supported. The phase must NOT record a
        # skip; instead it must run the normal install path. We mock the
        # mechanism layer so the test stays hermetic and asserts the install
        # was *attempted*.
        monkeypatch.setattr("platform.system", lambda: _PLATFORM_SYSTEM["darwin"])

        from ai_engineering.installer.phases import (
            InstallContext,
            InstallMode,
        )
        from ai_engineering.installer.phases.state import StatePhase
        from ai_engineering.installer.phases.tools import ToolsPhase

        attempted: list[str] = []

        from ai_engineering.installer.mechanisms import (
            BrewMechanism,
        )
        from ai_engineering.installer.mechanisms import (
            InstallResult as MechInstallResult,
        )

        def _record_attempt(self: BrewMechanism) -> MechInstallResult:
            attempted.append(self.formula)
            return MechInstallResult(
                failed=False,
                stderr="",
                mechanism="BrewMechanism",
                version="1.0.0",
            )

        # T-2.10 routes installs via mechanism.install(); the swift tools'
        # darwin entry uses ``BrewMechanism``, so patch the mechanism's
        # install method directly. ``self.formula`` carries the swift tool
        # name (``swiftlint`` / ``swift-format``) per ``tool_registry.py``.
        monkeypatch.setattr(
            "ai_engineering.installer.mechanisms.BrewMechanism.install",
            _record_attempt,
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
        plan = tools_phase.plan(ctx)
        tools_phase.execute(plan, ctx)

        # Both swift tools must have been attempted (the normal install path).
        for tool in SWIFT_TOOLS:
            assert tool in attempted, (
                f"swift tool {tool!r} was never attempted on darwin; the phase "
                "must take the normal install path when the stack is supported"
            )

        # And install-state.json MUST NOT mark either tool as skipped-stack.
        state_payload = _read_install_state_dict(fixture_manifest_root)
        required_tools_state = state_payload.get("required_tools_state", {})
        if isinstance(required_tools_state, dict):
            for tool in SWIFT_TOOLS:
                record = required_tools_state.get(tool)
                if record is None:
                    continue  # not yet recorded -- acceptable on the success path
                assert record.get("state") != "skipped_platform_unsupported_stack", (
                    f"swift tool {tool!r} must NOT be recorded as "
                    "skipped_platform_unsupported_stack on darwin; got "
                    f"{record.get('state')!r}"
                )
