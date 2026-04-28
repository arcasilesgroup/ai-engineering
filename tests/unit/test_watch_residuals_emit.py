"""RED tests for spec-104 T-6.4 — ``watch_residuals.emit`` JSON emission.

These tests pin the contract of the not-yet-implemented JSON emitter for
``watch-residuals.json`` per spec-104 D-104-05 (watch loop wall-clock cap)
and D-104-06 (gate-findings schema v1). T-6.5 GREEN phase will land
``emit`` in ``ai_engineering.policy.watch_residuals``; this file is
IMMUTABLE after T-6.4 — T-6.5 may only adjust the implementation to
satisfy these assertions, never edit the assertions.

Target function (does not exist yet, created in T-6.5)::

    def emit(
        failed_checks: list[dict],
        output_path: Path | None = None,
    ) -> Path: ...

The watch loop calls this helper when it hits the active 30-min or
passive 4-h wall-clock cap to materialise the residual failures into
``.ai-engineering/state/watch-residuals.json``. Schema is identical to
``gate-findings.json`` v1 (D-104-06) so spec-105 risk-accept can consume
either file with the same parser.

Contract assertions (6 tests, one per spec line in T-6.4):

1.  Default output goes to ``.ai-engineering/state/watch-residuals.json``
    relative to ``cwd`` when ``output_path`` is omitted.
2.  Schema literal is exactly ``"ai-engineering/gate-findings/v1"``;
    the document is structurally a ``GateFindingsDocument``.
3.  ``produced_by`` is the literal string ``"watch-loop"`` — distinct
    from ``ai-commit`` and ``ai-pr`` so consumers can route differently.
4.  Severity values supplied in the ``failed_checks`` list payload are
    preserved verbatim into the emitted findings (no normalisation
    or remapping). All five gate severities round-trip.
5.  Emitted JSON loads cleanly via
    ``GateFindingsDocument.model_validate_json`` (full Pydantic round-trip).
6.  Atomic write pattern (single ``os.replace`` to the target). Same
    invariant as ``orchestrator._emit_findings`` (T-2.6) and
    ``gate_cache._atomic_write`` — torn writes are impossible.

TDD CONSTRAINT: this file is IMMUTABLE after T-6.4 lands.
"""

from __future__ import annotations

import json
import os as _os
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Helpers — minimal valid ``failed_checks`` payload
# ---------------------------------------------------------------------------


def _failed_check(**overrides: Any) -> dict[str, Any]:
    """Construct one minimally valid ``failed_check`` dict.

    Mirrors the shape the watch loop produces from CI annotations: each
    entry carries enough metadata to be rendered as a ``GateFinding``
    without further enrichment by the emitter.
    """
    payload: dict[str, Any] = {
        "check": "ruff",
        "rule_id": "E501",
        "file": "src/long_line.py",
        "line": 120,
        "column": None,
        "severity": "low",
        "message": "line too long (132 > 100 chars)",
        "auto_fixable": True,
        "auto_fix_command": "ruff check --fix src/long_line.py",
    }
    payload.update(overrides)
    return payload


def _make_git_runner(branch: str | None = "main", sha: str | None = "abc1234"):
    """Return a ``subprocess.run`` side_effect that fakes ``git rev-parse``.

    Same shape as the helper used in ``test_orchestrator_emit_findings``.
    The watch-residuals emitter MAY (and is expected to) capture branch
    + commit_sha via the same git invocations because the schema is
    shared. ``None`` simulates a non-zero exit (unborn HEAD).
    """

    def _run(cmd: list[str], *args: Any, **kwargs: Any) -> mock.Mock:
        argv = list(cmd)
        proc = mock.Mock()
        proc.returncode = 0
        proc.stderr = ""
        proc.stdout = ""

        if argv[:2] == ["git", "rev-parse"]:
            if "--abbrev-ref" in argv:
                if branch is None:
                    proc.returncode = 1
                    proc.stderr = "fatal: ambiguous argument 'HEAD'"
                else:
                    proc.stdout = branch + "\n"
            elif "HEAD" in argv:
                if sha is None:
                    proc.returncode = 1
                    proc.stderr = "fatal: bad revision 'HEAD'"
                else:
                    proc.stdout = sha + "\n"
        return proc

    return _run


# ---------------------------------------------------------------------------
# 1. Default output path
# ---------------------------------------------------------------------------


def test_emit_writes_to_state_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Default output is ``.ai-engineering/state/watch-residuals.json``.

    Contract: when ``output_path`` is omitted, the emitter resolves the
    canonical state path relative to the current working directory.
    """
    # Arrange — chdir into an isolated tmp tree so the write lands here.
    monkeypatch.chdir(tmp_path)
    from ai_engineering.policy.watch_residuals import emit

    expected = tmp_path / ".ai-engineering" / "state" / "watch-residuals.json"
    assert not expected.exists(), "precondition: output file does not exist"

    # Act
    with mock.patch("subprocess.run", side_effect=_make_git_runner()):
        returned = emit(failed_checks=[_failed_check()])

    # Assert — file exists at the documented default path.
    assert expected.exists(), (
        "emit() must write to .ai-engineering/state/watch-residuals.json "
        f"by default; got {expected} missing"
    )
    assert Path(returned) == expected, (
        f"emit() must return the path it wrote; got {returned!r}, expected {expected!r}"
    )


# ---------------------------------------------------------------------------
# 2. Schema literal is v1
# ---------------------------------------------------------------------------


def test_emit_schema_v1_conforming(tmp_path: Path) -> None:
    """Emitted document carries the canonical schema-v1 literal.

    D-104-06 mandates the literal ``"ai-engineering/gate-findings/v1"``
    so consumers (spec-105 risk-accept) can reject unknown schema
    versions deterministically.
    """
    # Arrange
    from ai_engineering.policy.watch_residuals import emit

    output = tmp_path / "watch-residuals.json"

    # Act
    with mock.patch("subprocess.run", side_effect=_make_git_runner()):
        emit(
            failed_checks=[_failed_check()],
            output_path=output,
        )

    # Assert — schema literal exact match.
    on_disk = json.loads(output.read_text(encoding="utf-8"))
    assert on_disk.get("schema") == "ai-engineering/gate-findings/v1", (
        "schema literal must be the canonical v1 string per D-104-06; "
        f"got {on_disk.get('schema')!r}"
    )

    # Assert — top-level keys cover the required schema-v1 surface.
    required_keys = {
        "schema",
        "session_id",
        "produced_by",
        "produced_at",
        "branch",
        "findings",
        "wall_clock_ms",
    }
    missing = required_keys - set(on_disk.keys())
    assert not missing, (
        f"schema-v1 document must include all required top-level keys; missing {sorted(missing)!r}"
    )


# ---------------------------------------------------------------------------
# 3. produced_by is the watch-loop literal
# ---------------------------------------------------------------------------


def test_emit_produced_by_watch_loop(tmp_path: Path) -> None:
    """``produced_by`` is hard-coded to ``"watch-loop"``.

    Distinct from ``ai-commit`` and ``ai-pr`` so spec-105 risk-accept
    flow can route ``watch-residuals.json`` separately from the
    orchestrator's ``gate-findings.json``.
    """
    # Arrange
    from ai_engineering.policy.watch_residuals import emit

    output = tmp_path / "watch-residuals.json"

    # Act
    with mock.patch("subprocess.run", side_effect=_make_git_runner()):
        emit(
            failed_checks=[_failed_check()],
            output_path=output,
        )

    # Assert
    on_disk = json.loads(output.read_text(encoding="utf-8"))
    assert on_disk.get("produced_by") == "watch-loop", (
        "produced_by MUST be the literal 'watch-loop' for documents "
        "emitted from the watch loop wall-clock cap; "
        f"got {on_disk.get('produced_by')!r}"
    )


# ---------------------------------------------------------------------------
# 4. Severity preserved from CI annotations
# ---------------------------------------------------------------------------


def test_emit_severity_preserved_from_ci_annotations(tmp_path: Path) -> None:
    """Severity values from ``failed_checks`` round-trip into the document.

    The watch loop receives findings with severity already classified by
    CI annotations (e.g., semgrep emits ``high`` for security rules).
    The emitter MUST NOT downgrade, upgrade, or remap these values; the
    five gate severities (critical/high/medium/low/info) all preserve.
    """
    # Arrange — one finding per severity level.
    from ai_engineering.policy.watch_residuals import emit

    severities = ["critical", "high", "medium", "low", "info"]
    failed_checks = [
        _failed_check(
            check=f"check-{sev}",
            rule_id=f"RULE-{idx:03d}",
            file=f"src/file_{idx}.py",
            line=10 + idx,
            severity=sev,
            message=f"finding for severity {sev}",
            auto_fixable=False,
            auto_fix_command=None,
        )
        for idx, sev in enumerate(severities)
    ]

    output = tmp_path / "watch-residuals.json"

    # Act
    with mock.patch("subprocess.run", side_effect=_make_git_runner()):
        emit(
            failed_checks=failed_checks,
            output_path=output,
        )

    # Assert — severity round-trips per finding, ordering preserved.
    on_disk = json.loads(output.read_text(encoding="utf-8"))
    findings = on_disk.get("findings")
    assert isinstance(findings, list), f"findings must be a list; got {type(findings).__name__}"
    assert len(findings) == len(severities), (
        f"emit must preserve all input findings; "
        f"got {len(findings)} findings, expected {len(severities)}"
    )

    observed = [f.get("severity") for f in findings]
    assert observed == severities, (
        "severity values MUST be preserved verbatim from input failed_checks "
        "(no normalisation, no reordering); "
        f"got {observed!r}, expected {severities!r}"
    )


# ---------------------------------------------------------------------------
# 5. Round-trip via Pydantic GateFindingsDocument
# ---------------------------------------------------------------------------


def test_emit_round_trip_via_pydantic(tmp_path: Path) -> None:
    """Emitted JSON validates via ``GateFindingsDocument.model_validate_json``.

    Asserting strict Pydantic validation guarantees:

    * ``schema`` literal matches.
    * ``session_id`` is a valid UUID4.
    * ``produced_by`` is one of the three enum members.
    * ``produced_at`` is parseable ISO-8601.
    * Each finding satisfies ``GateFinding`` invariants (line >= 1,
      auto_fixable=True implies non-null auto_fix_command, severity
      is one of the five enum values).
    * ``wall_clock_ms`` is a closed three-key block.
    """
    # Arrange
    from ai_engineering.policy.watch_residuals import emit
    from ai_engineering.state.models import GateFindingsDocument

    output = tmp_path / "watch-residuals.json"

    # Act — emit a payload that exercises every required field.
    with mock.patch(
        "subprocess.run",
        side_effect=_make_git_runner(branch="feat/spec-104", sha="0" * 40),
    ):
        emit(
            failed_checks=[
                _failed_check(severity="critical", auto_fixable=False, auto_fix_command=None),
                _failed_check(
                    check="ruff",
                    rule_id="E501",
                    severity="low",
                    auto_fixable=True,
                    auto_fix_command="ruff check --fix src/long_line.py",
                ),
            ],
            output_path=output,
        )

    # Assert — strict Pydantic validation succeeds.
    raw = output.read_text(encoding="utf-8")
    try:
        doc = GateFindingsDocument.model_validate_json(raw)
    except Exception as exc:  # pragma: no cover — failure path
        pytest.fail(
            "watch_residuals.emit output must validate against "
            "GateFindingsDocument schema v1; "
            f"validation raised {type(exc).__name__}: {exc}\n--- raw ---\n{raw}"
        )

    # Sanity — produced_by survived the round-trip as the watch-loop literal.
    assert doc.produced_by == "watch-loop", (
        f"produced_by must round-trip through pydantic as 'watch-loop'; got {doc.produced_by!r}"
    )

    # Sanity — every input severity survived.
    severities = [f.severity for f in doc.findings]
    assert "critical" in severities and "low" in severities, (
        f"both input severities must survive the round-trip; got {severities!r}"
    )


# ---------------------------------------------------------------------------
# 6. Atomic write (single os.replace call)
# ---------------------------------------------------------------------------


def test_emit_atomic_write(tmp_path: Path) -> None:
    """Implementation publishes the output via a single ``os.replace`` call.

    Two assertions:

    * ``os.replace`` is invoked exactly once per ``emit()`` call.
    * The replace destination equals the requested target path; the
      source is a sibling tempfile in the same directory (so the rename
      is atomic on POSIX and never crosses filesystems).
    """
    # Arrange
    from ai_engineering.policy.watch_residuals import emit

    target = tmp_path / "watch-residuals.json"

    captured_calls: list[tuple[Path, Path]] = []
    real_replace = _os.replace

    def tracking_replace(src: str | Path, dst: str | Path) -> None:
        captured_calls.append((Path(src), Path(dst)))
        real_replace(src, dst)

    # Act — single emission; observe the publish primitive.
    with (
        mock.patch("subprocess.run", side_effect=_make_git_runner()),
        mock.patch("os.replace", side_effect=tracking_replace),
    ):
        emit(
            failed_checks=[_failed_check()],
            output_path=target,
        )

    # Assert — exactly one os.replace call landed during emit().
    assert len(captured_calls) == 1, (
        "emit() MUST invoke os.replace exactly once for atomic publish; "
        f"observed {len(captured_calls)} calls: {captured_calls!r}"
    )

    src_path, dst_path = captured_calls[0]

    # Assert — destination is the requested target.
    assert dst_path == target, (
        f"os.replace destination must equal requested target; "
        f"got dst={dst_path!r}, target={target!r}"
    )

    # Assert — source is a sibling tempfile (same directory, different name).
    assert src_path.parent == target.parent, (
        "tempfile MUST live in the target's directory so os.replace "
        f"is atomic; got src parent {src_path.parent!r}, "
        f"target parent {target.parent!r}"
    )
    assert src_path.name != target.name, (
        f"tempfile name must differ from final filename; got {src_path.name!r}"
    )

    # Assert — the surviving file on disk parses as valid schema-v1 JSON.
    on_disk = json.loads(target.read_text(encoding="utf-8"))
    assert on_disk.get("schema") == "ai-engineering/gate-findings/v1", (
        "atomic-published file must be a complete schema-v1 document; "
        f"got schema={on_disk.get('schema')!r}"
    )
