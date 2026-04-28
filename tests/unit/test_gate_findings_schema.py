"""RED tests for spec-104 T-0.3 — `gate-findings.json` schema v1 validation.

These tests assert the shape and governance rules of the canonical
`gate-findings/v1` schema declared in spec-104 D-104-06 and the
`WatchLoopState` persistence model used by D-104-05 (watch loop bounded
by wall-clock).

Models under test (created in T-0.4):
    - ``ai_engineering.state.models.GateFinding`` — single finding record.
    - ``ai_engineering.state.models.AutoFixedEntry`` — auto-fix metadata.
    - ``ai_engineering.state.models.GateFindingsDocument`` — top-level
      schema container emitted at
      ``.ai-engineering/state/gate-findings.json`` and
      ``.ai-engineering/state/watch-residuals.json``.
    - ``ai_engineering.state.models.WatchLoopState`` — watch loop runtime
      state used by handlers/watch.md (Phase 6 implementation).

All four are Pydantic ``BaseModel`` subclasses (existing convention in
``state/models.py``). T-0.4 lands the models so these tests turn GREEN;
this file is IMMUTABLE after T-0.3 -- T-0.4 may only add models or adjust
their shapes to satisfy these assertions, never edit the assertions
themselves.

Governance covered (per D-104-06 + D-104-05):
    - ``GateFinding`` minimum-valid record instantiates.
    - ``check`` and ``rule_id`` are required on ``GateFinding``.
    - ``severity`` enum is exhaustive
      (critical|high|medium|low|info) and rejects unknown values.
    - ``auto_fixable=True`` requires a non-null ``auto_fix_command``;
      ``auto_fixable=False`` permits null.
    - ``line`` must be positive (>= 1).
    - ``AutoFixedEntry.files`` must be non-empty.
    - ``GateFindingsDocument.schema_`` field MUST equal
      ``"ai-engineering/gate-findings/v1"`` (stored under JSON key
      ``schema`` per the canonical schema).
    - ``session_id`` is a UUID4 string.
    - ``produced_by`` enum exhaustive: ``ai-commit``, ``ai-pr``,
      ``watch-loop``.
    - ``wall_clock_ms`` MUST contain exactly the three keys
      ``wave1_fixers``, ``wave2_checkers``, ``total``.
    - JSON round-trip preserves the document.
    - ``WatchLoopState`` carries ISO-8601 ``watch_started_at`` and
      ``last_active_action_at`` plus a ``fix_attempts`` mapping
      (``dict[str, int]``).

This file is RED until T-0.4 lands the four models.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ai_engineering.state.models import (
    AutoFixedEntry,
    GateFinding,
    GateFindingsDocument,
    WatchLoopState,
)

# ---------------------------------------------------------------------------
# Helpers — minimal valid payloads
# ---------------------------------------------------------------------------

_VALID_SCHEMA_LITERAL = "ai-engineering/gate-findings/v1"


def _minimal_finding() -> dict[str, object]:
    """Return a fresh, valid ``GateFinding`` payload (auto_fixable=False)."""
    return {
        "check": "ruff",
        "rule_id": "E501",
        "file": "src/example.py",
        "line": 10,
        "column": 80,
        "severity": "low",
        "message": "Line too long",
        "auto_fixable": False,
        "auto_fix_command": None,
    }


def _minimal_document() -> dict[str, object]:
    """Return a fresh, valid ``GateFindingsDocument`` payload.

    The document is stored under JSON key ``schema``; Pydantic models will
    use a Python-safe attribute name (e.g. ``schema_``) with the JSON alias
    ``schema``. Tests construct via the alias so they remain robust to
    either ``populate_by_name`` style.
    """
    return {
        "schema": _VALID_SCHEMA_LITERAL,
        "session_id": str(uuid.uuid4()),
        "produced_by": "ai-commit",
        "produced_at": "2026-04-26T12:00:00+00:00",
        "branch": "feat/spec-104-pipeline-speed",
        "commit_sha": "0" * 40,
        "findings": [_minimal_finding()],
        "auto_fixed": [
            {
                "check": "ruff-format",
                "files": ["src/example.py"],
                "rules_fixed": ["E501"],
            }
        ],
        "cache_hits": ["gitleaks"],
        "cache_misses": ["ruff-check", "ty"],
        "wall_clock_ms": {
            "wave1_fixers": 1234,
            "wave2_checkers": 5678,
            "total": 6912,
        },
    }


# ---------------------------------------------------------------------------
# 1. GateFinding — happy path
# ---------------------------------------------------------------------------


def test_gate_finding_accepts_valid_record() -> None:
    """A minimum valid GateFinding payload instantiates without error."""
    finding = GateFinding.model_validate(_minimal_finding())

    assert finding.check == "ruff"
    assert finding.rule_id == "E501"
    assert finding.severity == "low"
    assert finding.auto_fixable is False
    assert finding.auto_fix_command is None


# ---------------------------------------------------------------------------
# 2-3. GateFinding — required fields
# ---------------------------------------------------------------------------


def test_gate_finding_rejects_missing_check() -> None:
    """`check` is a required field on every finding."""
    payload = _minimal_finding()
    del payload["check"]

    with pytest.raises(ValidationError):
        GateFinding.model_validate(payload)


def test_gate_finding_rejects_missing_rule_id() -> None:
    """`rule_id` is a required field — D-104-06 mandates stable IDs."""
    payload = _minimal_finding()
    del payload["rule_id"]

    with pytest.raises(ValidationError):
        GateFinding.model_validate(payload)


# ---------------------------------------------------------------------------
# 4. GateFinding — severity enum exhaustive
# ---------------------------------------------------------------------------


def test_gate_finding_severity_enum_exhaustive() -> None:
    """`severity` accepts critical|high|medium|low|info; rejects unknown."""
    for level in ("critical", "high", "medium", "low", "info"):
        payload = _minimal_finding()
        payload["severity"] = level
        finding = GateFinding.model_validate(payload)
        assert finding.severity == level

    bad_payload = _minimal_finding()
    bad_payload["severity"] = "unknown"
    with pytest.raises(ValidationError):
        GateFinding.model_validate(bad_payload)


# ---------------------------------------------------------------------------
# 5-6. GateFinding — auto_fixable / auto_fix_command coupling
# ---------------------------------------------------------------------------


def test_gate_finding_auto_fixable_requires_command() -> None:
    """When auto_fixable=True, auto_fix_command must be non-null."""
    payload = _minimal_finding()
    payload["auto_fixable"] = True
    payload["auto_fix_command"] = None

    with pytest.raises(ValidationError):
        GateFinding.model_validate(payload)


def test_gate_finding_auto_fixable_false_allows_null_command() -> None:
    """When auto_fixable=False, auto_fix_command may be null."""
    payload = _minimal_finding()
    payload["auto_fixable"] = False
    payload["auto_fix_command"] = None

    finding = GateFinding.model_validate(payload)
    assert finding.auto_fixable is False
    assert finding.auto_fix_command is None


# ---------------------------------------------------------------------------
# 7. GateFinding — line must be positive
# ---------------------------------------------------------------------------


def test_gate_finding_line_must_be_positive() -> None:
    """`line` must be >= 1; zero or negative values are rejected."""
    for bad_line in (0, -1, -100):
        payload = _minimal_finding()
        payload["line"] = bad_line
        with pytest.raises(ValidationError):
            GateFinding.model_validate(payload)


# ---------------------------------------------------------------------------
# 8. AutoFixedEntry — files non-empty
# ---------------------------------------------------------------------------


def test_auto_fixed_entry_files_non_empty() -> None:
    """`AutoFixedEntry.files` must be non-empty (no orphan auto-fix records)."""
    with pytest.raises(ValidationError):
        AutoFixedEntry.model_validate(
            {
                "check": "ruff-format",
                "files": [],
                "rules_fixed": ["E501"],
            }
        )


# ---------------------------------------------------------------------------
# 9. GateFindingsDocument — schema literal
# ---------------------------------------------------------------------------


def test_gate_findings_document_schema_literal() -> None:
    """`schema` field MUST be exactly "ai-engineering/gate-findings/v1"."""
    valid_payload = _minimal_document()
    doc = GateFindingsDocument.model_validate(valid_payload)
    # Pydantic stores it as `schema_` to avoid clashing with BaseModel.schema().
    assert getattr(doc, "schema_", None) == _VALID_SCHEMA_LITERAL or (
        getattr(doc, "schema", None) == _VALID_SCHEMA_LITERAL
    )

    # A different schema literal must be rejected.
    bad_payload = _minimal_document()
    bad_payload["schema"] = "ai-engineering/gate-findings/v0"
    with pytest.raises(ValidationError):
        GateFindingsDocument.model_validate(bad_payload)


# ---------------------------------------------------------------------------
# 10. GateFindingsDocument — session_id is UUID4
# ---------------------------------------------------------------------------


def test_gate_findings_document_session_id_uuid4() -> None:
    """`session_id` MUST be a UUID4-shaped string."""
    valid_payload = _minimal_document()
    valid_payload["session_id"] = str(uuid.uuid4())
    doc = GateFindingsDocument.model_validate(valid_payload)

    parsed = uuid.UUID(str(doc.session_id))
    assert parsed.version == 4

    # Non-UUID strings must be rejected.
    bad_payload = _minimal_document()
    bad_payload["session_id"] = "not-a-uuid"
    with pytest.raises(ValidationError):
        GateFindingsDocument.model_validate(bad_payload)


# ---------------------------------------------------------------------------
# 11. GateFindingsDocument — produced_by enum
# ---------------------------------------------------------------------------


def test_gate_findings_document_produced_by_enum() -> None:
    """`produced_by` accepts ai-commit|ai-pr|watch-loop; rejects others."""
    for source in ("ai-commit", "ai-pr", "watch-loop"):
        payload = _minimal_document()
        payload["produced_by"] = source
        doc = GateFindingsDocument.model_validate(payload)
        assert doc.produced_by == source

    bad_payload = _minimal_document()
    bad_payload["produced_by"] = "ai-other"
    with pytest.raises(ValidationError):
        GateFindingsDocument.model_validate(bad_payload)


# ---------------------------------------------------------------------------
# 12. GateFindingsDocument — wall_clock_ms keys exhaustive
# ---------------------------------------------------------------------------


def test_gate_findings_document_wall_clock_ms_keys_exhaustive() -> None:
    """`wall_clock_ms` MUST contain wave1_fixers + wave2_checkers + total."""
    # Missing one key → reject.
    for missing_key in ("wave1_fixers", "wave2_checkers", "total"):
        payload = _minimal_document()
        wall_clock = dict(payload["wall_clock_ms"])  # type: ignore[arg-type]
        del wall_clock[missing_key]
        payload["wall_clock_ms"] = wall_clock
        with pytest.raises(ValidationError):
            GateFindingsDocument.model_validate(payload)

    # Extra unrecognized key → reject (schema is fixed).
    payload = _minimal_document()
    wall_clock = dict(payload["wall_clock_ms"])  # type: ignore[arg-type]
    wall_clock["unknown_phase"] = 999
    payload["wall_clock_ms"] = wall_clock
    with pytest.raises(ValidationError):
        GateFindingsDocument.model_validate(payload)


# ---------------------------------------------------------------------------
# 13. GateFindingsDocument — JSON round-trip
# ---------------------------------------------------------------------------


def test_gate_findings_document_round_trip_json() -> None:
    """model.model_dump_json() then model_validate_json() returns equivalent."""
    original = GateFindingsDocument.model_validate(_minimal_document())

    json_str = original.model_dump_json(by_alias=True)
    restored = GateFindingsDocument.model_validate_json(json_str)

    assert restored.session_id == original.session_id
    assert restored.produced_by == original.produced_by
    assert restored.branch == original.branch
    assert restored.commit_sha == original.commit_sha
    assert len(restored.findings) == len(original.findings)
    assert restored.findings[0].check == original.findings[0].check
    assert restored.findings[0].rule_id == original.findings[0].rule_id
    assert restored.cache_hits == original.cache_hits
    assert restored.cache_misses == original.cache_misses
    assert restored.wall_clock_ms == original.wall_clock_ms

    # Schema literal must survive the round-trip under the JSON alias.
    parsed = json.loads(json_str)
    assert parsed["schema"] == _VALID_SCHEMA_LITERAL


# ---------------------------------------------------------------------------
# 14-15. WatchLoopState — used by D-104-05 + Phase 6 watch loop bounds
# ---------------------------------------------------------------------------


def test_watch_loop_state_iso8601_timestamps() -> None:
    """`watch_started_at` and `last_active_action_at` are ISO-8601 datetimes."""
    started = datetime(2026, 4, 26, 10, 0, 0, tzinfo=UTC)
    last_action = datetime(2026, 4, 26, 10, 5, 30, tzinfo=UTC)

    state = WatchLoopState.model_validate(
        {
            "watch_started_at": started.isoformat(),
            "last_active_action_at": last_action.isoformat(),
            "fix_attempts": {},
        }
    )
    assert state.watch_started_at == started
    assert state.last_active_action_at == last_action

    # Non-ISO-8601 strings must be rejected.
    with pytest.raises(ValidationError):
        WatchLoopState.model_validate(
            {
                "watch_started_at": "yesterday",
                "last_active_action_at": last_action.isoformat(),
                "fix_attempts": {},
            }
        )


def test_watch_loop_state_fix_attempts_dict() -> None:
    """`fix_attempts` is a dict[str, int] keyed by check name."""
    started = datetime(2026, 4, 26, 10, 0, 0, tzinfo=UTC)
    state = WatchLoopState.model_validate(
        {
            "watch_started_at": started.isoformat(),
            "last_active_action_at": started.isoformat(),
            "fix_attempts": {"ruff": 1, "gitleaks": 0, "ty": 2},
        }
    )
    assert state.fix_attempts == {"ruff": 1, "gitleaks": 0, "ty": 2}
    assert all(isinstance(k, str) for k in state.fix_attempts)
    assert all(isinstance(v, int) for v in state.fix_attempts.values())

    # Non-int values must be rejected.
    with pytest.raises(ValidationError):
        WatchLoopState.model_validate(
            {
                "watch_started_at": started.isoformat(),
                "last_active_action_at": started.isoformat(),
                "fix_attempts": {"ruff": "many"},
            }
        )
