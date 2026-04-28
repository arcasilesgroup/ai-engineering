"""RED tests for spec-104 T-3.1 — ``ai-eng gate run`` CLI flag surface.

These tests pin the contract of the not-yet-implemented ``ai-eng gate run``
sub-command per spec-104 D-104-10. T-3.2 GREEN phase will extend
``ai_engineering.cli_commands.gate`` with the new flags + JSON emission;
this file is IMMUTABLE after T-3.1 -- T-3.2 may only adjust the
implementation to satisfy these assertions, never edit the assertions.

Target sub-command (does not exist yet, created in T-3.2)::

    ai-eng gate run [--cache-aware] [--no-cache] [--force]
                    [--json] [--mode={local,ci}] [--target PATH]

Contract (12 tests, mapped to T-3.1 plan):

1.  Default behaviour: invocation without flags uses the cache (cache-aware ON).
2.  ``--no-cache`` skips the lookup; verified by patching ``gate_cache.lookup``
    as a spy and asserting zero invocations.
3.  ``--force`` skips the lookup AND clears the matching entry; verified by
    asserting ``gate_cache.clear_entry`` was called at least once.
4.  ``--json`` emits the ``GateFindingsDocument`` JSON to stdout.
5.  ``--json`` output round-trips cleanly via
    ``GateFindingsDocument.model_validate_json``.
6.  Default mode is ``local`` (fast-slice) when ``--mode`` is omitted.
7.  ``--mode=ci`` triggers the full CI check set.
8.  ``--mode=invalid`` exits non-zero with an actionable error message.
9.  ``--help`` documents each new flag (``--cache-aware``, ``--no-cache``,
    ``--force``, ``--json``, ``--mode``).
10. ``--no-cache`` and ``--force`` compose: both can be specified; ``--force``
    takes precedence (clear+rerun semantics dominate).
11. ``AIENG_CACHE_DISABLED=1`` env var is honoured equivalently to ``--no-cache``.
12. When findings include ``severity >= medium`` the command exits with code 1.

Each test currently fails because the ``run`` sub-command is not yet
registered on the gate Typer group (existing sub-commands are
``pre-commit``, ``commit-msg``, ``pre-push``, ``risk-check``, ``all``).
T-3.2 GREEN phase will land the new command with the contract above.

TDD CONSTRAINT: this file is IMMUTABLE after T-3.1 lands. T-3.2 may only
introduce production code that satisfies these assertions; the assertions
themselves never change.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app
from ai_engineering.state.models import GateFindingsDocument

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers — fabricate a deterministic ``GateFindingsDocument`` for the mocked
# orchestrator return value. Keeping this in one place makes the test
# assertions focused on flag plumbing, not document construction.
# ---------------------------------------------------------------------------


def _make_finding(
    *,
    severity: str = "low",
    check: str = "ruff",
    rule_id: str = "E501",
) -> dict[str, Any]:
    """Return a minimal valid ``GateFinding`` dict payload."""
    return {
        "check": check,
        "rule_id": rule_id,
        "file": "src/example.py",
        "line": 1,
        "column": 1,
        "severity": severity,
        "message": f"{check} reported {rule_id}",
        "auto_fixable": False,
        "auto_fix_command": None,
    }


def _make_document(
    *,
    findings: list[dict[str, Any]] | None = None,
    cache_hits: list[str] | None = None,
    cache_misses: list[str] | None = None,
    produced_by: str = "ai-commit",
) -> GateFindingsDocument:
    """Return a fresh, validated ``GateFindingsDocument`` for mock returns."""
    payload: dict[str, Any] = {
        "schema": "ai-engineering/gate-findings/v1",
        "session_id": str(uuid.uuid4()),
        "produced_by": produced_by,
        "produced_at": datetime.now(UTC).isoformat(),
        "branch": "feat/spec-104-pipeline-speed",
        "commit_sha": "0" * 40,
        "findings": findings if findings is not None else [],
        "auto_fixed": [],
        "cache_hits": cache_hits if cache_hits is not None else [],
        "cache_misses": cache_misses if cache_misses is not None else [],
        "wall_clock_ms": {
            "wave1_fixers": 100,
            "wave2_checkers": 200,
            "total": 300,
        },
    }
    return GateFindingsDocument.model_validate(payload)


def _seeded_target(tmp_path: Path) -> Path:
    """Create a minimal project skeleton so ``--target`` resolves cleanly."""
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".ai-engineering" / "specs").mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture(autouse=True)
def _clear_override_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test starts with a clean cache-toggle env baseline."""
    monkeypatch.delenv("AIENG_CACHE_DISABLED", raising=False)
    monkeypatch.delenv("AIENG_CACHE_DEBUG", raising=False)
    monkeypatch.delenv("AIENG_LEGACY_PIPELINE", raising=False)


# ---------------------------------------------------------------------------
# 1. Default behaviour — cache-aware ON when no flags given
# ---------------------------------------------------------------------------


def test_gate_run_default_cache_aware(tmp_path: Path) -> None:
    """Invocation without flags MUST use the cache by default.

    The CLI surface declares ``--cache-aware`` as the default; ``run_gate``
    is invoked WITHOUT ``cache_dir=None`` (i.e., a real cache_dir is passed),
    and the orchestrator decides whether each individual check consults
    ``gate_cache.lookup`` based on the run-mode (default modern path).
    """
    # Arrange
    target = _seeded_target(tmp_path)
    document = _make_document()

    with patch(
        "ai_engineering.cli_commands.gate.run_orchestrator_gate",
        return_value=document,
    ) as mock_run:
        # Act
        app = create_app()
        result = runner.invoke(
            app,
            ["gate", "run", "--target", str(target)],
        )

    # Assert
    assert result.exit_code == 0, (
        "Default `gate run` (no findings) must exit 0; "
        f"got exit_code={result.exit_code} stdout={result.stdout!r}"
    )
    assert mock_run.call_count == 1, (
        "`gate run` with no flags must invoke the orchestrator exactly once; "
        f"got {mock_run.call_count} calls"
    )

    # Inspect the call kwargs to confirm cache-aware default-on plumbing.
    _args, kwargs = mock_run.call_args
    # The default contract is "cache enabled" — the orchestrator receives a
    # truthy cache flag (no `disabled=True` override) and a real cache_dir.
    assert kwargs.get("disabled", False) is False, (
        f"Default `gate run` MUST pass disabled=False (cache-aware). Got kwargs={kwargs!r}"
    )
    assert kwargs.get("force", False) is False, (
        f"Default `gate run` MUST NOT set force; got kwargs={kwargs!r}"
    )


# ---------------------------------------------------------------------------
# 2. --no-cache skips lookup
# ---------------------------------------------------------------------------


def test_gate_run_no_cache_flag(tmp_path: Path) -> None:
    """``--no-cache`` MUST skip ``gate_cache.lookup`` entirely.

    Verified by spying on ``gate_cache.lookup`` and asserting zero
    invocations after the orchestrator has been driven through the run.
    """
    # Arrange
    target = _seeded_target(tmp_path)
    document = _make_document()
    lookup_spy = MagicMock(return_value=None)

    with (
        patch(
            "ai_engineering.cli_commands.gate.run_orchestrator_gate",
            return_value=document,
        ) as mock_run,
        patch("ai_engineering.policy.gate_cache.lookup", lookup_spy),
    ):
        # Act
        app = create_app()
        result = runner.invoke(
            app,
            ["gate", "run", "--target", str(target), "--no-cache"],
        )

    # Assert
    assert result.exit_code == 0, (
        "Healthy `gate run --no-cache` must exit 0; "
        f"got exit_code={result.exit_code} stdout={result.stdout!r}"
    )
    assert lookup_spy.call_count == 0, (
        f"`--no-cache` MUST cause zero `gate_cache.lookup` calls; got {lookup_spy.call_count} calls"
    )

    # Confirm the orchestrator was told the cache is disabled.
    _args, kwargs = mock_run.call_args
    assert kwargs.get("disabled", False) is True, (
        f"`--no-cache` MUST propagate disabled=True to the orchestrator. Got kwargs={kwargs!r}"
    )


# ---------------------------------------------------------------------------
# 3. --force skips lookup AND clears matching entry
# ---------------------------------------------------------------------------


def test_gate_run_force_flag(tmp_path: Path) -> None:
    """``--force`` MUST skip lookup AND call ``gate_cache.clear_entry``.

    The contract: ``--force`` is the most aggressive override — caller is
    declaring "I know the cache is wrong; nuke the matching entries and
    run fresh". Verified by spying on ``clear_entry`` and asserting at
    least one invocation.
    """
    # Arrange
    target = _seeded_target(tmp_path)
    document = _make_document()
    clear_spy = MagicMock(return_value=True)

    with (
        patch(
            "ai_engineering.cli_commands.gate.run_orchestrator_gate",
            return_value=document,
        ) as mock_run,
        patch("ai_engineering.policy.gate_cache.clear_entry", clear_spy),
    ):
        # Act
        app = create_app()
        result = runner.invoke(
            app,
            ["gate", "run", "--target", str(target), "--force"],
        )

    # Assert
    assert result.exit_code == 0, (
        "Healthy `gate run --force` must exit 0; "
        f"got exit_code={result.exit_code} stdout={result.stdout!r}"
    )
    assert clear_spy.call_count >= 1, (
        "`--force` MUST call `gate_cache.clear_entry` at least once; "
        f"got {clear_spy.call_count} calls"
    )

    # Force also implies disabled cache lookup for the run itself.
    _args, kwargs = mock_run.call_args
    assert kwargs.get("force", False) is True, (
        f"`--force` MUST propagate force=True to the orchestrator. Got kwargs={kwargs!r}"
    )


# ---------------------------------------------------------------------------
# 4. --json prints structured envelope to stdout
# ---------------------------------------------------------------------------


def test_gate_run_json_flag_outputs_to_stdout(tmp_path: Path) -> None:
    """``--json`` MUST emit the ``GateFindingsDocument`` JSON on stdout.

    The output MUST be parseable as JSON and MUST include the canonical
    schema literal so downstream agents (spec-105 risk-accept) can route
    the document by version.
    """
    # Arrange
    target = _seeded_target(tmp_path)
    document = _make_document(findings=[_make_finding(severity="low")])

    with patch(
        "ai_engineering.cli_commands.gate.run_orchestrator_gate",
        return_value=document,
    ):
        # Act
        app = create_app()
        result = runner.invoke(
            app,
            ["gate", "run", "--target", str(target), "--json"],
        )

    # Assert — exit clean (only low-severity finding, below medium threshold).
    assert result.exit_code == 0, (
        "Low-severity findings under `--json` must exit 0; "
        f"got exit_code={result.exit_code} stdout={result.stdout!r}"
    )

    # Find the JSON document in stdout (envelope or raw — both are valid;
    # the schema literal is the load-bearing assertion).
    assert "ai-engineering/gate-findings/v1" in result.stdout, (
        "`--json` output MUST contain the schema literal "
        "'ai-engineering/gate-findings/v1' so consumers can route by version. "
        f"Got stdout={result.stdout!r}"
    )

    # Output MUST be valid JSON (single document or envelope wrapper).
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        pytest.fail(f"`--json` stdout must be valid JSON; parse error: {exc}")

    assert isinstance(parsed, dict), (
        f"`--json` stdout MUST decode to a JSON object; got {type(parsed).__name__}"
    )


# ---------------------------------------------------------------------------
# 5. --json output validates against the GateFindingsDocument schema
# ---------------------------------------------------------------------------


def test_gate_run_json_validates_against_schema(tmp_path: Path) -> None:
    """``--json`` output MUST round-trip through ``GateFindingsDocument``.

    Whether the CLI wraps the document in a ``cli_envelope`` ``result`` field
    or emits it bare, somewhere in the output there MUST be a payload that
    ``GateFindingsDocument.model_validate(...)`` accepts. This guarantees the
    schema-v1 contract is preserved end-to-end.
    """
    # Arrange
    target = _seeded_target(tmp_path)
    document = _make_document(
        findings=[_make_finding(severity="low")],
        cache_hits=["gitleaks"],
        cache_misses=["ruff-check", "ty"],
    )

    with patch(
        "ai_engineering.cli_commands.gate.run_orchestrator_gate",
        return_value=document,
    ):
        # Act
        app = create_app()
        result = runner.invoke(
            app,
            ["gate", "run", "--target", str(target), "--json"],
        )

    # Assert — JSON is parseable
    assert result.exit_code == 0, (
        "Low-severity `--json` invocation must exit 0; "
        f"got exit_code={result.exit_code} stdout={result.stdout!r}"
    )

    parsed = json.loads(result.stdout)

    # Find the document payload — either at top level or under `result`/`document`.
    candidates: list[dict[str, Any]] = []
    if isinstance(parsed, dict):
        candidates.append(parsed)
        for key in ("result", "document", "findings_document", "data"):
            value = parsed.get(key)
            if isinstance(value, dict):
                candidates.append(value)

    matched: GateFindingsDocument | None = None
    last_error: Exception | None = None
    for candidate in candidates:
        try:
            matched = GateFindingsDocument.model_validate(candidate)
            break
        except Exception as exc:  # pragma: no cover - failure path explored on assert
            last_error = exc

    assert matched is not None, (
        "`--json` output MUST contain a payload that validates against "
        "`GateFindingsDocument` (schema v1). Tried candidates="
        f"{[list(c.keys()) for c in candidates]!r}; last_error={last_error!r}"
    )
    assert matched.cache_hits == ["gitleaks"], (
        f"Round-tripped document MUST preserve `cache_hits`; got {matched.cache_hits!r}"
    )


# ---------------------------------------------------------------------------
# 6. Default mode is local (fast-slice)
# ---------------------------------------------------------------------------


def test_gate_run_mode_local_default(tmp_path: Path) -> None:
    """Without ``--mode``, the orchestrator MUST receive ``mode="local"``.

    D-104-02 mandates the local fast-slice as the default — `semgrep`,
    `pip-audit`, and `pytest-full` are excluded from local runs and only
    activate under `--mode=ci`.
    """
    # Arrange
    target = _seeded_target(tmp_path)
    document = _make_document()

    with patch(
        "ai_engineering.cli_commands.gate.run_orchestrator_gate",
        return_value=document,
    ) as mock_run:
        # Act
        app = create_app()
        result = runner.invoke(
            app,
            ["gate", "run", "--target", str(target)],
        )

    # Assert
    assert result.exit_code == 0
    _args, kwargs = mock_run.call_args
    assert kwargs.get("mode") == "local", (
        f"Default `gate run` MUST pass mode='local' to the orchestrator. Got kwargs={kwargs!r}"
    )


# ---------------------------------------------------------------------------
# 7. --mode=ci propagates to the orchestrator
# ---------------------------------------------------------------------------


def test_gate_run_mode_ci_explicit(tmp_path: Path) -> None:
    """``--mode=ci`` MUST propagate to the orchestrator as ``mode="ci"``."""
    # Arrange
    target = _seeded_target(tmp_path)
    document = _make_document()

    with patch(
        "ai_engineering.cli_commands.gate.run_orchestrator_gate",
        return_value=document,
    ) as mock_run:
        # Act
        app = create_app()
        result = runner.invoke(
            app,
            ["gate", "run", "--target", str(target), "--mode", "ci"],
        )

    # Assert
    assert result.exit_code == 0, (
        "Healthy `--mode=ci` invocation must exit 0; "
        f"got exit_code={result.exit_code} stdout={result.stdout!r}"
    )
    _args, kwargs = mock_run.call_args
    assert kwargs.get("mode") == "ci", (
        f"`--mode=ci` MUST propagate mode='ci' to the orchestrator. Got kwargs={kwargs!r}"
    )


# ---------------------------------------------------------------------------
# 8. --mode=invalid exits non-zero with actionable message
# ---------------------------------------------------------------------------


def test_gate_run_mode_invalid_value(tmp_path: Path) -> None:
    """``--mode=invalid`` MUST reject the value and exit non-zero.

    The error message MUST mention the legal values (``local`` and ``ci``)
    so the user can self-correct without consulting docs.
    """
    # Arrange
    target = _seeded_target(tmp_path)

    with patch(
        "ai_engineering.cli_commands.gate.run_orchestrator_gate",
    ) as mock_run:
        # Act
        app = create_app()
        result = runner.invoke(
            app,
            ["gate", "run", "--target", str(target), "--mode", "invalid"],
        )

    # Assert — exit non-zero (Typer rejects choice before our handler runs).
    assert result.exit_code != 0, (
        "`--mode=invalid` MUST exit non-zero. "
        f"Got exit_code={result.exit_code} stdout={result.stdout!r}"
    )

    # Assert — orchestrator never invoked (validation rejected the value).
    assert mock_run.call_count == 0, (
        f"`--mode=invalid` MUST NOT reach the orchestrator. Got {mock_run.call_count} calls"
    )

    # Assert — error message mentions legal values.
    combined = (result.output or "") + (result.stdout or "")
    assert ("local" in combined.lower()) and ("ci" in combined.lower()), (
        "`--mode=invalid` error MUST mention legal values 'local' and 'ci' "
        f"so users can self-correct. Got output={combined!r}"
    )


# ---------------------------------------------------------------------------
# 9. --help documents each new flag
# ---------------------------------------------------------------------------


def test_gate_run_help_documents_each_flag() -> None:
    """``ai-eng gate run --help`` MUST list every new flag.

    A user running ``--help`` to discover the CLI surface MUST see all five
    flags in the rendered help text:
    ``--cache-aware``, ``--no-cache``, ``--force``, ``--json``, ``--mode``.

    Normalisation: Typer's rich-help renderer wraps long option names across
    line breaks (``-\\n-cache-aware``) and injects ANSI colour codes when
    stdout is non-TTY in some environments. We strip ANSI sequences and
    collapse whitespace before substring-checking the flag name.
    """
    import re as _re

    # Arrange / Act
    app = create_app()
    result = runner.invoke(app, ["gate", "run", "--help"])

    # Assert — help renders cleanly.
    assert result.exit_code == 0, (
        f"`gate run --help` must exit 0; got exit_code={result.exit_code} stdout={result.stdout!r}"
    )

    raw = result.output or result.stdout or ""
    # Strip ANSI escape sequences (rich's colour codes).
    no_ansi = _re.sub(r"\x1b\[[0-9;]*m", "", raw)
    # Collapse runs of whitespace (incl. newlines) so wrapped option names
    # like "-\n-cache-aware" become "- -cache-aware" → still searchable.
    normalised = _re.sub(r"\s+", " ", no_ansi)
    # Also fold split-after-dash variants explicitly to defend against
    # Rich's word-break inside long option labels.
    normalised_no_space_after_dash = normalised.replace("- -", "--")

    for flag in ("--cache-aware", "--no-cache", "--force", "--json", "--mode"):
        assert flag in normalised_no_space_after_dash, (
            f"`gate run --help` MUST document the {flag!r} flag. "
            f"Normalised help text=\n{normalised_no_space_after_dash[:2000]!r}"
        )


# ---------------------------------------------------------------------------
# 10. --no-cache and --force compose; --force takes precedence
# ---------------------------------------------------------------------------


def test_gate_run_no_cache_and_force_compose(tmp_path: Path) -> None:
    """Both ``--no-cache`` and ``--force`` can be specified together.

    ``--force`` is the more aggressive override (it ALSO clears the matching
    entry on top of skipping the lookup), so when both are given the
    behaviour MUST match plain ``--force`` — clear+rerun semantics dominate.
    """
    # Arrange
    target = _seeded_target(tmp_path)
    document = _make_document()
    clear_spy = MagicMock(return_value=True)

    with (
        patch(
            "ai_engineering.cli_commands.gate.run_orchestrator_gate",
            return_value=document,
        ) as mock_run,
        patch("ai_engineering.policy.gate_cache.clear_entry", clear_spy),
    ):
        # Act
        app = create_app()
        result = runner.invoke(
            app,
            [
                "gate",
                "run",
                "--target",
                str(target),
                "--no-cache",
                "--force",
            ],
        )

    # Assert — clean exit, both flags accepted.
    assert result.exit_code == 0, (
        "Composing `--no-cache` and `--force` must exit 0 (no findings). "
        f"Got exit_code={result.exit_code} stdout={result.stdout!r}"
    )

    # Assert — `--force` precedence: clear_entry was invoked.
    assert clear_spy.call_count >= 1, (
        "`--force` MUST call `clear_entry` even when combined with `--no-cache` "
        f"(force precedence). Got {clear_spy.call_count} calls"
    )

    # Assert — orchestrator received `force=True` (force wins).
    _args, kwargs = mock_run.call_args
    assert kwargs.get("force", False) is True, (
        "When `--force` is present, force=True MUST propagate even with "
        f"`--no-cache` also set. Got kwargs={kwargs!r}"
    )


# ---------------------------------------------------------------------------
# 11. AIENG_CACHE_DISABLED=1 env honored equivalently to --no-cache
# ---------------------------------------------------------------------------


def test_gate_run_propagates_aieng_cache_disabled_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``AIENG_CACHE_DISABLED=1`` MUST behave like ``--no-cache``.

    Per D-104-10 the env var is the global kill switch — agents and CI
    jobs that cannot easily inject CLI flags rely on it. The contract:
    ``gate_cache.lookup`` MUST NOT be consulted when the env var is set,
    even though no CLI flag was passed.
    """
    # Arrange
    target = _seeded_target(tmp_path)
    document = _make_document()
    lookup_spy = MagicMock(return_value=None)

    monkeypatch.setenv("AIENG_CACHE_DISABLED", "1")

    with (
        patch(
            "ai_engineering.cli_commands.gate.run_orchestrator_gate",
            return_value=document,
        ),
        patch("ai_engineering.policy.gate_cache.lookup", lookup_spy),
    ):
        # Act — NO `--no-cache` flag, only the env var.
        app = create_app()
        result = runner.invoke(
            app,
            ["gate", "run", "--target", str(target)],
        )

    # Assert
    assert result.exit_code == 0, (
        "Healthy `gate run` with AIENG_CACHE_DISABLED=1 must exit 0; "
        f"got exit_code={result.exit_code} stdout={result.stdout!r}"
    )
    assert lookup_spy.call_count == 0, (
        "AIENG_CACHE_DISABLED=1 MUST suppress all `gate_cache.lookup` calls "
        "(equivalent to `--no-cache`). "
        f"Got {lookup_spy.call_count} calls"
    )


# ---------------------------------------------------------------------------
# 12. Exit code 1 when findings include severity >= medium
# ---------------------------------------------------------------------------


def test_gate_run_exit_code_1_on_findings(tmp_path: Path) -> None:
    """Findings with ``severity >= medium`` MUST cause the command to exit 1.

    Per D-104-01 ``Comportamiento en falla``: the orchestrator surfaces
    medium-or-worse findings as gate failures, blocking commit/push until
    spec-105 risk-accept is wired.
    """
    # Arrange
    target = _seeded_target(tmp_path)
    document = _make_document(
        findings=[
            _make_finding(severity="medium"),
            _make_finding(severity="high", check="ty", rule_id="TY-002"),
        ],
    )

    with patch(
        "ai_engineering.cli_commands.gate.run_orchestrator_gate",
        return_value=document,
    ):
        # Act
        app = create_app()
        result = runner.invoke(
            app,
            ["gate", "run", "--target", str(target)],
        )

    # Assert — exit code MUST be 1 (gate failure).
    assert result.exit_code == 1, (
        "Findings with severity>=medium MUST cause exit code 1. "
        f"Got exit_code={result.exit_code} stdout={result.stdout!r}"
    )
