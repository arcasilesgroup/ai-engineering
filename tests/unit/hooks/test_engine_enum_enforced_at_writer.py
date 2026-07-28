"""``engine`` must be enum-enforced at both writers (spec-201 D-201-06).

``append_framework_event`` — hook side and package side alike — enum-checked
``kind`` and merely *normalised* ``engine``. Every
``emit_skill_invoked`` / ``emit_agent_dispatched`` / ``emit_context_load``
call site bypasses ``emit_event``'s validator entirely, so the engine enum
was decorative on the busiest path in the framework: any string at all
reached the audit chain unchallenged.

The two writers close the hole **asymmetrically, on purpose**:

* **Hook side — coerce and log.** This module is loaded inside every hook.
  Raising there would crash a hook over a *labelling* problem and dropping
  the write would lose the very telemetry D-201-06 exists to capture. An
  unadmitted engine is rewritten to ``unknown`` and the original preserved
  at ``detail.engine_raw`` — the log lives on the audit plane, which is
  durable and queryable, and the writer stays silent on both stdio streams
  (stdout is the hook protocol channel). Zero event loss and zero
  mislabelling-as-Claude, which is what D-201-06's rationale asks for.
* **Package side — fail closed.** Its callers are CLI and library code, not
  a sub-second hot path, and the raise sits symmetric with the ``kind``
  raise it lives beside.

Both postures are documented in
``.ai-engineering/reference/gate-policy.md``: security / integrity
boundaries fail closed; plumbing fails open **and must log**.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOKS_DIR = REPO / ".ai-engineering" / "scripts" / "hooks"

_EVENTS_REL = Path(".ai-engineering") / "state" / "framework-events.ndjson"


@pytest.fixture
def lib_obs():
    """Load the stdlib-only ``_lib.observability`` mirror via its real path."""
    if str(HOOKS_DIR) not in sys.path:
        sys.path.insert(0, str(HOOKS_DIR))
    return importlib.import_module("_lib.observability")


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _hook_entry(engine: str) -> dict:
    return {
        "kind": "skill_invoked",
        "engine": engine,
        "timestamp": "2026-07-27T00:00:00Z",
        "component": "hook.test",
        "outcome": "success",
        "correlationId": "corr-1",
        "schemaVersion": "1.0",
        "project": "ai-engineering",
        "detail": {"skill": "ai-test"},
    }


def _last_line(project_root: Path) -> dict:
    path = project_root / _EVENTS_REL
    assert path.exists(), f"no event written to {path}"
    return json.loads(path.read_text(encoding="utf-8").strip().splitlines()[-1])


# ---------------------------------------------------------------------------
# hook side: coerce and log, never lose the event
# ---------------------------------------------------------------------------


def test_hook_writer_coerces_unadmitted_engine(lib_obs, project_root: Path) -> None:
    lib_obs.append_framework_event(project_root, _hook_entry("cursor"))

    written = _last_line(project_root)
    assert written["engine"] == "unknown", "an unadmitted engine must not enter the chain as-is"
    assert written["detail"]["engine_raw"] == "cursor", "the evidence must survive coercion"
    assert written["kind"] == "skill_invoked", "the event itself must still land (zero loss)"


def test_hook_writer_does_not_raise_on_unadmitted_engine(lib_obs, project_root: Path) -> None:
    """A labelling problem must never crash a hook."""
    lib_obs.append_framework_event(project_root, _hook_entry("gemini"))


def test_hook_writer_stays_silent_on_both_stdio_streams(
    lib_obs, project_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """stdout is the hook protocol channel; a stray byte corrupts the payload."""
    lib_obs.append_framework_event(project_root, _hook_entry("cursor"))

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_hook_writer_leaves_admitted_engine_untouched(lib_obs, project_root: Path) -> None:
    lib_obs.append_framework_event(project_root, _hook_entry("openai_compatible"))

    written = _last_line(project_root)
    assert written["engine"] == "openai_compatible"
    assert "engine_raw" not in written["detail"]


def test_hook_writer_normalises_alias_before_the_enum_check(lib_obs, project_root: Path) -> None:
    """``github_copilot`` resolves to ``copilot`` and must not be coerced."""
    lib_obs.append_framework_event(project_root, _hook_entry("github_copilot"))

    written = _last_line(project_root)
    assert written["engine"] == "copilot"
    assert "engine_raw" not in written["detail"]


def test_hook_writer_does_not_mutate_the_caller_dict(lib_obs, project_root: Path) -> None:
    """Coercion happens on the writer's own copy, as the chain pointer does."""
    entry = _hook_entry("cursor")
    detail = entry["detail"]

    lib_obs.append_framework_event(project_root, entry)

    assert entry["engine"] == "cursor"
    assert detail == {"skill": "ai-test"}


# ---------------------------------------------------------------------------
# package side: fail closed
# ---------------------------------------------------------------------------


def _pkg_event(engine: str):
    from ai_engineering.state.models import FrameworkEvent

    return FrameworkEvent(
        project="ai-engineering",
        engine=engine,
        kind="skill_invoked",
        outcome="success",
        component="hook.test",
        correlationId="corr-1",
        detail={"skill": "ai-test"},
    )


def test_package_writer_raises_on_unadmitted_engine(project_root: Path) -> None:
    from ai_engineering.state.observability import append_framework_event

    with pytest.raises(ValueError, match="Unsupported framework event engine"):
        append_framework_event(project_root, _pkg_event("cursor"))


def test_package_writer_accepts_admitted_engine(project_root: Path) -> None:
    from ai_engineering.state.observability import append_framework_event

    append_framework_event(project_root, _pkg_event("openai_compatible"))

    assert _last_line(project_root)["engine"] == "openai_compatible"


def test_package_writer_normalises_alias_before_the_enum_check(project_root: Path) -> None:
    from ai_engineering.state.observability import append_framework_event

    append_framework_event(project_root, _pkg_event("github_copilot"))

    assert _last_line(project_root)["engine"] == "copilot"


def test_package_writer_refuses_before_writing_anything(project_root: Path) -> None:
    """Fail closed means the chain is untouched, not half-written."""
    from ai_engineering.state.observability import append_framework_event

    with pytest.raises(ValueError, match="Unsupported framework event engine"):
        append_framework_event(project_root, _pkg_event("gemini"))

    assert not (project_root / _EVENTS_REL).exists()
