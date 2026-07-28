"""``brief_drafted`` must survive all three event writers (spec-201 D-201-07).

``.claude/skills/ai-spec-draft/SKILL.md`` step 6 has instructed
``framework_event kind=brief_drafted`` since the skill shipped, and every
one of the three writers refused it: the package validator and the
hook-side validator returned False (silent drop), and the busiest
hook-side writer raised ``ValueError``. Zero ``brief_drafted`` events
exist in the live stream as a result.

The parent plan's gate for this was "run ``/ai-spec-draft`` and watch a
``brief_drafted`` event land". That is not runnable: there is no producer
anywhere — ``_lib/observability`` exposes no arbitrary-kind emitter,
``.claude/skills/ai-spec-draft/`` has no ``handlers/`` directory, and
``ai-eng audit`` exposes only ``verify`` / ``tokens`` / ``replay``. This
module substitutes an executable three-writer proof of the same property
and deliberately does not commission a producer (§10.2 YAGNI).
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOKS_DIR = REPO / ".ai-engineering" / "scripts" / "hooks"
HOOK_COMMON_PATH = HOOKS_DIR / "_lib" / "hook-common.py"

# The exact shape .claude/skills/ai-spec-draft/SKILL.md step 6 instructs:
# kind=brief_drafted, component=ai-spec-draft, detail={topic, path,
# citations_count}. `engine` is deliberately the spec-201 addition so the
# kind and the engine are proven on the same line.
_BRIEF_DETAIL: dict = {
    "topic": "event-plane-identity",
    "path": ".ai-engineering/specs/drafts/event-plane-identity-brief.md",
    "citations_count": 7,
}


def _brief_drafted_event() -> dict:
    return {
        "kind": "brief_drafted",
        "engine": "openai_compatible",
        "timestamp": "2026-07-27T00:00:00Z",
        "component": "ai-spec-draft",
        "outcome": "success",
        "correlationId": "corr-brief-201",
        "schemaVersion": "1.0",
        "project": "ai-engineering",
        "source": "skill",
        "detail": dict(_BRIEF_DETAIL),
    }


@pytest.fixture
def hook_common():
    """Load ``_lib/hook-common.py`` by path (the filename is hyphenated)."""
    spec = importlib.util.spec_from_file_location(
        "aieng_hook_common_brief_drafted", HOOK_COMMON_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


# --- writer 1: the package validator ---------------------------------------


def test_package_validator_accepts_brief_drafted() -> None:
    from ai_engineering.state.event_schema import validate_event_schema

    assert validate_event_schema(_brief_drafted_event()) is True


def test_package_kind_enum_admits_brief_drafted() -> None:
    from ai_engineering.state.event_schema import ALLOWED_EVENT_KINDS

    assert "brief_drafted" in ALLOWED_EVENT_KINDS


# --- writer 2: the hook-side validator --------------------------------------


def test_hook_common_validator_accepts_brief_drafted(hook_common) -> None:
    assert hook_common.validate_event_schema(_brief_drafted_event()) is True


def test_hook_common_emit_writes_brief_drafted(hook_common, project_root: Path) -> None:
    """The refusing path is the one that dropped it; prove the write lands."""
    assert hook_common.emit_event(project_root, _brief_drafted_event()) is True

    ndjson = project_root / ".ai-engineering" / "state" / "framework-events.ndjson"
    written = json.loads(ndjson.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert written["kind"] == "brief_drafted"
    assert written["engine"] == "openai_compatible"
    assert written["detail"] == _BRIEF_DETAIL


# --- writer 3: the stdlib-only hook writer with 10 call sites ---------------


def test_lib_observability_writes_brief_drafted(lib_obs, project_root: Path) -> None:
    """``append_framework_event`` raised ``ValueError`` on this kind before spec-201."""
    lib_obs.append_framework_event(project_root, _brief_drafted_event())

    ndjson = project_root / ".ai-engineering" / "state" / "framework-events.ndjson"
    written = json.loads(ndjson.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert written["kind"] == "brief_drafted"
    assert written["engine"] == "openai_compatible", "engine must survive the writer intact"
    assert written["component"] == "ai-spec-draft"
    assert written["detail"] == _BRIEF_DETAIL
    assert "prev_event_hash" in written


def test_lib_observability_still_refuses_unadmitted_kind(lib_obs, project_root: Path) -> None:
    """Negative control: admitting one kind must not disable the enum check.

    ``upstream_bug_filed`` is one of three further skill-declared kinds the
    schema still refuses (``.claude/skills/ai-engineering-issue/SKILL.md``).
    D-201-07 names only ``brief_drafted``, so this asserts the current — and
    still buggy for those three — behaviour rather than pretending otherwise.
    """
    event = _brief_drafted_event()
    event["kind"] = "upstream_bug_filed"
    with pytest.raises(ValueError, match="Unsupported framework event kind"):
        lib_obs.append_framework_event(project_root, event)
