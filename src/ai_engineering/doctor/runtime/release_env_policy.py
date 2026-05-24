"""Doctor runtime check: release-env-policy -- guards the tag-triggered
publish path against GitHub deployment-environment drift.

Why this exists
---------------
spec-152 made ``.github/workflows/release.yml`` *tag-triggered*
(``on: push: tags: ['v*']``). A GitHub **deployment environment** whose
protection rules restrict deployments to *branches* (e.g. only ``main``)
will reject a deploy that runs from a tag ref with::

    Tag vX.Y.Z is not allowed to deploy to <env> due to environment
    protection rules.

That is the regression that nearly broke the 0.8.0 production publish: the
``pypi`` environment allowed only the ``main`` branch (correct for the
pre-spec-152 *branch*-triggered workflow), and 0.8.0 was the first
tag-triggered release to hit the drift. The fix was to add a ``v*`` *tag*
deployment policy to the environment.

That policy lives in **GitHub repo settings, not in the repository**, so
nothing in-tree stops it from drifting again. This check closes the gap:
for every environment the release workflow deploys through, it asks the
live GitHub API whether a *tag* deployment policy matching the workflow's
tag glob exists, and WARNs when it does not.

Robustness
----------
WARN-never-FAIL, like every doctor runtime check. ``service._run_runtime_modules``
calls ``check(ctx)`` with no surrounding try/except, so this module catches
everything internally and downgrades to WARN -- a missing ``gh`` binary,
absent auth, a network failure, or an under-scoped token must never crash
``ai-eng doctor``. A repository whose ``release.yml`` is not tag-triggered
(or has no deployment environments) contributes nothing and pays zero
network cost -- the release file is read and parsed before any API call.

The companion static guard
``tests/unit/workflows/test_release_env_policy_docs.py`` keeps the
documentation (``docs/ci-branch-protection.md``) honest whenever the
workflow's environment set changes; ``scripts/check_workflow_policy.py``
keeps the tag trigger itself from being removed.
"""

from __future__ import annotations

import fnmatch
import json
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import quote

import yaml

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext

_CHECK = "release-env-policy"
_RELEASE_WORKFLOW = Path(".github") / "workflows" / "release.yml"
_GH_TIMEOUT = 10


def check(ctx: DoctorContext) -> list[CheckResult]:
    """Verify release deployment environments admit the workflow's tag glob."""
    try:
        return _check(ctx)
    except Exception as exc:
        # service._run_runtime_modules calls check(ctx) unwrapped: a broad
        # catch here is the contract that keeps doctor from crashing.
        return [_result(CheckStatus.WARN, f"release env policy check errored: {exc}")]


def _check(ctx: DoctorContext) -> list[CheckResult]:
    workflow_path = ctx.target / _RELEASE_WORKFLOW
    if not workflow_path.is_file():
        # No release workflow (typical for consumer installs) -> not applicable.
        return []

    try:
        data = yaml.safe_load(workflow_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        # A malformed release.yml is caught by actionlint / check_workflow_policy;
        # it is not this check's concern.
        return []
    if not isinstance(data, dict):
        return []

    tag_globs = _tag_globs(data)
    if not tag_globs:
        # Branch-triggered (or non-tag) release workflows do not hit the
        # tag-vs-branch environment drift this check guards.
        return []

    environments = _environment_names(data)
    if not environments:
        return []

    # Only now -- once we know the coupling applies -- do we touch the network.
    slug = _resolve_repo_slug(ctx.target)
    if slug is None:
        return [
            _result(
                CheckStatus.WARN,
                "gh CLI unavailable or repository unresolved; cannot verify that "
                f"release environments {sorted(environments)} admit tag glob "
                f"{sorted(tag_globs)} (run 'gh auth login' with admin scope)",
            )
        ]

    return [_evaluate_env(ctx.target, slug, env, tag_globs) for env in environments]


# ---------------------------------------------------------------------------
# Workflow parsing
# ---------------------------------------------------------------------------


def _tag_globs(data: dict[Any, Any]) -> list[str]:
    """Return the workflow's ``on: push: tags`` globs.

    Handles PyYAML parsing the bare ``on:`` key as the boolean ``True`` (YAML
    1.1), so the parsed document is keyed by ``str | bool`` -- hence ``dict[Any,
    Any]`` rather than ``dict[str, Any]``.
    """
    triggers = data.get("on", data.get(True))
    if not isinstance(triggers, dict):
        return []
    push = triggers.get("push")
    if not isinstance(push, dict):
        return []
    tags = push.get("tags")
    if isinstance(tags, str):
        return [tags]
    if isinstance(tags, list):
        return [str(item) for item in tags]
    return []


def _environment_names(data: dict[str, Any]) -> list[str]:
    """Collect the unique deployment-environment names across all jobs.

    A job's ``environment`` may be a plain string or a mapping with a
    ``name`` key. Order is preserved (first-seen) for stable output.
    """
    jobs = data.get("jobs")
    if not isinstance(jobs, dict):
        return []
    names: list[str] = []
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        environment = job.get("environment")
        name: str | None = None
        if isinstance(environment, str):
            name = environment
        elif isinstance(environment, dict):
            raw = environment.get("name")
            if isinstance(raw, str):
                name = raw
        # Skip environment names that interpolate workflow expressions --
        # we cannot resolve "${{ ... }}" to a real environment here.
        if name and "${{" not in name and name not in names:
            names.append(name)
    return names


# ---------------------------------------------------------------------------
# GitHub API
# ---------------------------------------------------------------------------


def _resolve_repo_slug(target: Path) -> str | None:
    """Return ``owner/repo`` via gh, or None when gh/auth/remote is unavailable.

    Doubles as the gh availability + authentication preflight so the
    per-environment calls below can assume a resolvable repository.
    """
    proc = _gh(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"], target)
    if proc is None or proc.returncode != 0:
        return None
    slug = (proc.stdout or "").strip()
    return slug or None


def _evaluate_env(target: Path, slug: str, env: str, tag_globs: list[str]) -> CheckResult:
    """Evaluate one environment's live deployment policy against the tag globs."""
    name = f"release-env-{env}"
    env_path = f"repos/{slug}/environments/{quote(env, safe='')}"
    proc = _gh(["api", env_path], target)
    if proc is None or proc.returncode != 0:
        return _result(
            CheckStatus.WARN,
            f"could not read environment {env!r} deployment policy via gh api: "
            f"{_first_error_line(proc)}; ensure gh is authenticated with admin scope",
            name=name,
        )

    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return _result(
            CheckStatus.WARN,
            f"environment {env!r} API response was not valid JSON",
            name=name,
        )

    policy = payload.get("deployment_branch_policy")
    if policy is None:
        return _result(
            CheckStatus.OK,
            f"environment {env!r} allows all refs; tag-triggered deploys are permitted",
            name=name,
        )

    if isinstance(policy, dict) and policy.get("custom_branch_policies"):
        return _evaluate_custom_policies(target, slug, env, tag_globs, name)

    if isinstance(policy, dict) and policy.get("protected_branches"):
        return _result(
            CheckStatus.WARN,
            f"environment {env!r} restricts deployments to protected branches; the "
            f"tag-triggered release ({sorted(tag_globs)}) will be REJECTED. Set "
            "'Deployment branches and tags' to 'Selected branches and tags' and add a "
            f"tag rule. Fix: {_fix_command(slug, env)}",
            name=name,
        )

    return _result(
        CheckStatus.WARN,
        f"environment {env!r} has an unrecognized deployment policy {policy!r}; "
        f"verify it admits the release tag glob {sorted(tag_globs)}",
        name=name,
    )


def _evaluate_custom_policies(
    target: Path, slug: str, env: str, tag_globs: list[str], name: str
) -> CheckResult:
    """Inspect an environment's custom deployment-branch-policies list."""
    policies_path = f"repos/{slug}/environments/{quote(env, safe='')}/deployment-branch-policies"
    proc = _gh(["api", policies_path], target)
    if proc is None or proc.returncode != 0:
        return _result(
            CheckStatus.WARN,
            f"could not list environment {env!r} deployment-branch-policies via gh api: "
            f"{_first_error_line(proc)}",
            name=name,
        )

    try:
        items = json.loads(proc.stdout or "{}").get("branch_policies", [])
    except json.JSONDecodeError:
        return _result(
            CheckStatus.WARN,
            f"environment {env!r} deployment-branch-policies response was not valid JSON",
            name=name,
        )

    if _admits_all_tag_globs(items, tag_globs):
        return _result(
            CheckStatus.OK,
            f"environment {env!r} has a tag deployment policy admitting {sorted(tag_globs)}",
            name=name,
        )

    return _result(
        CheckStatus.WARN,
        f"environment {env!r} has custom deployment policies but none admit the release "
        f"tag glob {sorted(tag_globs)}; tag-triggered publish will be REJECTED. "
        f"Fix: {_fix_command(slug, env)}",
        name=name,
    )


def _admits_all_tag_globs(items: list[Any], tag_globs: list[str]) -> bool:
    """True when every workflow tag glob is admitted by some tag policy.

    A custom deployment policy entry is ``{"name": <glob>, "type": <"branch"|"tag">}``.
    Each policy name is itself a glob, so we test whether it admits a
    representative tag the workflow's glob would produce (``v*`` -> ``v0``):
    if the policy ``v*`` admits ``v0`` it admits every real ``vX.Y.Z`` tag.
    Entries without ``type == "tag"`` (older API responses default to branch)
    cannot admit a tag and are ignored.
    """
    tag_policy_names = [
        item["name"]
        for item in items
        if isinstance(item, dict)
        and item.get("type") == "tag"
        and isinstance(item.get("name"), str)
    ]
    if not tag_policy_names:
        return False
    for glob in tag_globs:
        representative = glob.replace("*", "0").replace("?", "0")
        if not any(fnmatch.fnmatch(representative, policy) for policy in tag_policy_names):
            return False
    return True


def _fix_command(slug: str, env: str) -> str:
    """Return the copy-pasteable gh command that adds the v* tag policy."""
    return (
        f"gh api --method POST repos/{slug}/environments/{env}/deployment-branch-policies "
        "-f name='v*' -f type='tag'"
    )


def _gh(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str] | None:
    """Run a gh command, returning None when gh itself is unavailable."""
    try:
        return subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=_GH_TIMEOUT,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None


def _first_error_line(proc: subprocess.CompletedProcess[str] | None) -> str:
    """Return the first non-empty stderr/stdout line for a WARN message."""
    if proc is None:
        return "gh CLI not found or timed out"
    for stream in (proc.stderr, proc.stdout):
        for line in (stream or "").splitlines():
            if line.strip():
                return line.strip()
    return f"gh exited {proc.returncode}"


def _result(status: CheckStatus, message: str, *, name: str = _CHECK) -> CheckResult:
    return CheckResult(name=name, status=status, message=message)
