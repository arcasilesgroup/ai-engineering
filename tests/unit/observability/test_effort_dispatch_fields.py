"""effort dispatch metadata — spec-131 S3 / spec-189 (D-189-04).

Asserts that ``_lib.observability`` records the ``effort`` dispatch field
when ``emit_agent_dispatched`` / ``emit_skill_invoked`` receive it via the
``metadata`` kwarg (D-131-08). Per spec-189 (D-189-04) ``effort`` is the
sole skill dispatch axis; the former ``model_tier`` field is deleted.

* Valid metadata flows through ``detail.*`` and surfaces in the NDJSON.
* Invalid enum (``effort=medium``) raises ``ValueError`` so callers fail
  loud rather than emit drifted events.
* Schema version stays ``1.0`` — the addition is purely additive per
  spec-120 precedent.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

_HOOKS_DIR = Path(__file__).parents[3] / ".ai-engineering" / "scripts" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
lib_obs = importlib.import_module("_lib.observability")


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    state = tmp_path / ".ai-engineering" / "state"
    state.mkdir(parents=True)
    return tmp_path


@pytest.fixture()
def ndjson_path(project_root: Path) -> Path:
    return project_root / ".ai-engineering" / "state" / "framework-events.ndjson"


# ---------------------------------------------------------------------------
# 1. Valid metadata round-trips through the NDJSON.
# ---------------------------------------------------------------------------


def test_emit_agent_dispatched_records_effort(project_root: Path, ndjson_path: Path) -> None:
    """``detail.effort`` appears on the NDJSON entry."""
    lib_obs.emit_agent_dispatched(
        project_root,
        engine="claude_code",
        agent_name="ai-build",
        component="dispatch",
        metadata={"effort": "cheap", "patch_present": True},
    )
    assert ndjson_path.is_file(), "framework-events.ndjson not created"
    lines = ndjson_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 1
    entry = json.loads(lines[-1])
    assert entry["kind"] == "agent_dispatched"
    assert entry["detail"]["effort"] == "cheap"
    assert entry["detail"]["patch_present"] is True


def test_emit_skill_invoked_records_effort(project_root: Path, ndjson_path: Path) -> None:
    """``emit_skill_invoked`` mirrors the same convention."""
    lib_obs.emit_skill_invoked(
        project_root,
        engine="claude_code",
        skill_name="ai-build",
        component="dispatch",
        metadata={"effort": "mid"},
    )
    lines = ndjson_path.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[-1])
    assert entry["detail"]["effort"] == "mid"


# ---------------------------------------------------------------------------
# 2. Invalid enum fails loud.
# ---------------------------------------------------------------------------


def test_invalid_effort_raises(project_root: Path) -> None:
    """``effort=medium`` (legacy vocabulary) → ``ValueError``."""
    with pytest.raises(ValueError, match="effort"):
        lib_obs.emit_agent_dispatched(
            project_root,
            engine="claude_code",
            agent_name="ai-build",
            component="dispatch",
            metadata={"effort": "medium"},
        )


# ---------------------------------------------------------------------------
# 3. Absence of metadata stays additive (no breakage).
# ---------------------------------------------------------------------------


def test_emit_without_dispatch_metadata_still_works(project_root: Path, ndjson_path: Path) -> None:
    """Existing callers that omit ``effort`` are unaffected."""
    lib_obs.emit_agent_dispatched(
        project_root,
        engine="claude_code",
        agent_name="ai-build",
        component="dispatch",
    )
    lines = ndjson_path.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[-1])
    assert "effort" not in entry["detail"]


# ---------------------------------------------------------------------------
# 4. Schema version unchanged (additive contract).
# ---------------------------------------------------------------------------


def test_schema_version_unchanged(project_root: Path, ndjson_path: Path) -> None:
    """``schemaVersion`` stays at the spec-120 declared value."""
    lib_obs.emit_agent_dispatched(
        project_root,
        engine="claude_code",
        agent_name="ai-build",
        component="dispatch",
        metadata={"effort": "cheap"},
    )
    lines = ndjson_path.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[-1])
    assert entry["schemaVersion"] == lib_obs.FRAMEWORK_EVENT_SCHEMA_VERSION
    assert entry["schemaVersion"] == "1.0"
