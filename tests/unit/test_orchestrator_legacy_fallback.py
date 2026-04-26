"""Unit tests for the ``AIENG_LEGACY_PIPELINE=1`` emergency fallback.

RED phase for spec-104 T-2.9 (D-104-01 ``Fallback de emergencia`` clause).

> ``AIENG_LEGACY_PIPELINE=1`` env restaura el flujo secuencial pre-spec-104;
> documentado en CHANGELOG migration.
> -- ``.ai-engineering/specs/spec.md`` D-104-01

Target module / API surface (do not exist yet — landed by T-2.10 GREEN):

    - ``ai_engineering.policy.orchestrator.run_gate(
          checks: Sequence[CheckSpec],
          *,
          cache_dir: Path | None = None,
          mode: Literal["local", "ci"] = "local",
          project_root: Path,
      ) -> GateFindingsDocument``

      The default (modern) path runs Wave 1 fixers serial, then Wave 2
      checkers via ``ThreadPoolExecutor(max_workers=5)`` consulting
      ``gate_cache.lookup``/``persist`` for each check.

      With ``AIENG_LEGACY_PIPELINE=1`` set in the environment the
      function MUST switch to the pre-spec-104 flow:
        1. Cache lookup is SKIPPED entirely (equivalent to ``--no-cache``).
        2. Wave 2 checkers run STRICTLY SEQUENTIALLY (next starts only
           after previous returns).
        3. A WARNING-level log entry is emitted on the
           ``ai_engineering.policy.orchestrator`` logger that mentions
           the env-var name and recommends opening an issue.
        4. The final ``GateFindingsDocument.findings`` list is identical
           (modulo ordering) to the modern path's output for the same
           inputs.

      Strict env parsing per D-104-10 / D-104-01: only the literal value
      ``"1"`` enables legacy. Any other value (``"0"``, ``"true"``,
      ``"yes"``, empty string, the env var being unset) keeps the modern
      path. This keeps the kill-switch unambiguous and impossible to
      trigger by accident from a misformatted shell rc file.

These tests currently fail with ``ImportError`` on
``ai_engineering.policy.orchestrator`` because the module does not yet
exist. T-2.10 GREEN phase wires the legacy branch on top of the modern
orchestrator skeleton (T-2.2/T-2.4) and these assertions become the
contract for the emergency fallback.

TDD CONSTRAINT: this file is IMMUTABLE after T-2.9 lands. T-2.10 may only
add the production behaviour; never modify these assertions. If the
contract here turns out to be wrong, escalate to the user — do not weaken
or rewrite to match an easier implementation.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Helpers — instrumented checker stand-ins
# ---------------------------------------------------------------------------
#
# The orchestrator dispatches each Wave 2 check through a callable that
# returns ``(outcome, findings)``. These tests inject *controllable* fake
# checkers so we can:
#   - assert serial vs parallel scheduling without running real subprocesses;
#   - assert the same finding payloads are returned via either path;
#   - assert the cache-lookup hook is/isn't consulted.
#
# We attach instrumentation via a module-level registry keyed on the check
# name. The orchestrator under test is expected to look up the registered
# checker callable when running Wave 2 (this is the wiring T-2.4 ships).
# If the production module exposes a different injection seam, the GREEN
# phase MUST still satisfy the *observable* assertions below — the
# helpers are a reasonable default; the contract is the assertions.
# ---------------------------------------------------------------------------


@dataclass
class _CheckerCall:
    """Record of one fake-checker invocation for ordering assertions."""

    name: str
    started_at: float
    finished_at: float


@dataclass
class _CheckerLedger:
    """Thread-safe ledger that records checker start/finish times."""

    lock: threading.Lock = field(default_factory=threading.Lock)
    calls: list[_CheckerCall] = field(default_factory=list)
    in_flight: set[str] = field(default_factory=set)
    max_concurrent: int = 0

    def record_start(self, name: str, ts: float) -> None:
        with self.lock:
            self.in_flight.add(name)
            if len(self.in_flight) > self.max_concurrent:
                self.max_concurrent = len(self.in_flight)

    def record_finish(self, name: str, started_at: float, finished_at: float) -> None:
        with self.lock:
            self.in_flight.discard(name)
            self.calls.append(
                _CheckerCall(name=name, started_at=started_at, finished_at=finished_at)
            )


def _wave2_check_names() -> list[str]:
    """The 5 Wave 2 checkers per D-104-01."""
    return [
        "gitleaks",
        "validate",
        "docs-gate",
        "ty",
        "pytest-smoke",
    ]


def _build_fake_checks(
    ledger: _CheckerLedger,
    *,
    sleep_seconds: float = 0.05,
    findings_per_check: dict[str, list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    """Return a list of CheckSpec-shaped dicts for the 5 Wave 2 checkers.

    Each fake checker:
      - records a start/finish timestamp via ``ledger``;
      - sleeps ``sleep_seconds`` so parallel-vs-serial timing is observable;
      - returns the deterministic findings list assigned to its name.
    """
    import time as _time

    findings_per_check = findings_per_check or {
        name: [
            {
                "check": name,
                "rule_id": f"{name.upper()}-001",
                "file": f"src/{name}_target.py",
                "line": 1,
                "column": 1,
                "severity": "low",
                "message": f"deterministic finding from {name}",
                "auto_fixable": False,
                "auto_fix_command": None,
            }
        ]
        for name in _wave2_check_names()
    }

    specs: list[dict[str, Any]] = []
    for name in _wave2_check_names():
        captured_name = name
        captured_findings = findings_per_check[name]

        def _runner(
            *_args: Any,
            _name: str = captured_name,
            _findings: list[dict[str, Any]] = captured_findings,
            **_kwargs: Any,
        ) -> dict[str, Any]:
            t0 = _time.perf_counter()
            ledger.record_start(_name, t0)
            _time.sleep(sleep_seconds)
            t1 = _time.perf_counter()
            ledger.record_finish(_name, t0, t1)
            return {
                "check": _name,
                "outcome": "fail" if _findings else "pass",
                "findings": list(_findings),
                "exit_code": 1 if _findings else 0,
                "stdout": "",
                "stderr": "",
            }

        specs.append({"name": captured_name, "runner": _runner, "wave": 2})
    return specs


def _project_root_with_min_state(tmp_path: Path) -> Path:
    """Return a tmp_path-rooted project skeleton sufficient for the orchestrator.

    Creates ``.ai-engineering/state/`` and ``.ai-engineering/specs/`` so the
    orchestrator's ``gate-findings.json`` emit (and any spec-verify lookup)
    can find a writable location.
    """
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".ai-engineering" / "specs").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _findings_signature(document: Any) -> list[tuple[str, str, str, int]]:
    """Reduce a ``GateFindingsDocument`` (or dict) to a comparable signature.

    Sorts findings by ``(check, rule_id, file, line)`` and drops volatile fields
    (timestamps, session_id, wall_clock_ms) so legacy and modern paths can be
    compared structurally.
    """
    findings = getattr(document, "findings", None)
    if findings is None and isinstance(document, dict):
        findings = document.get("findings", [])
    findings = findings or []

    signature: list[tuple[str, str, str, int]] = []
    for finding in findings:
        if isinstance(finding, dict):
            signature.append(
                (
                    str(finding.get("check", "")),
                    str(finding.get("rule_id", "")),
                    str(finding.get("file", "")),
                    int(finding.get("line", 0) or 0),
                )
            )
        else:
            signature.append(
                (
                    str(getattr(finding, "check", "")),
                    str(getattr(finding, "rule_id", "")),
                    str(getattr(finding, "file", "")),
                    int(getattr(finding, "line", 0) or 0),
                )
            )
    signature.sort()
    return signature


@pytest.fixture(autouse=True)
def _clear_legacy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test starts with the env var cleared to avoid cross-test bleed."""
    monkeypatch.delenv("AIENG_LEGACY_PIPELINE", raising=False)
    # Cache toggles must also start clean — otherwise
    # ``test_legacy_pipeline_env_unset_uses_modern`` could pass for the wrong
    # reason (cache hit because a prior test happened to populate the cache).
    monkeypatch.delenv("AIENG_CACHE_DISABLED", raising=False)


# ---------------------------------------------------------------------------
# Test 1 — legacy env disables Wave 2 parallelism (strict serial ordering)
# ---------------------------------------------------------------------------


def test_legacy_pipeline_env_disables_parallel_wave2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``AIENG_LEGACY_PIPELINE=1`` must run all 5 Wave 2 checkers strictly
    sequentially: each subsequent checker only starts AFTER the previous one
    has returned (no overlap)."""
    # Arrange
    from ai_engineering.policy.orchestrator import run_gate

    project_root = _project_root_with_min_state(tmp_path)
    cache_dir = tmp_path / "gate-cache"
    ledger = _CheckerLedger()
    # Sleep long enough that any concurrent scheduling would produce overlap
    # in the ledger; 50ms is well above the recording resolution.
    specs = _build_fake_checks(ledger, sleep_seconds=0.05)

    monkeypatch.setenv("AIENG_LEGACY_PIPELINE", "1")

    # Act
    run_gate(
        checks=specs,
        cache_dir=cache_dir,
        mode="local",
        project_root=project_root,
    )

    # Assert — every check ran exactly once.
    invocations = sorted(call.name for call in ledger.calls)
    assert invocations == sorted(_wave2_check_names()), (
        "Legacy path must still execute all 5 Wave 2 checkers; "
        f"got invocations={invocations!r}, expected={_wave2_check_names()!r}"
    )

    # Assert — at no point did more than one checker run concurrently.
    assert ledger.max_concurrent == 1, (
        "AIENG_LEGACY_PIPELINE=1 must run Wave 2 checkers strictly serial; "
        f"observed max_concurrent={ledger.max_concurrent} (expected 1)"
    )

    # Assert — strict ordering: each call's start_time >= previous call's
    # finish_time (a strong serial proof).
    sorted_calls = sorted(ledger.calls, key=lambda c: c.started_at)
    for prev, curr in pairwise(sorted_calls):
        assert curr.started_at >= prev.finished_at, (
            f"Legacy path must wait for {prev.name!r} to finish before "
            f"starting {curr.name!r}; got prev.finished_at={prev.finished_at} "
            f"curr.started_at={curr.started_at} (overlap of "
            f"{prev.finished_at - curr.started_at:.4f}s)"
        )


# ---------------------------------------------------------------------------
# Test 2 — legacy env disables cache lookup
# ---------------------------------------------------------------------------


def test_legacy_pipeline_env_disables_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``AIENG_LEGACY_PIPELINE=1`` must skip cache lookup entirely
    (equivalent to ``--no-cache`` from D-104-10).

    The contract is observable: even when a perfectly-matching cache entry
    exists on disk for every check, the legacy path still executes each
    checker (the cache is NOT consulted). This is verified by the ledger
    recording a real invocation per check.
    """
    # Arrange
    from ai_engineering.policy import gate_cache
    from ai_engineering.policy.orchestrator import run_gate

    project_root = _project_root_with_min_state(tmp_path)
    cache_dir = tmp_path / "gate-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    ledger = _CheckerLedger()
    specs = _build_fake_checks(ledger, sleep_seconds=0.001)

    # Spy on gate_cache.lookup to assert it is NOT consulted under legacy.
    lookup_call_count = {"n": 0}
    real_lookup = getattr(gate_cache, "lookup", None)

    def _spy_lookup(*args: Any, **kwargs: Any) -> Any:
        lookup_call_count["n"] += 1
        if real_lookup is None:
            return None
        return real_lookup(*args, **kwargs)

    monkeypatch.setattr(gate_cache, "lookup", _spy_lookup, raising=False)
    monkeypatch.setenv("AIENG_LEGACY_PIPELINE", "1")

    # Act
    run_gate(
        checks=specs,
        cache_dir=cache_dir,
        mode="local",
        project_root=project_root,
    )

    # Assert — cache lookup helper was never consulted.
    assert lookup_call_count["n"] == 0, (
        "AIENG_LEGACY_PIPELINE=1 must skip cache lookup entirely; "
        f"observed gate_cache.lookup calls={lookup_call_count['n']} (expected 0)"
    )

    # Assert — every checker actually ran (proves no replay-from-cache).
    actually_invoked = sorted(call.name for call in ledger.calls)
    assert actually_invoked == sorted(_wave2_check_names()), (
        "Legacy path must invoke every checker, not replay from cache; "
        f"got actually_invoked={actually_invoked!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — legacy env emits a WARNING that mentions the env var + issue link
# ---------------------------------------------------------------------------


def test_legacy_pipeline_env_logs_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When legacy mode is active, exactly one WARNING-level log record is
    emitted on the orchestrator logger that mentions
    ``AIENG_LEGACY_PIPELINE`` and recommends opening an issue.

    This is the audit-trail signal the spec-104 R-12 mitigation relies on
    (``fallback ... documentado en CHANGELOG migration``): if a user is
    running the legacy path we MUST tell them, loudly, and point them at
    the issue tracker so we collect data on why they needed it.
    """
    # Arrange
    from ai_engineering.policy.orchestrator import run_gate

    project_root = _project_root_with_min_state(tmp_path)
    cache_dir = tmp_path / "gate-cache"
    ledger = _CheckerLedger()
    specs = _build_fake_checks(ledger, sleep_seconds=0.001)

    monkeypatch.setenv("AIENG_LEGACY_PIPELINE", "1")

    # Act
    with caplog.at_level(logging.WARNING, logger="ai_engineering.policy.orchestrator"):
        run_gate(
            checks=specs,
            cache_dir=cache_dir,
            mode="local",
            project_root=project_root,
        )

    # Assert — at least one WARNING record on the orchestrator logger.
    orchestrator_warnings = [
        record
        for record in caplog.records
        if record.name == "ai_engineering.policy.orchestrator" and record.levelno == logging.WARNING
    ]
    assert orchestrator_warnings, (
        "Legacy mode must emit a WARNING on "
        "ai_engineering.policy.orchestrator; "
        f"got records={[(r.name, r.levelname, r.getMessage()) for r in caplog.records]!r}"
    )

    # Assert — message mentions the env var name (so users can grep for it).
    combined_messages = " | ".join(record.getMessage() for record in orchestrator_warnings)
    assert "AIENG_LEGACY_PIPELINE" in combined_messages, (
        "Legacy WARNING must include the literal env-var name "
        "'AIENG_LEGACY_PIPELINE' so users can search for it; "
        f"got messages={combined_messages!r}"
    )

    # Assert — message recommends opening an issue (audit-trail directive).
    lowered = combined_messages.lower()
    assert "issue" in lowered, (
        "Legacy WARNING must recommend opening an issue (per R-12 audit "
        f"trail); got messages={combined_messages!r}"
    )


# ---------------------------------------------------------------------------
# Test 4 — legacy and modern paths produce equivalent findings
# ---------------------------------------------------------------------------


def test_legacy_pipeline_produces_same_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """For identical inputs, the legacy path and the modern path must
    produce the same ``findings`` list (sorted by check name).

    This is the safety net for D-104-01's ``Fallback de emergencia``: if
    a user trips the kill-switch, they MUST still receive the same
    diagnostic information they would have received from the modern
    pipeline. Anything else would surprise the user during an incident.
    """
    # Arrange
    from ai_engineering.policy.orchestrator import run_gate

    findings_per_check = {
        name: [
            {
                "check": name,
                "rule_id": f"{name.upper()}-007",
                "file": f"src/{name}_module.py",
                "line": 21,
                "column": 4,
                "severity": "medium",
                "message": f"deterministic-{name}",
                "auto_fixable": False,
                "auto_fix_command": None,
            }
        ]
        for name in _wave2_check_names()
    }

    # --- Modern run ---------------------------------------------------------
    project_root_modern = _project_root_with_min_state(tmp_path / "modern")
    ledger_modern = _CheckerLedger()
    specs_modern = _build_fake_checks(
        ledger_modern,
        sleep_seconds=0.001,
        findings_per_check=findings_per_check,
    )
    monkeypatch.delenv("AIENG_LEGACY_PIPELINE", raising=False)
    modern_doc = run_gate(
        checks=specs_modern,
        cache_dir=tmp_path / "modern" / "cache",
        mode="local",
        project_root=project_root_modern,
    )

    # --- Legacy run ---------------------------------------------------------
    project_root_legacy = _project_root_with_min_state(tmp_path / "legacy")
    ledger_legacy = _CheckerLedger()
    specs_legacy = _build_fake_checks(
        ledger_legacy,
        sleep_seconds=0.001,
        findings_per_check=findings_per_check,
    )
    monkeypatch.setenv("AIENG_LEGACY_PIPELINE", "1")
    legacy_doc = run_gate(
        checks=specs_legacy,
        cache_dir=tmp_path / "legacy" / "cache",
        mode="local",
        project_root=project_root_legacy,
    )

    # Assert — structural equivalence after sorting.
    modern_signature = _findings_signature(modern_doc)
    legacy_signature = _findings_signature(legacy_doc)
    assert legacy_signature == modern_signature, (
        "Legacy path must produce the same findings (sorted by check name + "
        "rule_id + file + line) as the modern path for identical inputs; "
        f"modern={modern_signature!r} legacy={legacy_signature!r}"
    )

    # Assert — count parity (defence against silent skips in either path).
    assert len(modern_signature) == len(_wave2_check_names()), (
        "Modern path should have one finding per Wave 2 checker; "
        f"got {len(modern_signature)} findings"
    )
    assert len(legacy_signature) == len(_wave2_check_names()), (
        "Legacy path should have one finding per Wave 2 checker; "
        f"got {len(legacy_signature)} findings"
    )


# ---------------------------------------------------------------------------
# Test 5 — strict env-var parsing: only "1" enables legacy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "env_value",
    [
        "0",
        "true",
        "yes",
        "",
        "01",  # not strictly "1"
        "TRUE",
        " 1",  # whitespace makes it not strictly "1"
        "1 ",
    ],
)
def test_legacy_pipeline_env_value_strict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    env_value: str,
) -> None:
    """Only the literal string ``"1"`` enables legacy mode.

    Per D-104-10's strict-flag philosophy (the cache kill-switch follows
    the same rule), the legacy fallback must NOT be triggered by
    truthy-looking values like ``"true"`` / ``"yes"`` / ``"01"`` /
    whitespace-padded ``" 1"``. Strict parsing eliminates ambiguity:
    operators flip a single bit, period.

    With any non-"1" value the orchestrator MUST take the modern parallel
    path. We verify this by asserting Wave 2 checkers run with overlap
    (max_concurrent >= 2) — only achievable in the parallel branch.
    """
    # Arrange
    from ai_engineering.policy.orchestrator import run_gate

    project_root = _project_root_with_min_state(tmp_path)
    cache_dir = tmp_path / "gate-cache"
    ledger = _CheckerLedger()
    # Enough sleep that even a weak parallel scheduler will overlap two
    # invocations.
    specs = _build_fake_checks(ledger, sleep_seconds=0.05)

    monkeypatch.setenv("AIENG_LEGACY_PIPELINE", env_value)

    # Act
    run_gate(
        checks=specs,
        cache_dir=cache_dir,
        mode="local",
        project_root=project_root,
    )

    # Assert — modern parallel path: at least 2 checkers ran concurrently.
    assert ledger.max_concurrent >= 2, (
        "AIENG_LEGACY_PIPELINE only switches to legacy on the literal "
        f"value '1'; for env_value={env_value!r} the modern parallel path "
        f"must be used (expected max_concurrent>=2; got {ledger.max_concurrent})"
    )


# ---------------------------------------------------------------------------
# Test 6 — env unset: modern parallel + cache by default
# ---------------------------------------------------------------------------


def test_legacy_pipeline_env_unset_uses_modern(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With ``AIENG_LEGACY_PIPELINE`` unset entirely, the orchestrator runs
    the modern path: Wave 2 checkers in parallel AND cache lookup is
    consulted.

    This test pins the *default* behaviour so a future regression that
    inverts the env-var sense (e.g., flipping the default to legacy) is
    caught immediately.
    """
    # Arrange
    from ai_engineering.policy import gate_cache
    from ai_engineering.policy.orchestrator import run_gate

    project_root = _project_root_with_min_state(tmp_path)
    cache_dir = tmp_path / "gate-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    ledger = _CheckerLedger()
    specs = _build_fake_checks(ledger, sleep_seconds=0.05)

    # Spy on gate_cache.lookup so we can assert the modern path consults it.
    lookup_call_count = {"n": 0}
    real_lookup = getattr(gate_cache, "lookup", None)

    def _spy_lookup(*args: Any, **kwargs: Any) -> Any:
        lookup_call_count["n"] += 1
        if real_lookup is None:
            return None
        return real_lookup(*args, **kwargs)

    monkeypatch.setattr(gate_cache, "lookup", _spy_lookup, raising=False)
    # Belt-and-suspenders: the autouse fixture already deletes the env var,
    # but be explicit here so the assertion's intent is unambiguous.
    monkeypatch.delenv("AIENG_LEGACY_PIPELINE", raising=False)

    # Act
    run_gate(
        checks=specs,
        cache_dir=cache_dir,
        mode="local",
        project_root=project_root,
    )

    # Assert — every Wave 2 checker still ran exactly once.
    invocations = sorted(call.name for call in ledger.calls)
    assert invocations == sorted(_wave2_check_names()), (
        f"Modern path must invoke all 5 Wave 2 checkers; got invocations={invocations!r}"
    )

    # Assert — modern path consulted gate_cache.lookup for at least one check.
    # (Exact count is implementation-defined; the contract is "consulted",
    # not "consulted exactly N times".)
    assert lookup_call_count["n"] >= 1, (
        "Modern path (env unset) must consult gate_cache.lookup at least "
        f"once per run; observed call count={lookup_call_count['n']}"
    )

    # Assert — parallelism: at least 2 checkers ran concurrently.
    assert ledger.max_concurrent >= 2, (
        "Modern path (env unset) must run Wave 2 checkers in parallel; "
        f"observed max_concurrent={ledger.max_concurrent} (expected >=2)"
    )
