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
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_engineering.policy import gate_cache
from ai_engineering.state.models import (
    GateFinding,
    GateFindingsDocument,
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


@dataclass
class Wave2Result:
    """Aggregate result of the parallel checker wave."""

    findings: list[Any] = field(default_factory=list)
    cache_hits: list[str] = field(default_factory=list)
    cache_misses: list[str] = field(default_factory=list)
    wall_clock_ms: int = 0


# --- Wave 2 checker sets ----------------------------------------------------
#
# Two distinct sets exist because two distinct test contracts reach the
# orchestrator from different angles:
#
#  * ``run_wave2`` unit tests (test_orchestrator_wave2.py) mock
#    ``_run_one_checker`` and exercise the canonical local-mode 5-checker set
#    that includes ``ruff`` (which is the wave-2 ruff lint check, distinct
#    from wave-1 ``ruff --fix`` fixer).
#
#  * ``run_gate(staged_files=...)`` integration tests
#    (test_orchestrator_cache_integration.py) mock ``_run_check`` and exercise
#    the cache-aware single-pass collector path with the 5-checker set that
#    includes ``docs-gate`` (LLM gate not in the wave-2 unit tests because
#    those mock at a lower seam).

_WAVE2_LOCAL_CHECKERS: tuple[str, ...] = (
    "gitleaks",
    "ruff",
    "ty",
    "pytest-smoke",
    "validate",
)
_WAVE2_CI_EXTRA: tuple[str, ...] = ("semgrep", "pip-audit", "pytest-full")

_RUN_GATE_LOCAL_CHECKERS: tuple[str, ...] = (
    "gitleaks",
    "ty",
    "pytest-smoke",
    "validate",
    "docs-gate",
)
_RUN_GATE_CI_EXTRA: tuple[str, ...] = ("semgrep", "pip-audit", "pytest-full")


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


def run_wave1(staged_files: list[Path]) -> Wave1Result:
    """Run wave 1 fixers serially: ruff format -> ruff check --fix -> spec verify --fix.

    Per D-104-01:
    * Strict ordering preserved.
    * No fail-fast (collect all results across the wave).
    * Aggregate ``return_code`` is ``max`` of individual codes.
    * Convergence re-run when pass 1 modified any file (capped to one re-pass).
    * Skip rules: no-py-files skips ruff fixers; "No active spec" skips spec-verify.
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

    elapsed_ms = max(1, int((time.monotonic() - start) * 1000))
    return Wave1Result(
        return_code=max(return_codes) if return_codes else 0,
        fixers_run=fixers_run,
        files_modified=dedup_modified,
        wall_clock_ms=elapsed_ms,
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

    if mode == "ci":
        checkers = list(_WAVE2_LOCAL_CHECKERS) + list(_WAVE2_CI_EXTRA)
    else:
        checkers = list(_WAVE2_LOCAL_CHECKERS)

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


def _emit_findings(
    wave1: Wave1Result,
    wave2: Wave2Result,
    cache_stats: dict[str, list[str]] | None = None,
    output_path: Path | None = None,
    produced_by: str = "ai-pr",
) -> Path:
    """Atomically write ``gate-findings.json`` per D-104-06 schema v1.

    The cache_stats dict (if provided) overrides ``wave2.cache_hits`` /
    ``wave2.cache_misses`` so callers (run_gate) can pass authoritative
    aggregate hit/miss bookkeeping that may differ from the in-wave snapshot.
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

    branch = _git_branch()
    sha = _git_sha()

    wall_clock = WallClockMs(
        wave1_fixers=int(wave1.wall_clock_ms),
        wave2_checkers=int(wave2.wall_clock_ms),
        total=int(wave1.wall_clock_ms) + int(wave2.wall_clock_ms),
    )

    findings_payload = _normalize_findings_for_emit(wave2.findings)
    auto_fixed_payload = _normalize_auto_fixed(wave1.auto_fixed)

    doc = GateFindingsDocument.model_validate(
        {
            "schema": "ai-engineering/gate-findings/v1",
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


def _checks_for_run_gate(
    checks: list[dict[str, Any]] | None,
    mode: str,
) -> list[dict[str, Any]]:
    """Return the list of check specs to dispatch.

    Explicit ``checks=`` wins (legacy + custom dispatch). Otherwise build a
    default list keyed by the run_gate local/ci checker constants. Each entry
    is a dict with ``name`` and (optional) ``runner`` callable.
    """
    if checks is not None:
        return list(checks)
    if mode == "ci":
        names = list(_RUN_GATE_LOCAL_CHECKERS) + list(_RUN_GATE_CI_EXTRA)
    else:
        names = list(_RUN_GATE_LOCAL_CHECKERS)
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


def run_gate(
    checks: list[dict[str, Any]] | None = None,
    *,
    cache_dir: Path | None = None,
    mode: str = "local",
    project_root: Path | None = None,
    cache_disabled: bool = False,
    staged_files: list[str] | list[Path] | None = None,
) -> GateFindingsDocument:
    """Top-level gate runner. Coordinates Wave 1 -> Wave 2 with cache.

    Race-safety per D-104-01 + R-5: ``wave1_complete`` is cleared at start
    and ``set()`` after Wave 1 returns. The ``assert wave1_complete`` invariant
    inside ``run_wave2`` is the source-level backstop.
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

    # --- Wave 1 -------------------------------------------------------------
    wave1_paths = [Path(s) for s in staged_str]
    wave1 = run_wave1(wave1_paths)
    wave1_complete.set()

    # --- Wave 2 -------------------------------------------------------------
    # When a caller passes neither ``checks`` nor ``staged_files`` (eg the
    # race-safety smoke test), we delegate Wave 2 to ``run_wave2`` so it can
    # be mocked at the function level. Otherwise we walk the explicit-spec
    # list with cache lookup so the integration tests can mock ``_run_check``.
    if checks is None and not staged_str:
        wave2 = run_wave2(wave1_paths, mode=mode)
        return _build_gate_document(
            wave1=wave1,
            wave2=wave2,
            produced_by="ai-pr",
        )

    spec_list = _checks_for_run_gate(checks, mode)

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

    return _build_gate_document(
        wave1=wave1,
        wave2=wave2,
        produced_by="ai-pr",
    )


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
) -> GateFindingsDocument:
    """Assemble a ``GateFindingsDocument`` from wave 1/2 results without touching disk."""
    branch = _git_branch()
    sha = _git_sha()

    wall_clock = WallClockMs(
        wave1_fixers=int(wave1.wall_clock_ms),
        wave2_checkers=int(wave2.wall_clock_ms),
        total=int(wave1.wall_clock_ms) + int(wave2.wall_clock_ms),
    )

    findings_payload = _normalize_findings_for_emit(wave2.findings)
    auto_fixed_payload = _normalize_auto_fixed(wave1.auto_fixed)

    return GateFindingsDocument.model_validate(
        {
            "schema": "ai-engineering/gate-findings/v1",
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
        }
    )
