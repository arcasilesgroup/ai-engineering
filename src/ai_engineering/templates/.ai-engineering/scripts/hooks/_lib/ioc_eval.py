"""IOC-evaluation subsystem for the prompt-injection guard (single SoT).

spec-191 D-191-03: this module is the single source of truth for
Indicator-of-Compromise (IOC) evaluation. It was extracted verbatim from
``prompt-injection-guard.py`` so both the PreToolUse guard and the
spec-191 read-side hook consult ONE evaluator instead of duplicating the
catalog-loading, decision-store lookup, and pattern-matching logic.

The module is intentionally stdlib-only (no ``ai_engineering.*`` imports)
mirroring the guard's hot-path contract — direct raw-JSON parsing of
``iocs.json`` / ``decision-store.json`` keeps the evaluator independent of
the installer's runtime. The only non-stdlib touch is a lazy ``import
yaml`` inside :func:`_fail_closed_enabled`, guarded by a broad except so a
missing PyYAML never traps the host.

spec-107 D-107-05/06/07 semantics (preserved verbatim):

- ``allow``: no IOC match (default, fast path).
- ``deny``: IOC match without an active risk-acceptance.
- ``warn``: IOC match WITH an active risk-acceptance for the canonical
  ``finding_id = sentinel-<category>-<pattern_normalized>``.

The loader is fail-open: missing or corrupt ``iocs.json`` returns an empty
dict, which the evaluator treats as "no IOC layer active" (``allow``-only)
unless the opt-in fail-closed posture is enabled (spec-160 D-160-01/02).

spec-191 D-191-02: the ``allowlist`` block (``allowlist.domains`` /
``allowlist.paths``) in ``iocs.json`` is consulted so known-good hosts and
paths never drive deny/risk. Absent/malformed allowlist is fail-open.
"""

from __future__ import annotations

import functools
import json
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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

# spec-107 D-107-05: canonical IOC categories spec-mandated. The vendored
# upstream catalog also exposes ``suspicious_network`` and
# ``dangerous_commands`` aliases; both names index the same payload.
_IOC_CATEGORIES = ("sensitive_paths", "sensitive_env_vars", "malicious_domains", "shell_patterns")
_IOC_RELATIVE = Path(".ai-engineering") / "security" / "iocs" / "iocs.json"


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


def _load_allowlist(
    catalog: dict[str, Any],
) -> tuple[frozenset[str], tuple[str, ...]]:
    """Return ``(allow_domains, allow_paths)`` from the catalog's allowlist.

    Fail-open: an absent, malformed, or empty ``allowlist`` block yields empty
    sets so every match is adjudicated normally (the dead-config fix is a
    no-op until an operator curates the list).
    """
    block = catalog.get("allowlist")
    if not isinstance(block, dict):
        return frozenset(), ()
    domains = block.get("domains")
    paths = block.get("paths")
    allow_domains = (
        frozenset(d.lower() for d in domains if isinstance(d, str))
        if isinstance(domains, list)
        else frozenset()
    )
    allow_paths = tuple(p for p in paths if isinstance(p, str)) if isinstance(paths, list) else ()
    return allow_domains, allow_paths


def _is_allowlisted(
    category: str,
    kind: str,
    pattern: str,
    allow_domains: frozenset[str],
    allow_paths: tuple[str, ...],
) -> bool:
    """True when ``pattern`` is a known-good host/TLD or rooted path.

    spec-191 D-191-02: a ``host``-kind match whose domain is in
    ``allowlist.domains``, or a ``sensitive_paths`` match rooted at an
    ``allowlist.paths`` entry, is dropped before adjudication — no ``deny`` and
    no risk accumulation.
    """
    return (kind == "host" and pattern.lower() in allow_domains) or (
        category == "sensitive_paths"
        and allow_paths
        and any(pattern.startswith(p) for p in allow_paths)
    )


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
    allow_domains, allow_paths = _load_allowlist(cat)
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
            if _is_allowlisted(category, kind, pattern, allow_domains, allow_paths):
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
