"""CI cache key schema parity with local gate cache (T-8.3 RED).

Spec ref: ``.ai-engineering/specs/spec.md`` D-104-03 (CI integration via
``actions/cache@v4`` with key schema identical to local) and D-104-09
(cache key inputs include `tool_version`, `staged_blob_shas`,
`config_file_hashes`, `args` -- the CI ``hashFiles()`` mirror is the
``config_file_hashes`` slice).

Plan ref: ``.ai-engineering/specs/plan.md`` Phase 8 (CI cache wiring).
T-8.1 adds ``actions/cache@v4`` to ``ci-build.yml``; T-8.2 mirrors it to
``ci-check.yml``; T-8.3 (this file) is the RED contract for that work;
T-8.4 closes the GREEN by confirming key components match the local
``_CONFIG_FILE_WHITELIST`` (D-104-09) inputs.

The 4 tests fail today because no cache step has been wired into either
workflow yet:

1. ``test_ci_build_yml_has_cache_step`` -- fails until T-8.1 lands.
2. ``test_ci_check_yml_has_cache_step`` -- fails until T-8.2 lands.
3. ``test_ci_cache_key_includes_required_components`` -- fails until the
   key string in ci-build.yml references the same config files the local
   ``_CONFIG_FILE_WHITELIST`` consumes (``pyproject.toml`` for ruff/ty,
   ``.ruff.toml`` for ruff, ``.gitleaks.toml`` for gitleaks).
4. ``test_ci_cache_path_matches_local`` -- fails until ``with.path`` is
   set to the per-cwd local cache directory ``.ai-engineering/state/gate-cache/``
   so a CI cache restore lands the entries where ``gate_cache.lookup``
   will read them (D-104-03 storage contract).

TDD CONSTRAINT: this file is IMMUTABLE after T-8.3 lands. T-8.1 / T-8.2 /
T-8.4 may only edit the workflow YAML; never edit these assertions.
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

CI_BUILD_PATH = REPO_ROOT / ".github" / "workflows" / "ci-build.yml"
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

# Local cache directory written by ``gate_cache._atomic_write`` (D-104-03).
# CI cache restore must populate this exact relative path so a subsequent
# ``ai-eng gate run --cache-aware`` lookup hits the restored entries
# without an extra copy step.
EXPECTED_CACHE_PATH = ".ai-engineering/state/gate-cache/"


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


def _is_v4(uses: str) -> bool:
    """``actions/cache@v4`` (explicit tag).

    PyYAML's ``safe_load`` strips comments, so a pinned-SHA alias variant
    (``actions/cache@<sha> # v4.x.y``) is not detectable from the parsed
    value alone. The canonical accepted form here is therefore the
    explicit ``@v4`` tag -- pinned SHAs without a textual ``v4`` token
    are rejected to avoid silent downgrades to v3 (which lacks the
    save-always semantics D-104-03 relies on).
    """
    return uses.startswith(f"{CACHE_ACTION_PREFIX}v4")


# ---------------------------------------------------------------------------
# Tests (4 RED)
# ---------------------------------------------------------------------------


def test_ci_build_yml_has_cache_step() -> None:
    """``ci-build.yml`` declares an ``actions/cache@v4`` step (T-8.1).

    FAIL today: no cache step has been wired into ci-build.yml yet.
    """
    workflow = _load_workflow(CI_BUILD_PATH)
    cache_steps = _iter_cache_steps(workflow)

    assert cache_steps, (
        f"{CI_BUILD_PATH.relative_to(REPO_ROOT)} has no actions/cache@v4 step. "
        "T-8.1 must add one before lint/typecheck/test jobs."
    )
    # At least one of the cache steps must pin v4 (D-104-03 requires v4
    # for cross-job save-always semantics).
    v4_steps = [s for s in cache_steps if _is_v4(s["uses"])]
    assert v4_steps, (
        f"{CI_BUILD_PATH.relative_to(REPO_ROOT)} cache step is not pinned to v4. "
        f"Found: {[s['uses'] for s in cache_steps]}. "
        "Required: actions/cache@v4 (cross-job save-always semantics)."
    )


def test_ci_check_yml_has_cache_step() -> None:
    """``ci-check.yml`` declares an ``actions/cache@v4`` step (T-8.2).

    FAIL today: no cache step has been wired into ci-check.yml yet.
    """
    workflow = _load_workflow(CI_CHECK_PATH)
    cache_steps = _iter_cache_steps(workflow)

    assert cache_steps, (
        f"{CI_CHECK_PATH.relative_to(REPO_ROOT)} has no actions/cache@v4 step. "
        "T-8.2 must add one for security/test jobs."
    )
    v4_steps = [s for s in cache_steps if _is_v4(s["uses"])]
    assert v4_steps, (
        f"{CI_CHECK_PATH.relative_to(REPO_ROOT)} cache step is not pinned to v4. "
        f"Found: {[s['uses'] for s in cache_steps]}. "
        "Required: actions/cache@v4 (cross-job save-always semantics)."
    )


def test_ci_cache_key_includes_required_components() -> None:
    """CI cache key string includes ``hashFiles()`` for the same config
    files the local ``_CONFIG_FILE_WHITELIST`` consumes (D-104-09).

    The cache key in either workflow must include ``hashFiles(...)``
    references to ``pyproject.toml``, ``.ruff.toml``, and
    ``.gitleaks.toml`` so that a config change invalidates the CI cache
    in lock-step with the local ``_compute_cache_key`` rerun.

    FAIL today: no cache step exists, so no key string to inspect.
    """
    workflow = _load_workflow(CI_BUILD_PATH)
    cache_steps = _iter_cache_steps(workflow)
    assert cache_steps, (
        f"{CI_BUILD_PATH.relative_to(REPO_ROOT)} has no cache step "
        "to inspect for key schema parity (T-8.1 must land first)."
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
        f"{CI_BUILD_PATH.relative_to(REPO_ROOT)} cache step is missing a with.key expression."
    )

    missing = [token for token in REQUIRED_HASHFILES_INPUTS if token not in combined]
    assert not missing, (
        f"{CI_BUILD_PATH.relative_to(REPO_ROOT)} cache key is missing "
        f"required hashFiles inputs: {missing}. "
        f"Required (matches local _CONFIG_FILE_WHITELIST): "
        f"{list(REQUIRED_HASHFILES_INPUTS)}. "
        f"Found key expression(s): {combined!r}."
    )


def test_ci_cache_path_matches_local() -> None:
    """CI cache ``with.path`` matches the local gate-cache directory
    (D-104-03 storage contract).

    The cache step must point at ``.ai-engineering/state/gate-cache/`` so
    a CI restore puts entries exactly where ``gate_cache.lookup`` reads
    them at the next ``ai-eng gate run --cache-aware`` invocation; no
    extra copy step is permitted.

    FAIL today: no cache step exists, so no path field to inspect.
    """
    workflow = _load_workflow(CI_BUILD_PATH)
    cache_steps = _iter_cache_steps(workflow)
    assert cache_steps, (
        f"{CI_BUILD_PATH.relative_to(REPO_ROOT)} has no cache step "
        "to inspect for path parity (T-8.1 must land first)."
    )

    paths: list[str] = []
    for step in cache_steps:
        with_block = (step or {}).get("with", {}) or {}
        path_field = with_block.get("path")
        if isinstance(path_field, str):
            paths.append(path_field)

    assert paths, f"{CI_BUILD_PATH.relative_to(REPO_ROOT)} cache step is missing a with.path field."

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
        f"{CI_BUILD_PATH.relative_to(REPO_ROOT)} cache step path "
        f"does not include {EXPECTED_CACHE_PATH!r}. "
        f"Found: {paths!r}. "
        "The local gate_cache writes to this exact directory; CI restore "
        "must land entries in the same location."
    )
