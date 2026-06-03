"""CI cache key schema parity with local gate cache.

Spec ref: ``.ai-engineering/specs/spec.md`` D-104-03 (CI integration via
``actions/cache@v4`` with key schema identical to local) and D-104-09
(cache key inputs include `tool_version`, `staged_blob_shas`,
`config_file_hashes`, `args` -- the CI ``hashFiles()`` mirror is the
``config_file_hashes`` slice).

spec-152 W2.T13 hard-deleted ``.github/workflows/ci-build.yml`` (orphaned
post-CI build with zero ``dist``-artifact consumers). The cache-schema
parity invariant survives against the workflow that still carries the
gate-cache steps -- ``ci-check.yml`` -- so the three assertions below
were retargeted from ``ci-build.yml`` to ``ci-check.yml``. The original
spec-104 TDD-immutability note no longer applies: D-152-25 requires
coupled tests to update in lockstep with the deletion they depend on.

Coverage:

1. ``test_ci_check_yml_has_cache_step`` -- ``ci-check.yml`` declares an
   ``actions/cache@v4`` step.
2. ``test_ci_cache_key_includes_required_components`` -- the key string
   in ``ci-check.yml`` references the same config files the local
   ``_CONFIG_FILE_WHITELIST`` consumes (``pyproject.toml`` for ruff/ty,
   ``.ruff.toml`` for ruff, ``.gitleaks.toml`` for gitleaks).
3. ``test_ci_cache_path_matches_local`` -- ``with.path`` points at the
   per-cwd local cache directory ``.ai-engineering/cache/gate/`` so a CI
   cache restore lands entries where ``gate_cache.lookup`` will read them
   (D-104-03 storage contract).

spec-152 W3.T15 (D-152-09) adds trust-tier isolation to the cache-key
schema. A PR/fork run must never be able to restore a cache entry that a
push-to-main run wrote (or vice-versa), because a poisoned PR cache could
otherwise leak into a privileged main/release build. Every
``actions/cache`` ``key:`` must therefore begin with a trust-tier token
(``pr-``/``main-``/``release-``) derived from ``github.event_name``, and
NO ``restore-keys`` entry may be a broad cross-tier fallback (one that
omits the tier token). The two assertions below extend the existing
schema-parity coverage:

4. ``test_ci_cache_keys_carry_trust_tier_prefix`` -- every ``key:`` and
   every ``restore-keys`` entry begins with a tier-token expression.
5. ``test_ci_cache_has_no_cross_tier_restore_fallback`` -- no
   ``restore-keys`` entry is a broad ``<cache-name>-${{ runner.os }}-``
   fallback that lacks the tier token.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

# ---------------------------------------------------------------------------
# Path constants -- anchored at the repo root regardless of cwd.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]

CI_CHECK_PATH = REPO_ROOT / ".github" / "workflows" / "ci-check.yml"

# The cache action pinned by ``actions/cache@v4`` is the GHA-side mirror
# of the local ``gate_cache`` storage contract (D-104-03). v4 is the
# minimum version that supports the cross-job ``save-always`` semantics
# the orchestrator relies on; tests therefore accept ``actions/cache@v4``
# OR a pinned commit-sha alias of v4 (``actions/cache@<sha> # v4.x.x``).
CACHE_ACTION_PREFIX = "actions/cache@"

# Local-cache config files that MUST appear in the CI cache key
# expression. These are the union of ``_CONFIG_FILE_WHITELIST`` entries
# whose contents drive lint/typecheck/secret-scan behaviour and therefore
# must invalidate the CI cache on change (D-104-09).
REQUIRED_HASHFILES_INPUTS = (
    "pyproject.toml",  # ruff-format, ruff-check, ty, pytest-smoke configs
    ".ruff.toml",  # explicit ruff override file (whitelisted per check)
    ".gitleaks.toml",  # gitleaks rule config
)

# Local cache directory written by ``gate_cache._atomic_write``.
# Spec-125 D-125-09 relocated the gate cache from
# ``.ai-engineering/state/gate-cache/`` to ``.ai-engineering/cache/gate/``;
# CI cache restore must populate the new path so a subsequent
# ``ai-eng gate run --cache-aware`` lookup hits the restored entries
# without an extra copy step.
EXPECTED_CACHE_PATH = ".ai-engineering/cache/gate/"

# spec-152 W3.T15 (D-152-09): the trust-tier token a cache key must carry
# immediately after its ``<cache-name>-`` namespace. The canonical scheme
# derives the token from the event class via a GHA conditional expression
# (``github.event_name == 'pull_request' && 'pr' || 'main'``); a literal
# ``release-`` is also accepted for release-only caches. The token isolates
# PR/fork caches from push/main caches so a poisoned PR cache cannot leak
# into a privileged build (the spec-152 cache-poisoning defect).
TRUST_TIER_LITERALS = ("pr", "main", "release")

# A ``restore-keys`` entry is a forbidden cross-tier fallback when, after the
# ``<cache-name>-`` namespace, it jumps straight to ``${{ runner.os }}``
# without first carrying a tier token. This is the broad
# ``gate-cache-${{ runner.os }}-`` form the migration removes.
_RUNNER_OS_EXPR = "${{ runner.os }}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_workflow(path: Path) -> dict[str, Any]:
    """Parse a GitHub Actions workflow file via ``yaml.safe_load``.

    Raises a clear ``pytest.fail`` if the file is missing -- protects the
    test from silent skips when a workflow is renamed or deleted.
    """
    if not path.is_file():
        pytest.fail(f"Workflow file missing: {path.relative_to(REPO_ROOT)}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _iter_cache_steps(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    """Return every step across all jobs whose ``uses`` invokes ``actions/cache``.

    The shape navigated is ``jobs.<job_id>.steps[*]`` per the GHA workflow
    schema. Steps without a ``uses`` field (e.g., ``run:`` shell steps)
    are skipped naturally.
    """
    cache_steps: list[dict[str, Any]] = []
    jobs = workflow.get("jobs", {}) or {}
    for job in jobs.values():
        steps = (job or {}).get("steps", []) or []
        for step in steps:
            uses = (step or {}).get("uses")
            if isinstance(uses, str) and uses.startswith(CACHE_ACTION_PREFIX):
                cache_steps.append(step)
    return cache_steps


def _is_supported_cache_version(uses: str, *, workflow_path: Path | None = None) -> bool:
    """``actions/cache@v4`` or ``@v5`` accepted, as either an explicit tag or
    a SHA-pinned form annotated with ``# v4.x.y`` / ``# v5.x.y``.

    v4 was the original gate-cache pin (D-104-03); v5 is its maintained
    successor after GitHub deprecated the v4 cache-service backend. v5 is
    key+path compatible with the ``gate_cache`` storage contract, so the
    dependabot v4->v5 bump is accepted (spec-163). Spec-110 (Article VI
    supply-chain hardening) pins all Actions to commit SHAs with a trailing
    ``# v<version>`` comment (e.g. ``actions/cache@<sha> # v5.0.5``). PyYAML's
    ``safe_load`` strips the comment, so for a SHA-pinned form this helper
    scans the raw workflow text for a line carrying both the SHA and a
    ``# v4``/``# v5`` annotation. Without that fallback, the test would force
    an unpinned tag and contradict Article VI.
    """
    if uses.startswith((f"{CACHE_ACTION_PREFIX}v4", f"{CACHE_ACTION_PREFIX}v5")):
        return True
    if workflow_path is None:
        return False
    sha = uses.removeprefix(CACHE_ACTION_PREFIX)
    if not (len(sha) == 40 and all(c in "0123456789abcdef" for c in sha)):
        return False
    raw = workflow_path.read_text(encoding="utf-8")
    pin_marker = f"{CACHE_ACTION_PREFIX}{sha}"
    return any(
        pin_marker in line and ("# v4" in line or "# v5" in line) for line in raw.splitlines()
    )


def _tier_segment(cache_entry: str) -> str:
    """Return the text that follows the ``<cache-name>-`` namespace prefix.

    A cache key is ``<cache-name>-<tier>-<rest>`` (e.g.
    ``gate-cache-${{ ... && 'pr' || 'main' }}-Linux-<hash>``). The cache name
    itself contains hyphens (``gate-cache``, ``semgrep-packs``), so the tier
    token is not simply ``split("-")[0]``. This helper strips the leading
    ``${{ ... }}`` expression block (if present) and returns the remainder so
    the caller can inspect what the tier position holds.

    We locate the first ``${{`` (every tier-bearing expression starts there)
    and return the substring from that point; for a literal-tier key
    (``release-...``) the whole string is returned. The caller then checks
    that a tier token appears before ``${{ runner.os }}``.
    """
    return cache_entry.strip()


def _carries_trust_tier(cache_entry: str) -> bool:
    """Return whether ``cache_entry`` carries a trust-tier token before the OS.

    Accepts either form:

    * a GHA conditional expression that yields the tier — recognised by the
      presence of every tier literal it can resolve to (``'pr'`` and
      ``'main'``) inside a ``${{ ... }}`` block that precedes
      ``${{ runner.os }}``; or
    * a literal tier prefix (``release-...``).

    The tier MUST appear *before* ``${{ runner.os }}`` — a key that reaches
    ``${{ runner.os }}`` without first emitting a tier token is a cross-tier
    key and fails.
    """
    text = _tier_segment(cache_entry)
    os_idx = text.find(_RUNNER_OS_EXPR)
    head = text if os_idx == -1 else text[:os_idx]
    # Conditional-expression form: the tier expression resolves to a quoted
    # literal such as 'pr' / 'main' and sits ahead of the OS segment.
    if any(f"'{literal}'" in head for literal in TRUST_TIER_LITERALS):
        return True
    # Literal-tier form: ``release-...`` / ``pr-...`` / ``main-...`` namespace
    # token sitting ahead of the OS segment.
    return any(
        f"-{literal}-" in head or head.startswith(f"{literal}-") for literal in TRUST_TIER_LITERALS
    )


def _is_cross_tier_fallback(restore_entry: str) -> bool:
    """Return whether a ``restore-keys`` line is a broad cross-tier fallback.

    The forbidden shape reaches ``${{ runner.os }}`` with no tier token in
    front of it — i.e. ``gate-cache-${{ runner.os }}-`` — so a push/main run
    could restore a PR-written entry. A same-tier hash-scoped restore key
    (``gate-cache-<tier>-${{ runner.os }}-<hashFiles...>-``) is allowed.
    """
    return not _carries_trust_tier(restore_entry)


def _cache_key_strings(cache_steps: list[dict[str, Any]]) -> list[str]:
    """Collect every non-empty ``with.key`` expression across cache steps."""
    keys: list[str] = []
    for step in cache_steps:
        with_block = (step or {}).get("with", {}) or {}
        key = with_block.get("key")
        if isinstance(key, str) and key.strip():
            keys.append(key)
    return keys


def _restore_key_entries(cache_steps: list[dict[str, Any]]) -> list[str]:
    """Collect every individual ``with.restore-keys`` entry across cache steps.

    GHA ``restore-keys`` is a newline-separated YAML literal; PyYAML returns it
    as a single string. Each non-blank line is one restore key.
    """
    entries: list[str] = []
    for step in cache_steps:
        with_block = (step or {}).get("with", {}) or {}
        restore = with_block.get("restore-keys")
        if not isinstance(restore, str):
            continue
        for line in restore.splitlines():
            if line.strip():
                entries.append(line)
    return entries


# ---------------------------------------------------------------------------
# Tests (4 RED)
# ---------------------------------------------------------------------------


def test_ci_check_yml_has_cache_step() -> None:
    """``ci-check.yml`` declares an ``actions/cache@v4`` step.

    spec-104 wired the gate-cache; spec-152 W2.T13 left ``ci-check.yml``
    as the sole workflow carrying it after ``ci-build.yml`` was deleted.
    """
    workflow = _load_workflow(CI_CHECK_PATH)
    cache_steps = _iter_cache_steps(workflow)

    assert cache_steps, (
        f"{CI_CHECK_PATH.relative_to(REPO_ROOT)} has no actions/cache@v4 step. "
        "T-8.2 must add one for security/test jobs."
    )
    v4_steps = [
        s
        for s in cache_steps
        if _is_supported_cache_version(s["uses"], workflow_path=CI_CHECK_PATH)
    ]
    assert v4_steps, (
        f"{CI_CHECK_PATH.relative_to(REPO_ROOT)} cache step is not pinned to v4 or v5. "
        f"Found: {[s['uses'] for s in cache_steps]}. "
        "Required: actions/cache@v4 or @v5 (gate-cache storage contract)."
    )


def test_ci_cache_key_includes_required_components() -> None:
    """CI cache key string includes ``hashFiles()`` for the same config
    files the local ``_CONFIG_FILE_WHITELIST`` consumes (D-104-09).

    The cache key must include ``hashFiles(...)`` references to
    ``pyproject.toml``, ``.ruff.toml``, and ``.gitleaks.toml`` so that a
    config change invalidates the CI cache in lock-step with the local
    ``_compute_cache_key`` rerun.
    """
    workflow = _load_workflow(CI_CHECK_PATH)
    cache_steps = _iter_cache_steps(workflow)
    assert cache_steps, (
        f"{CI_CHECK_PATH.relative_to(REPO_ROOT)} has no cache step "
        "to inspect for key schema parity."
    )

    # Concatenate every cache step's key expression so the assertion is
    # robust to either a single combined step or split lint+test steps.
    key_strings: list[str] = []
    for step in cache_steps:
        with_block = (step or {}).get("with", {}) or {}
        key = with_block.get("key")
        if isinstance(key, str):
            key_strings.append(key)
    combined = "\n".join(key_strings)

    assert combined, (
        f"{CI_CHECK_PATH.relative_to(REPO_ROOT)} cache step is missing a with.key expression."
    )

    missing = [token for token in REQUIRED_HASHFILES_INPUTS if token not in combined]
    assert not missing, (
        f"{CI_CHECK_PATH.relative_to(REPO_ROOT)} cache key is missing "
        f"required hashFiles inputs: {missing}. "
        f"Required (matches local _CONFIG_FILE_WHITELIST): "
        f"{list(REQUIRED_HASHFILES_INPUTS)}. "
        f"Found key expression(s): {combined!r}."
    )


def test_ci_cache_path_matches_local() -> None:
    """CI cache ``with.path`` matches the local gate-cache directory
    (D-104-03 storage contract).

    The cache step must point at ``.ai-engineering/cache/gate/`` so a CI
    restore puts entries exactly where ``gate_cache.lookup`` reads them at
    the next ``ai-eng gate run --cache-aware`` invocation; no extra copy
    step is permitted.
    """
    workflow = _load_workflow(CI_CHECK_PATH)
    cache_steps = _iter_cache_steps(workflow)
    assert cache_steps, (
        f"{CI_CHECK_PATH.relative_to(REPO_ROOT)} has no cache step to inspect for path parity."
    )

    paths: list[str] = []
    for step in cache_steps:
        with_block = (step or {}).get("with", {}) or {}
        path_field = with_block.get("path")
        if isinstance(path_field, str):
            paths.append(path_field)

    assert paths, f"{CI_CHECK_PATH.relative_to(REPO_ROOT)} cache step is missing a with.path field."

    # Accept either the exact directory or a multi-line YAML literal that
    # CONTAINS the directory (GHA cache action supports newline-separated
    # path lists). Trailing slash is normalised.
    def _normalise(value: str) -> str:
        return value.strip().rstrip("/") + "/"

    expected_norm = _normalise(EXPECTED_CACHE_PATH)
    matched = any(
        expected_norm in _normalise(line)
        for path_value in paths
        for line in path_value.splitlines() or [path_value]
    )

    assert matched, (
        f"{CI_CHECK_PATH.relative_to(REPO_ROOT)} cache step path "
        f"does not include {EXPECTED_CACHE_PATH!r}. "
        f"Found: {paths!r}. "
        "The local gate_cache writes to this exact directory; CI restore "
        "must land entries in the same location."
    )


def test_ci_cache_keys_carry_trust_tier_prefix() -> None:
    """spec-152 T-15 (D-152-09): every cache ``key`` and ``restore-keys`` entry
    carries a trust-tier token before the OS segment.

    A PR/fork run must not share a cache namespace with a push-to-main run. The
    canonical scheme derives the tier from ``github.event_name`` via a GHA
    conditional (``... && 'pr' || 'main'``) immediately after the cache-name
    namespace, so a PR run can only ever read/write the ``pr`` tier and a push
    run only the ``main`` tier. ``release-`` is accepted for release-only
    caches. RED today: the live keys go straight from ``gate-cache-`` /
    ``semgrep-packs-`` to ``${{ runner.os }}`` with no tier token.
    """
    workflow = _load_workflow(CI_CHECK_PATH)
    cache_steps = _iter_cache_steps(workflow)
    assert cache_steps, (
        f"{CI_CHECK_PATH.relative_to(REPO_ROOT)} has no cache step "
        "to inspect for trust-tier prefixes."
    )

    keys = _cache_key_strings(cache_steps)
    assert keys, f"{CI_CHECK_PATH.relative_to(REPO_ROOT)} cache steps have no with.key."

    untiered_keys = [key for key in keys if not _carries_trust_tier(key)]
    assert not untiered_keys, (
        f"{CI_CHECK_PATH.relative_to(REPO_ROOT)} cache key(s) lack a trust-tier "
        f"token before ${{{{ runner.os }}}}: {untiered_keys}. "
        "Each key must begin with a tier expression "
        "(e.g. gate-cache-${{ github.event_name == 'pull_request' && 'pr' "
        "|| 'main' }}-${{ runner.os }}-...) so PR caches are isolated from "
        "main/release caches (D-152-09)."
    )

    restore_entries = _restore_key_entries(cache_steps)
    untiered_restores = [entry for entry in restore_entries if not _carries_trust_tier(entry)]
    assert not untiered_restores, (
        f"{CI_CHECK_PATH.relative_to(REPO_ROOT)} restore-keys entry/entries lack "
        f"a trust-tier token before ${{{{ runner.os }}}}: {untiered_restores}. "
        "Every restore-key must stay within its own tier."
    )


def test_ci_cache_has_no_cross_tier_restore_fallback() -> None:
    """spec-152 T-15 (D-152-09): no ``restore-keys`` entry is a broad
    cross-tier fallback.

    The pre-migration keys ended their ``restore-keys`` list with a broad
    ``gate-cache-${{ runner.os }}-`` (and ``semgrep-packs-${{ runner.os }}-``)
    that a push/main job could use to restore a PR-written cache. That fallback
    MUST be removed; only same-tier restore keys (which still carry the tier
    token) may remain. RED today.
    """
    workflow = _load_workflow(CI_CHECK_PATH)
    cache_steps = _iter_cache_steps(workflow)
    assert cache_steps, (
        f"{CI_CHECK_PATH.relative_to(REPO_ROOT)} has no cache step to inspect "
        "for cross-tier restore fallbacks."
    )

    cross_tier = [
        entry for entry in _restore_key_entries(cache_steps) if _is_cross_tier_fallback(entry)
    ]
    assert not cross_tier, (
        f"{CI_CHECK_PATH.relative_to(REPO_ROOT)} has cross-tier restore-key "
        f"fallback(s) that let one tier restore another tier's cache: {cross_tier}. "
        "Drop the broad '<cache-name>-${{ runner.os }}-' restore-key; keep only "
        "the same-tier (tier-prefixed) hash-scoped restore-key (D-152-09)."
    )
