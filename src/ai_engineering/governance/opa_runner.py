"""OPA subprocess wrapper (spec-122 Phase C, T-3.5).

Replaces the custom mini-Rego interpreter at ``governance.policy_engine``
with a thin shim around the OPA CLI. ``evaluate(query, input_dict, *,
bundle_path=None, timeout=5.0) -> OpaResult`` invokes
``opa eval --bundle <path> --input <stdin>``, parses the JSON result, and
returns a small typed value.

The binary path is memoised via ``shutil.which`` on first call to avoid
repeating ~10 ms PATH scans on the hot path. Missing binary raises
:class:`OpaError` with a clear ``run 'ai-eng install'`` message; callers
treat this as fail-closed with a remediation hint (see T-3.11/T-3.12 for
the wiring).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Memoised path to the OPA binary. ``None`` means "not yet looked up";
# any string means "looked up — this is the answer (may be empty if not
# installed)". The sentinel-vs-string distinction matters because we
# want to retry exactly once if the install lands mid-session.
_OPA_PATH_CACHE: str | None = None
_OPA_PATH_CHECKED: bool = False

# Default location of the signed policy bundle once `opa build` lands.
# Kept as a module constant so callers (gates, decision_log) can share
# the same default without re-deriving it.
DEFAULT_BUNDLE_PATH: Path = Path(".ai-engineering") / "policies"

__all__ = [
    "DEFAULT_BUNDLE_PATH",
    "OpaError",
    "OpaResult",
    "available",
    "evaluate",
    "evaluate_bundle",
    "reset_path_cache",
    "version",
    "which",
]


class OpaError(RuntimeError):
    """Raised when OPA cannot be invoked or returns a malformed payload.

    The message is user-facing — callers either propagate it verbatim
    (CLI surfaces) or wrap it in a `framework_error` event (gate hooks).
    """


@dataclass(frozen=True)
class OpaResult:
    """Outcome of an ``opa eval`` invocation.

    Attributes
    ----------
    allow:
        Convenience flag — ``True`` when the queried expression evaluated
        to a truthy non-empty value, ``False`` otherwise. For
        ``data.<pkg>.allow`` queries this is the obvious mapping; for
        ``data.<pkg>.deny`` queries ``allow`` is ``False`` whenever the
        deny set is non-empty (i.e. inverted semantics on the caller's
        side).
    deny_messages:
        Flat list of deny strings extracted from the raw result. Empty
        when the query is ``data.<pkg>.allow`` or when nothing fired.
    raw:
        The full JSON document emitted by ``opa eval``, kept verbatim
        for callers that need access to other expressions / metadata.
    """

    allow: bool
    deny_messages: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Binary lookup (memoised)
# ---------------------------------------------------------------------------


def reset_path_cache() -> None:
    """Reset the memoised binary path. Used by tests."""
    global _OPA_PATH_CACHE, _OPA_PATH_CHECKED
    _OPA_PATH_CACHE = None
    _OPA_PATH_CHECKED = False


def which() -> str | None:
    """Return the path to the OPA binary, or ``None`` if not installed.

    The result is memoised on the first call to avoid repeated PATH
    walks on the gate hot path. Call :func:`reset_path_cache` from tests
    that need to simulate install / uninstall transitions.
    """
    global _OPA_PATH_CACHE, _OPA_PATH_CHECKED
    if not _OPA_PATH_CHECKED:
        _OPA_PATH_CACHE = shutil.which("opa")
        _OPA_PATH_CHECKED = True
    return _OPA_PATH_CACHE


def available() -> bool:
    """``True`` iff the OPA binary is on PATH."""
    return which() is not None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def version() -> str:
    """Return the running OPA version string (e.g. ``"1.16.1"``).

    Raises
    ------
    OpaError
        If the binary is missing, the subprocess fails, or the output
        does not match the expected ``Version: <semver>`` shape.
    """
    binary = which()
    if binary is None:
        raise OpaError("opa not installed; run 'ai-eng install'")
    try:
        proc = subprocess.run(
            [binary, "version"],
            capture_output=True,
            text=True,
            timeout=5.0,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise OpaError("opa version timed out") from exc
    except OSError as exc:
        raise OpaError(f"opa version failed to launch: {exc}") from exc
    if proc.returncode != 0:
        raise OpaError(
            f"opa version exited with code {proc.returncode}: {proc.stderr.strip()}",
        )
    for line in proc.stdout.splitlines():
        if line.lower().startswith("version:"):
            return line.split(":", 1)[1].strip()
    raise OpaError(f"opa version output missing 'Version:' line: {proc.stdout!r}")


def evaluate(
    query: str,
    input_data: dict[str, Any] | None = None,
    *,
    bundle_path: Path | str | None = None,
    timeout: float = 5.0,
) -> OpaResult:
    """Run ``opa eval`` against ``query`` and return a typed result.

    Parameters
    ----------
    query:
        Rego query expression, e.g. ``"data.commit_conventional.deny"``.
    input_data:
        JSON-serialisable dict piped as the ``--stdin-input`` payload.
        ``None`` is sent as ``{}`` to avoid OPA's "no input" warning.
    bundle_path:
        Path to the bundle directory or signed bundle archive. Defaults
        to :data:`DEFAULT_BUNDLE_PATH`.
    timeout:
        Subprocess wall-clock timeout in seconds.

    Returns
    -------
    OpaResult
        Typed wrapper around the JSON document emitted by ``opa eval``.

    Raises
    ------
    OpaError
        Missing binary, subprocess failure, malformed JSON, or empty
        result set.
    """
    binary = which()
    if binary is None:
        raise OpaError("opa not installed; run 'ai-eng install'")

    bundle = Path(bundle_path) if bundle_path is not None else DEFAULT_BUNDLE_PATH
    payload = json.dumps(input_data if input_data is not None else {})

    cmd = [
        binary,
        "eval",
        "--bundle",
        str(bundle),
        "--stdin-input",
        "--format",
        "json",
        query,
    ]

    try:
        proc = subprocess.run(
            cmd,
            input=payload,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise OpaError(f"opa eval timed out after {timeout}s") from exc
    except OSError as exc:
        raise OpaError(f"opa eval failed to launch: {exc}") from exc

    if proc.returncode != 0:
        raise OpaError(
            f"opa eval exited with code {proc.returncode}: {proc.stderr.strip()}",
        )

    try:
        raw = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise OpaError(f"opa eval emitted malformed JSON: {exc}; output={proc.stdout!r}") from exc

    return _result_from_raw(raw, query=query)


def evaluate_bundle(
    query: str,
    input_data: dict[str, Any] | None,
    bundle_path: Path | str,
    *,
    timeout: float = 5.0,
) -> OpaResult:
    """Convenience wrapper for callers that always pass a bundle path.

    Equivalent to :func:`evaluate` with ``bundle_path`` required. Kept as
    a separate public symbol because the call sites (gate checks,
    risk-cmd) read more clearly when the bundle path is the third arg
    rather than a keyword.
    """
    return evaluate(query, input_data, bundle_path=bundle_path, timeout=timeout)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _result_from_raw(raw: dict[str, Any], *, query: str) -> OpaResult:
    """Translate the ``opa eval --format json`` payload into ``OpaResult``."""
    results = raw.get("result") or []
    if not isinstance(results, list) or not results:
        # No results means the rule was undefined for the given input
        # (e.g. `allow` without matching `allow if`). For `deny` queries
        # this is an allow; for `allow` queries this is a deny.
        return OpaResult(allow=False, deny_messages=[], raw=raw)

    first = results[0]
    if not isinstance(first, dict):
        raise OpaError(f"opa eval result[0] is not an object: {first!r}")

    expressions = first.get("expressions") or []
    if not isinstance(expressions, list) or not expressions:
        raise OpaError(f"opa eval result[0].expressions missing or empty: {first!r}")

    expr = expressions[0]
    if not isinstance(expr, dict):
        raise OpaError(f"opa eval expressions[0] is not an object: {expr!r}")

    value = expr.get("value")
    deny_messages = _extract_deny_messages(value) if "deny" in query else []
    allow = _truthy(value) and not deny_messages
    return OpaResult(allow=allow, deny_messages=deny_messages, raw=raw)


def _extract_deny_messages(value: Any) -> list[str]:
    """Flatten a deny rule's value into a list of strings.

    OPA emits set-typed rule values as JSON arrays; the policies in
    spec-122 use ``deny contains "msg" if ...`` so the value shape is
    ``["msg1", "msg2", ...]``. Accepts ``None`` and empty lists as
    "nothing fired".
    """
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if isinstance(value, dict):
        # Legacy ``deny["msg"]`` (and ``deny["msg"] if ...``) assigns
        # produce a set-as-object shape ``{"msg": true, ...}``. The
        # message is the key, not the value.
        return [str(key) for key in value if key is not None]
    return [str(value)]


def _truthy(value: Any) -> bool:
    """Boolean conversion that matches OPA's view of "set this allow"."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, dict):
        return len(value) > 0
    return bool(value)
