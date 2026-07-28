"""A schema-refused emit must be visible on the audit plane (spec-201 D-201-07).

``_lib/hook-common.emit_event`` refused malformed events by writing a
``logger.error`` line and returning ``False``. All four callers in the same
module discard that boolean, the logger has no ``basicConfig`` anywhere in
the tree (so the message only reaches stderr through
``logging.lastResort``), and **no event is produced** — the refusal is
invisible to the very audit plane it protects. That is the mechanism which
hid the closed engine enum and the missing ``brief_drafted`` kind for their
entire lifetimes.

Scope, deliberately narrowed (deep-plan correction, see the module note in
``sub-002/plan.md``): the audit-plane refusal fires for an **enum**
refusal — a structurally complete event whose ``kind`` or ``engine`` the
frozensets do not admit. A structurally incomplete event (missing required
keys) keeps the pre-existing silent-refusal contract pinned at
``tests/unit/hooks/test_hook_common_lib.py:81-90``, which asserts the
NDJSON stays empty. The enum refusal is the D-201-06 / D-201-07 defect
class; a caller that omits ``timestamp`` is a local programming error that
the stderr log already names.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOKS_DIR = REPO / ".ai-engineering" / "scripts" / "hooks"
HOOK_COMMON_PATH = HOOKS_DIR / "_lib" / "hook-common.py"

_EVENTS_REL = Path(".ai-engineering") / "state" / "framework-events.ndjson"


@pytest.fixture
def hc(monkeypatch: pytest.MonkeyPatch):
    """Load ``_lib/hook-common.py`` fresh so the re-entrancy sentinel is cold."""
    monkeypatch.syspath_prepend(str(HOOKS_DIR))
    spec = importlib.util.spec_from_file_location(
        "aieng_hook_common_loud_refusal", HOOK_COMMON_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".ai-engineering" / "runtime").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _well_formed_event() -> dict:
    return {
        "kind": "skill_invoked",
        "engine": "claude_code",
        "timestamp": "2026-07-27T00:00:00Z",
        "component": "hook.test",
        "outcome": "success",
        "correlationId": "corr-1",
        "schemaVersion": "1.0",
        "project": "ai-engineering",
        "detail": {"skill": "ai-test"},
    }


def _events(project_root: Path) -> list[dict]:
    path = project_root / _EVENTS_REL
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


# ---------------------------------------------------------------------------
# (a) the refusal reaches the audit plane
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [("kind", "upstream_bug_filed"), ("engine", "gemini")],
)
def test_enum_refusal_emits_framework_error(
    hc, project_root: Path, field: str, bad_value: str
) -> None:
    event = _well_formed_event()
    event[field] = bad_value

    assert hc.emit_event(project_root, event) is False

    written = _events(project_root)
    assert len(written) == 1, f"expected exactly one refusal event, got {written}"
    refusal = written[0]
    assert refusal["kind"] == "framework_error"
    assert refusal["outcome"] == "failure"
    assert refusal["detail"]["error_code"] == "event_schema_refused"
    assert refusal["detail"]["refused_kind"] == str(event["kind"])
    assert refusal["detail"]["refused_engine"] == str(event["engine"])


def test_refused_event_itself_is_never_written(hc, project_root: Path) -> None:
    """The refusal is announced; the malformed payload still does not land."""
    event = _well_formed_event()
    event["kind"] = "upstream_bug_filed"

    hc.emit_event(project_root, event)

    kinds = [entry["kind"] for entry in _events(project_root)]
    assert "upstream_bug_filed" not in kinds


def test_refusal_carries_the_resolved_engine(hc, project_root: Path) -> None:
    """The refusal event is attributed to the real harness, not the refused label."""
    event = _well_formed_event()
    event["engine"] = "gemini"

    hc.emit_event(project_root, event)

    assert _events(project_root)[0]["engine"] == hc._resolve_engine()


def test_two_distinct_refusals_are_both_loud(hc, project_root: Path) -> None:
    """The sentinel resets: a second, different refusal is not swallowed."""
    first = _well_formed_event()
    first["kind"] = "upstream_bug_filed"
    second = _well_formed_event()
    second["kind"] = "work_item_created"

    hc.emit_event(project_root, first)
    hc.emit_event(project_root, second)

    refused = [entry["detail"]["refused_kind"] for entry in _events(project_root)]
    assert refused == ["upstream_bug_filed", "work_item_created"]


# ---------------------------------------------------------------------------
# (b) the existing contract is untouched
# ---------------------------------------------------------------------------


def test_return_type_is_still_a_plain_false(hc, project_root: Path) -> None:
    event = _well_formed_event()
    event["kind"] = "upstream_bug_filed"
    assert hc.emit_event(project_root, event) is False


def test_structurally_incomplete_event_stays_silent(hc, project_root: Path) -> None:
    """Pins the deliberate narrowing (test_hook_common_lib.py:81-90 stays green)."""
    incomplete = {"kind": "skill_invoked", "engine": "bogus_engine"}

    assert hc.emit_event(project_root, incomplete) is False
    assert _events(project_root) == []


def test_emit_event_still_raises_nothing(hc, project_root: Path) -> None:
    """Four fail-open callers wrap this in ``except Exception``; never raise."""
    for payload in (None, [], "nope", {}, {"kind": None, "engine": None}):
        assert hc.emit_event(project_root, payload) is False


# ---------------------------------------------------------------------------
# (c) the re-entrancy guard
# ---------------------------------------------------------------------------


def test_refusal_cannot_recurse(hc, project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every other brake removed, the sentinel must still stop the loop.

    ``validate_event_schema`` is forced to reject everything and the enum
    refusal predicate forced to accept everything, so the refusal event the
    module builds is itself refused. Without the sentinel this recurses
    until the interpreter stack dies.
    """
    monkeypatch.setattr(hc, "validate_event_schema", lambda _event: False)
    monkeypatch.setattr(hc, "_is_enum_refusal", lambda _event: True)

    calls: list[int] = []
    real_emit = hc.emit_event

    def counting_emit(root, event):
        calls.append(1)
        return real_emit(root, event)

    monkeypatch.setattr(hc, "emit_event", counting_emit)

    assert counting_emit(project_root, _well_formed_event()) is False
    assert len(calls) <= 2, f"emit_event re-entered {len(calls) - 1} times; expected at most 1"


# ---------------------------------------------------------------------------
# (d) no spurious noise on the happy path
# ---------------------------------------------------------------------------


def test_valid_event_produces_no_refusal(hc, project_root: Path) -> None:
    assert hc.emit_event(project_root, _well_formed_event()) is True

    written = _events(project_root)
    assert len(written) == 1
    assert written[0]["kind"] == "skill_invoked"
    assert "error_code" not in written[0]["detail"]


def test_alias_normalised_engine_is_not_refused(hc, project_root: Path) -> None:
    """``github_copilot`` normalises to ``copilot`` before validation."""
    event = _well_formed_event()
    event["engine"] = "github_copilot"

    assert hc.emit_event(project_root, event) is True
    assert _events(project_root)[0]["engine"] == "copilot"
