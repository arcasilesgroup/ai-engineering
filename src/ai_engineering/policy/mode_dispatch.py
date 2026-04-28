"""spec-105 D-105-02 + D-105-03 + D-105-04 -- gate mode dispatch.

This module implements the unified gate-mode resolver used by the
``policy/orchestrator.py`` to decide which check tiers run at gate time.

Two modes are supported per D-105-02:

* ``regulated`` (default) -- runs Tier 0 + Tier 1 + Tier 2 checks (full
  governance surface). This is the conservative choice for any project
  that ships to a regulated audience (banking, finance, healthcare).
* ``prototyping`` -- runs Tier 0 + Tier 1 only, skipping the slower
  Tier 2 governance checks (``ai-eng-validate``, ``ai-eng-spec-verify``,
  ``docs-gate``, ``risk-expiry-warning``). Designed for fast iteration on
  feature branches where ship-time checks would be noise.

Per D-105-03, a manifest declaration of ``prototyping`` is *advisory*
only. Three independent escalation triggers force the resolver to
return ``regulated`` regardless of the manifest, ensuring prototyping
never leaks into production:

1. **Branch trigger** -- ``HEAD`` matches one of
   :data:`ai_engineering.git.operations.PROTECTED_BRANCHES` (frozenset
   ``{"main", "master"}``) or the ``release/*`` glob.
2. **CI trigger** -- any of ``CI=true``, ``GITHUB_ACTIONS=true``, or
   ``TF_BUILD=True`` env vars are present.
3. **Pre-push target trigger** -- ``AIENG_PUSH_TARGET_REF`` env var
   names a protected branch (canonical ``refs/heads/<name>`` form is
   stripped before matching).

When ``git symbolic-ref --short HEAD`` raises
:class:`subprocess.CalledProcessError` (the canonical signal for a
detached HEAD or an empty repo), the resolver falls back to
``regulated`` -- the conservative default keeps Tier 2 active when the
branch context cannot be determined.

Per D-105-04, the tier allocation is hardcoded in this module rather
than configurable via manifest. Any change requires a code change with
the corresponding governance review.
"""

from __future__ import annotations

import fnmatch
import logging
import os
import subprocess
from pathlib import Path
from typing import Literal

from ai_engineering.config.loader import load_manifest_config
from ai_engineering.git.operations import PROTECTED_BRANCHES

logger = logging.getLogger(__name__)


# --- Mode literal ----------------------------------------------------------

GateMode = Literal["regulated", "prototyping"]


# --- Tier allocation constants (D-105-04) ----------------------------------
#
# Tier 0 -- inviolable: secrets, branch, hook integrity, expired risks.
# These run in EVERY gate execution regardless of mode and always block.

_TIER_0_CHECKS: tuple[str, ...] = (
    "branch_protection",
    "hook_integrity",
    "gitleaks",
    "expired_risk_acceptances",
)

# Tier 1 -- code health (TDD discipline, type safety, smoke tests).
# Always block (cannot be skipped in any mode).

_TIER_1_CHECKS: tuple[str, ...] = (
    "ruff-format",
    "ruff-check",
    "ty-check",
    "pytest-smoke",
)

# Tier 2 -- governance + ship-time (slower; skipped in prototyping mode).
# When mode resolves to ``regulated`` (or escalates from prototyping),
# these block. When mode honors ``prototyping``, these are skipped --
# CI authoritative pre-merge ensures they still run before main lands.

_TIER_2_CHECKS: tuple[str, ...] = (
    "ai-eng-validate",
    "ai-eng-spec-verify",
    "docs-gate",
    "risk-expiry-warning",
)

# ``_ALWAYS_BLOCK`` -- Tier 0 + Tier 1 union. Test_tier_allocation_invariants
# asserts that no Tier 0+1 check ever appears in a skip-list under any mode.
_ALWAYS_BLOCK: frozenset[str] = frozenset(_TIER_0_CHECKS + _TIER_1_CHECKS)


# --- CI sentinel env vars (D-105-03) ---------------------------------------
#
# Any of these being present in the environment forces escalation.
# ``TF_BUILD=True`` notes the Azure Pipelines PascalCase convention.

_CI_SENTINEL_ENV_VARS: tuple[tuple[str, str], ...] = (
    ("CI", "true"),
    ("GITHUB_ACTIONS", "true"),
    ("TF_BUILD", "True"),
)


# --- Release branch glob (D-105-03 + OQ-4 hardcoded) -----------------------
#
# Per D-105-03 + spec OQ-4, branch escalation matches ``PROTECTED_BRANCHES``
# (currently ``{"main", "master"}``) plus the ``release/*`` glob. The glob
# is hardcoded here rather than added to ``PROTECTED_BRANCHES`` because the
# Python constant in ``git/operations.py`` is exact-match for commit-time
# branch protection -- the glob is only applicable to mode escalation.

_RELEASE_BRANCH_GLOBS: tuple[str, ...] = ("release/*",)


# --- Public API ------------------------------------------------------------


def select_checks_for_mode(mode: GateMode) -> list[str]:
    """Return the ordered list of check names to run for a given mode.

    Args:
        mode: ``"regulated"`` -- union of Tier 0 + Tier 1 + Tier 2.
            ``"prototyping"`` -- union of Tier 0 + Tier 1 (Tier 2 skipped).

    Returns:
        Deterministically ordered list of check names. Order: Tier 0 first,
        then Tier 1, then (if regulated) Tier 2 -- matches the spec table
        layout so test output and CI logs share a stable shape.
    """
    if mode == "regulated":
        return list(_TIER_0_CHECKS) + list(_TIER_1_CHECKS) + list(_TIER_2_CHECKS)
    return list(_TIER_0_CHECKS) + list(_TIER_1_CHECKS)


def _branch_is_protected(branch: str) -> bool:
    """Return True iff ``branch`` matches a protected exact name or glob."""
    if branch in PROTECTED_BRANCHES:
        return True
    return any(fnmatch.fnmatch(branch, pattern) for pattern in _RELEASE_BRANCH_GLOBS)


def _push_target_is_protected(env: dict[str, str]) -> bool:
    """Return True iff ``AIENG_PUSH_TARGET_REF`` names a protected branch.

    Strips the canonical ``refs/heads/`` prefix before matching so both
    ``refs/heads/main`` and the bare ``main`` form work uniformly.
    """
    raw = env.get("AIENG_PUSH_TARGET_REF", "").strip()
    if not raw:
        return False
    branch = raw.removeprefix("refs/heads/")
    return _branch_is_protected(branch)


def _ci_environment_active(env: dict[str, str]) -> bool:
    """Return True iff any CI sentinel env var is present (D-105-03 step 2).

    Per spec, the *presence* of any sentinel triggers escalation. Common
    truthy spellings (``true`` / ``True`` / ``1``) all qualify; only
    explicit empty values are ignored.
    """
    for key, _expected in _CI_SENTINEL_ENV_VARS:
        value = env.get(key, "").strip()
        if value:
            return True
    return False


def _read_manifest_mode(project_root: Path) -> GateMode:
    """Read ``gates.mode`` from manifest with conservative fallback."""
    try:
        config = load_manifest_config(project_root)
    except Exception:
        # Loader misconfiguration must never break gate execution; fall
        # back to the conservative default so Tier 2 keeps running.
        logger.debug("manifest load failed; defaulting to regulated", exc_info=True)
        return "regulated"
    return config.gates.mode


def _current_branch_or_none(project_root: Path) -> str | None:
    """Return current branch name, or ``None`` on detached HEAD / empty repo.

    Uses ``git symbolic-ref --short HEAD`` per D-105-03 (canonical for
    detecting branch vs detached state). On
    :class:`subprocess.CalledProcessError` -- the documented signal for
    detached HEAD or an empty repo -- returns ``None`` so the caller can
    apply the conservative fallback.
    """
    try:
        output = subprocess.check_output(
            ["git", "symbolic-ref", "--short", "HEAD"],
            cwd=project_root,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None
    branch = output.strip()
    return branch or None


def resolve_mode(
    project_root: Path,
    *,
    env: dict[str, str] | None = None,
) -> GateMode:
    """Resolve the effective gate mode for a run (D-105-02 + D-105-03).

    Resolution order (any escalation trigger wins):

    1. CI override -- if any of ``CI`` / ``GITHUB_ACTIONS`` / ``TF_BUILD``
       are set, return ``regulated`` regardless of manifest.
    2. Pre-push target -- if ``AIENG_PUSH_TARGET_REF`` names a protected
       branch, return ``regulated``.
    3. Branch trigger -- if ``git symbolic-ref --short HEAD`` returns a
       protected branch (exact match in :data:`PROTECTED_BRANCHES` or
       ``release/*`` glob), return ``regulated``.
    4. Detached HEAD / no repo -- conservative fallback to ``regulated``.
    5. Otherwise -- honor the manifest declaration (``regulated`` default
       or ``prototyping`` if explicitly opted-in).

    Args:
        project_root: Repository root used both for manifest loading and
            for the ``git symbolic-ref`` invocation.
        env: Environment mapping to consult for CI sentinels and the
            push-target ref. Defaults to a snapshot of ``os.environ``.

    Returns:
        Either ``"regulated"`` or ``"prototyping"``.
    """
    effective_env = dict(os.environ if env is None else env)

    # Trigger 1 -- CI override (cheapest check first).
    if _ci_environment_active(effective_env):
        return "regulated"

    # Trigger 2 -- pre-push target ref.
    if _push_target_is_protected(effective_env):
        return "regulated"

    # Trigger 3 -- branch-aware escalation.
    branch = _current_branch_or_none(project_root)
    if branch is None:
        # Detached HEAD or empty repo: conservative fallback.
        return "regulated"
    if _branch_is_protected(branch):
        return "regulated"

    # No escalation trigger fired -- honor the manifest declaration.
    return _read_manifest_mode(project_root)


# --- Banner helpers (D-105-02 / D-105-03 CLI output) -----------------------


def banner_for_mode(
    resolved: GateMode,
    *,
    manifest_mode: GateMode,
    reason: str | None = None,
) -> str:
    """Return the CLI banner string for a resolved gate mode.

    Per D-105-02 / D-105-03:

    * When ``manifest_mode`` is ``prototyping`` but ``resolved`` is
      ``regulated``, emit the escalation banner with the reason.
    * When ``manifest_mode`` and ``resolved`` are both ``prototyping``,
      emit the prototyping warning banner.
    * Otherwise, emit an empty string (no banner needed for the
      regulated default).

    Args:
        resolved: The output of :func:`resolve_mode`.
        manifest_mode: The mode declared in ``manifest.yml`` (uncoerced).
        reason: Human-readable escalation reason (e.g. "protected branch
            'main'", "CI environment", "push target 'refs/heads/main'").

    Returns:
        Banner string ready to print, or empty string when no banner
        should be emitted.
    """
    if manifest_mode == "prototyping" and resolved == "regulated":
        why = reason or "branch / CI escalation"
        return f"[REGULATED MODE -- escalated from prototyping due to: {why}]"
    if manifest_mode == "prototyping" and resolved == "prototyping":
        return (
            "[PROTOTYPING MODE -- Tier 2 governance checks skipped. "
            "Switch to regulated before merge.]"
        )
    return ""


def explain_escalation_reason(
    project_root: Path,
    *,
    env: dict[str, str] | None = None,
) -> str | None:
    """Return a human-readable escalation reason, or ``None`` if no escalation.

    Reproduces the same trigger order as :func:`resolve_mode` but returns
    a label suitable for CLI display rather than a mode literal.
    """
    effective_env = dict(os.environ if env is None else env)

    if _ci_environment_active(effective_env):
        # Identify the first matching sentinel for display.
        for key, _expected in _CI_SENTINEL_ENV_VARS:
            if effective_env.get(key, "").strip():
                return f"CI environment ({key}={effective_env[key]!s})"
        return "CI environment"

    if _push_target_is_protected(effective_env):
        target = effective_env.get("AIENG_PUSH_TARGET_REF", "")
        return f"push target '{target}'"

    branch = _current_branch_or_none(project_root)
    if branch is None:
        return "detached HEAD"
    if _branch_is_protected(branch):
        return f"protected branch '{branch}'"

    return None
