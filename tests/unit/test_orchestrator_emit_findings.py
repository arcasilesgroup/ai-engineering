"""RED tests for spec-104 T-2.5 — ``orchestrator._emit_findings`` JSON emission.

These tests pin the contract of the not-yet-implemented JSON emitter for
``gate-findings.json`` per spec-104 D-104-06 schema v1. T-2.6 GREEN phase
will land ``_emit_findings`` in ``ai_engineering.policy.orchestrator``;
this file is IMMUTABLE after T-2.5 -- T-2.6 may only adjust the
implementation to satisfy these assertions, never edit the assertions.

Target function (does not exist yet, created in T-2.6)::

    def _emit_findings(
        wave1: Wave1Result,
        wave2: Wave2Result,
        cache_stats: dict[str, list[str]],
        output_path: Path,
        produced_by: str,
    ) -> Path: ...

Contract assertions (10 tests, one per spec line in T-2.5):

1.  Output goes to ``.ai-engineering/state/gate-findings.json`` by default
    when called via the orchestrator entry point with no override.
2.  Schema literal is exactly ``"ai-engineering/gate-findings/v1"``.
3.  ``session_id`` is a freshly generated UUID4 (different across calls).
4.  ``produced_by`` parameter (``ai-commit``|``ai-pr``|``watch-loop``)
    propagates to the document.
5.  ``produced_at`` is a parseable ISO-8601 string in UTC.
6.  ``branch`` captured via ``git rev-parse --abbrev-ref HEAD`` (mocked).
7.  ``commit_sha`` captured via ``git rev-parse HEAD`` (mocked); ``null``
    when the working tree has no HEAD (uncommitted).
8.  ``wall_clock_ms`` aggregates wave1_fixers + wave2_checkers + total.
9.  Output JSON loads cleanly via ``GateFindingsDocument.model_validate_json``.
10. Atomic write pattern (tempfile + ``os.replace``) shared with
    ``gate_cache._atomic_write`` -- last-writer-wins, no half-written files.

TDD CONSTRAINT: this file is IMMUTABLE after T-2.5 lands.
"""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest import mock

import pytest

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Helpers — minimal valid Wave1/Wave2 result shapes
# ---------------------------------------------------------------------------


def _make_wave1(**overrides: Any) -> Any:
    """Construct a minimal valid ``Wave1Result``.

    The orchestrator module does not yet exist, so we defer the import to
    test-call time to keep the import-graph honest (RED ⇒ ImportError on
    the first failing assertion).
    """
    from ai_engineering.policy.orchestrator import Wave1Result

    payload: dict[str, Any] = {
        "auto_fixed": [
            {
                "check": "ruff-format",
                "files": ["src/example.py"],
                "rules_fixed": ["W291"],
            }
        ],
        "wall_clock_ms": 1234,
    }
    payload.update(overrides)
    return Wave1Result(**payload)


def _make_wave2(**overrides: Any) -> Any:
    """Construct a minimal valid ``Wave2Result``."""
    from ai_engineering.policy.orchestrator import Wave2Result

    payload: dict[str, Any] = {
        "findings": [
            {
                "check": "ruff",
                "rule_id": "E501",
                "file": "src/example.py",
                "line": 10,
                "column": 80,
                "severity": "low",
                "message": "Line too long",
                "auto_fixable": True,
                "auto_fix_command": "ruff check --fix src/example.py",
            }
        ],
        "wall_clock_ms": 5678,
    }
    payload.update(overrides)
    return Wave2Result(**payload)


def _cache_stats(
    hits: list[str] | None = None,
    misses: list[str] | None = None,
) -> dict[str, list[str]]:
    """Return a cache_stats dict with the documented two-key shape."""
    return {
        "cache_hits": list(hits) if hits is not None else ["gitleaks"],
        "cache_misses": list(misses) if misses is not None else ["ruff-check", "ty"],
    }


def _make_git_runner(branch: str | None, sha: str | None):
    """Return a ``subprocess.run`` side_effect that fakes ``git rev-parse``.

    The faked runner inspects the argv of each call and dispatches to the
    correct stub:

        * ``git rev-parse --abbrev-ref HEAD`` -> ``branch``
        * ``git rev-parse HEAD`` -> ``sha``

    Passing ``None`` for either return value simulates a non-zero exit
    (e.g. an unborn HEAD ``commit_sha = None`` case).
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


def test_emit_findings_writes_to_state_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Output goes to ``.ai-engineering/state/gate-findings.json`` by default."""
    # Arrange
    monkeypatch.chdir(tmp_path)
    from ai_engineering.policy.orchestrator import _emit_findings

    output = tmp_path / ".ai-engineering" / "state" / "gate-findings.json"
    assert not output.exists(), "precondition: output file does not exist"

    # Act
    with mock.patch("subprocess.run", side_effect=_make_git_runner("feat/spec-104", "abc1234")):
        returned = _emit_findings(
            wave1=_make_wave1(),
            wave2=_make_wave2(),
            cache_stats=_cache_stats(),
            output_path=output,
            produced_by="ai-commit",
        )

    # Assert
    assert output.exists(), (
        "_emit_findings must write to the requested output_path "
        f"(.ai-engineering/state/gate-findings.json); got {output} missing"
    )
    assert returned == output, (
        f"_emit_findings must return the path it wrote; got {returned!r}, expected {output!r}"
    )


# ---------------------------------------------------------------------------
# 2. Schema literal
# ---------------------------------------------------------------------------


def test_emit_findings_schema_v1_literal(tmp_path: Path) -> None:
    """Emitted JSON has ``"schema": "ai-engineering/gate-findings/v1"``."""
    # Arrange
    from ai_engineering.policy.orchestrator import _emit_findings

    output = tmp_path / "gate-findings.json"

    # Act
    with mock.patch("subprocess.run", side_effect=_make_git_runner("main", "deadbeef")):
        _emit_findings(
            wave1=_make_wave1(),
            wave2=_make_wave2(),
            cache_stats=_cache_stats(),
            output_path=output,
            produced_by="ai-pr",
        )

    # Assert
    on_disk = json.loads(output.read_text(encoding="utf-8"))
    assert on_disk.get("schema") == "ai-engineering/gate-findings/v1", (
        "schema literal must be the canonical v1 string per D-104-06; "
        f"got {on_disk.get('schema')!r}"
    )


# ---------------------------------------------------------------------------
# 3. UUID4 session_id
# ---------------------------------------------------------------------------


def test_emit_findings_session_id_is_uuid4(tmp_path: Path) -> None:
    """``session_id`` is a freshly generated UUID4; differs across calls."""
    # Arrange
    from ai_engineering.policy.orchestrator import _emit_findings

    out_a = tmp_path / "a.json"
    out_b = tmp_path / "b.json"

    # Act — two consecutive emissions with identical inputs
    with mock.patch("subprocess.run", side_effect=_make_git_runner("main", "deadbeef")):
        _emit_findings(
            wave1=_make_wave1(),
            wave2=_make_wave2(),
            cache_stats=_cache_stats(),
            output_path=out_a,
            produced_by="ai-pr",
        )
        _emit_findings(
            wave1=_make_wave1(),
            wave2=_make_wave2(),
            cache_stats=_cache_stats(),
            output_path=out_b,
            produced_by="ai-pr",
        )

    # Assert — both are valid UUID4s and they differ.
    raw_a = json.loads(out_a.read_text(encoding="utf-8"))
    raw_b = json.loads(out_b.read_text(encoding="utf-8"))

    sid_a = raw_a.get("session_id", "")
    sid_b = raw_b.get("session_id", "")

    parsed_a = uuid.UUID(str(sid_a))
    parsed_b = uuid.UUID(str(sid_b))

    assert parsed_a.version == 4, f"session_id must be UUID4; got version {parsed_a.version}"
    assert parsed_b.version == 4, f"session_id must be UUID4; got version {parsed_b.version}"
    assert sid_a != sid_b, (
        "two consecutive emissions must produce distinct session_ids "
        "(fresh UUID4 per call); both were equal"
    )


# ---------------------------------------------------------------------------
# 4. produced_by propagated
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("producer", ["ai-commit", "ai-pr", "watch-loop"])
def test_emit_findings_produced_by_propagated(tmp_path: Path, producer: str) -> None:
    """``produced_by`` parameter (one of three enum values) reaches the output."""
    # Arrange
    from ai_engineering.policy.orchestrator import _emit_findings

    output = tmp_path / "gf.json"

    # Act
    with mock.patch("subprocess.run", side_effect=_make_git_runner("main", "abc")):
        _emit_findings(
            wave1=_make_wave1(),
            wave2=_make_wave2(),
            cache_stats=_cache_stats(),
            output_path=output,
            produced_by=producer,
        )

    # Assert
    on_disk = json.loads(output.read_text(encoding="utf-8"))
    assert on_disk.get("produced_by") == producer, (
        f"produced_by must be propagated verbatim; got {on_disk.get('produced_by')!r}, "
        f"expected {producer!r}"
    )


# ---------------------------------------------------------------------------
# 5. produced_at ISO-8601 UTC
# ---------------------------------------------------------------------------


def test_emit_findings_produced_at_iso8601_utc(tmp_path: Path) -> None:
    """``produced_at`` is parseable ISO-8601 carrying a UTC offset."""
    # Arrange
    from ai_engineering.policy.orchestrator import _emit_findings

    output = tmp_path / "gf.json"

    # Act
    with mock.patch("subprocess.run", side_effect=_make_git_runner("main", "abc")):
        _emit_findings(
            wave1=_make_wave1(),
            wave2=_make_wave2(),
            cache_stats=_cache_stats(),
            output_path=output,
            produced_by="ai-commit",
        )

    # Assert
    on_disk = json.loads(output.read_text(encoding="utf-8"))
    raw = on_disk.get("produced_at")
    assert isinstance(raw, str) and raw, f"produced_at must be a non-empty string; got {raw!r}"

    # Accept "...Z" (UTC suffix) by normalising before parsing.
    candidate = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:  # pragma: no cover — failure path
        pytest.fail(f"produced_at must be ISO-8601 parseable; raw={raw!r}, error={exc}")

    assert parsed.tzinfo is not None, (
        f"produced_at must carry a timezone (UTC); got naive datetime {parsed!r}"
    )
    offset = parsed.utcoffset()
    assert offset is not None and offset.total_seconds() == 0, (
        f"produced_at must be UTC (offset 0); got offset {offset!r}"
    )


# ---------------------------------------------------------------------------
# 6. Branch captured from git
# ---------------------------------------------------------------------------


def test_emit_findings_branch_captured_from_git(tmp_path: Path) -> None:
    """``branch`` is the result of ``git rev-parse --abbrev-ref HEAD``."""
    # Arrange
    from ai_engineering.policy.orchestrator import _emit_findings

    output = tmp_path / "gf.json"
    expected_branch = "feat/spec-104-pipeline-speed"

    runner = _make_git_runner(branch=expected_branch, sha="0" * 40)

    # Act
    with mock.patch("subprocess.run", side_effect=runner) as mocked:
        _emit_findings(
            wave1=_make_wave1(),
            wave2=_make_wave2(),
            cache_stats=_cache_stats(),
            output_path=output,
            produced_by="ai-pr",
        )

    # Assert — the command was actually invoked (we mocked subprocess.run).
    invoked_argvs = [
        list(call.args[0]) if call.args else list(call.kwargs.get("args", []))
        for call in mocked.call_args_list
    ]
    assert any(
        "git" in argv and "rev-parse" in argv and "--abbrev-ref" in argv for argv in invoked_argvs
    ), (
        "_emit_findings must invoke `git rev-parse --abbrev-ref HEAD`; "
        f"observed argvs: {invoked_argvs!r}"
    )

    # Assert — the captured branch is in the document.
    on_disk = json.loads(output.read_text(encoding="utf-8"))
    assert on_disk.get("branch") == expected_branch, (
        f"branch must be captured from git; got {on_disk.get('branch')!r}, "
        f"expected {expected_branch!r}"
    )


# ---------------------------------------------------------------------------
# 7. commit_sha captured (or null when uncommitted)
# ---------------------------------------------------------------------------


def test_emit_findings_commit_sha_captured(tmp_path: Path) -> None:
    """``commit_sha`` is captured from ``git rev-parse HEAD``; null when no HEAD."""
    # Arrange
    from ai_engineering.policy.orchestrator import _emit_findings

    out_a = tmp_path / "a.json"
    out_b = tmp_path / "b.json"

    full_sha = "deadbeefcafebabefeedface0123456789abcdef"

    # Act — Case A: HEAD exists.
    with mock.patch("subprocess.run", side_effect=_make_git_runner(branch="main", sha=full_sha)):
        _emit_findings(
            wave1=_make_wave1(),
            wave2=_make_wave2(),
            cache_stats=_cache_stats(),
            output_path=out_a,
            produced_by="ai-pr",
        )

    # Act — Case B: HEAD missing (unborn / uncommitted).
    with mock.patch("subprocess.run", side_effect=_make_git_runner(branch="main", sha=None)):
        _emit_findings(
            wave1=_make_wave1(),
            wave2=_make_wave2(),
            cache_stats=_cache_stats(),
            output_path=out_b,
            produced_by="ai-pr",
        )

    # Assert — Case A captures the sha verbatim.
    on_disk_a = json.loads(out_a.read_text(encoding="utf-8"))
    assert on_disk_a.get("commit_sha") == full_sha, (
        f"commit_sha must be captured from `git rev-parse HEAD`; "
        f"got {on_disk_a.get('commit_sha')!r}, expected {full_sha!r}"
    )

    # Assert — Case B records ``null`` when there is no HEAD.
    on_disk_b = json.loads(out_b.read_text(encoding="utf-8"))
    assert on_disk_b.get("commit_sha") is None, (
        f"commit_sha must be JSON null when HEAD is unborn; got {on_disk_b.get('commit_sha')!r}"
    )


# ---------------------------------------------------------------------------
# 8. wall_clock_ms aggregated from waves
# ---------------------------------------------------------------------------


def test_emit_findings_wall_clock_ms_aggregated(tmp_path: Path) -> None:
    """``wall_clock_ms`` populates wave1_fixers + wave2_checkers + total."""
    # Arrange
    from ai_engineering.policy.orchestrator import _emit_findings

    output = tmp_path / "gf.json"

    wave1 = _make_wave1(wall_clock_ms=4321)
    wave2 = _make_wave2(wall_clock_ms=8765)

    # Act
    with mock.patch("subprocess.run", side_effect=_make_git_runner("main", "abc")):
        _emit_findings(
            wave1=wave1,
            wave2=wave2,
            cache_stats=_cache_stats(),
            output_path=output,
            produced_by="ai-commit",
        )

    # Assert — exact three-key block, total == sum of waves.
    on_disk = json.loads(output.read_text(encoding="utf-8"))
    block = on_disk.get("wall_clock_ms")
    assert isinstance(block, dict), f"wall_clock_ms must be an object; got {type(block).__name__}"
    assert set(block.keys()) == {"wave1_fixers", "wave2_checkers", "total"}, (
        f"wall_clock_ms must contain exactly the three documented keys; "
        f"got keys {sorted(block.keys())!r}"
    )
    assert block["wave1_fixers"] == 4321, (
        f"wave1_fixers must mirror wave1.wall_clock_ms; got {block['wave1_fixers']!r}"
    )
    assert block["wave2_checkers"] == 8765, (
        f"wave2_checkers must mirror wave2.wall_clock_ms; got {block['wave2_checkers']!r}"
    )
    assert block["total"] == 4321 + 8765, (
        f"total must equal wave1_fixers + wave2_checkers; "
        f"got {block['total']!r}, expected {4321 + 8765}"
    )


# ---------------------------------------------------------------------------
# 9. Round-trip via Pydantic model
# ---------------------------------------------------------------------------


def test_emit_findings_validates_against_pydantic(tmp_path: Path) -> None:
    """Emitted JSON validates via ``GateFindingsDocument.model_validate_json``."""
    # Arrange
    from ai_engineering.policy.orchestrator import _emit_findings
    from ai_engineering.state.models import GateFindingsDocument

    output = tmp_path / "gf.json"

    # Act
    with mock.patch(
        "subprocess.run",
        side_effect=_make_git_runner("feat/branch", "1" * 40),
    ):
        _emit_findings(
            wave1=_make_wave1(),
            wave2=_make_wave2(),
            cache_stats=_cache_stats(hits=["gitleaks"], misses=["ty"]),
            output_path=output,
            produced_by="watch-loop",
        )

    # Assert — strict Pydantic validation succeeds.
    raw = output.read_text(encoding="utf-8")
    try:
        doc = GateFindingsDocument.model_validate_json(raw)
    except Exception as exc:  # pragma: no cover — failure path
        pytest.fail(
            f"_emit_findings output must validate against GateFindingsDocument schema v1; "
            f"validation raised {type(exc).__name__}: {exc}\n--- raw ---\n{raw}"
        )

    # Sanity — the validated model carries the producer we passed in.
    assert doc.produced_by == "watch-loop", (
        f"produced_by must round-trip through pydantic; got {doc.produced_by!r}"
    )


# ---------------------------------------------------------------------------
# 10. Atomic write (tempfile + os.replace)
# ---------------------------------------------------------------------------


def test_emit_findings_atomic_write(tmp_path: Path) -> None:
    """Implementation uses the same atomic-write pattern as ``gate_cache``.

    Two assertions:

    * Single ``os.replace`` call publishes a sibling tempfile to the target.
      The tempfile MUST live in the same directory as the target so the
      rename is atomic on POSIX (and not cross-device).
    * Concurrent emissions never produce a half-written file -- every
      surviving payload parses to a complete schema-v1 document.
    """
    # Arrange
    from ai_engineering.policy.orchestrator import _emit_findings

    target = tmp_path / "gf.json"
    captured: dict[str, Path] = {}

    import os as _os

    real_replace = _os.replace

    def tracking_replace(src: str | Path, dst: str | Path) -> None:
        captured.setdefault("src", Path(src))
        captured.setdefault("dst", Path(dst))
        real_replace(src, dst)

    # Act — single emission, observe the publish primitive.
    with (
        mock.patch("subprocess.run", side_effect=_make_git_runner("main", "abc")),
        mock.patch("os.replace", side_effect=tracking_replace),
    ):
        _emit_findings(
            wave1=_make_wave1(),
            wave2=_make_wave2(),
            cache_stats=_cache_stats(),
            output_path=target,
            produced_by="ai-commit",
        )

    # Assert — os.replace was invoked on a sibling tempfile.
    assert "src" in captured, (
        "_emit_findings must publish via os.replace (atomic write); no os.replace call was observed"
    )
    assert captured["dst"] == target, (
        f"os.replace destination must equal the requested target; "
        f"got dst={captured['dst']!r}, target={target!r}"
    )
    assert captured["src"].parent == target.parent, (
        "tempfile MUST be a sibling of the target (same directory) so "
        "os.replace is atomic; got src parent "
        f"{captured['src'].parent!r}, target parent {target.parent!r}"
    )
    assert captured["src"].name != target.name, (
        f"tempfile name must differ from final filename; got {captured['src'].name!r}"
    )

    # Act — concurrent emissions on the same path. The subprocess.run patch
    # is installed ONCE around the whole thread fan-out: nested `mock.patch`
    # contexts inside worker threads are not thread-safe (the patcher's
    # save/restore stack is module-level), so per-thread `with mock.patch`
    # blocks would leak the mock past test-end and contaminate later tests
    # that drive real subprocesses (e.g. test_safe_run_env_scrub).
    concurrent_target = tmp_path / "concurrent.json"
    writers = 6
    errors: list[BaseException] = []
    barrier = threading.Barrier(writers)

    def _worker(idx: int) -> None:
        try:
            barrier.wait(timeout=10)
            _emit_findings(
                wave1=_make_wave1(wall_clock_ms=100 + idx),
                wave2=_make_wave2(wall_clock_ms=200 + idx),
                cache_stats=_cache_stats(),
                output_path=concurrent_target,
                produced_by="ai-pr",
            )
        except BaseException as exc:  # pragma: no cover — captured in assertion
            errors.append(exc)

    with mock.patch(
        "subprocess.run",
        side_effect=_make_git_runner("main", "abc1234"),
    ):
        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(writers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

    # Assert — every writer finished cleanly and the surviving file is intact.
    assert not errors, f"concurrent emit raised: {errors!r}"
    assert concurrent_target.exists(), "concurrent target must exist after writes"

    on_disk = json.loads(concurrent_target.read_text(encoding="utf-8"))
    assert on_disk.get("schema") == "ai-engineering/gate-findings/v1", (
        "concurrent surviving file must be a valid schema-v1 document; "
        f"got schema={on_disk.get('schema')!r}"
    )
