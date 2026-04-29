"""Gate cache (spec-104 D-104-03, D-104-09, D-104-10).

Persist + lookup + invalidate + prune for gate-check results, keyed by
`_compute_cache_key`. Robust against torn writes via tempfile + ``os.replace``.
Honors override flags (``disabled=`` kwarg, ``AIENG_CACHE_DISABLED`` env) and
emits debug markers (``AIENG_CACHE_DEBUG``) for hit-rate observability.

The module supports two complementary call signatures:

* **Keyword form** -- caller provides cache-key inputs (``check_name``, ``args``,
  ``staged_blob_shas``, ``tool_version``, ``config_file_hashes``); the helper
  computes the cache key internally and writes a structured entry containing
  ``check_name``/``key_inputs``/``result``/``verified_at`` fields. Used by the
  orchestrator (D-104-01).
* **Positional form** -- caller provides the precomputed ``cache_key`` and a
  raw entry dict; the helper writes the dict verbatim (with ``verified_at``
  refreshed to UTC now). Used by ``--force`` and other CLI flows that already
  hold the key.

Both forms persist into ``cache_dir / f"{cache_key}.json"`` so a lookup against
the same ``cache_key`` round-trips cleanly. Lookup returns ``None`` for
miss/disabled/stale/future/corrupt and a :class:`CacheEntry` (a dict subclass
with attribute access) for hit -- with ``cache_hit=True`` injected for callers
that wish to log replay decisions in ``gate-findings.json``.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os as _stdlib_os
import tempfile
import types
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Module-local ``os`` proxy so tests can ``mock.patch`` our atomic-publish call
# (``os.replace``) without mutating the global ``os`` module — patching the
# real ``os.replace`` would also affect any test helper that re-enters
# ``os.replace`` (e.g., to validate the patched call), causing recursion.
# All ``os`` API access in this module goes through this namespace.
os = types.SimpleNamespace(
    replace=_stdlib_os.replace,
    rename=_stdlib_os.rename,
    fsync=_stdlib_os.fsync,
    unlink=_stdlib_os.unlink,
    sep=_stdlib_os.sep,
    environ=_stdlib_os.environ,
)

# D-104-03 invariants
MAX_AGE_HOURS = 24
MAX_ENTRIES = 256

# D-104-09: per-check whitelist of config files whose hash invalidates the cache.
_CONFIG_FILE_WHITELIST: dict[str, list[str]] = {
    "ruff-format": ["pyproject.toml", ".ruff.toml", "ruff.toml"],
    "ruff-check": ["pyproject.toml", ".ruff.toml", "ruff.toml"],
    "gitleaks": [".gitleaks.toml", "gitleaks.toml"],
    "ty": ["pyproject.toml", ".ai-engineering/manifest.yml"],
    "pytest-smoke": ["pyproject.toml", "pytest.ini", "conftest.py"],
    "validate": [".ai-engineering/manifest.yml"],
    "spec-verify": [".ai-engineering/specs/spec.md", ".ai-engineering/specs/plan.md"],
    "docs-gate": [".ai-engineering/manifest.yml"],
}


def _compute_cache_key(
    check_name: str,
    args: list[str],
    staged_blob_shas: list[str],
    tool_version: str,
    config_file_hashes: dict[str, str],
) -> str:
    """Deterministic 32-char hex cache key for a gate check invocation.

    Inputs are sorted before hashing to make ordering irrelevant.
    """
    parts = [
        check_name,
        tool_version,
        "|".join(sorted(staged_blob_shas)),
        "|".join(f"{k}:{v}" for k, v in sorted(config_file_hashes.items())),
        "|".join(sorted(args)),
    ]
    payload = " ".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:32]


# ---------------------------------------------------------------------------
# CacheEntry — dict subclass with attribute access
# ---------------------------------------------------------------------------


class CacheEntry(dict):
    """A cached gate check result.

    Implemented as a ``dict`` subclass with ``__getattr__`` fallback so that
    callers may use either attribute access (``entry.check_name``) or dict
    access (``entry.get("check_name")``). The shape on disk varies by which
    persist signature wrote the file:

    * Keyword-form persist writes ``{check_name, key_inputs, result, verified_at}``.
    * Positional-form persist writes the caller's dict verbatim with
      ``verified_at`` refreshed to UTC now.

    Lookup augments the on-disk dict with ``cache_hit=True`` before returning.
    """

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


# ---------------------------------------------------------------------------
# Atomic write + corruption-safe read (T-1.2)
# ---------------------------------------------------------------------------


def _atomic_write(path: Path, data: dict) -> None:
    """Write ``data`` as JSON to ``path`` atomically.

    Uses ``tempfile.NamedTemporaryFile`` in the same directory as the target
    (so ``os.replace`` does not cross filesystems and remains atomic) and then
    publishes via ``os.replace`` (atomic on both POSIX and Windows -- see
    phase-0-notes.md Risk-C).

    Windows-specific retry: ``os.replace`` can raise ``PermissionError`` when
    another process (or pytest-xdist worker) momentarily holds a handle on
    the target path -- AV scanners, indexers, and concurrent persist() calls
    against neighbouring keys all trigger the lock. POSIX never lifts this
    failure mode. A bounded retry with backoff converts the transient
    Windows lock into a successful replace; if it still fails after the
    budget, the original exception propagates to the caller (which on the
    orchestrator path swallows + logs, preserving the legacy contract while
    eliminating the flake on healthy systems).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=path.parent,
            prefix=f"{path.name}.",
            suffix=".tmp",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp_path = tmp.name
            json.dump(data, tmp, ensure_ascii=False)
            tmp.flush()
            os.fsync(tmp.fileno())
    except BaseException:
        # Cleanup the partial tempfile if dump failed before context exit.
        if tmp_path is not None:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
        raise
    _replace_with_retry(tmp_path, path)


# Windows-only transient-lock budget for ``os.replace``. 5 attempts with
# 25/50/100/200/400 ms backoff covers typical AV-scan / indexer windows
# without slowing the POSIX path (which never enters the loop body).
_REPLACE_MAX_ATTEMPTS: int = 5
_REPLACE_BACKOFF_MS: int = 25


def _replace_with_retry(src: str, dst: Path) -> None:
    """``os.replace(src, dst)`` with bounded retry on Windows lock errors.

    Raises the last :class:`PermissionError` / :class:`OSError` if the
    budget is exhausted -- callers that swallow exceptions retain that
    behaviour (the orchestrator already logs and continues), so the
    failure mode tightens but does not regress.
    """
    import time as _time

    last_exc: OSError | None = None
    delay_ms = _REPLACE_BACKOFF_MS
    for _ in range(_REPLACE_MAX_ATTEMPTS):
        try:
            os.replace(src, dst)
            return
        except PermissionError as exc:
            # Windows transient lock (AV / indexer / sibling persist call).
            last_exc = exc
            _time.sleep(delay_ms / 1000.0)
            delay_ms *= 2
        except OSError as exc:
            # Non-Permission OSError (e.g. cross-device, EBADF) is not a
            # lock issue; do not waste retries.
            raise exc from None
    if last_exc is not None:
        raise last_exc


def _read_safe(path: Path) -> dict | None:
    """Return the parsed JSON dict, or ``None`` for missing/empty/corrupt files.

    Logs a WARNING on corruption so operators see drift; never raises. Handles
    binary garbage (invalid UTF-8) and truncated JSON in addition to standard
    decode errors.
    """
    try:
        raw_bytes = path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        logger.warning("gate-cache entry unreadable at %s: %s", path, exc)
        return None
    if not raw_bytes:
        return None
    try:
        raw = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        logger.warning(
            "gate-cache entry corrupt (invalid UTF-8, decode error) at %s: %s",
            path,
            exc,
        )
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning(
            "gate-cache entry corrupt (invalid JSON, decode error) at %s: %s",
            path,
            exc,
        )
        return None
    if not isinstance(parsed, dict):
        logger.warning(
            "gate-cache entry at %s did not parse to a JSON object (got %s)",
            path,
            type(parsed).__name__,
        )
        return None
    return parsed


# ---------------------------------------------------------------------------
# Override flags + observability helpers
# ---------------------------------------------------------------------------


def _is_disabled(disabled: bool) -> bool:
    """Return True when caller opted out OR ``AIENG_CACHE_DISABLED`` is set.

    Per D-104-10 the env var is the more-conservative override and wins over
    a permissive ``disabled=False`` kwarg.
    """
    if os.environ.get("AIENG_CACHE_DISABLED") == "1":
        return True
    return disabled


def _debug_enabled() -> bool:
    """True when ``AIENG_CACHE_DEBUG=1`` -- emit hit/miss markers on the logger."""
    return os.environ.get("AIENG_CACHE_DEBUG") == "1"


def _entry_path(cache_dir: Path, cache_key: str) -> Path:
    return cache_dir / f"{cache_key}.json"


def _resolve_cache_key(
    cache_key: str | None,
    check_name: str | None,
    args: list[str] | None,
    staged_blob_shas: list[str] | None,
    tool_version: str | None,
    config_file_hashes: dict[str, str] | None,
) -> str:
    """Return the cache key to use, computing from kwargs when ``cache_key`` absent."""
    if cache_key is not None:
        return cache_key
    if (
        check_name is None
        or args is None
        or staged_blob_shas is None
        or tool_version is None
        or config_file_hashes is None
    ):
        raise TypeError(
            "lookup/persist requires either cache_key (positional) or the full set "
            "of cache-key inputs (check_name, args, staged_blob_shas, tool_version, "
            "config_file_hashes)"
        )
    return _compute_cache_key(
        check_name=check_name,
        args=args,
        staged_blob_shas=staged_blob_shas,
        tool_version=tool_version,
        config_file_hashes=config_file_hashes,
    )


# ---------------------------------------------------------------------------
# lookup (T-1.4 + T-1.6 + T-1.10)
# ---------------------------------------------------------------------------


def lookup(
    cache_dir: Path,
    cache_key: str | None = None,
    *,
    check_name: str | None = None,
    args: list[str] | None = None,
    staged_blob_shas: list[str] | None = None,
    tool_version: str | None = None,
    config_file_hashes: dict[str, str] | None = None,
    disabled: bool = False,
) -> CacheEntry | None:
    """Return the cached entry for the given key, or ``None`` on miss/disabled/stale.

    Two equivalent call shapes:

    * Positional: ``lookup(cache_dir, cache_key)`` -- key is precomputed.
    * Keyword: ``lookup(cache_dir=..., check_name=..., args=..., staged_blob_shas=...,
      tool_version=..., config_file_hashes=...)`` -- key derived via
      :func:`_compute_cache_key`.

    Side-effects:
    * On a stale-or-future entry, the on-disk file is removed so the next
      caller regenerates a fresh entry instead of recycling drift.
    * On a corrupted file, a WARNING is logged and the call returns ``None``
      without modifying state (LRU prune cleans up corruption later).
    """
    if _is_disabled(disabled):
        if _debug_enabled():
            logger.debug(
                "gate-cache disabled (env or kwarg) -- lookup miss key=%s",
                cache_key or "<computed>",
            )
        return None

    key = _resolve_cache_key(
        cache_key,
        check_name,
        args,
        staged_blob_shas,
        tool_version,
        config_file_hashes,
    )
    path = _entry_path(cache_dir, key)
    raw = _read_safe(path)
    if raw is None:
        if _debug_enabled():
            logger.debug("gate-cache miss key=%s path=%s", key, path)
        return None

    verified_at_str = raw.get("verified_at")
    if not isinstance(verified_at_str, str):
        logger.warning(
            "gate-cache entry at %s missing/invalid verified_at field -- treating as miss",
            path,
        )
        with contextlib.suppress(FileNotFoundError):
            path.unlink()
        if _debug_enabled():
            logger.debug("gate-cache miss (no verified_at) key=%s", key)
        return None

    try:
        verified_at = datetime.fromisoformat(verified_at_str.replace("Z", "+00:00"))
    except ValueError as exc:
        logger.warning(
            "gate-cache entry at %s has unparseable verified_at=%r (%s) -- treating as miss",
            path,
            verified_at_str,
            exc,
        )
        with contextlib.suppress(FileNotFoundError):
            path.unlink()
        if _debug_enabled():
            logger.debug("gate-cache miss (unparseable verified_at) key=%s", key)
        return None

    # Anchor "now" to the same timezone as the parsed timestamp.
    if verified_at.tzinfo is None:
        verified_at = verified_at.replace(tzinfo=UTC)
    now = datetime.now(UTC)
    age = now - verified_at

    # Half-open [verified_at, verified_at + 24h) freshness window.
    if age >= timedelta(hours=MAX_AGE_HOURS) or age < timedelta(0):
        with contextlib.suppress(FileNotFoundError):
            path.unlink()
        if _debug_enabled():
            reason = "stale" if age >= timedelta(hours=MAX_AGE_HOURS) else "future"
            logger.debug(
                "gate-cache miss (%s, age=%s) key=%s",
                reason,
                age,
                key,
            )
        return None

    entry = CacheEntry(raw)
    entry["cache_hit"] = True
    if _debug_enabled():
        logger.debug("gate-cache hit key=%s path=%s", key, path)
    return entry


# ---------------------------------------------------------------------------
# persist (T-1.4 + T-1.10)
# ---------------------------------------------------------------------------


def persist(
    cache_dir: Path,
    cache_key: str | None = None,
    entry: dict | None = None,
    *,
    check_name: str | None = None,
    args: list[str] | None = None,
    staged_blob_shas: list[str] | None = None,
    tool_version: str | None = None,
    config_file_hashes: dict[str, str] | None = None,
    result: dict | None = None,
    disabled: bool = False,
) -> None:
    """Persist a gate check result. Insensitive to ``disabled`` / env kill switch.

    Two equivalent call shapes:

    * Positional: ``persist(cache_dir, cache_key, entry)`` -- write the caller's
      dict verbatim (with ``verified_at`` refreshed to UTC now).
    * Keyword: ``persist(cache_dir=..., result=..., check_name=...,
      args=..., staged_blob_shas=..., tool_version=..., config_file_hashes=...)``
      -- builds a structured entry containing ``check_name`` / ``key_inputs`` /
      ``result`` / ``verified_at`` then writes under the computed key.

    Per D-104-10, ``persist`` always writes the entry so that subsequent
    non-disabled callers benefit from a warm cache; ``disabled`` is accepted
    only for API symmetry with :func:`lookup`.
    """
    _ = disabled  # contract-allowed but ignored — see docstring.

    key = _resolve_cache_key(
        cache_key,
        check_name,
        args,
        staged_blob_shas,
        tool_version,
        config_file_hashes,
    )

    now_iso = datetime.now(UTC).isoformat()

    if entry is not None:
        # Positional form: write the caller's dict verbatim, refreshing
        # verified_at so freshness checks succeed regardless of caller-supplied
        # timestamps.
        payload = dict(entry)
        payload["verified_at"] = now_iso
    else:
        # Keyword form: build the canonical structured entry.
        if (
            check_name is None
            or args is None
            or staged_blob_shas is None
            or tool_version is None
            or config_file_hashes is None
            or result is None
        ):
            raise TypeError(
                "persist keyword form requires check_name, args, staged_blob_shas, "
                "tool_version, config_file_hashes, and result"
            )
        payload = {
            "check_name": check_name,
            "key_inputs": {
                "check_name": check_name,
                "tool_version": tool_version,
                "args": list(args),
                "staged_blob_shas": list(staged_blob_shas),
                "config_file_hashes": dict(config_file_hashes),
            },
            "result": result,
            "verified_at": now_iso,
        }

    path = _entry_path(cache_dir, key)
    _atomic_write(path, payload)
    _prune_if_oversize(cache_dir, MAX_ENTRIES)


# ---------------------------------------------------------------------------
# clear_entry (T-1.10) -- single-entry deletion for --force semantics
# ---------------------------------------------------------------------------


def clear_entry(cache_dir: Path, cache_key: str) -> bool:
    """Remove ``cache_dir / f"{cache_key}.json"``.

    Returns ``True`` when a file was actually deleted, ``False`` when no
    matching entry existed (idempotent -- no exception on missing key).
    """
    path = _entry_path(cache_dir, cache_key)
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    return True


# ---------------------------------------------------------------------------
# LRU prune (T-1.8) -- bound disk usage at MAX_ENTRIES
# ---------------------------------------------------------------------------


def _prune_if_oversize(cache_dir: Path, max_entries: int = MAX_ENTRIES) -> int:
    """Evict oldest-by-``verified_at`` entries until at most ``max_entries`` remain.

    Corrupted entries (unparseable JSON, missing ``verified_at``, wrong shape)
    are evicted unconditionally — they can't participate in LRU ordering and
    shouldn't waste disk space.

    Returns the number of files removed (corrupted + LRU-evicted).
    """
    if not cache_dir.exists():
        return 0

    healthy: list[tuple[datetime, Path]] = []
    corrupted: list[Path] = []

    for child in cache_dir.iterdir():
        if not child.is_file() or child.suffix != ".json":
            continue
        raw = _read_safe(child)
        if raw is None:
            corrupted.append(child)
            continue
        verified_at_str = raw.get("verified_at")
        if not isinstance(verified_at_str, str):
            corrupted.append(child)
            continue
        try:
            verified_at = datetime.fromisoformat(verified_at_str.replace("Z", "+00:00"))
        except ValueError:
            corrupted.append(child)
            continue
        if verified_at.tzinfo is None:
            verified_at = verified_at.replace(tzinfo=UTC)
        healthy.append((verified_at, child))

    evicted = 0
    for path in corrupted:
        try:
            path.unlink()
            evicted += 1
        except FileNotFoundError:
            # Concurrent prune may have already removed it.
            pass

    if len(healthy) <= max_entries:
        return evicted

    # LRU evict the oldest entries until we're at the cap.
    healthy.sort(key=lambda kv: kv[0])
    overflow = len(healthy) - max_entries
    for _, path in healthy[:overflow]:
        try:
            path.unlink()
            evicted += 1
        except FileNotFoundError:
            pass
    return evicted
