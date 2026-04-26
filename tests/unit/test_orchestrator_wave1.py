"""Unit tests for ``ai_engineering.policy.orchestrator`` Wave 1 fixers (serial).

RED phase for spec-104 T-2.1 (D-104-01 Wave 1 — three fixers run strictly
in serial because each one's output is the next one's input):

    > Wave 1 — Fixers (serial): ``ruff format`` → ``ruff check --fix`` →
    > ``ai-eng spec verify --fix``. Serial porque ``format`` modifica
    > archivos que ``check`` lee y porque ``spec verify --fix`` puede tocar
    > ``_history.md`` que otros checkers leen.

Target API (does not exist yet — created in T-2.2 GREEN):

    - ``Wave1Result`` immutable record with fields:
        * ``return_code: int`` — worst-of (max) across the three fixers.
        * ``fixers_run: list[str]`` — names of fixers actually invoked,
          in invocation order ("ruff-format", "ruff-check", "spec-verify").
        * ``files_modified: list[str]`` — union of file paths the fixers
          touched (e.g., reported on stdout / collected from filesystem
          mtime diff). Order-stable, deduplicated.
        * ``wall_clock_ms: int`` — non-zero millisecond wall-clock for
          the entire wave (across both passes when convergence re-run
          fires).

    - ``run_wave1(staged_files: list[pathlib.Path]) -> Wave1Result``
        Orchestrates the three fixers serially against the staged file
        set. Behaviour contract proved by the assertions below:
            1. Strict ordering: format → check → spec-verify.
            2. Serial timing: fixer N+1 only starts after fixer N
               returns.
            3. Failure isolation: a non-zero exit from an earlier fixer
               does NOT short-circuit later fixers (collect, don't bail).
            4. Aggregated return code is ``max`` of individual codes
               (worst-of semantics).
            5. Convergence re-run: if pass 1 modified files, pass 2 runs
               so the wave validates idempotent convergence (max one
               re-pass; if pass 2 still modifies files the ``return_code``
               reflects non-convergence).
            6. No re-run when pass 1 produced no changes (single pass).
            7. ``files_modified`` accurately captures actual paths.
            8. ``wall_clock_ms`` is populated and non-zero.
            9. Non-Python staged files skip ruff fixers gracefully.
           10. The "No active spec" placeholder skips ``spec verify``
               cleanly (no subprocess invoked).

Each test currently fails with ``ImportError`` (or ``ModuleNotFoundError``)
because ``ai_engineering.policy.orchestrator`` is not yet on the import
path. T-2.2 GREEN phase will land the module and all 10 assertions become
the contract for D-104-01 Wave 1.

TDD CONSTRAINT: this file is IMMUTABLE after T-2.1 lands. T-2.2 may only
introduce production code that satisfies these assertions; the assertions
themselves never change.
"""

from __future__ import annotations

import itertools
import time
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Helpers — synthesise mocked subprocess.CompletedProcess instances
# ---------------------------------------------------------------------------


class _CompletedProcessStub:
    """Minimal CompletedProcess shape the orchestrator expects.

    Mirrors ``subprocess.CompletedProcess`` (returncode/stdout/stderr/args)
    without pulling the heavyweight stdlib helper into a unit test where we
    only need attribute access.
    """

    def __init__(
        self,
        *,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
        args: list[str] | None = None,
    ) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.args = args or []


def _ruff_format_pass(args: list[str]) -> _CompletedProcessStub:
    return _CompletedProcessStub(
        returncode=0,
        stdout="2 files reformatted, 3 files left unchanged\n",
        stderr="",
        args=args,
    )


def _ruff_format_fail(args: list[str]) -> _CompletedProcessStub:
    return _CompletedProcessStub(
        returncode=2,
        stdout="",
        stderr="error: Failed to read src/example.py: Permission denied\n",
        args=args,
    )


def _ruff_check_pass(args: list[str]) -> _CompletedProcessStub:
    return _CompletedProcessStub(
        returncode=0,
        stdout="All checks passed!\n",
        stderr="",
        args=args,
    )


def _ruff_check_fix(args: list[str]) -> _CompletedProcessStub:
    return _CompletedProcessStub(
        returncode=0,
        stdout="Fixed 4 errors (1 fix available with `--unsafe-fixes`)\n",
        stderr="",
        args=args,
    )


def _spec_verify_pass(args: list[str]) -> _CompletedProcessStub:
    return _CompletedProcessStub(
        returncode=0,
        stdout="spec verify: OK\n",
        stderr="",
        args=args,
    )


def _spec_verify_fail(args: list[str]) -> _CompletedProcessStub:
    return _CompletedProcessStub(
        returncode=1,
        stdout="",
        stderr="spec verify: 2 plan items missing acceptance criteria\n",
        args=args,
    )


def _classify_fixer(args: list[str]) -> str:
    """Return a stable token identifying which fixer is being invoked.

    Matches against argv shape: ``["ruff", "format", ...]`` →
    ``"ruff-format"``; ``["ruff", "check", "--fix", ...]`` →
    ``"ruff-check"``; ``["ai-eng", "spec", "verify", "--fix", ...]`` →
    ``"spec-verify"``. Anything else is "unknown" so test failures are
    informative.
    """
    if not args:
        return "unknown"
    head = list(args)
    if "ruff" in head[0] and "format" in head:
        return "ruff-format"
    if "ruff" in head[0] and "check" in head:
        return "ruff-check"
    if "ai-eng" in head[0] and "verify" in head:
        return "spec-verify"
    # Some implementations may invoke via "uv run <tool>"; tolerate that.
    joined = " ".join(head)
    if "ruff format" in joined:
        return "ruff-format"
    if "ruff check" in joined:
        return "ruff-check"
    if "spec verify" in joined or ("spec" in head and "verify" in head):
        return "spec-verify"
    return "unknown"


def _python_files(tmp_path: Path) -> list[Path]:
    """Materialise two python files under ``tmp_path`` and return their paths."""
    a = tmp_path / "a.py"
    b = tmp_path / "b.py"
    a.write_text("x = 1\n", encoding="utf-8")
    b.write_text("y = 2\n", encoding="utf-8")
    return [a, b]


# ---------------------------------------------------------------------------
# Tests — 10 RED assertions wired to the T-2.2 contract
# ---------------------------------------------------------------------------


def test_wave1_runs_three_fixers_in_order(tmp_path: Path) -> None:
    """``run_wave1`` invokes ruff format → ruff check --fix → spec verify --fix.

    Captures the order via a recorded list of fixer-tokens harvested from
    each subprocess.run invocation and asserts the canonical sequence.
    """
    # Arrange
    from ai_engineering.policy.orchestrator import run_wave1

    invocations: list[str] = []

    def fake_run(args: list[str], *_: Any, **__: Any) -> _CompletedProcessStub:
        token = _classify_fixer(list(args))
        invocations.append(token)
        if token == "ruff-format":
            return _ruff_format_pass(list(args))
        if token == "ruff-check":
            return _ruff_check_pass(list(args))
        if token == "spec-verify":
            return _spec_verify_pass(list(args))
        return _CompletedProcessStub(returncode=0, args=list(args))

    staged = _python_files(tmp_path)

    # Act
    with mock.patch(
        "ai_engineering.policy.orchestrator.subprocess.run",
        side_effect=fake_run,
    ):
        result = run_wave1(staged)

    # Assert — at least one invocation per canonical fixer.
    assert "ruff-format" in invocations
    assert "ruff-check" in invocations
    assert "spec-verify" in invocations

    # Reduce to first occurrence per fixer to assert canonical ordering;
    # convergence re-runs may add further entries that we do not constrain
    # here (covered by dedicated tests below).
    first_seen: dict[str, int] = {}
    for idx, token in enumerate(invocations):
        if token in {"ruff-format", "ruff-check", "spec-verify"}:
            first_seen.setdefault(token, idx)

    assert first_seen["ruff-format"] < first_seen["ruff-check"], (
        f"ruff format must run before ruff check --fix; got invocation order {invocations!r}"
    )
    assert first_seen["ruff-check"] < first_seen["spec-verify"], (
        f"ruff check --fix must run before spec verify --fix; got invocation order {invocations!r}"
    )

    # Public-surface sanity: result.fixers_run also reflects the canonical
    # ordering for the first occurrence of each fixer.
    fixers_seen = list(result.fixers_run)
    canonical = ["ruff-format", "ruff-check", "spec-verify"]
    canonical_indices = [fixers_seen.index(name) for name in canonical if name in fixers_seen]
    assert canonical_indices == sorted(canonical_indices), (
        f"Wave1Result.fixers_run must reflect canonical first-seen ordering; got {fixers_seen!r}"
    )


def test_wave1_serial_not_parallel(tmp_path: Path) -> None:
    """The second fixer must NOT start until the first one returns.

    Each fake subprocess.run records ``enter_at`` / ``exit_at`` monotonic
    timestamps and sleeps long enough that an accidental parallel impl
    would produce overlapping intervals.
    """
    # Arrange
    from ai_engineering.policy.orchestrator import run_wave1

    timeline: list[tuple[str, str, float]] = []
    sleep_ms = 0.030  # 30 ms: comfortably above OS-scheduler jitter.

    def fake_run(args: list[str], *_: Any, **__: Any) -> _CompletedProcessStub:
        token = _classify_fixer(list(args))
        timeline.append((token, "enter", time.perf_counter()))
        time.sleep(sleep_ms)
        timeline.append((token, "exit", time.perf_counter()))
        if token == "ruff-format":
            return _ruff_format_pass(list(args))
        if token == "ruff-check":
            return _ruff_check_pass(list(args))
        if token == "spec-verify":
            return _spec_verify_pass(list(args))
        return _CompletedProcessStub(returncode=0, args=list(args))

    staged = _python_files(tmp_path)

    # Act
    with mock.patch(
        "ai_engineering.policy.orchestrator.subprocess.run",
        side_effect=fake_run,
    ):
        run_wave1(staged)

    # Assert — every (enter, exit) interval is non-overlapping.
    # Reconstruct intervals per invocation and check no two overlap.
    intervals: list[tuple[str, float, float]] = []
    open_starts: dict[int, tuple[str, float]] = {}
    for token, kind, ts in timeline:
        if kind == "enter":
            open_starts[len(intervals)] = (token, ts)
        elif kind == "exit":
            assert open_starts, f"exit without enter for {token!r}"
            idx = max(open_starts.keys())
            start_token, start_ts = open_starts.pop(idx)
            assert start_token == token, (
                f"interleaved enter/exit detected — parallelism leaked! "
                f"start={start_token}, exit={token}"
            )
            intervals.append((token, start_ts, ts))

    intervals.sort(key=lambda x: x[1])
    for prev, cur in itertools.pairwise(intervals):
        prev_token, _prev_start, prev_end = prev
        cur_token, cur_start, _cur_end = cur
        assert cur_start >= prev_end, (
            f"Wave 1 ran fixers in parallel — {cur_token!r} started at "
            f"{cur_start:.4f} before {prev_token!r} finished at {prev_end:.4f}; "
            "Wave 1 must be strictly serial."
        )


def test_wave1_continues_on_first_fixer_failure(tmp_path: Path) -> None:
    """If ruff format fails, ruff check --fix and spec verify --fix STILL run.

    Wave 1 collects results across all three fixers — it does not bail on
    the first non-zero exit. This matches the D-104-01 contract that the
    user gets the full picture even when the wave does not converge.
    """
    # Arrange
    from ai_engineering.policy.orchestrator import run_wave1

    invocations: list[str] = []

    def fake_run(args: list[str], *_: Any, **__: Any) -> _CompletedProcessStub:
        token = _classify_fixer(list(args))
        invocations.append(token)
        if token == "ruff-format":
            return _ruff_format_fail(list(args))
        if token == "ruff-check":
            return _ruff_check_pass(list(args))
        if token == "spec-verify":
            return _spec_verify_pass(list(args))
        return _CompletedProcessStub(returncode=0, args=list(args))

    staged = _python_files(tmp_path)

    # Act
    with mock.patch(
        "ai_engineering.policy.orchestrator.subprocess.run",
        side_effect=fake_run,
    ):
        result = run_wave1(staged)

    # Assert — every fixer was still invoked despite ruff format's failure.
    assert "ruff-format" in invocations
    assert "ruff-check" in invocations, (
        f"ruff check --fix MUST run even when ruff format fails — invocations: {invocations!r}"
    )
    assert "spec-verify" in invocations, (
        f"spec verify --fix MUST run even when ruff format fails — invocations: {invocations!r}"
    )

    # The aggregate return code reflects the failure.
    assert result.return_code != 0, (
        f"Wave1Result.return_code must surface the upstream failure; got {result.return_code!r}"
    )
    # All three fixers are recorded as having run.
    for name in ("ruff-format", "ruff-check", "spec-verify"):
        assert name in result.fixers_run


def test_wave1_returns_aggregate_return_code(tmp_path: Path) -> None:
    """Aggregate ``return_code`` == max(individual return codes) — worst-of.

    Mock returns 0 (format), 0 (check), 1 (spec-verify). Expect 1.
    Mock returns 2 (format), 0 (check), 1 (spec-verify). Expect 2.
    """
    # Arrange
    from ai_engineering.policy.orchestrator import run_wave1

    staged = _python_files(tmp_path)

    # Scenario A: only spec-verify fails (rc=1).
    def fake_run_a(args: list[str], *_: Any, **__: Any) -> _CompletedProcessStub:
        token = _classify_fixer(list(args))
        if token == "ruff-format":
            return _ruff_format_pass(list(args))
        if token == "ruff-check":
            return _ruff_check_pass(list(args))
        if token == "spec-verify":
            return _spec_verify_fail(list(args))
        return _CompletedProcessStub(returncode=0, args=list(args))

    with mock.patch(
        "ai_engineering.policy.orchestrator.subprocess.run",
        side_effect=fake_run_a,
    ):
        result_a = run_wave1(staged)

    assert result_a.return_code == 1, (
        f"Expected worst-of=1 (spec-verify failed), got {result_a.return_code!r}"
    )

    # Scenario B: format fails harder (rc=2) than spec-verify (rc=1).
    def fake_run_b(args: list[str], *_: Any, **__: Any) -> _CompletedProcessStub:
        token = _classify_fixer(list(args))
        if token == "ruff-format":
            return _ruff_format_fail(list(args))  # rc=2
        if token == "ruff-check":
            return _ruff_check_pass(list(args))  # rc=0
        if token == "spec-verify":
            return _spec_verify_fail(list(args))  # rc=1
        return _CompletedProcessStub(returncode=0, args=list(args))

    with mock.patch(
        "ai_engineering.policy.orchestrator.subprocess.run",
        side_effect=fake_run_b,
    ):
        result_b = run_wave1(staged)

    assert result_b.return_code == 2, (
        f"Expected worst-of=2 (format=2 dominates), got {result_b.return_code!r}"
    )


def test_wave1_intra_wave_rerun_on_changes(tmp_path: Path) -> None:
    """If pass 1 produces file changes, fixers run a second time.

    Per D-104-01 (Wave 1 fixers): ``Wave 1 falla solo si los fixers no
    convergen tras un re-run automático intra-wave``. So the orchestrator
    must invoke each fixer twice when pass 1 reports any file modification.
    Convergence is bounded to a single re-pass to prevent runaway loops.
    """
    # Arrange
    from ai_engineering.policy.orchestrator import run_wave1

    invocations: list[str] = []
    pass_counter = {"ruff-format": 0, "ruff-check": 0, "spec-verify": 0}
    staged = _python_files(tmp_path)

    def fake_run(args: list[str], *_: Any, **__: Any) -> _CompletedProcessStub:
        token = _classify_fixer(list(args))
        invocations.append(token)
        if token in pass_counter:
            pass_counter[token] += 1

        if token == "ruff-format":
            # Pass 1: report file changes; Pass 2: stable / no-op.
            if pass_counter["ruff-format"] == 1:
                # Touch the staged file's mtime to simulate a real reformat.
                target = staged[0]
                target.write_text("x = 1  # reformatted\n", encoding="utf-8")
                return _CompletedProcessStub(
                    returncode=0,
                    stdout="1 file reformatted, 1 file left unchanged\n",
                    stderr="",
                    args=list(args),
                )
            return _ruff_format_pass(list(args))
        if token == "ruff-check":
            return _ruff_check_pass(list(args))
        if token == "spec-verify":
            return _spec_verify_pass(list(args))
        return _CompletedProcessStub(returncode=0, args=list(args))

    # Act
    with mock.patch(
        "ai_engineering.policy.orchestrator.subprocess.run",
        side_effect=fake_run,
    ):
        run_wave1(staged)

    # Assert — each canonical fixer was invoked twice (pass 1 + convergence pass 2).
    assert pass_counter["ruff-format"] == 2, (
        "ruff-format must re-run after pass 1 modifies files; "
        f"counters={pass_counter!r}, invocations={invocations!r}"
    )
    assert pass_counter["ruff-check"] >= 2, (
        "ruff-check must re-run on the convergence pass; "
        f"counters={pass_counter!r}, invocations={invocations!r}"
    )
    assert pass_counter["spec-verify"] >= 2, (
        "spec-verify must re-run on the convergence pass; "
        f"counters={pass_counter!r}, invocations={invocations!r}"
    )

    # And convergence is bounded to ONE re-pass — no third pass.
    for name, count in pass_counter.items():
        assert count <= 2, (
            f"{name} ran {count} times; convergence re-run must be capped at 1 "
            "(2 total passes max)."
        )


def test_wave1_no_rerun_when_no_changes(tmp_path: Path) -> None:
    """Single pass when pass 1 modifies no files — no convergence re-run.

    The opposite of the previous test: pass 1 reports zero modifications
    so the orchestrator returns immediately without spawning a redundant
    pass 2.
    """
    # Arrange
    from ai_engineering.policy.orchestrator import run_wave1

    pass_counter = {"ruff-format": 0, "ruff-check": 0, "spec-verify": 0}
    staged = _python_files(tmp_path)

    def fake_run(args: list[str], *_: Any, **__: Any) -> _CompletedProcessStub:
        token = _classify_fixer(list(args))
        if token in pass_counter:
            pass_counter[token] += 1

        if token == "ruff-format":
            return _CompletedProcessStub(
                returncode=0,
                stdout="0 files reformatted, 5 files left unchanged\n",
                stderr="",
                args=list(args),
            )
        if token == "ruff-check":
            return _CompletedProcessStub(
                returncode=0,
                stdout="All checks passed!\n",
                stderr="",
                args=list(args),
            )
        if token == "spec-verify":
            return _spec_verify_pass(list(args))
        return _CompletedProcessStub(returncode=0, args=list(args))

    # Act
    with mock.patch(
        "ai_engineering.policy.orchestrator.subprocess.run",
        side_effect=fake_run,
    ):
        result = run_wave1(staged)

    # Assert — exactly one invocation per canonical fixer (no convergence pass).
    assert pass_counter == {"ruff-format": 1, "ruff-check": 1, "spec-verify": 1}, (
        "When pass 1 modifies nothing, Wave 1 must NOT re-run the fixers; "
        f"counters={pass_counter!r}"
    )

    # files_modified is empty; return_code is success.
    assert list(result.files_modified) == [], (
        f"files_modified must be empty when no fixer touched a file; got {result.files_modified!r}"
    )
    assert result.return_code == 0


def test_wave1_records_files_modified(tmp_path: Path) -> None:
    """``files_modified`` captures actual paths the fixers changed.

    Mock ruff format to physically modify ``staged[0]`` and ruff check to
    modify ``staged[1]``. The result's ``files_modified`` set must contain
    both file paths (deduplicated, order-stable).
    """
    # Arrange
    from ai_engineering.policy.orchestrator import run_wave1

    staged = _python_files(tmp_path)
    a, b = staged

    def fake_run(args: list[str], *_: Any, **__: Any) -> _CompletedProcessStub:
        token = _classify_fixer(list(args))
        if token == "ruff-format":
            # Touch a.py
            a.write_text("x = 1  # reformatted\n", encoding="utf-8")
            return _CompletedProcessStub(
                returncode=0,
                stdout=f"1 file reformatted: {a}\n1 file left unchanged\n",
                stderr="",
                args=list(args),
            )
        if token == "ruff-check":
            # Touch b.py
            b.write_text("y = 2  # autofixed\n", encoding="utf-8")
            return _CompletedProcessStub(
                returncode=0,
                stdout=f"Fixed 1 error in {b}\n",
                stderr="",
                args=list(args),
            )
        if token == "spec-verify":
            return _spec_verify_pass(list(args))
        return _CompletedProcessStub(returncode=0, args=list(args))

    # Act
    with mock.patch(
        "ai_engineering.policy.orchestrator.subprocess.run",
        side_effect=fake_run,
    ):
        result = run_wave1(staged)

    # Assert — both files are reported in files_modified.
    modified_paths = {Path(p).resolve() for p in result.files_modified}
    assert a.resolve() in modified_paths, (
        f"a.py expected in files_modified; got {result.files_modified!r}"
    )
    assert b.resolve() in modified_paths, (
        f"b.py expected in files_modified; got {result.files_modified!r}"
    )

    # Deduplicated — listing each path at most once.
    assert len(result.files_modified) == len(set(result.files_modified)), (
        f"files_modified must be deduplicated; got {result.files_modified!r}"
    )


def test_wave1_wall_clock_ms_populated(tmp_path: Path) -> None:
    """``wall_clock_ms`` is non-zero milliseconds for the wave run.

    Each mocked fixer sleeps ~10 ms; over three fixers the wall clock must
    measurably exceed zero. This is the contract that telemetry consumers
    (gate-findings.json wall_clock_ms field, perf benchmarks) rely on.
    """
    # Arrange
    from ai_engineering.policy.orchestrator import run_wave1

    sleep_ms = 0.010

    def fake_run(args: list[str], *_: Any, **__: Any) -> _CompletedProcessStub:
        token = _classify_fixer(list(args))
        time.sleep(sleep_ms)
        if token == "ruff-format":
            return _ruff_format_pass(list(args))
        if token == "ruff-check":
            return _ruff_check_pass(list(args))
        if token == "spec-verify":
            return _spec_verify_pass(list(args))
        return _CompletedProcessStub(returncode=0, args=list(args))

    staged = _python_files(tmp_path)

    # Act
    with mock.patch(
        "ai_engineering.policy.orchestrator.subprocess.run",
        side_effect=fake_run,
    ):
        result = run_wave1(staged)

    # Assert — wall_clock_ms is an int and non-zero.
    assert isinstance(result.wall_clock_ms, int), (
        f"wall_clock_ms must be int; got {type(result.wall_clock_ms).__name__}"
    )
    assert result.wall_clock_ms > 0, (
        f"wall_clock_ms must be > 0 ms after running 3 mocked fixers; got {result.wall_clock_ms!r}"
    )


def test_wave1_skips_ruff_when_no_python_files(tmp_path: Path) -> None:
    """Non-Python staged files → ruff fixers are skipped gracefully.

    Per D-104-01 + R-13 (graceful skip semantics): if the staged file set
    contains zero ``.py`` files, ruff format and ruff check are skipped
    without spawning a subprocess. ``spec verify --fix`` still runs because
    it inspects ``.ai-engineering/specs/`` regardless of staged files.
    """
    # Arrange
    from ai_engineering.policy.orchestrator import run_wave1

    invocations: list[str] = []

    def fake_run(args: list[str], *_: Any, **__: Any) -> _CompletedProcessStub:
        token = _classify_fixer(list(args))
        invocations.append(token)
        if token == "spec-verify":
            return _spec_verify_pass(list(args))
        # Should not reach for ruff-format / ruff-check when no python files.
        return _CompletedProcessStub(returncode=0, args=list(args))

    md = tmp_path / "README.md"
    md.write_text("# title\n", encoding="utf-8")
    yaml = tmp_path / "config.yaml"
    yaml.write_text("key: value\n", encoding="utf-8")
    staged_non_python = [md, yaml]

    # Act
    with mock.patch(
        "ai_engineering.policy.orchestrator.subprocess.run",
        side_effect=fake_run,
    ):
        result = run_wave1(staged_non_python)

    # Assert — neither ruff fixer was invoked.
    assert "ruff-format" not in invocations, (
        f"ruff-format must be skipped when no .py files staged; invocations={invocations!r}"
    )
    assert "ruff-check" not in invocations, (
        f"ruff-check must be skipped when no .py files staged; invocations={invocations!r}"
    )

    # And the result reflects the skip — fixers_run does NOT include ruff entries.
    assert "ruff-format" not in result.fixers_run
    assert "ruff-check" not in result.fixers_run

    # Wave still considered successful (skip is not a failure).
    assert result.return_code == 0, (
        "Skipping ruff for non-python staged files must NOT raise return_code; "
        f"got {result.return_code!r}"
    )


def test_wave1_handles_no_active_spec(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When ``.ai-engineering/specs/spec.md`` is the "No active spec" placeholder,
    skip ``spec verify --fix`` gracefully (no subprocess invoked).

    Per ``cli_commands/spec_cmd.py`` the placeholder marker is the literal
    line ``# No active spec`` (case-sensitive, beginning of the file). The
    orchestrator must detect this and skip the spec-verify subprocess call
    so noise is not added to the audit trail.
    """
    # Arrange
    from ai_engineering.policy.orchestrator import run_wave1

    # Construct a synthetic project root with the placeholder spec.
    project_root = tmp_path / "project"
    spec_dir = project_root / ".ai-engineering" / "specs"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text(
        "# No active spec\n\nUse `/ai-brainstorm` to start a new one.\n",
        encoding="utf-8",
    )

    # Pivot the orchestrator's working directory to the synthetic project.
    monkeypatch.chdir(project_root)

    invocations: list[str] = []

    def fake_run(args: list[str], *_: Any, **__: Any) -> _CompletedProcessStub:
        token = _classify_fixer(list(args))
        invocations.append(token)
        if token == "ruff-format":
            return _ruff_format_pass(list(args))
        if token == "ruff-check":
            return _ruff_check_pass(list(args))
        # spec-verify should be skipped — if we reach here, the test fails.
        return _CompletedProcessStub(returncode=0, args=list(args))

    # Stage a python file inside the project so ruff still runs.
    py = project_root / "main.py"
    py.write_text("z = 3\n", encoding="utf-8")

    # Act
    with mock.patch(
        "ai_engineering.policy.orchestrator.subprocess.run",
        side_effect=fake_run,
    ):
        result = run_wave1([py])

    # Assert — spec-verify was NOT invoked.
    assert "spec-verify" not in invocations, (
        "spec-verify --fix must be skipped when spec.md is the 'No active spec' "
        f"placeholder; invocations={invocations!r}"
    )

    # And the result reflects the skip.
    assert "spec-verify" not in result.fixers_run, (
        f"Wave1Result.fixers_run must omit skipped spec-verify; got {result.fixers_run!r}"
    )

    # Skip is success, not failure.
    assert result.return_code == 0, (
        "Skipping spec-verify for placeholder spec must NOT raise return_code; "
        f"got {result.return_code!r}"
    )
