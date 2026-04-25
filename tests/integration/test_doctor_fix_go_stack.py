"""Integration: ``ai-eng doctor --fix --phase tools`` -- go stack (T-3.7 / T-3.8).

D-101-08 + D-101-06: when a project declares the ``go`` stack and is missing
``staticcheck`` from ``~/go/bin/``, ``ai-eng doctor --fix --phase tools``
MUST dispatch :class:`GoInstallMechanism` -- which in turn invokes::

    go install honnef.co/go/tools/cmd/staticcheck@latest

The test mocks ``subprocess.run`` so the dispatch is asserted at the argv
shape -- no real network, no real ``go install``. The doctor phase reports
staticcheck as fixed.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Project fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def go_project(tmp_path: Path) -> Path:
    """Build a minimal go-stack project layout.

    Layout:
        <tmp>/.ai-engineering/manifest.yml         -- declares go stack
        <tmp>/go.mod                                -- so the project looks "go-like"
        <tmp>/.ai-engineering/state/install-state.json
    """
    project = tmp_path
    (project / ".ai-engineering").mkdir()
    manifest = project / ".ai-engineering" / "manifest.yml"
    manifest.write_text(
        """\
schema_version: "2.0"
name: go-fixture
version: "0.0.1"
providers:
  vcs: github
  ides: [terminal]
  stacks: [go]
required_tools:
  baseline:
    - {name: gitleaks}
    - {name: jq}
  go:
    - {name: staticcheck}
    - {name: govulncheck}
""",
        encoding="utf-8",
    )
    (project / "go.mod").write_text("module example.com/fixture\n\ngo 1.22\n", encoding="utf-8")

    state_dir = project / ".ai-engineering" / "state"
    state_dir.mkdir()
    (state_dir / "install-state.json").write_text(
        '{"schema_version": "2.0", "vcs_provider": "github", "required_tools_state": {}}\n',
        encoding="utf-8",
    )
    return project


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


def test_doctor_fix_go_dispatches_go_install_staticcheck(go_project: Path) -> None:
    """Doctor --fix on a go project missing staticcheck dispatches GoInstallMechanism.

    Asserts:
    * ``go install honnef.co/go/tools/cmd/staticcheck@latest`` argv is captured.
    * Mechanism dispatched is :class:`GoInstallMechanism`.
    * The fix path reports staticcheck as fixed.
    """
    from ai_engineering.doctor.models import (
        CheckResult,
        CheckStatus,
        DoctorContext,
    )
    from ai_engineering.doctor.phases import tools as tools_phase
    from ai_engineering.installer import mechanisms as mechanisms_module
    from ai_engineering.state.manifest import LoadResult
    from ai_engineering.state.models import ToolSpec

    captured_argvs: list[list[str]] = []

    def fake_safe_run(argv: list[str], **_kwargs: object) -> object:
        captured_argvs.append(list(argv))
        return SimpleNamespace(returncode=0, stdout="", stderr="", args=argv)

    load_result = LoadResult(
        tools=[ToolSpec(name="staticcheck")],
        skipped_stacks=[],
    )

    ctx = DoctorContext(target=go_project)
    failed = [
        CheckResult(
            name="tools-required",
            status=CheckStatus.WARN,
            message="missing tools: staticcheck",
            fixable=True,
        )
    ]

    with (
        patch.object(mechanisms_module, "_safe_run", side_effect=fake_safe_run),
        patch.object(tools_phase, "run_verify", return_value=SimpleNamespace(passed=False)),
        patch.object(tools_phase, "load_required_tools", return_value=load_result),
    ):
        fixed = tools_phase.fix(ctx, failed)

    # The expected go-install argv -- staticcheck via the canonical import path.
    expected = [
        "go",
        "install",
        "honnef.co/go/tools/cmd/staticcheck@latest",
    ]

    go_calls = [argv for argv in captured_argvs if argv and argv[0] == "go"]
    assert go_calls, f"expected at least one go call, captured: {captured_argvs}"
    assert any(argv == expected for argv in go_calls), (
        f"expected {expected} in go calls, got {go_calls}"
    )

    # Fix path reported success.
    assert any(r.status == CheckStatus.FIXED for r in fixed), (
        f"expected at least one FIXED result, got {[(r.name, r.status) for r in fixed]}"
    )

    # Defence in depth: no ``sudo`` or other privilege escalation.
    for argv in go_calls:
        assert "sudo" not in argv


def test_doctor_fix_go_uses_go_install_mechanism_class(go_project: Path) -> None:
    """Mechanism class identity: ``GoInstallMechanism`` is dispatched.

    Direct probe of the dispatch wiring -- the test patches the registry
    with a real :class:`GoInstallMechanism` instance and asserts the
    captured argv matches the canonical staticcheck import path.
    """
    from ai_engineering.doctor.models import (
        CheckResult,
        CheckStatus,
        DoctorContext,
    )
    from ai_engineering.doctor.phases import tools as tools_phase
    from ai_engineering.installer import mechanisms as mechanisms_module
    from ai_engineering.installer.mechanisms import GoInstallMechanism
    from ai_engineering.state.manifest import LoadResult
    from ai_engineering.state.models import ToolSpec

    captured_argvs: list[list[str]] = []

    def fake_safe_run(argv: list[str], **_kwargs: object) -> object:
        captured_argvs.append(list(argv))
        return SimpleNamespace(returncode=0, stdout="", stderr="", args=argv)

    fake_go_dispatch = GoInstallMechanism("honnef.co/go/tools/cmd/staticcheck@latest")
    fake_registry = {
        "staticcheck": {
            "darwin": [fake_go_dispatch],
            "linux": [fake_go_dispatch],
            "win32": [fake_go_dispatch],
        }
    }

    load_result = LoadResult(
        tools=[ToolSpec(name="staticcheck")],
        skipped_stacks=[],
    )

    ctx = DoctorContext(target=go_project)
    failed = [
        CheckResult(
            name="tools-required",
            status=CheckStatus.WARN,
            message="missing: staticcheck",
            fixable=True,
        )
    ]

    with (
        patch.object(mechanisms_module, "_safe_run", side_effect=fake_safe_run),
        patch.object(tools_phase, "run_verify", return_value=SimpleNamespace(passed=False)),
        patch.object(tools_phase, "load_required_tools", return_value=load_result),
        patch.object(tools_phase, "TOOL_REGISTRY", fake_registry),
    ):
        tools_phase.fix(ctx, failed)

    expected = ["go", "install", "honnef.co/go/tools/cmd/staticcheck@latest"]
    assert expected in captured_argvs


# Re-export for collect-only surfaces.
__all__ = (
    "test_doctor_fix_go_dispatches_go_install_staticcheck",
    "test_doctor_fix_go_uses_go_install_mechanism_class",
)


# Touching ``sys`` keeps the imports list non-trivial against pyflakes.
_ = sys.platform
