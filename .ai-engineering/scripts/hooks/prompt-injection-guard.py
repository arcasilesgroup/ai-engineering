#!/usr/bin/env python3
"""PreToolUse hook: scan tool inputs for prompt injection patterns + IOC matches.

Blocks CRITICAL injection matches (exit 2), warns on HIGH matches (exit 0).
Applies to Bash, Write, Edit, and MultiEdit tools.

spec-105 G-12: ``ai-eng risk accept`` and ``ai-eng risk accept-all`` are
explicitly whitelisted because their inputs (gate-findings.json fixtures)
intentionally embed rule names like ``aws-access-token`` /
``stripe-key`` / etc. that the injection-pattern set classifies as
CRITICAL. Whitelisted invocations bypass the pattern scan but still emit
a telemetry event so the bypass is auditable.

spec-107 D-107-05/06/07 (Phase 4): the hook also matches tool inputs
against a vendored IOC catalog (``.ai-engineering/security/iocs/iocs.json``)
and emits a 3-valued verdict per IOC match:

- ``allow``: no IOC match (default, fast path).
- ``deny``: IOC match without an active risk-acceptance — blocks the tool
  call (exit 2) with a remediation banner.
- ``warn``: IOC match WITH an active risk-acceptance for the canonical
  ``finding_id = sentinel-<category>-<pattern_normalized>`` — execution is
  permitted but a telemetry event is emitted so the bypass is auditable.

The IOC loader is fail-open: missing or corrupt ``iocs.json`` returns an
empty dict, which downstream evaluator treats as "no IOC layer active"
(``allow``-only) so a missing catalog never crashes the host.

The hook is intentionally stdlib-only (no ``ai_engineering.*`` imports)
mirroring the spec-105/spec-107 mcp-health.py contract — direct raw-JSON
parsing of decision-store.json keeps the hook independent of the
installer's runtime.
"""

import contextlib
import functools
import hashlib
import json
import os
import re
import shlex
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from _lib import risk_accumulator
from _lib.audit import is_debug_mode, passthrough_stdin
from _lib.hook_common import get_correlation_id, run_hook_safe
from _lib.hook_context import get_hook_context
from _lib.injection_patterns import PATTERNS
from _lib.observability import (
    emit_control_outcome,
    emit_framework_error,
    emit_framework_operation,
)

# spec-120 follow-up: PRISM-style risk accumulator wiring. Disable
# entirely with ``AIENG_RISK_ACCUMULATOR_DISABLED=1`` (e.g. tests that
# do not want risk-state.json side effects).
RISK_DISABLED = (os.environ.get("AIENG_RISK_ACCUMULATOR_DISABLED") or "").strip() == "1"
_RISK_COMPONENT = "hook.prompt-injection-guard"

# spec-139 M5.T1: module-level mtime LRU caches for the IOC catalogue and
# decision-store. The PreToolUse hook fires on every Bash/Edit/Write/MultiEdit
# call; without caching each invocation reparses ~38 KB of JSON from disk.
# The cache keys on (path, mtime_ns, size, ttl_window) — any change to the
# file invalidates the cache. Fail-open: any cache error falls back to a
# fresh read so a corrupt mtime never traps the host hook.
#
# Tunables:
# - ``AIENG_HOOK_CACHE_TTL_SEC`` (default 300): a wall-clock fallback so
#   long-lived interpreters (worktree shells, watch loops) eventually drop
#   the cache even when mtime is stable.
_IOC_CACHE: tuple[float, float, int, dict[str, Any]] | None = None
_DECISION_STORE_CACHE: tuple[float, float, int, dict[str, Any]] | None = None


def _hook_cache_ttl() -> float:
    """Return the per-process cache TTL in seconds.

    Reads ``AIENG_HOOK_CACHE_TTL_SEC`` once per call (cheap env lookup).
    Defaults to 300 s. Negative / unparseable values fall back to the
    default so a stray env var never disables the cache silently.
    """
    raw = (os.environ.get("AIENG_HOOK_CACHE_TTL_SEC") or "").strip()
    if not raw:
        return 300.0
    try:
        value = float(raw)
    except ValueError:
        return 300.0
    if value <= 0:
        return 300.0
    return value


def _stat_signature(path: Path) -> tuple[float, int] | None:
    """Return ``(mtime_ns, size)`` for ``path``, or ``None`` on stat failure.

    Returning ``None`` on any OS error keeps the cache miss path deterministic
    — the caller falls back to a fresh read rather than crashing.
    """
    try:
        st = path.stat()
    except OSError:
        return None
    return (float(st.st_mtime_ns), int(st.st_size))


def _apply_risk(
    project_root: Path,
    *,
    session_id: str | None,
    severity: str,
    ioc_id: str,
    correlation_id: str,
) -> None:
    """Add a finding to the per-session risk accumulator and act on the threshold.

    Pipeline:
    1. ``risk_accumulator.add(...)`` to bump the running score (writes
       ``runtime/risk-score.json``).
    2. ``risk_accumulator.threshold_action(...)`` maps the new score
       to one of ``silent | warn | block | force_stop``.
    3. ``warn`` emits a ``framework_operation`` (``risk_warn``) so the
       audit chain records the elevation. The hook does NOT block.
    4. ``block`` emits a ``framework_error`` (``risk_threshold_block``)
       and exits 2 — Claude Code interprets that as deny.
    5. ``force_stop`` emits ``risk_force_stop``, writes a ``decision:
       block`` JSON to stdout (so the user sees a deterministic
       termination message), and exits 2.

    Defensive: any exception inside the accumulator (corrupt state,
    write race) is swallowed — the host hook MUST keep running.
    Disable with ``AIENG_RISK_ACCUMULATOR_DISABLED=1``.
    """
    if RISK_DISABLED:
        return
    try:
        state = risk_accumulator.add(
            project_root,
            session_id=session_id or "unknown",
            severity=severity,
            ioc_id=ioc_id,
        )
        action = risk_accumulator.threshold_action(state.score)
    except Exception:
        return  # fail-open: never let risk telemetry break the host hook.
    if action == "warn":
        with contextlib.suppress(Exception):
            emit_framework_operation(
                project_root,
                operation="risk_warn",
                component=_RISK_COMPONENT,
                source="hook",
                correlation_id=correlation_id,
                metadata={"score": round(state.score, 2), "ioc_id": ioc_id},
            )
    elif action == "block":
        with contextlib.suppress(Exception):
            emit_framework_error(
                project_root,
                engine="ai_engineering",
                component=_RISK_COMPONENT,
                error_code="risk_threshold_block",
                source="hook",
                session_id=session_id,
                correlation_id=correlation_id,
                metadata={"score": round(state.score, 2), "ioc_id": ioc_id},
            )
        sys.exit(2)
    elif action == "force_stop":
        with contextlib.suppress(Exception):
            emit_framework_error(
                project_root,
                engine="ai_engineering",
                component=_RISK_COMPONENT,
                error_code="risk_force_stop",
                source="hook",
                session_id=session_id,
                correlation_id=correlation_id,
                metadata={"score": round(state.score, 2), "ioc_id": ioc_id},
            )
        sys.stdout.write(
            json.dumps(
                {
                    "decision": "block",
                    "additionalContext": (
                        f"Session terminated — accumulated risk "
                        f"{state.score:.1f} exceeds force_stop threshold."
                    ),
                }
            )
        )
        sys.stdout.flush()
        sys.exit(2)


_GUARDED_TOOLS = {"Bash", "Write", "Edit", "MultiEdit"}
_MIN_CONTENT_LEN = 10
_MAX_CONTENT_LEN = 4000

# spec-107 D-107-05: canonical IOC categories spec-mandated. The vendored
# upstream catalog also exposes ``suspicious_network`` and
# ``dangerous_commands`` aliases; both names index the same payload.
_IOC_CATEGORIES = ("sensitive_paths", "sensitive_env_vars", "malicious_domains", "shell_patterns")
_IOC_RELATIVE = Path(".ai-engineering") / "security" / "iocs" / "iocs.json"

# spec-105 G-12: commands that legitimately handle gate-findings JSON
# embedding secret-related rule names. Match by argv[0..2] joined with
# single spaces. Add new entries with care -- every whitelisted command
# bypasses the injection-pattern scan.
WHITELISTED_COMMANDS = frozenset(
    {
        "ai-eng risk accept-all",
        "ai-eng risk accept",
    }
)


def _extract_content(tool_name: str, tool_input: dict) -> str:
    """Extract scannable content from tool input based on tool type."""
    if tool_name in ("Write", "MultiEdit"):
        return tool_input.get("content", "")
    if tool_name == "Edit":
        return tool_input.get("new_string", "")
    if tool_name == "Bash":
        return tool_input.get("command", "")
    return ""


def _parsed_command_prefix(command: str) -> str | None:
    """Return the first three argv tokens joined with single spaces.

    Used to match against ``WHITELISTED_COMMANDS``. Returns ``None`` when
    parsing fails (malformed quoting) or the command has fewer than two
    tokens (top-level only -- never enough to be a whitelisted invocation).
    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) < 2:
        return None
    return " ".join(tokens[:3])


def _is_whitelisted(tool_name: str, content: str) -> str | None:
    """Return the matched whitelist key, or ``None`` if not whitelisted.

    Only Bash invocations can be whitelisted; Write/Edit/MultiEdit always
    pass through the pattern scan because the whitelist contract is
    ``ai-eng risk *`` CLI invocations -- not file edits.
    """
    if tool_name != "Bash":
        return None
    prefix = _parsed_command_prefix(content)
    if prefix is None:
        return None
    if prefix in WHITELISTED_COMMANDS:
        return prefix
    return None


# spec-131 sub-004 T-4.B / D-131-11: positive allow-list of read-only
# commands that legitimately bypass the IOC scan when invoked by a
# Task-tool sub-agent. The main thread still runs the full scan.
#
# spec-131 closure sweep (review-H1): ``cat`` is intentionally OMITTED
# from this allow-list. The lane was designed for read-only PROBES
# (``rg`` / ``grep`` / ``find`` / ``ls`` — discovery primitives) and
# ``cat`` is the highest-value exfiltration primitive a sub-agent can
# wield to leak arbitrary file content while bypassing the IOC scan.
# Removing it forces ``cat`` invocations through the full IOC veto
# path so ``sensitive_paths`` / ``sensitive_env_vars`` still apply.
# Regression test: ``tests/unit/hooks/test_prompt_injection_guard_subagent_lane.py``.
_SUBAGENT_READONLY_CMDS: frozenset[str] = frozenset({"rg", "grep", "find", "ls"})
_SUBAGENT_SHELL_META: frozenset[str] = frozenset({"|", ";", "&&", "||", ">", ">>", "<", "<<", "&"})
_SUBAGENT_FIND_DESTRUCTIVE: frozenset[str] = frozenset(
    {"-delete", "-exec", "-execdir", "-ok", "-okdir"}
)


# spec-131 sub-004 T-4.F / D-131-12: trusted-script lane.
#
# Dual-key enforcement (literal argv match + script bytes match) closes
# two bypass vectors:
#   1. ``bash -c "python3 trusted.py"`` — the inner command runs in a
#      subshell so the literal-argv match fails, denying the bypass.
#   2. Byte modification of ``trusted.py`` — sha256 in ``trustedScripts``
#      changes, the integrity check fails, drift is surfaced as a
#      framework_error.
#
# ``_TRUSTED_SCRIPT_DRIFT_SENTINEL`` is a non-empty constant returned
# when argv matches a trusted entry but the underlying bytes have
# drifted, so callers can distinguish a clean miss (None) from a
# tampered match.
_TRUSTED_SCRIPT_DRIFT_SENTINEL: str = "__trusted_script_drift__"


def _load_trusted_argvs(project_root: Path) -> list[str]:
    """Return the ``trustedArgvs`` list from ``hooks-manifest.json``.

    Fail-open: any I/O / parse failure returns an empty list — a missing
    or malformed manifest must never crash the host hook.
    """
    manifest_path = project_root / ".ai-engineering" / "state" / "hooks-manifest.json"
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return []
    if not isinstance(payload, dict):
        return []
    argvs = payload.get("trustedArgvs") or []
    if not isinstance(argvs, list):
        return []
    return [str(x) for x in argvs if isinstance(x, str) and x]


def _resolve_trusted_script_path(content: str, project_root: Path) -> Path | None:
    """Resolve the script path from a trusted argv form.

    Trusted argv forms are ``python3 <relative-path>`` shapes. The helper
    parses tokens and returns the absolute path to the candidate script
    so the integrity check can verify its bytes. Returns ``None`` when
    parsing fails or the path does not resolve to a regular file.
    """
    try:
        tokens = shlex.split(content)
    except ValueError:
        return None
    candidate: str | None = None
    for token in tokens:
        if token.endswith(".py") and not token.startswith("-"):
            candidate = token
            break
    if not candidate:
        return None
    abs_path = (project_root / candidate).resolve()
    if not abs_path.is_file():
        return None
    return abs_path


def _is_trusted_script_argv(content: str, project_root: Path) -> str | None:
    """Return the matched trusted argv, the drift sentinel, or None.

    Contract (spec-131 sub-004 D-131-12):
    1. ``content`` MUST literally equal one of the entries in
       ``trustedArgvs`` (post strip()). No wildcard, no prefix match —
       this closes the ``bash -c "..."`` and "extra args" bypasses.
    2. The corresponding script path MUST resolve to a file whose
       sha256 matches the ``trustedScripts`` entry.
    3. On a clean match -> return the matched argv string.
    4. On argv match + bytes drift -> return
       :data:`_TRUSTED_SCRIPT_DRIFT_SENTINEL` so the caller can emit a
       distinct framework_error (drift) instead of a clean bypass.
    5. No match -> ``None``.
    """
    if not content:
        return None
    stripped = content.strip()
    if not stripped:
        return None
    trusted_argvs = _load_trusted_argvs(project_root)
    if stripped not in trusted_argvs:
        return None
    script_path = _resolve_trusted_script_path(stripped, project_root)
    if script_path is None:
        return _TRUSTED_SCRIPT_DRIFT_SENTINEL
    try:
        from _lib.integrity import verify_trusted_script
    except Exception:
        return _TRUSTED_SCRIPT_DRIFT_SENTINEL
    ok, _reason = verify_trusted_script(script_path, project_root)
    if not ok:
        return _TRUSTED_SCRIPT_DRIFT_SENTINEL
    return stripped


def _is_subagent_readonly(content: str) -> str | None:
    """Return the matched argv0 when ``content`` is a clear read-only command.

    Contract (spec-131 sub-004 E-3):
    1. Parse via ``shlex.split``; malformed quoting -> None (fail-closed).
    2. ``argv[0]`` must be in :data:`_SUBAGENT_READONLY_CMDS`.
    3. No shell metacharacter token (``|``, ``;``, ``&&``, ``>``, ...).
    4. ``find`` must not carry destructive predicates
       (``-delete``, ``-exec``, ``-execdir``, ``-ok``, ``-okdir``).

    Returns the matched argv0 (for telemetry) on success, ``None`` otherwise.
    """
    if not content:
        return None
    try:
        tokens = shlex.split(content)
    except ValueError:
        return None
    if not tokens:
        return None
    argv0 = tokens[0]
    if argv0 not in _SUBAGENT_READONLY_CMDS:
        return None
    for token in tokens:
        if token in _SUBAGENT_SHELL_META:
            return None
    if argv0 == "find":
        for token in tokens:
            if token in _SUBAGENT_FIND_DESTRUCTIVE:
                return None
    return argv0


def _is_test_fixture_target(tool_name: str, tool_input: dict) -> str | None:
    """Return the file_path when Write/Edit targets a test fixture, else None.

    spec-107 D-107-06: IOC patterns embedded in test files (under ``tests/``,
    ``test_*.py``, or fixture directories) are legitimate. Without this
    bypass the hook would block writing IOC test fixtures via the very
    same patterns those tests exist to validate. The bypass emits a
    telemetry event so the audit trail records every test-fixture-bypassed
    write, preserving the spec-105 G-12 auditable-bypass contract.
    """
    if tool_name not in ("Write", "Edit", "MultiEdit"):
        return None
    file_path = tool_input.get("file_path") or ""
    if not isinstance(file_path, str) or not file_path:
        return None
    # Match repo-relative tests/ trees and pytest-style filenames.
    parts = Path(file_path).parts
    if "tests" in parts or "test_data" in parts or "fixtures" in parts:
        return file_path
    name = Path(file_path).name
    if name.startswith("test_") or name.endswith("_test.py"):
        return file_path
    return None


_DOC_EXTENSIONS = (".md", ".mdx", ".markdown", ".rst", ".txt")


def _is_doc_target(tool_name: str, tool_input: dict) -> str | None:
    """Return file_path when Write/Edit targets a non-executable doc file.

    spec-160 D-160-04: documentation/spec/runbook text legitimately cites
    sensitive-path and env-var literals. Such targets bypass ONLY the
    sensitive_paths / sensitive_env_vars IOC categories (D-160-05); the
    malicious_domains / shell_patterns categories and the Layer-2 injection
    scan still apply. The call site emits an auditable bypass event.
    """
    if tool_name not in ("Write", "Edit", "MultiEdit"):
        return None
    file_path = tool_input.get("file_path") or ""
    if not isinstance(file_path, str) or not file_path:
        return None
    if Path(file_path).suffix.lower() in _DOC_EXTENSIONS:
        return file_path
    return None


# ---------------------------------------------------------------------------
# spec-107 D-107-05/06/07: IOC catalog loading + 3-valued evaluation
# ---------------------------------------------------------------------------


def _ioc_catalog_path(project_root: Path) -> Path:
    """Resolve the vendored IOC catalog path."""
    return project_root / _IOC_RELATIVE


def _parse_ioc_catalog(payload: Any) -> dict[str, Any]:
    """Apply spec107_aliases dereference to a freshly-parsed catalog payload.

    Pulled out of :func:`load_iocs` so the cache fast-path can re-use the
    same dereferenced dict without re-parsing JSON. ``payload`` is the raw
    ``json.loads`` result; non-dict values collapse to an empty dict
    (fail-open).
    """
    if not isinstance(payload, dict):
        return {}
    # Dereference spec107_aliases: alias_key -> canonical_key. Inject the
    # canonical payload under the alias name so downstream evaluators that
    # reference the alias key continue to work without per-callsite changes.
    aliases = payload.get("spec107_aliases")
    if isinstance(aliases, dict):
        for alias_key, canonical_key in aliases.items():
            if not isinstance(alias_key, str) or not isinstance(canonical_key, str):
                continue
            if alias_key in payload:
                # Don't clobber an explicit (non-alias) entry.
                continue
            canonical = payload.get(canonical_key)
            if canonical is None:
                # Pointer to a missing canonical — skip silently (fail-open).
                continue
            payload[alias_key] = canonical
    return payload


def load_iocs(project_root: Path) -> dict[str, Any]:
    """Load the vendored IOC catalog (fail-open + module-level mtime cache).

    Returns an empty dict when the file is missing or corrupt — downstream
    callers treat empty as "no IOC layer active" so a missing or broken
    catalog never blocks the host. This is the deliberate fail-open
    posture: spec-107 D-107-05 prefers availability over secret-leak
    blocking when the catalog itself is absent (e.g. fresh checkout).

    spec-122-a (D-122-04): the catalog now stores only canonical
    category keys (``suspicious_network``, ``dangerous_commands``).
    Alias keys that legacy callers depend on (``malicious_domains``,
    ``shell_patterns``) are derived at load time from the
    ``spec107_aliases`` pointer map, which removes ~30 LOC of
    duplicated payload from ``iocs.json``. Pointers to unknown
    canonical keys are silently skipped (defensive: malformed catalog
    must never break callers).

    spec-139 M5.T1: the parsed catalog (~38 KB) is cached at module scope
    keyed on (mtime_ns, size, last-load-wall-clock). A fresh stat returns
    the cached dict when (mtime_ns, size) match the cache key AND the
    cache age is below ``AIENG_HOOK_CACHE_TTL_SEC``. The cache is shared
    across hook invocations within a single Python process (worktree
    shells, watch loops). Fail-open: any cache error reverts to a fresh
    read so a corrupt mtime never traps the host hook.
    """
    global _IOC_CACHE
    path = _ioc_catalog_path(project_root)
    if not path.exists():
        # Drop a stale cache when the catalog disappears between calls.
        _IOC_CACHE = None
        return {}
    sig = _stat_signature(path)
    now = time.monotonic()
    ttl = _hook_cache_ttl()
    cache = _IOC_CACHE
    if cache is not None and sig is not None:
        cached_loaded_at, cached_mtime, cached_size, cached_payload = cache
        if cached_mtime == sig[0] and cached_size == sig[1] and (now - cached_loaded_at) <= ttl:
            return cached_payload
    try:
        raw = path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        _IOC_CACHE = None
        return {}
    parsed = _parse_ioc_catalog(payload)
    # Cache only when stat succeeded — otherwise we cannot validate the
    # next call cheaply and would risk serving a stale catalog forever.
    _IOC_CACHE = (now, sig[0], sig[1], parsed) if sig is not None else None
    return parsed


# spec-160 D-160-01/02: opt-in fail-closed posture.
_FAIL_CLOSED_ENV = "AIENG_IOC_FAIL_CLOSED"
_MANIFEST_RELATIVE = Path(".ai-engineering") / "manifest.yml"


def _fail_closed_enabled(project_root: Path) -> bool:
    """Return True when the IOC layer should fail CLOSED on an unavailable catalog.

    spec-160 D-160-01: the posture is opt-in and default-off (fail-open).
    Resolution order (env wins, matching the repo escape-hatch pattern):

    1. ``AIENG_IOC_FAIL_CLOSED`` set to ``"1"`` -> True; ``"0"`` -> False.
    2. Else read ``manifest.yml`` ``security.iocs.fail_closed`` (lazy
       ``import yaml`` mirroring ``_lib/instincts.py``).
    3. Any ImportError / I/O / parse failure -> fail-open ``False`` so a
       broken manifest never locks out the host.
    """
    raw = (os.environ.get(_FAIL_CLOSED_ENV) or "").strip()
    if raw == "1":
        return True
    if raw == "0":
        return False
    manifest_path = project_root / _MANIFEST_RELATIVE
    try:
        import yaml

        payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    if not isinstance(payload, dict):
        return False
    security = payload.get("security")
    if not isinstance(security, dict):
        return False
    iocs = security.get("iocs")
    if not isinstance(iocs, dict):
        return False
    return bool(iocs.get("fail_closed") is True)


def _ioc_catalog_unavailable(project_root: Path) -> bool:
    """Return True iff the on-disk IOC catalog is missing OR unparseable.

    spec-160 D-160-02: an absent catalog and a corrupt/non-dict catalog are
    equally dangerous (both disable enforcement), so both count as
    "unavailable". A valid-but-empty ``{}`` catalog is AVAILABLE (returns
    False) — it parses cleanly, it just has no entries. This distinction is
    what lets a supplied ``catalog={}`` stay fail-open while a deleted or
    truncated file fails closed under the flag.
    """
    path = _ioc_catalog_path(project_root)
    if not path.exists():
        return True
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return True
    return not isinstance(payload, dict)


def _fail_closed_reason() -> str:
    """Recovery banner for a fail-closed deny (names every recovery path)."""
    return (
        "Sentinel IOC catalog unavailable and fail-closed is enabled. "
        "Recover by restoring .ai-engineering/security/iocs/iocs.json, "
        f"setting {_FAIL_CLOSED_ENV}=0 to revert to fail-open, or running "
        "ai-eng risk accept to bypass via the audited risk-acceptance lane."
    )


def _decision_store_path(project_root: Path) -> Path:
    """Resolve the project decision-store.json location."""
    return project_root / ".ai-engineering" / "state" / "decision-store.json"


def _parse_decision_timestamp(value: Any) -> datetime | None:
    """Parse an ISO-8601 timestamp; return None when missing/unparseable.

    ``None`` means "no expiry" (matches Pydantic Decision.expires_at
    semantics where None is perpetual).
    """
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _normalize_pattern(pattern: str) -> str:
    """Lower-case + replace `/` with `_` for canonical finding-id slug.

    spec-107 D-107-07: the canonical sentinel finding_id format is
    ``f"sentinel-{category}-{pattern_normalized}"``. Pattern normalization
    ensures idempotent lookups even when upstream IOC patterns contain
    path separators or upper-case characters.
    """
    return pattern.lower().replace("/", "_")


def canonical_finding_id(category: str, pattern: str) -> str:
    """Build the canonical sentinel finding_id used for risk-accept lookup."""
    return f"sentinel-{category}-{_normalize_pattern(pattern)}"


def _load_decision_store(project_root: Path) -> dict[str, Any]:
    """Load + cache the project decision-store.json (fail-open).

    spec-139 M5.T1: separate module-level cache from the IOC catalogue —
    the decision-store is mutated by ``ai-eng risk accept`` so we still
    invalidate on mtime change, but cache hits within the same TTL avoid
    the per-call JSON parse. Returns an empty dict on any I/O / parse
    failure so callers transparently treat it as "no acceptances".
    """
    global _DECISION_STORE_CACHE
    store_path = _decision_store_path(project_root)
    if not store_path.exists():
        _DECISION_STORE_CACHE = None
        return {}
    sig = _stat_signature(store_path)
    now = time.monotonic()
    ttl = _hook_cache_ttl()
    cache = _DECISION_STORE_CACHE
    if cache is not None and sig is not None:
        cached_loaded_at, cached_mtime, cached_size, cached_payload = cache
        if cached_mtime == sig[0] and cached_size == sig[1] and (now - cached_loaded_at) <= ttl:
            return cached_payload
    try:
        raw = store_path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        _DECISION_STORE_CACHE = None
        return {}
    if not isinstance(payload, dict):
        _DECISION_STORE_CACHE = None
        return {}
    _DECISION_STORE_CACHE = (now, sig[0], sig[1], payload) if sig is not None else None
    return payload


def find_active_risk_acceptance(
    project_root: Path,
    finding_id: str,
    *,
    now: datetime | None = None,
) -> dict | None:
    """Look up an active risk-acceptance entry by ``finding_id``.

    Mirrors the spec-105 ``find_active_risk_acceptance`` lookup primitive
    used by ``mcp-health.py`` (spec-107 D-107-01). Operates on raw JSON
    because the hook intentionally avoids ``ai_engineering.*`` imports
    (stdlib-only contract per ``_lib/observability.py`` header).

    A match must satisfy ALL of:
    - ``finding_id`` (or alias ``findingId``) equals the requested id
    - ``status`` equals ``"active"`` (case-insensitive)
    - ``risk_category`` (or ``riskCategory``) equals ``"risk-acceptance"``
    - ``expires_at`` (or ``expiresAt``) is absent OR strictly greater than ``now``

    Returns the matching decision dict, or ``None``. Failures opening or
    parsing the store are treated as "no acceptance" — the hook never
    crashes the host on malformed state. The store payload is fetched
    via the module-level cache (spec-139 M5.T1).
    """
    reference = now or datetime.now(UTC)
    payload = _load_decision_store(project_root)
    if not payload:
        return None
    decisions = payload.get("decisions")
    if not isinstance(decisions, list):
        return None
    for entry in decisions:
        if not isinstance(entry, dict):
            continue
        entry_finding = entry.get("finding_id") or entry.get("findingId")
        if entry_finding != finding_id:
            continue
        status = (entry.get("status") or "").lower()
        if status != "active":
            continue
        risk_category = (entry.get("risk_category") or entry.get("riskCategory") or "").lower()
        if risk_category != "risk-acceptance":
            continue
        expires_at = _parse_decision_timestamp(entry.get("expires_at") or entry.get("expiresAt"))
        if expires_at is not None and expires_at <= reference:
            continue
        return entry
    return None


_HOME_PREFIX = "~/"


def _expand_user_path(pattern: str) -> str:
    """Return the ``$HOME/``-expanded form of a ``~/``-prefixed IOC pattern.

    The vendored catalog uses ``~/`` to denote the user's home directory.
    For a ``~/X`` pattern this returns ``$HOME/X``; any other pattern is
    returned unchanged. Kept as a thin compatibility shim — the full
    equivalence set is produced by :func:`_expanded_literals` and
    :func:`_home_path_regex` (spec-160 D-160-07).
    """
    if pattern.startswith(_HOME_PREFIX):
        return "$HOME/" + pattern[len(_HOME_PREFIX) :]
    return pattern


@functools.lru_cache(maxsize=256)
def _expanded_literals(pattern: str) -> tuple[str, ...]:
    """Return the literal equivalence forms of a ``~/``-prefixed pattern.

    spec-160 D-160-07: a ``~/X`` catalog literal is also written by tools
    as ``$HOME/X`` and ``${HOME}/X``. For those forms a plain substring
    compare is enough (no regex), so they live here. Absolute-home and
    Windows forms need anchored regexes (see :func:`_home_path_regex`).

    Non-``~/`` patterns return a single-element tuple of themselves, so the
    caller can iterate uniformly. Cached because the catalog pattern set is
    tiny and stable across the per-call hot path.
    """
    if not pattern.startswith(_HOME_PREFIX):
        return (pattern,)
    suffix = pattern[len(_HOME_PREFIX) :]
    return (pattern, "$HOME/" + suffix, "${HOME}/" + suffix)


@functools.lru_cache(maxsize=256)
def _home_path_regex(pattern: str) -> re.Pattern[str] | None:
    """Compile an absolute-home + Windows equivalence regex for ``~/X``.

    spec-160 D-160-07/08: a ``~/X`` catalog literal must also match the
    absolute-home POSIX forms (``/Users/<u>/X``, ``/home/<u>/X``) and the
    Windows ``C:\\Users\\<u>\\X`` form (drive-letter, backslashes,
    case-insensitive). The regex is anchored to the catalog's specific
    suffix (R4 mitigation: never a bare home prefix) and the username
    segment is bounded to a single path component (``[^/\\s]+`` POSIX,
    ``[^\\\\\\s]+`` Windows) so it cannot over-broaden.

    Returns ``None`` for non-``~/`` patterns. Cached: compiled once per
    catalog pattern, reused across the hot path.
    """
    if not pattern.startswith(_HOME_PREFIX):
        return None
    suffix = pattern[len(_HOME_PREFIX) :]
    # POSIX: /Users/<u>/<suffix> or /home/<u>/<suffix>. Escape the suffix
    # so dots/special chars are literal; the username is one component.
    posix_suffix = re.escape(suffix)
    posix_alt = rf"(?:/Users/[^/\s]+|/home/[^/\s]+)/{posix_suffix}"
    # Windows: <drive>:\Users\<u>\<suffix-with-backslashes>. The content is
    # backslash-normalized to forward slashes by the caller for the compare,
    # so we anchor on the normalized form: <drive>:/Users/<u>/<suffix>.
    win_suffix = re.escape(suffix)
    win_alt = rf"[A-Za-z]:/Users/[^/\s]+/{win_suffix}"
    return re.compile(rf"(?:{posix_alt}|{win_alt})", re.IGNORECASE)


def _host_ioc_regex(token: str) -> str:
    """Boundary-anchored regex for a hostname / TLD indicator.

    Host indicators (known-bad domains, suspicious TLDs, paste sites)
    were previously matched as raw substrings, so a short two- or
    three-character TLD matched any dotted identifier — style-sheet
    selectors, utility class names, and member access on a benign
    source file all matched and drove the risk accumulator to a hard
    block.

    A bare TLD entry now matches only as a real domain suffix: a domain
    label must precede the dot AND a host terminator (anything other
    than ``[A-Za-z0-9-]``) must follow. A full domain entry matches
    only at host boundaries on both ends. Matching is case-insensitive
    (hostnames are).
    """
    if token.startswith("."):
        tld = re.escape(token[1:])
        return rf"(?i)[A-Za-z0-9-]+\.{tld}(?![A-Za-z0-9-])"
    domain = re.escape(token)
    return rf"(?i)(?<![A-Za-z0-9-]){domain}(?![A-Za-z0-9-])"


def _category_patterns(catalog: dict[str, Any], category: str) -> list[tuple[str, str]]:
    """Return ``[(kind, pattern), ...]`` tuples for a category.

    ``kind`` is one of ``"literal"`` (substring match) or ``"regex"``
    (re.search match). Schema mapping per upstream
    ``claude-mcp-sentinel/references/iocs.json`` (preserved verbatim):

    - ``sensitive_paths`` / ``sensitive_env_vars`` → ``patterns`` is
      LITERAL (path or env-var names); ``regex_patterns`` is REGEX.
    - ``malicious_domains`` (alias ``suspicious_network``) →
      ``known_malicious_domains`` (list[dict|str]) is LITERAL,
      ``suspicious_tlds`` / ``pastebin_style`` is LITERAL,
      ``suspicious_patterns`` is REGEX.
    - ``shell_patterns`` (alias ``dangerous_commands``) → ``patterns``
      is REGEX. There is no literal substring set for shell patterns.
    """
    section = catalog.get(category)
    if not isinstance(section, dict):
        return []
    out: list[tuple[str, str]] = []
    # `patterns` semantics differ by category (upstream schema quirk):
    # shell_patterns/dangerous_commands ships regex; the rest ship literals.
    patterns_kind = "regex" if category in ("shell_patterns", "dangerous_commands") else "literal"
    base_patterns = section.get("patterns") or []
    if isinstance(base_patterns, list):
        for p in base_patterns:
            if isinstance(p, str) and p:
                out.append((patterns_kind, p))
    regexes = section.get("regex_patterns") or []
    if isinstance(regexes, list):
        for p in regexes:
            if isinstance(p, str) and p:
                out.append(("regex", p))
    # malicious_domains-specific schema: nested dicts + alias lists.
    # Host/TLD entries use the ``host`` kind (boundary-anchored match,
    # not raw substring) so a short TLD can't false-positive on a
    # benign dotted identifier. The display token is preserved verbatim
    # so finding_id / risk-accept keys / telemetry are unchanged.
    domains = section.get("known_malicious_domains") or []
    if isinstance(domains, list):
        for entry in domains:
            if isinstance(entry, dict):
                domain = entry.get("domain")
                if isinstance(domain, str) and domain:
                    out.append(("host", domain))
            elif isinstance(entry, str) and entry:
                out.append(("host", entry))
    for alias_key in ("suspicious_tlds", "pastebin_style"):
        alias = section.get(alias_key) or []
        if isinstance(alias, list):
            for p in alias:
                if isinstance(p, str) and p:
                    out.append(("host", p))
    sus_patterns = section.get("suspicious_patterns") or []
    if isinstance(sus_patterns, list):
        for p in sus_patterns:
            if isinstance(p, str) and p:
                out.append(("regex", p))
    return out


def _match_pattern(content: str, kind: str, pattern: str) -> bool:
    """Return True when ``content`` matches ``pattern`` per ``kind`` rules."""
    if kind == "host":
        # Hostname / TLD IOC: boundary-anchored so a short TLD can't
        # match a benign dotted identifier (see _host_ioc_regex). The
        # built pattern is cached by the re module across calls.
        return re.search(_host_ioc_regex(pattern), content) is not None
    if kind == "literal":
        # spec-160 D-160-07: a ``~/X`` catalog literal is matched against its
        # full equivalence set — the ``~/``/``$HOME/``/``${HOME}/`` literal
        # forms (substring) plus the absolute-home + Windows regex forms.
        # Non-``~/`` literals fall through to a single plain substring check.
        if any(form in content for form in _expanded_literals(pattern)):
            return True
        rx = _home_path_regex(pattern)
        if rx is None:
            return False
        # Windows-shaped inputs use backslashes; compare a backslash-
        # normalized COPY so the POSIX match path (R3 mitigation) is never
        # mutated. The regex's POSIX alternative still matches the original
        # forward-slash form because normalization is a no-op there.
        if rx.search(content):
            return True
        normalized = content.replace("\\", "/")
        return bool(rx.search(normalized))
    if kind == "regex":
        try:
            return re.search(pattern, content) is not None
        except re.error:
            return False
    return False


def evaluate_against_iocs(
    project_root: Path,
    content: str,
    *,
    catalog: dict[str, Any] | None = None,
    now: datetime | None = None,
    skip_categories: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Evaluate ``content`` against the vendored IOC catalog.

    Returns a dict with at minimum:
    - ``verdict``: one of ``"allow"`` | ``"deny"`` | ``"warn"``
    - ``matches``: list of dicts with keys
      ``category``, ``pattern``, ``finding_id``, ``kind``, ``accepted``,
      ``dec_id``
    - ``reason``: human-readable string when verdict != allow

    Decision logic:
    - No IOC match → ``allow``.
    - At least one IOC match without an active risk-acceptance for its
      ``finding_id`` → ``deny``.
    - All IOC matches have active risk-acceptance entries → ``warn``
      (allow execution + every match emits a telemetry event so the
      audit trail records the bypass).

    The evaluator is pure (no I/O when ``catalog`` is supplied); pass a
    pre-loaded catalog from tests to avoid filesystem overhead.
    """
    cat = catalog if catalog is not None else load_iocs(project_root)
    if not cat:
        # spec-160 D-160-01/02: opt-in fail-closed. ONLY when the catalog was
        # loaded from disk (``catalog is None`` arg) AND fail-closed is enabled
        # AND the on-disk catalog is genuinely unavailable (missing/corrupt)
        # do we deny. A supplied valid-but-empty ``catalog={}`` stays fail-open.
        if (
            catalog is None
            and _fail_closed_enabled(project_root)
            and _ioc_catalog_unavailable(project_root)
        ):
            return {
                "verdict": "deny",
                "matches": [],
                "reason": _fail_closed_reason(),
            }
        return {"verdict": "allow", "matches": [], "reason": ""}

    matches: list[dict[str, Any]] = []
    any_unaccepted = False
    for category in _IOC_CATEGORIES:
        # spec-160 D-160-05: doc-context targets relax ONLY the credential
        # categories (sensitive_paths / sensitive_env_vars). All other
        # categories — and the Layer-2 injection scan in main() — stay active.
        if category in skip_categories:
            continue
        for kind, pattern in _category_patterns(cat, category):
            if not _match_pattern(content, kind, pattern):
                continue
            finding = canonical_finding_id(category, pattern)
            decision = find_active_risk_acceptance(project_root, finding, now=now)
            accepted = decision is not None
            if not accepted:
                any_unaccepted = True
            matches.append(
                {
                    "category": category,
                    "pattern": pattern,
                    "kind": kind,
                    "finding_id": finding,
                    "accepted": accepted,
                    "dec_id": decision.get("id") or decision.get("decision_id")
                    if decision
                    else None,
                }
            )
    if not matches:
        return {"verdict": "allow", "matches": [], "reason": ""}
    if any_unaccepted:
        names = ", ".join(f"{m['category']}:{m['pattern']}" for m in matches if not m["accepted"])
        return {
            "verdict": "deny",
            "matches": matches,
            "reason": (
                f"Sentinel IOC match: {names}. "
                f"To accept this risk: ai-eng risk accept --finding-id "
                f"{matches[0]['finding_id']} --severity medium "
                '--justification "..." --spec spec-107'
            ),
        }
    # All matches accepted via active DEC → warn (allow + audit).
    accepted_names = ", ".join(f"{m['category']}:{m['pattern']}" for m in matches)
    return {
        "verdict": "warn",
        "matches": matches,
        "reason": f"Sentinel IOC match accepted via DEC: {accepted_names}",
    }


def _emit_ioc_outcomes(project_root: Path, tool_name: str, result: dict[str, Any]) -> None:
    """Emit one control_outcome event per IOC match.

    - verdict=deny → one ``ioc-match-deny`` event per unaccepted match.
    - verdict=warn → one ``ioc-match-allowed-via-dec`` event per accepted
      match (D-107-06 mandates per-match emission for compliance trace).
    """
    verdict = result.get("verdict")
    matches = result.get("matches") or []
    for match in matches:
        if not isinstance(match, dict):
            continue
        accepted = match.get("accepted")
        if verdict == "deny" and not accepted:
            control = "ioc-match-deny"
            outcome = "failure"
        elif verdict == "warn" and accepted:
            control = "ioc-match-allowed-via-dec"
            outcome = "warning"
        else:
            continue
        meta = {
            "tool": tool_name,
            "category": match.get("category"),
            "pattern": match.get("pattern"),
            "finding_id": match.get("finding_id"),
            "kind": match.get("kind"),
            "dec_id": match.get("dec_id"),
        }
        with contextlib.suppress(Exception):
            emit_control_outcome(
                project_root,
                category="mcp-sentinel",
                control=control,
                component="hook.prompt-injection-guard",
                outcome=outcome,
                source="hook",
                metadata=meta,
            )
        # spec-120 #17: feed risk accumulator. Severity inferred from the
        # match category. CRITICAL on deny (un-accepted), HIGH otherwise.
        finding_id = match.get("finding_id") or match.get("pattern") or "unknown"
        severity = "CRITICAL" if (verdict == "deny" and not accepted) else "HIGH"
        with contextlib.suppress(Exception):
            _apply_risk(
                project_root,
                session_id=None,
                severity=severity,
                ioc_id=str(finding_id),
                correlation_id=get_correlation_id(),
            )


def main() -> None:
    ctx = get_hook_context()
    tool_name = ctx.data.get("tool_name", "")

    if tool_name not in _GUARDED_TOOLS:
        passthrough_stdin(ctx.data)
        return

    tool_input = ctx.data.get("tool_input", {})
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except (json.JSONDecodeError, TypeError):
            tool_input = {}

    content = _extract_content(tool_name, tool_input)

    if len(content) < _MIN_CONTENT_LEN:
        passthrough_stdin(ctx.data)
        return

    # spec-131 sub-004 T-4.B / D-131-11: sub-agent positive allow-list lane.
    # When the caller is a Task-tool sub-agent, short-circuit on clean
    # read-only commands (rg/grep/find/ls/cat without shell-metacharacters
    # or destructive predicates). Main-thread invocations still go through
    # the full IOC + injection-pattern scan. Telemetry preserves the bypass
    # in the audit chain (CLAUDE.md G-12 auditable-bypass contract).
    if tool_name == "Bash" and ctx.agent_kind == "subagent":
        matched_argv0 = _is_subagent_readonly(content)
        if matched_argv0 is not None:
            argv_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            with contextlib.suppress(Exception):
                emit_control_outcome(
                    ctx.project_root,
                    category="security",
                    control="subagent-readonly-bypass",
                    component="hook.prompt-injection-guard",
                    outcome="success",
                    source="hook",
                    metadata={
                        "tool": tool_name,
                        "argv0": matched_argv0,
                        "argv_hash": argv_hash,
                    },
                )
            passthrough_stdin(ctx.data)
            return

    # spec-131 sub-004 T-4.F / D-131-12: trusted-script lane. Hash-pinned
    # scripts (e.g. session_bootstrap.py once sub-003 lands it) bypass
    # RTK rewriting + IOC re-evaluation when invoked in the exact argv
    # form the manifest pins. Drift on the underlying bytes surfaces as
    # a framework_error (R-131-07 mitigation).
    if tool_name == "Bash":
        trusted_outcome = _is_trusted_script_argv(content, ctx.project_root)
        if trusted_outcome == _TRUSTED_SCRIPT_DRIFT_SENTINEL:
            with contextlib.suppress(Exception):
                emit_framework_error(
                    ctx.project_root,
                    engine="ai_engineering",
                    component="hook.prompt-injection-guard",
                    error_code="trusted_script_drift",
                    source="hook",
                    session_id=ctx.session_id,
                    correlation_id=get_correlation_id(),
                    metadata={"tool": tool_name, "argv": content[:200]},
                )
            sys.stderr.write(
                "[prompt-injection-guard] trusted-script integrity drift; "
                "regenerate hooks-manifest.json and retry.\n"
            )
            sys.stderr.flush()
            sys.exit(3)
        if trusted_outcome is not None:
            with contextlib.suppress(Exception):
                emit_control_outcome(
                    ctx.project_root,
                    category="security",
                    control="trusted-script-bypass",
                    component="hook.prompt-injection-guard",
                    outcome="success",
                    source="hook",
                    metadata={
                        "tool": tool_name,
                        "argv": trusted_outcome[:200],
                    },
                )
            passthrough_stdin(ctx.data)
            return

    # spec-105 G-12: short-circuit pattern scan for whitelisted CLI
    # invocations. The findings.json payload embeds rule names like
    # ``aws-access-token`` / ``stripe-key`` that the CRITICAL pattern set
    # would otherwise flag. Emit telemetry so the bypass remains auditable.
    matched_command = _is_whitelisted(tool_name, content)
    if matched_command is not None:
        argv_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        emit_control_outcome(
            ctx.project_root,
            category="security",
            control="prompt-guard-whitelisted",
            component="hook.prompt-injection-guard",
            outcome="success",
            source="hook",
            metadata={
                "tool": tool_name,
                "command": matched_command,
                "argv_hash": argv_hash,
            },
        )
        passthrough_stdin(ctx.data)
        return

    scan_content = content[:_MAX_CONTENT_LEN]

    # spec-107 D-107-06: Write/Edit operations targeting test fixtures
    # legitimately embed IOC patterns (the catalog itself, IOC test
    # fixtures, etc.). Bypass the IOC scan for those targets but emit a
    # telemetry event so every bypass is auditable.
    fixture_path = _is_test_fixture_target(tool_name, tool_input)
    if fixture_path is not None:
        argv_hash = hashlib.sha256(scan_content.encode("utf-8")).hexdigest()
        with contextlib.suppress(Exception):
            emit_control_outcome(
                ctx.project_root,
                category="security",
                control="ioc-scan-test-fixture-bypass",
                component="hook.prompt-injection-guard",
                outcome="success",
                source="hook",
                metadata={
                    "tool": tool_name,
                    "file_path": fixture_path,
                    "content_hash": argv_hash,
                },
            )
        passthrough_stdin(ctx.data)
        return

    # spec-160 D-160-04/05/06: doc-context bypass. A Write/Edit to a
    # doc-extension target legitimately cites credential-path / env-var
    # literals (security runbooks, specs, CHANGELOG). Relax ONLY the
    # sensitive_paths + sensitive_env_vars categories for those targets;
    # malicious_domains / shell_patterns and the Layer-2 injection scan
    # below stay active. Bash never receives this bypass. Emit an auditable
    # event carrying tool + file_path + skipped categories — never the raw
    # matched literal (Open Question resolution / D-160-06).
    doc_path = _is_doc_target(tool_name, tool_input)
    skip_cats: tuple[str, ...] = ()
    if doc_path is not None:
        skip_cats = ("sensitive_paths", "sensitive_env_vars")
        with contextlib.suppress(Exception):
            emit_control_outcome(
                ctx.project_root,
                category="security",
                control="ioc-scan-doc-context-bypass",
                component="hook.prompt-injection-guard",
                outcome="success",
                source="hook",
                metadata={
                    "tool": tool_name,
                    "file_path": doc_path,
                    "skipped_categories": list(skip_cats),
                },
            )

    # spec-107 D-107-05/06/07: IOC catalog evaluation. Runs BEFORE the
    # injection-pattern scan so a sentinel-classified payload never
    # reaches the (looser) prompt-injection layer. Fail-open: missing
    # catalog returns verdict=allow + matches=[] which is a no-op.
    ioc_result = evaluate_against_iocs(ctx.project_root, scan_content, skip_categories=skip_cats)
    if ioc_result["verdict"] in ("deny", "warn"):
        _emit_ioc_outcomes(ctx.project_root, tool_name, ioc_result)
    if ioc_result["verdict"] == "deny":
        feedback = {
            "decision": "block",
            "reason": ioc_result["reason"],
        }
        sys.stdout.write(json.dumps(feedback))
        sys.stdout.flush()
        sys.exit(2)
    if ioc_result["verdict"] == "warn":
        sys.stderr.write(
            f"[prompt-injection-guard] WARN sentinel IOC accepted via risk-acceptance: "
            f"{ioc_result['reason']}\n"
        )
        sys.stderr.flush()

    critical_matches = []
    high_matches = []

    for pattern in PATTERNS:
        if pattern.regex.search(scan_content):
            match_info = {"pattern": pattern.name, "severity": pattern.severity}
            if pattern.severity == "CRITICAL":
                critical_matches.append(match_info)
            else:
                high_matches.append(match_info)

    all_matches = critical_matches + high_matches

    if all_matches:
        emit_control_outcome(
            ctx.project_root,
            category="security",
            control="prompt-injection-guard",
            component="hook.prompt-injection-guard",
            outcome="failure" if critical_matches else "warning",
            source="hook",
            metadata={
                "tool": tool_name,
                "matches": all_matches,
                "action": "blocked" if critical_matches else "warned",
            },
        )

        if is_debug_mode():
            debug_log = ctx.project_root / ".ai-engineering" / "state" / "telemetry-debug.log"
            try:
                timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                names = ", ".join(m["pattern"] for m in all_matches)
                with open(debug_log, "a", encoding="utf-8") as f:
                    f.write(f"[{timestamp}] injection scan: tool={tool_name} matches=[{names}]\n")
            except Exception:
                pass

    if critical_matches:
        pattern_names = ", ".join(m["pattern"] for m in critical_matches)
        feedback = {
            "decision": "block",
            "reason": (
                f"Prompt injection detected: {pattern_names}. "
                "This tool call has been blocked for security. "
                "Please rephrase your request without injection patterns."
            ),
        }
        sys.stdout.write(json.dumps(feedback))
        sys.stdout.flush()
        sys.exit(2)

    if high_matches:
        pattern_names = ", ".join(m["pattern"] for m in high_matches)
        sys.stderr.write(
            f"[prompt-injection-guard] WARNING: Suspicious pattern detected: {pattern_names}. "
            "Allowing tool call but logging for review.\n"
        )
        sys.stderr.flush()

    passthrough_stdin(ctx.data)


if __name__ == "__main__":
    run_hook_safe(
        main,
        component="hook.prompt-injection-guard",
        hook_kind="pre-tool-use",
        script_path=__file__,
    )
