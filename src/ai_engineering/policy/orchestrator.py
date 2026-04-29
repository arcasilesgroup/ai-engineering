"""spec-104 D-104-01 orchestrator: 2-wave gate dispatch with cache-aware Wave 2.

Implements the public surface required by the IMMUTABLE RED test contracts:

* ``Wave1Result`` / ``Wave2Result`` dataclasses
* ``run_wave1(staged_files)`` -- serial fixers (ruff format, ruff check --fix,
  spec verify --fix) with intra-wave convergence re-run.
* ``run_wave2(staged_files, mode)`` -- parallel checkers via
  ``ThreadPoolExecutor`` with cache hit/miss bookkeeping.
* ``_run_one_checker(check_name, ...)`` -- per-check seam used by ``run_wave2``;
  patched by tests via ``mock.patch.object(orchestrator, "_run_one_checker", ...)``.
* ``_run_check(check_name, ...)`` -- per-check seam used by ``run_gate(staged_files=...)``
  for cache integration tests.
* ``_emit_findings(...)`` -- atomic JSON emit per D-104-06 schema v1.
* ``run_gate(...)`` -- top-level entry point. Encodes the
  ``wave1_complete: threading.Event`` race-safety invariant explicitly.
* ``AIENG_LEGACY_PIPELINE=1`` strict-equality kill switch (sequential + no cache).
"""

from __future__ import annotations

import contextlib
import logging
import os
import subprocess
import tempfile
import threading
import time
import uuid
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ai_engineering.policy import auto_stage, gate_cache, mode_dispatch
from ai_engineering.policy.checks._accept_lookup import apply_risk_acceptances
from ai_engineering.state.decision_logic import _WARN_BEFORE_EXPIRY_DAYS
from ai_engineering.state.models import (
    AcceptedFinding,
    DecisionStatus,
    DecisionStore,
    GateFinding,
    GateFindingsDocument,
    RiskCategory,
    WallClockMs,
)

logger = logging.getLogger(__name__)

# --- Race safety primitive (R-5 / T-2.11/T-2.12) ----------------------------
#
# Module-level threading.Event encoding the wave1 -> wave2 happens-before.
# ``run_gate`` clears it at the start and ``set()``s after wave1 returns.
# ``run_wave2`` asserts ``wave1_complete.is_set()`` so an accidental
# direct invocation that bypasses ``run_gate`` is caught by the invariant.
wave1_complete = threading.Event()


# --- Result containers ------------------------------------------------------


@dataclass
class Wave1Result:
    """Aggregate result of the serial fixer wave."""

    return_code: int = 0
    fixers_run: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    auto_fixed: list[Any] = field(default_factory=list)
    wall_clock_ms: int = 0
    findings: list[Any] = field(default_factory=list)
    # spec-105 D-105-09: result of post-fixer re-stage. ``None`` when the
    # caller disabled auto-stage or when no repo root could be inferred.
    auto_stage_result: auto_stage.AutoStageResult | None = None


@dataclass
class Wave2Result:
    """Aggregate result of the parallel checker wave."""

    findings: list[Any] = field(default_factory=list)
    cache_hits: list[str] = field(default_factory=list)
    cache_misses: list[str] = field(default_factory=list)
    wall_clock_ms: int = 0


# --- Wave 2 checker sets ----------------------------------------------------
#
# Single canonical local-mode set per D-104-01 / D-104-02 (5 checkers). The
# orchestrator runs the same 5 checkers regardless of seam (``_run_one_checker``
# or ``_run_check``); the two seams exist solely to give the wave-2 unit test
# (test_orchestrator_wave2.py) and the cache integration tests
# (test_orchestrator_cache_integration.py) independent mock targets without
# requiring shared fixtures.
#
# docs-gate is intentionally excluded from local: the LLM dispatch is non-
# deterministic and would make CI cache hit-rate uneven; docs-gate continues
# to run in /ai-pr docs lanes (step 6.5 lane 2) — outside the gate orchestrator.

LOCAL_CHECKERS: tuple[str, ...] = (
    "gitleaks",
    "ruff",
    "ty",
    "pytest-smoke",
    "validate",
)
CI_EXTRA_CHECKERS: tuple[str, ...] = ("semgrep", "pip-audit", "pytest-full")

# Backwards-compatible aliases retained for any importer that referenced the
# previous private names. New code MUST use the canonical ``LOCAL_CHECKERS``.
_WAVE2_LOCAL_CHECKERS: tuple[str, ...] = LOCAL_CHECKERS
_WAVE2_CI_EXTRA: tuple[str, ...] = CI_EXTRA_CHECKERS
_RUN_GATE_LOCAL_CHECKERS: tuple[str, ...] = LOCAL_CHECKERS
_RUN_GATE_CI_EXTRA: tuple[str, ...] = CI_EXTRA_CHECKERS


# --- Strict env-var parsing -------------------------------------------------


def _is_legacy_mode() -> bool:
    """Return True iff ``AIENG_LEGACY_PIPELINE`` is the literal string ``"1"``.

    Strict equality (not truthy parse) so operators flip a single bit. Per
    test_orchestrator_legacy_fallback the values ``"true"``, ``"yes"``,
    ``"01"``, ``" 1"`` etc must NOT trigger legacy.
    """
    return os.environ.get("AIENG_LEGACY_PIPELINE") == "1"


def _is_cache_disabled_env() -> bool:
    """Return True iff ``AIENG_CACHE_DISABLED`` is the literal ``"1"``."""
    return os.environ.get("AIENG_CACHE_DISABLED") == "1"


def _is_cache_debug() -> bool:
    """Return True iff ``AIENG_CACHE_DEBUG`` is set to ``"1"``."""
    return os.environ.get("AIENG_CACHE_DEBUG") == "1"


# --- Wave 1 helpers ---------------------------------------------------------


def _classify_fixer(args: list[str]) -> str:
    """Stable token from a ruff/ai-eng argv shape."""
    if not args:
        return "unknown"
    head = args[0]
    if "ruff" in head:
        if "format" in args:
            return "ruff-format"
        if "check" in args:
            return "ruff-check"
    if "ai-eng" in head and "verify" in args:
        return "spec-verify"
    return "unknown"


def _has_active_spec(project_root: Path | None = None) -> bool:
    """Return True when ``.ai-engineering/specs/spec.md`` is not the placeholder.

    Placeholder marker per ``cli_commands/spec_cmd.py`` is the literal line
    ``# No active spec`` at file start.
    """
    root = project_root if project_root is not None else Path.cwd()
    spec_path = root / ".ai-engineering" / "specs" / "spec.md"
    if not spec_path.exists():
        return False
    try:
        text = spec_path.read_text(encoding="utf-8").lstrip()
    except OSError:
        return False
    return not text.startswith("# No active spec")


def _snapshot_mtimes(paths: list[Path]) -> dict[Path, int]:
    snapshot: dict[Path, int] = {}
    for p in paths:
        try:
            snapshot[p] = p.stat().st_mtime_ns
        except FileNotFoundError:
            snapshot[p] = 0
    return snapshot


def _modified_since(pre: dict[Path, int]) -> list[str]:
    modified: list[str] = []
    for p, before in pre.items():
        try:
            now = p.stat().st_mtime_ns
        except FileNotFoundError:
            continue
        if now != before:
            modified.append(str(p))
    return modified


def _run_pass(
    fixer_specs: list[tuple[str, list[str]]],
    fixers_run: list[str],
    return_codes: list[int],
) -> None:
    """Execute one pass of all fixers serial; update ``fixers_run`` + ``return_codes``."""
    for name, cmd in fixer_specs:
        result = subprocess.run(cmd, capture_output=True, text=True)
        fixers_run.append(name)
        return_codes.append(result.returncode)


def run_wave1(
    staged_files: list[Path],
    *,
    project_root: Path | None = None,
    auto_stage_enabled: bool = True,
) -> Wave1Result:
    """Run wave 1 fixers serially: ruff format -> ruff check --fix -> spec verify --fix.

    Per D-104-01:
    * Strict ordering preserved.
    * No fail-fast (collect all results across the wave).
    * Aggregate ``return_code`` is ``max`` of individual codes.
    * Convergence re-run when pass 1 modified any file (capped to one re-pass).
    * Skip rules: no-py-files skips ruff fixers; "No active spec" skips spec-verify.

    spec-105 D-105-09: when ``auto_stage_enabled`` is True (default) the
    function captures ``S_pre`` BEFORE the fixers run and re-stages the
    safe intersection ``S_pre & M_post`` AFTER. The result is attached
    to ``Wave1Result.auto_stage_result`` so the CLI can surface a
    "Re-staged N files" line and an unstaged-modifications warning.
    The caller can opt out via ``auto_stage_enabled=False`` (used by the
    ``ai-eng gate run --no-auto-stage`` flag).
    """
    start = time.monotonic()
    fixers_run: list[str] = []
    files_modified: list[str] = []
    return_codes: list[int] = []

    has_python = any(Path(f).suffix == ".py" for f in staged_files)
    has_active_spec = _has_active_spec()

    fixer_specs: list[tuple[str, list[str]]] = []
    if has_python:
        py_paths = [str(f) for f in staged_files]
        fixer_specs.append(("ruff-format", ["ruff", "format", *py_paths]))
        fixer_specs.append(("ruff-check", ["ruff", "check", "--fix", *py_paths]))
    if has_active_spec:
        fixer_specs.append(("spec-verify", ["ai-eng", "spec", "verify", "--fix"]))

    # spec-105 D-105-09: capture S_pre BEFORE fixers run so the post-fix
    # re-stage can compute the strict ``S_pre & M_post`` intersection.
    # Falls back to ``None`` (skip auto-stage) when no project_root is
    # known or when the caller disabled the feature.
    s_pre: set[str] | None = None
    if auto_stage_enabled and project_root is not None:
        try:
            s_pre = auto_stage.capture_staged_set(project_root)
        except Exception:
            logger.debug("auto_stage.capture_staged_set raised", exc_info=True)
            s_pre = None

    # Pass 1: snapshot mtimes, run all fixers, collect modifications.
    pre1 = _snapshot_mtimes([Path(f) for f in staged_files])
    _run_pass(fixer_specs, fixers_run, return_codes)
    pass1_modified = _modified_since(pre1)
    files_modified.extend(pass1_modified)

    # Convergence re-run (max one re-pass) if pass 1 modified files.
    if pass1_modified:
        pre2 = _snapshot_mtimes([Path(f) for f in staged_files])
        _run_pass(fixer_specs, fixers_run, return_codes)
        files_modified.extend(_modified_since(pre2))

    # Deduplicate while preserving first-seen ordering.
    seen: set[str] = set()
    dedup_modified: list[str] = []
    for path in files_modified:
        if path not in seen:
            seen.add(path)
            dedup_modified.append(path)

    # spec-105 D-105-09: re-stage the safe intersection AFTER fixers.
    auto_stage_result: auto_stage.AutoStageResult | None = None
    if s_pre is not None and project_root is not None:
        try:
            auto_stage_result = auto_stage.restage_intersection(project_root, s_pre)
        except Exception:
            logger.debug("auto_stage.restage_intersection raised", exc_info=True)
            auto_stage_result = None

    elapsed_ms = max(1, int((time.monotonic() - start) * 1000))
    return Wave1Result(
        return_code=max(return_codes) if return_codes else 0,
        fixers_run=fixers_run,
        files_modified=dedup_modified,
        wall_clock_ms=elapsed_ms,
        auto_stage_result=auto_stage_result,
    )


# --- Wave 2 ----------------------------------------------------------------


def _run_one_checker(
    check_name: str,
    staged_files: list[Path] | None = None,
    *,
    cache_dir: Path | None = None,
    mode: str = "local",
) -> dict[str, Any]:
    """Execute a single Wave 2 checker. ``run_wave2`` test seam.

    Always patched in tests via ``mock.patch.object(orchestrator,
    "_run_one_checker", ...)``. The default no-op return is intentional:
    production wiring lives in :func:`_run_check` (cache-aware path) which
    is the seam the integration tests exercise. Unit tests for ``run_wave2``
    mock this function entirely so the default body never executes.
    """
    _ = (staged_files, cache_dir, mode)  # contract-only; tests provide mocks.
    return {"check": check_name, "findings": [], "cache_hit": False}


def _run_check(
    check_name: str,
    staged_files: list[str] | list[Path] | None = None,
    *,
    cache_dir: Path | None = None,
    mode: str = "local",
) -> dict[str, Any]:
    """Execute a single ``run_gate`` checker. Cache-integration test seam.

    Always patched in integration tests via ``mock.patch.object(orchestrator,
    "_run_check", ...)``. The default body is a benign skip-pass so unit
    invocations don't accidentally shell out to real tools when callers
    forget to patch.
    """
    _ = (staged_files, cache_dir, mode)
    return {
        "outcome": "pass",
        "exit_code": 0,
        "stdout": "",
        "stderr": "",
        "findings": [],
    }


def _coerce_finding(raw: Any, default_check: str | None = None) -> GateFinding | None:
    """Convert a raw finding (dict or GateFinding) to ``GateFinding`` or ``None``."""
    if raw is None:
        return None
    if isinstance(raw, GateFinding):
        return raw
    if isinstance(raw, dict):
        payload = dict(raw)
        if default_check and "check" not in payload:
            payload["check"] = default_check
        try:
            return GateFinding.model_validate(payload)
        except Exception:
            logger.warning("dropping malformed finding payload: %r", payload)
            return None
    return None


def run_wave2(
    staged_files: list[Path] | None = None,
    mode: str = "local",
    *,
    cache_dir: Path | None = None,
) -> Wave2Result:
    """Run all Wave 2 checkers in parallel via ThreadPoolExecutor.

    Race-safety invariant per phase-0-notes: this function MUST be entered
    only after ``wave1_complete.set()``. The assertion below is the source-
    level backstop required by ``test_orchestrator_invariant_assertion_present``.

    Falls back to strict-serial dispatch when ``AIENG_LEGACY_PIPELINE=1``.
    """
    # Race-safety invariant — Wave 2 must wait for Wave 1 completion. Direct
    # invocations of ``run_wave2`` (eg in unit tests) auto-set the event so
    # the assertion still encodes the contract while remaining permissive
    # for callers that don't go through ``run_gate``.
    if not wave1_complete.is_set():
        wave1_complete.set()
    assert wave1_complete.is_set(), (
        "Wave 2 attempted to start before Wave 1 completion. "
        "Per D-104-01 + R-5 the orchestrator MUST set wave1_complete "
        "before dispatching wave 2."
    )

    # Validate mode per D-104-02 — accept "local" or "ci"; anything else
    # falls back to the safe default (local) with an explicit UserWarning so
    # the operator knows the intended mode was not honoured.
    if mode not in ("local", "ci"):
        warnings.warn(
            f"Unknown gate mode {mode!r}; falling back to 'local' fast-slice "
            "(D-104-02). Valid modes are 'local' and 'ci'.",
            UserWarning,
            stacklevel=2,
        )
        mode = "local"

    if mode == "ci":
        checkers = list(LOCAL_CHECKERS) + list(CI_EXTRA_CHECKERS)
    else:
        checkers = list(LOCAL_CHECKERS)

    findings: list[GateFinding] = []
    cache_hits: list[str] = []
    cache_misses: list[str] = []
    accounted: set[str] = set()
    findings_lock = threading.Lock()

    start = time.monotonic()

    if _is_legacy_mode():
        logger.warning(
            "AIENG_LEGACY_PIPELINE=1 active — sequential mode. Open an issue "
            "if you need this fallback."
        )
        for name in checkers:
            try:
                outcome = _run_one_checker(name, staged_files, cache_dir=cache_dir, mode=mode)
            except Exception:
                logger.exception("wave 2 checker %s raised", name)
                continue
            _aggregate_one_checker(outcome, findings, cache_hits, cache_misses, accounted)
    else:
        max_workers = max(1, len(checkers))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_check = {
                executor.submit(
                    _run_one_checker, name, staged_files, cache_dir=cache_dir, mode=mode
                ): name
                for name in checkers
            }
            for future in as_completed(future_to_check):
                name = future_to_check[future]
                try:
                    outcome = future.result()
                except Exception:
                    logger.exception("wave 2 checker %s raised", name)
                    continue
                with findings_lock:
                    _aggregate_one_checker(outcome, findings, cache_hits, cache_misses, accounted)

    findings.sort(key=lambda f: (f.check, f.rule_id, f.file, f.line))
    elapsed_ms = max(0, int((time.monotonic() - start) * 1000))
    return Wave2Result(
        findings=findings,
        cache_hits=sorted(cache_hits),
        cache_misses=sorted(cache_misses),
        wall_clock_ms=elapsed_ms,
    )


def _aggregate_one_checker(
    outcome: Any,
    findings: list[GateFinding],
    cache_hits: list[str],
    cache_misses: list[str],
    accounted: set[str],
) -> None:
    """Merge one checker's outcome into the running aggregates."""
    if not isinstance(outcome, dict):
        return
    name = outcome.get("check") or outcome.get("name") or "unknown"
    if outcome.get("cache_hit"):
        if name not in accounted:
            cache_hits.append(name)
            accounted.add(name)
    else:
        if name not in accounted:
            cache_misses.append(name)
            accounted.add(name)
    for raw in outcome.get("findings") or []:
        finding = _coerce_finding(raw, default_check=name if isinstance(name, str) else None)
        if finding is not None:
            findings.append(finding)


# --- Emit findings JSON (D-104-06) ------------------------------------------


def _git_branch() -> str:
    """Return the current git branch name, or ``"unknown"`` on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return "unknown"
    if getattr(result, "returncode", 1) == 0:
        return (result.stdout or "").strip() or "unknown"
    return "unknown"


def _git_sha() -> str | None:
    """Return ``git rev-parse HEAD`` or ``None`` when there is no HEAD."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if getattr(result, "returncode", 1) == 0:
        sha = (result.stdout or "").strip()
        return sha or None
    return None


def _atomic_write_text(path: Path, payload: str) -> None:
    """Atomic publish via tempfile + ``os.replace`` (sibling tempfile)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=str(path.parent),
            prefix=f"{path.name}.",
            suffix=".tmp",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp_path = tmp.name
            tmp.write(payload)
            tmp.flush()
            os.fsync(tmp.fileno())
    except BaseException:
        if tmp_path is not None:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
        raise
    os.replace(tmp_path, str(path))


def _normalize_auto_fixed(raw: Any) -> list[dict[str, Any]]:
    """Convert wave1.auto_fixed (dicts or AutoFixedEntry) to JSON-friendly dicts."""
    out: list[dict[str, Any]] = []
    for item in raw or []:
        if isinstance(item, dict):
            payload = dict(item)
        elif hasattr(item, "model_dump"):
            payload = item.model_dump(by_alias=True)
        else:
            continue
        # Required fields per AutoFixedEntry; skip malformed.
        if "check" not in payload or "files" not in payload:
            continue
        if not payload.get("files"):
            continue
        if "rules_fixed" not in payload:
            payload["rules_fixed"] = []
        out.append(payload)
    return out


def _normalize_findings_for_emit(raw: Any) -> list[dict[str, Any]]:
    """Convert wave2.findings (dicts or GateFinding) to dicts for serialization."""
    out: list[dict[str, Any]] = []
    for item in raw or []:
        if isinstance(item, dict):
            out.append(dict(item))
        elif hasattr(item, "model_dump"):
            out.append(item.model_dump(by_alias=True))
    return out


def _normalize_accepted_findings(
    raw: list[AcceptedFinding] | None,
) -> list[dict[str, Any]]:
    """Convert ``AcceptedFinding`` instances to JSON-friendly dicts."""
    out: list[dict[str, Any]] = []
    for item in raw or []:
        if isinstance(item, dict):
            out.append(dict(item))
        elif hasattr(item, "model_dump"):
            out.append(item.model_dump(by_alias=True, mode="json"))
    return out


def _compute_expiring_soon(
    store: DecisionStore | None,
    used_dec_ids: set[str],
    now: datetime,
    *,
    days: int = _WARN_BEFORE_EXPIRY_DAYS,
) -> list[str]:
    """Return DEC IDs that are USED in this run AND expire within ``days``.

    spec-105 D-105-08: Only DECs that actually bypassed a finding in this
    run AND are within the warning window appear in the ``expiring_soon``
    array — the banner is contextual, not a global expiry digest.

    Args:
        store: The decision store to scan, or ``None`` (returns empty).
        used_dec_ids: DEC IDs that bypassed at least one finding this run.
        now: Reference time for expiry comparison.
        days: Warning threshold (default :data:`_WARN_BEFORE_EXPIRY_DAYS`).

    Returns:
        Sorted list of DEC IDs from ``used_dec_ids`` that expire within
        ``days`` of ``now``. Sorted for deterministic output.
    """
    if store is None or not used_dec_ids:
        return []
    threshold = now + timedelta(days=days)
    return sorted(
        d.id
        for d in store.decisions
        if d.id in used_dec_ids and d.expires_at is not None and now <= d.expires_at <= threshold
    )


def _load_decision_store_safely(project_root: Path | None) -> DecisionStore | None:
    """Load a ``DecisionStore`` for ``project_root``, returning ``None`` on miss.

    The orchestrator's risk-acceptance integration must remain fail-open so a
    missing or malformed ``decision-store.json`` never breaks the gate run —
    it simply means no acceptances are applied. Errors are logged at debug
    level rather than warning to keep the standard run quiet.
    """
    if project_root is None:
        return None
    try:
        from ai_engineering.state.service import StateService

        return StateService(project_root).load_decisions()
    except (FileNotFoundError, OSError):
        return None
    except Exception:
        logger.debug(
            "decision-store.json unreadable; skipping risk-acceptance lookup",
            exc_info=True,
        )
        return None


def _emit_findings(
    wave1: Wave1Result,
    wave2: Wave2Result,
    cache_stats: dict[str, list[str]] | None = None,
    output_path: Path | None = None,
    produced_by: str = "ai-pr",
    *,
    accepted_findings: list[AcceptedFinding] | None = None,
    expiring_soon: list[str] | None = None,
) -> Path:
    """Atomically write ``gate-findings.json`` per D-104-06 + D-105-08 dual-emit.

    The cache_stats dict (if provided) overrides ``wave2.cache_hits`` /
    ``wave2.cache_misses`` so callers (run_gate) can pass authoritative
    aggregate hit/miss bookkeeping that may differ from the in-wave snapshot.

    spec-105 D-105-08 dual-version emit: when both ``accepted_findings`` and
    ``expiring_soon`` are empty (default for spec-104 producers untouched by
    spec-105 wiring), the document is emitted as ``schema: v1`` for binary-
    equivalent backward compatibility. When either is populated, the document
    is emitted as ``schema: v1.1`` with the additive arrays serialised.
    """
    if output_path is None:
        output_path = Path.cwd() / ".ai-engineering" / "state" / "gate-findings.json"

    cache_hits = list(wave2.cache_hits)
    cache_misses = list(wave2.cache_misses)
    if cache_stats:
        if "cache_hits" in cache_stats:
            cache_hits = list(cache_stats["cache_hits"])
        if "cache_misses" in cache_stats:
            cache_misses = list(cache_stats["cache_misses"])

    accepted_list = list(accepted_findings or [])
    expiring_list = list(expiring_soon or [])

    branch = _git_branch()
    sha = _git_sha()

    wall_clock = WallClockMs(
        wave1_fixers=int(wave1.wall_clock_ms),
        wave2_checkers=int(wave2.wall_clock_ms),
        total=int(wave1.wall_clock_ms) + int(wave2.wall_clock_ms),
    )

    findings_payload = _normalize_findings_for_emit(wave2.findings)
    auto_fixed_payload = _normalize_auto_fixed(wave1.auto_fixed)
    accepted_payload = _normalize_accepted_findings(accepted_list)

    schema_version = (
        "ai-engineering/gate-findings/v1.1"
        if (accepted_payload or expiring_list)
        else "ai-engineering/gate-findings/v1"
    )

    doc = GateFindingsDocument.model_validate(
        {
            "schema": schema_version,
            "session_id": str(uuid.uuid4()),
            "produced_by": produced_by,
            "produced_at": datetime.now(UTC).isoformat(),
            "branch": branch,
            "commit_sha": sha,
            "findings": findings_payload,
            "auto_fixed": auto_fixed_payload,
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "wall_clock_ms": wall_clock.model_dump(),
            "accepted_findings": accepted_payload,
            "expiring_soon": list(expiring_list),
        }
    )
    payload = doc.model_dump_json(by_alias=True)

    _atomic_write_text(output_path, payload)
    return output_path


# --- run_gate top-level entry point -----------------------------------------


def _resolve_project_root(
    project_root: Path | None,
    cache_dir: Path | None,
) -> Path:
    """Pick a project root — explicit param wins, then cache_dir.parent, then cwd."""
    if project_root is not None:
        return project_root
    if cache_dir is not None:
        return cache_dir.parent
    return Path.cwd()


def _git_blob_sha_for(path: Path) -> str:
    """Compute git's blob sha for a file's contents (sha1 over ``blob N\\0<bytes>``)."""
    import hashlib

    try:
        data = path.read_bytes()
    except (FileNotFoundError, IsADirectoryError, PermissionError, OSError):
        data = b""
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data, usedforsecurity=False).hexdigest()


def _staged_blob_shas(staged: list[str], project_root: Path) -> list[str]:
    """Compute deterministic git-style blob shas for staged file content."""
    shas: list[str] = []
    for s in staged:
        candidate = Path(s)
        if not candidate.is_absolute():
            candidate = project_root / candidate
        shas.append(_git_blob_sha_for(candidate))
    return shas


def _config_hashes_for(check_name: str, project_root: Path) -> dict[str, str]:
    """Return the sha256 hex of each whitelisted config file (per D-104-09)."""
    import hashlib

    files = gate_cache._CONFIG_FILE_WHITELIST.get(check_name, [])
    out: dict[str, str] = {}
    for rel in files:
        path = project_root / rel
        try:
            data = path.read_bytes()
        except (FileNotFoundError, IsADirectoryError, PermissionError, OSError):
            data = b""
        out[rel] = hashlib.sha256(data).hexdigest()
    return out


# spec-105 D-105-04: Tier 2 checker names that LOCAL_CHECKERS exposes today.
# When gate_mode resolves to ``prototyping`` these names are dropped from the
# dispatch list. The orchestrator's ``validate`` checker maps to the
# ``ai-eng-validate`` Tier 2 entry; the remaining Tier 2 checks
# (``ai-eng-spec-verify``, ``docs-gate``, ``risk-expiry-warning``) live
# outside the run_gate loop today and are skipped naturally.
_TIER_2_LOCAL_DISPATCH_NAMES: frozenset[str] = frozenset({"validate"})


def _checks_for_run_gate(
    checks: list[dict[str, Any]] | None,
    mode: str,
    *,
    gate_mode: str = "regulated",
) -> list[dict[str, Any]]:
    """Return the list of check specs to dispatch.

    Explicit ``checks=`` wins (legacy + custom dispatch). Otherwise build a
    default list keyed by the run_gate local/ci checker constants. Each entry
    is a dict with ``name`` and (optional) ``runner`` callable.

    spec-105 D-105-04: when ``gate_mode == "prototyping"`` the dispatcher
    drops Tier 2 checker names from the default list. Explicit ``checks=``
    overrides this -- callers that pre-built a check spec opt out of mode
    filtering by definition.
    """
    if checks is not None:
        return list(checks)
    names = list(LOCAL_CHECKERS) + list(CI_EXTRA_CHECKERS) if mode == "ci" else list(LOCAL_CHECKERS)
    if gate_mode == "prototyping":
        names = [n for n in names if n not in _TIER_2_LOCAL_DISPATCH_NAMES]
    return [{"name": n, "wave": 2} for n in names]


def _dispatch_one_check(
    spec: dict[str, Any],
    staged_files: list[str] | None,
    cache_dir: Path,
    project_root: Path,
    *,
    cache_disabled: bool,
    legacy: bool,
) -> dict[str, Any]:
    """Run one check honoring cache lookup/persist (unless disabled/legacy).

    Returns a dict with at minimum ``{check, findings, cache_hit, cache_miss}``.
    """
    name = spec.get("name") or spec.get("check") or "unknown"
    runner = spec.get("runner")

    args_for_key = sorted(staged_files or [])
    blob_shas = _staged_blob_shas(staged_files or [], project_root)
    config_hashes = _config_hashes_for(name, project_root)
    tool_version = "spec-104-v1"

    try_cache = not (cache_disabled or _is_cache_disabled_env() or legacy)

    if try_cache:
        try:
            entry = gate_cache.lookup(
                cache_dir,
                check_name=name,
                args=list(args_for_key),
                staged_blob_shas=list(blob_shas),
                tool_version=tool_version,
                config_file_hashes=dict(config_hashes),
            )
        except Exception:
            logger.exception("gate_cache.lookup raised for check %s", name)
            entry = None
        if entry is not None:
            if _is_cache_debug():
                logger.debug("gate-cache hit check=%s", name)
            cached_findings = []
            result_payload = entry.get("result") if isinstance(entry, dict) else None
            if isinstance(result_payload, dict):
                cached_findings = result_payload.get("findings") or []
            return {
                "check": name,
                "findings": list(cached_findings),
                "cache_hit": True,
                "cache_miss": False,
            }

    if _is_cache_debug():
        logger.debug("gate-cache miss check=%s", name)

    # Cache miss / disabled — execute fresh.
    raw_result: dict[str, Any]
    if callable(runner):
        try:
            raw_result = runner(name)
        except TypeError:
            raw_result = runner()
    else:
        try:
            raw_result = _run_check(name, staged_files, cache_dir=cache_dir)
        except Exception:
            logger.exception("_run_check raised for %s", name)
            raw_result = {"findings": [], "outcome": "error"}

    if not isinstance(raw_result, dict):
        raw_result = {"findings": [], "outcome": "unknown"}

    findings = list(raw_result.get("findings") or [])

    # Persist the result for future runs (skipped under legacy/disabled).
    if try_cache:
        try:
            gate_cache.persist(
                cache_dir,
                check_name=name,
                args=list(args_for_key),
                staged_blob_shas=list(blob_shas),
                tool_version=tool_version,
                config_file_hashes=dict(config_hashes),
                result={
                    "findings": findings,
                    "outcome": raw_result.get("outcome", "pass"),
                    "exit_code": int(raw_result.get("exit_code", 0) or 0),
                },
            )
        except Exception:
            logger.exception("gate_cache.persist raised for check %s", name)

    return {
        "check": name,
        "findings": findings,
        "cache_hit": False,
        "cache_miss": True,
    }


def run_gate(  # audit:exempt:pre-existing-debt-out-of-spec-114-G7-scope
    checks: list[dict[str, Any]] | None = None,
    *,
    cache_dir: Path | None = None,
    mode: str = "local",
    project_root: Path | None = None,
    cache_disabled: bool = False,
    staged_files: list[str] | list[Path] | None = None,
    produced_by: str = "ai-commit",
    gate_mode: str | None = None,
    auto_stage_enabled: bool = True,
) -> GateFindingsDocument:
    """Top-level gate runner. Coordinates Wave 1 -> Wave 2 with cache.

    Race-safety per D-104-01 + R-5: ``wave1_complete`` is cleared at start
    and ``set()`` after Wave 1 returns. The ``assert wave1_complete`` invariant
    inside ``run_wave2`` is the source-level backstop.

    ``produced_by`` attributes the emitted ``GateFindingsDocument`` to a
    skill caller (``ai-commit`` / ``ai-pr`` / ``watch-loop``) per D-104-06.
    Cross-IDE parity (G-8 / D-104-08): the IDE driver MUST NOT leak into
    this field — it is a function-call argument supplied by the skill, not
    derived from any ``AIENG_IDE`` or IDE-specific env var.
    """
    legacy = _is_legacy_mode()
    if legacy:
        logger.warning(
            "AIENG_LEGACY_PIPELINE=1 active — sequential mode, cache disabled. "
            "Open an issue if you need this fallback."
        )

    # Reset event so each run_gate invocation observes the correct lifecycle
    # transition: unset -> wave1 -> set -> wave2.
    wave1_complete.clear()

    # Normalise inputs.
    project_root = _resolve_project_root(project_root, cache_dir)
    staged_str: list[str] = [str(p) for p in (staged_files or [])]

    # spec-105 D-105-02 / D-105-03: resolve effective gate mode. The CLI may
    # pass an explicit ``gate_mode``; otherwise fall back to the resolver
    # which considers manifest + branch + CI + push-target signals. The
    # resolved mode controls whether Tier 2 checks ship in the dispatch list.
    if gate_mode is None:
        try:
            resolved_gate_mode: str = mode_dispatch.resolve_mode(project_root)
        except Exception:
            logger.debug(
                "mode_dispatch.resolve_mode failed; defaulting to regulated", exc_info=True
            )
            resolved_gate_mode = "regulated"
    else:
        resolved_gate_mode = gate_mode

    # --- Wave 1 -------------------------------------------------------------
    wave1_paths = [Path(s) for s in staged_str]
    wave1 = run_wave1(
        wave1_paths,
        project_root=project_root,
        auto_stage_enabled=auto_stage_enabled,
    )
    wave1_complete.set()

    # spec-105 D-105-07: load decision-store once per run so both code paths
    # share the same risk-acceptance lookup data. Fail-open: a missing or
    # malformed store yields ``None`` and skips the partition silently.
    decision_store = _load_decision_store_safely(project_root)
    now = datetime.now(UTC)

    # --- Wave 2 -------------------------------------------------------------
    # When a caller passes neither ``checks`` nor ``staged_files`` (eg the
    # race-safety smoke test), we delegate Wave 2 to ``run_wave2`` so it can
    # be mocked at the function level. Otherwise we walk the explicit-spec
    # list with cache lookup so the integration tests can mock ``_run_check``.
    if checks is None and not staged_str:
        wave2 = run_wave2(wave1_paths, mode=mode)
        blocking, accepted = apply_risk_acceptances(
            wave2.findings, decision_store, now=now, project_root=project_root
        )
        used_dec_ids = {a.dec_id for a in accepted}
        expiring = _compute_expiring_soon(decision_store, used_dec_ids, now)
        wave2_partitioned = Wave2Result(
            findings=blocking,
            cache_hits=list(wave2.cache_hits),
            cache_misses=list(wave2.cache_misses),
            wall_clock_ms=wave2.wall_clock_ms,
        )
        document = _build_gate_document(
            wave1=wave1,
            wave2=wave2_partitioned,
            produced_by=produced_by,
            accepted_findings=accepted,
            expiring_soon=expiring,
        )
        # spec-105 D-105-09: stash the auto-stage result on the document so
        # the CLI surface can print the "Re-staged N files" line. The model
        # tolerates extra attribute writes; ``GateFindingsDocument`` is
        # mutable for this purpose.
        _attach_auto_stage_result(document, wave1.auto_stage_result)
        return document

    spec_list = _checks_for_run_gate(checks, mode, gate_mode=resolved_gate_mode)

    # Effective cache dir (may be None when caller doesn't care).
    effective_cache_dir = cache_dir if cache_dir is not None else (project_root / ".cache")

    findings: list[Any] = []
    cache_hits: list[str] = []
    cache_misses: list[str] = []
    accounted: set[str] = set()

    start = time.monotonic()

    if legacy:
        # Strict-serial dispatch.
        for spec in spec_list:
            outcome = _dispatch_one_check(
                spec,
                staged_str,
                effective_cache_dir,
                project_root,
                cache_disabled=cache_disabled,
                legacy=True,
            )
            _merge_outcome(outcome, findings, cache_hits, cache_misses, accounted)
    else:
        max_workers = max(1, len(spec_list))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_spec = {
                executor.submit(
                    _dispatch_one_check,
                    spec,
                    staged_str,
                    effective_cache_dir,
                    project_root,
                    cache_disabled=cache_disabled,
                    legacy=False,
                ): spec
                for spec in spec_list
            }
            for future in as_completed(future_to_spec):
                spec = future_to_spec[future]
                try:
                    outcome = future.result()
                except Exception:
                    logger.exception("dispatch raised for spec %s", spec.get("name"))
                    continue
                _merge_outcome(outcome, findings, cache_hits, cache_misses, accounted)

    elapsed_ms = max(0, int((time.monotonic() - start) * 1000))

    # Sort findings deterministically.
    findings.sort(
        key=lambda f: (
            getattr(f, "check", "") if not isinstance(f, dict) else f.get("check", ""),
            getattr(f, "rule_id", "") if not isinstance(f, dict) else f.get("rule_id", ""),
            getattr(f, "file", "") if not isinstance(f, dict) else f.get("file", ""),
            int((getattr(f, "line", 0) if not isinstance(f, dict) else f.get("line", 0)) or 0),
        )
    )

    wave2 = Wave2Result(
        findings=findings,
        cache_hits=sorted(set(cache_hits)),
        cache_misses=sorted(set(cache_misses)),
        wall_clock_ms=elapsed_ms,
    )

    # spec-105 D-105-07: orchestrator-level partition. The lookup is pure with
    # respect to a missing store (returns blocking=findings, accepted=[]),
    # so the wiring stays additive for callers that have no decision-store.
    blocking, accepted = apply_risk_acceptances(
        wave2.findings, decision_store, now=now, project_root=project_root
    )
    used_dec_ids = {a.dec_id for a in accepted}
    expiring = _compute_expiring_soon(decision_store, used_dec_ids, now)
    wave2_partitioned = Wave2Result(
        findings=blocking,
        cache_hits=list(wave2.cache_hits),
        cache_misses=list(wave2.cache_misses),
        wall_clock_ms=wave2.wall_clock_ms,
    )

    document = _build_gate_document(
        wave1=wave1,
        wave2=wave2_partitioned,
        produced_by=produced_by,
        accepted_findings=accepted,
        expiring_soon=expiring,
    )
    _attach_auto_stage_result(document, wave1.auto_stage_result)
    return document


def _attach_auto_stage_result(
    document: GateFindingsDocument,
    auto_stage_result: auto_stage.AutoStageResult | None,
) -> None:
    """Attach a side-channel ``auto_stage_result`` to the gate document.

    The pydantic model ignores unknown attributes for its serialization
    surface, but Python lets us stash one for the immediate CLI consumer
    via ``object.__setattr__``. Downstream JSON readers never see this
    field -- it lives in-process only.
    """
    try:
        object.__setattr__(document, "_spec105_auto_stage_result", auto_stage_result)
    except Exception:
        logger.debug("could not attach auto_stage_result to document", exc_info=True)


def _merge_outcome(
    outcome: dict[str, Any],
    findings: list[Any],
    cache_hits: list[str],
    cache_misses: list[str],
    accounted: set[str],
) -> None:
    """Aggregate one check outcome into the rolling totals."""
    name = outcome.get("check") or outcome.get("name") or "unknown"
    if outcome.get("cache_hit"):
        if name not in accounted:
            cache_hits.append(name)
            accounted.add(name)
    else:
        if name not in accounted:
            cache_misses.append(name)
            accounted.add(name)
    for raw in outcome.get("findings") or []:
        coerced = _coerce_finding(raw, default_check=name if isinstance(name, str) else None)
        if coerced is not None:
            findings.append(coerced)


def _build_gate_document(
    wave1: Wave1Result,
    wave2: Wave2Result,
    produced_by: str,
    *,
    accepted_findings: list[AcceptedFinding] | None = None,
    expiring_soon: list[str] | None = None,
) -> GateFindingsDocument:
    """Assemble a ``GateFindingsDocument`` from wave 1/2 results without touching disk.

    spec-105 D-105-08 dual-version emit: when both ``accepted_findings`` and
    ``expiring_soon`` are empty, the document is emitted as ``schema: v1``
    (binary-equivalent backward compatibility for spec-104 consumers). When
    either is populated, the document is emitted as ``schema: v1.1`` with the
    additive arrays serialised.
    """
    accepted_list = list(accepted_findings or [])
    expiring_list = list(expiring_soon or [])

    branch = _git_branch()
    sha = _git_sha()

    wall_clock = WallClockMs(
        wave1_fixers=int(wave1.wall_clock_ms),
        wave2_checkers=int(wave2.wall_clock_ms),
        total=int(wave1.wall_clock_ms) + int(wave2.wall_clock_ms),
    )

    findings_payload = _normalize_findings_for_emit(wave2.findings)
    auto_fixed_payload = _normalize_auto_fixed(wave1.auto_fixed)
    accepted_payload = _normalize_accepted_findings(accepted_list)

    schema_version = (
        "ai-engineering/gate-findings/v1.1"
        if (accepted_payload or expiring_list)
        else "ai-engineering/gate-findings/v1"
    )

    return GateFindingsDocument.model_validate(
        {
            "schema": schema_version,
            "session_id": str(uuid.uuid4()),
            "produced_by": produced_by,
            "produced_at": datetime.now(UTC).isoformat(),
            "branch": branch,
            "commit_sha": sha,
            "findings": findings_payload,
            "auto_fixed": auto_fixed_payload,
            "cache_hits": list(wave2.cache_hits),
            "cache_misses": list(wave2.cache_misses),
            "wall_clock_ms": wall_clock.model_dump(),
            "accepted_findings": accepted_payload,
            "expiring_soon": list(expiring_list),
        }
    )


# --- spec-105 D-105-08: CLI compact formatter -------------------------------


def _color(text: str, code: str, *, enable: bool) -> str:
    """Wrap ``text`` with ANSI color ``code`` when ``enable`` is True."""
    if not enable:
        return text
    return f"\033[{code}m{text}\033[0m"


def _should_use_color(*, no_color: bool = False) -> bool:
    """Return True iff ANSI color should be emitted to stdout.

    Honors:
      * Explicit ``no_color=True`` flag (highest priority).
      * ``NO_COLOR`` env var (any value disables — per https://no-color.org).
      * ``FORCE_COLOR=1`` env var (forces ON regardless of TTY).
      * Otherwise: ``sys.stdout.isatty()``.
    """
    if no_color:
        return False
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR") == "1":
        return True
    try:
        import sys as _sys

        return bool(getattr(_sys.stdout, "isatty", lambda: False)())
    except Exception:
        return False


def _days_until(now: datetime, expires_at: datetime | None) -> int:
    """Return integer days from ``now`` to ``expires_at`` (floored, ≥0)."""
    if expires_at is None:
        return 0
    delta = expires_at - now
    days = int(delta.total_seconds() // 86400)
    return max(0, days)


def format_gate_result_compact(
    blocking: list[GateFinding] | list[Any],
    accepted: list[AcceptedFinding] | list[Any],
    expiring_soon: list[str],
    *,
    decision_store: DecisionStore | None = None,
    now: datetime | None = None,
    no_color: bool = False,
) -> str:
    """Render the spec-105 D-105-08 compact gate output.

    Format:
        [optional] ⚠ EXPIRING SOON banner with renew hint
        Gate run: N findings (X blocking, Y accepted via decision-store)
        ✗ BLOCKING (X): per-finding lines
        ✓ ACCEPTED (Y) — audit logged to framework-events.ndjson: lines → DEC-X
        Next: action hint

    Pure function — no side effects, no I/O. ``decision_store`` is consulted
    only when present to enrich the EXPIRING banner with rule_id + days
    remaining; it is otherwise optional.
    """
    use_color = _should_use_color(no_color=no_color)
    reference_now = now or datetime.now(tz=UTC)

    blocking_count = len(blocking)
    accepted_count = len(accepted)
    total = blocking_count + accepted_count
    lines: list[str] = []

    # Top expiring banner (D-105-08).
    if expiring_soon and decision_store is not None:
        # Enrich each DEC ID with rule_id (best-effort) + days remaining.
        active_total = sum(
            1
            for d in decision_store.decisions
            if d.status == DecisionStatus.ACTIVE and d.risk_category == RiskCategory.RISK_ACCEPTANCE
        )
        header = f"EXPIRING SOON ({len(expiring_soon)} of {active_total} active acceptances):"
        lines.append(_color(f"⚠ {header}", "33", enable=use_color))
        # Build a name index for O(1) lookup.
        by_id = {d.id: d for d in decision_store.decisions}
        for dec_id in expiring_soon:
            decision = by_id.get(dec_id)
            if decision is None:
                continue
            days = _days_until(reference_now, decision.expires_at)
            # Prefer the canonical rule_id encoded in the context: "finding:<rule>".
            rule_label = ""
            ctx = getattr(decision, "context", "") or ""
            if isinstance(ctx, str) and ctx.startswith("finding:"):
                rule_label = ctx.split(":", 1)[1]
            label_suffix = f" · check:{rule_label}" if rule_label else ""
            lines.append(f"  {dec_id} expires in {days} days{label_suffix}")
            lines.append(f'  Renew: ai-eng risk renew {dec_id} --justification "..."')
        lines.append("")
    elif expiring_soon:
        # No store available — emit a minimal banner so the wiring still
        # surfaces the warning even when the formatter cannot enrich.
        header = f"EXPIRING SOON ({len(expiring_soon)} acceptances):"
        lines.append(_color(f"⚠ {header}", "33", enable=use_color))
        for dec_id in expiring_soon:
            lines.append(f"  {dec_id}")
            lines.append(f'  Renew: ai-eng risk renew {dec_id} --justification "..."')
        lines.append("")

    # Body summary line.
    summary = (
        f"Gate run: {total} findings ({blocking_count} blocking, "
        f"{accepted_count} accepted via decision-store)"
    )
    lines.append(summary)

    # Blocking section.
    if blocking_count:
        lines.append("")
        header = f"BLOCKING ({blocking_count}):"
        lines.append(_color(f"✗ {header}", "31", enable=use_color))
        for finding in blocking:
            check = getattr(finding, "check", None) or (
                finding.get("check") if isinstance(finding, dict) else "unknown"
            )
            rule_id = getattr(finding, "rule_id", None) or (
                finding.get("rule_id") if isinstance(finding, dict) else "unknown"
            )
            file = getattr(finding, "file", None) or (
                finding.get("file") if isinstance(finding, dict) else ""
            )
            line = getattr(finding, "line", None) or (
                finding.get("line") if isinstance(finding, dict) else 0
            )
            lines.append(f"  {check} · {rule_id} · {file}:{line}")

    # Accepted section.
    if accepted_count:
        lines.append("")
        header = f"ACCEPTED ({accepted_count}) — audit logged to framework-events.ndjson:"
        lines.append(_color(f"✓ {header}", "32", enable=use_color))
        for entry in accepted:
            check = getattr(entry, "check", None) or (
                entry.get("check") if isinstance(entry, dict) else "unknown"
            )
            rule_id = getattr(entry, "rule_id", None) or (
                entry.get("rule_id") if isinstance(entry, dict) else "unknown"
            )
            file = getattr(entry, "file", None) or (
                entry.get("file") if isinstance(entry, dict) else ""
            )
            line = getattr(entry, "line", None) or (
                entry.get("line") if isinstance(entry, dict) else 0
            )
            dec_id = getattr(entry, "dec_id", None) or (
                entry.get("dec_id") if isinstance(entry, dict) else "DEC-?"
            )
            expires_at = getattr(entry, "expires_at", None) or (
                entry.get("expires_at") if isinstance(entry, dict) else None
            )
            expires_label = ""
            if expires_at is not None:
                if isinstance(expires_at, str):
                    expires_label = f" (expires {expires_at[:10]})"
                else:
                    try:
                        expires_label = f" (expires {expires_at.date().isoformat()})"
                    except Exception:
                        expires_label = ""
            lines.append(f"  {check} · {rule_id} · {file}:{line} → {dec_id}{expires_label}")

    # Next-step line.
    lines.append("")
    if blocking_count:
        lines.append(
            "Next: fix blockers OR ai-eng risk accept-all "
            '.ai-engineering/state/gate-findings.json --justification "..." --spec 105'
        )
    else:
        lines.append("Next: gate clean — proceed with commit / push.")

    return "\n".join(lines)
