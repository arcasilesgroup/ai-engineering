"""Per-tool / per-hook progress callback tests (spec-124 D-124-03, T-2.1).

The installer's tool and git-hooks phases run long enough that users
need feedback about *which* tool / hook is currently being processed.
The pipeline-level callback only fires once per phase ("[5/6] tools"),
so each phase MUST also emit per-tool ``tool_started`` / ``tool_finished``
events that the CLI surface translates into a Rich Status spinner sub-step.

These tests assert the contract:

* ``InstallContext`` exposes an optional ``progress_callback``.
* ``ToolsPhase.execute()`` calls it once per tool with
  ``"tool_started:<name>"`` BEFORE the install attempt and once with
  ``"tool_finished:<name>"`` AFTER (regardless of success / failure /
  skip).
* ``HooksPhase.execute()`` does the same with
  ``"hook_started:<name>"`` / ``"hook_finished:<name>"`` for each git
  hook installed.
* Callback errors are swallowed so progress UI failures cannot break
  the pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from ai_engineering.installer.phases import (
    InstallContext,
    InstallMode,
)
from ai_engineering.installer.phases.hooks import HooksPhase
from ai_engineering.installer.phases.tools import ToolsPhase
from ai_engineering.state.models import ToolScope, ToolSpec

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _Recorder:
    """Recording callable; ``ctx.progress_callback is recorder`` works."""

    def __init__(self) -> None:
        self.events: list[str] = []

    def __call__(self, message: str) -> None:
        self.events.append(message)


def _ctx(tmp_path: Path, *, callback) -> InstallContext:
    """Build an InstallContext with a captured progress callback."""
    return InstallContext(
        target=tmp_path,
        mode=InstallMode.INSTALL,
        providers=["claude-code"],
        vcs_provider="github",
        stacks=["python"],
        ides=["terminal"],
        progress_callback=callback,
    )


class _FakeLoadResult:
    """Iterable test double mirroring ``state.manifest.LoadResult``."""

    def __init__(
        self,
        tools: list[ToolSpec],
        skipped_stacks: list[Any] | None = None,
    ) -> None:
        self.tools = tools
        self.skipped_stacks = skipped_stacks or []

    def __iter__(self) -> Any:
        return iter(self.tools)

    def __len__(self) -> int:
        return len(self.tools)


def _fake_tools() -> _FakeLoadResult:
    """Return four synthetic tools so the per-tool callback is exercised."""
    return _FakeLoadResult(
        tools=[
            ToolSpec(name="gitleaks", scope=ToolScope.USER_GLOBAL),
            ToolSpec(name="jq", scope=ToolScope.USER_GLOBAL),
            ToolSpec(name="ruff", scope=ToolScope.USER_GLOBAL_UV_TOOL),
            ToolSpec(name="pytest", scope=ToolScope.USER_GLOBAL_UV_TOOL),
        ]
    )


# ---------------------------------------------------------------------------
# T-2.1 RED -- ToolsPhase per-tool callbacks
# ---------------------------------------------------------------------------


class TestToolsPhasePerToolProgress:
    def test_install_context_accepts_progress_callback(self, tmp_path: Path) -> None:
        """``InstallContext`` MUST expose ``progress_callback`` attribute."""
        recorder = _Recorder()
        ctx = _ctx(tmp_path, callback=recorder)
        assert ctx.progress_callback is recorder

    def test_install_context_default_progress_callback_is_none(self, tmp_path: Path) -> None:
        """``progress_callback`` defaults to None for backward compat."""
        ctx = InstallContext(
            target=tmp_path,
            mode=InstallMode.INSTALL,
        )
        assert ctx.progress_callback is None

    def test_tools_phase_emits_per_tool_started_and_finished(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Each tool produces tool_started/tool_finished progress events."""
        # Force the smoke-test simulate hook so install attempts succeed
        # synthetically without touching the registry.
        monkeypatch.setenv("AIENG_TEST_SIMULATE_INSTALL_OK", "*")

        recorder = _Recorder()
        ctx = _ctx(tmp_path, callback=recorder)

        phase = ToolsPhase()
        with patch(
            "ai_engineering.installer.phases.tools.load_required_tools",
            return_value=_fake_tools(),
        ):
            plan = phase.plan(ctx)
            phase.execute(plan, ctx)

        started = [e for e in recorder.events if e.startswith("tool_started:")]
        finished = [e for e in recorder.events if e.startswith("tool_finished:")]
        # 4 fake tools enumerated -- expect 4 started + 4 finished.
        assert len(started) == 4, f"expected 4 started events; got {recorder.events!r}"
        assert len(started) == len(finished), (
            f"started ({len(started)}) != finished ({len(finished)}) "
            f"-- every started must pair with a finished. events={recorder.events!r}"
        )

    def test_tools_phase_callback_fires_in_started_finished_order(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """For each tool, started MUST be emitted before finished."""
        monkeypatch.setenv("AIENG_TEST_SIMULATE_INSTALL_OK", "*")

        recorder = _Recorder()
        ctx = _ctx(tmp_path, callback=recorder)

        phase = ToolsPhase()
        with patch(
            "ai_engineering.installer.phases.tools.load_required_tools",
            return_value=_fake_tools(),
        ):
            plan = phase.plan(ctx)
            phase.execute(plan, ctx)

        # Pair starts and finishes by tool name; assert started precedes finished
        # for every tool in event order.
        seen_started: set[str] = set()
        for event in recorder.events:
            if event.startswith("tool_started:"):
                tool = event.split(":", 1)[1]
                seen_started.add(tool)
            elif event.startswith("tool_finished:"):
                tool = event.split(":", 1)[1]
                assert tool in seen_started, (
                    f"tool_finished:{tool} emitted before tool_started:{tool} "
                    f"in event sequence {recorder.events!r}"
                )

    def test_tools_phase_callback_swallows_exceptions(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A raising callback MUST NOT break the install pipeline."""
        monkeypatch.setenv("AIENG_TEST_SIMULATE_INSTALL_OK", "*")

        def explode(_message: str) -> None:
            raise RuntimeError("boom")

        ctx = _ctx(tmp_path, callback=explode)

        phase = ToolsPhase()
        with patch(
            "ai_engineering.installer.phases.tools.load_required_tools",
            return_value=_fake_tools(),
        ):
            plan = phase.plan(ctx)
            # Must not propagate the RuntimeError.
            result = phase.execute(plan, ctx)
        assert result.phase_name == "tools"


# ---------------------------------------------------------------------------
# T-2.1 RED -- HooksPhase per-hook callbacks
# ---------------------------------------------------------------------------


class TestHooksPhasePerHookProgress:
    def test_hooks_phase_emits_per_hook_started_and_finished(self, tmp_path: Path) -> None:
        """Each git hook installed produces hook_started/hook_finished events."""
        # HooksPhase needs a .git directory to install hooks into.
        (tmp_path / ".git" / "hooks").mkdir(parents=True)
        # Need a .ai-engineering/state directory so install_hooks can run.
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)

        events: list[str] = []
        ctx = _ctx(tmp_path, callback=events.append)

        phase = HooksPhase()
        plan = phase.plan(ctx)
        phase.execute(plan, ctx)

        started = [e for e in events if e.startswith("hook_started:")]
        finished = [e for e in events if e.startswith("hook_finished:")]
        assert len(started) > 0, f"expected per-hook started events; got {events!r}"
        assert len(started) == len(finished), (
            f"started ({len(started)}) != finished ({len(finished)}) "
            f"-- every started must pair with a finished. events={events!r}"
        )

    def test_hooks_phase_callback_swallows_exceptions(self, tmp_path: Path) -> None:
        """A raising callback MUST NOT break hook installation."""
        (tmp_path / ".git" / "hooks").mkdir(parents=True)
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)

        def explode(_message: str) -> None:
            raise RuntimeError("boom")

        ctx = _ctx(tmp_path, callback=explode)

        phase = HooksPhase()
        plan = phase.plan(ctx)
        result = phase.execute(plan, ctx)
        assert result.phase_name == "hooks"
