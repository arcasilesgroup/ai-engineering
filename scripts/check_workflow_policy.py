"""Workflow policy sanity checks for GitHub Actions files.

Current enforced policies:
- No use of `pull_request_target` trigger.
- Top-level `permissions` key must be present.
- Every job must have `timeout-minutes`.
- Workflows with `pull_request` trigger must have `concurrency` key.
- Third-party actions (not `actions/*`) must use SHA pinning.
- `release.yml` must preserve the governed tag-triggered publish path.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

# First-party GitHub action orgs whose major-version tags are acceptable
_FIRST_PARTY_PREFIXES = (
    "actions/",
    "github/",
    "pypa/",
    "astral-sh/",
    "SonarSource/",
    "CycloneDX/",
    "EndBug/",
    "dorny/",
)

# Pattern: owner/action@<40-hex-char SHA>
_SHA_PIN_RE = re.compile(r"^[^/]+/[^@]+@[0-9a-f]{40}$")

_CANONICAL_REPOSITORY = "arcasilesgroup/ai-engineering"
_RELEASE_WORKFLOW = Path(".github/workflows/release.yml")
_RELEASE_JOB_ORDER = (
    "resolve-version",
    "release-readiness",
    "release-build",
    "attest-and-verify",
    "publish-testpypi",
    "verify-testpypi-install",
    "publish-pypi",
    "finalize-release-packet",
)
_PRIVILEGED_RELEASE_JOBS = (
    "publish-testpypi",
    "publish-pypi",
    "finalize-release-packet",
)


def workflow_triggers(data: dict[str, Any]) -> dict[str, Any]:
    """Return the workflow trigger mapping, handling PyYAML's boolean `on` key."""
    triggers = data.get("on", data.get(True, {}))
    if triggers is None:
        return {}
    if isinstance(triggers, str):
        return {triggers: None}
    if isinstance(triggers, list):
        return {str(item): None for item in triggers}
    if isinstance(triggers, dict):
        return {str(key): value for key, value in triggers.items()}
    return {}


def _steps_text(job: dict[str, Any]) -> str:
    """Serialize a job's steps for narrow textual policy checks."""
    steps = job.get("steps", [])
    return yaml.safe_dump(steps, sort_keys=False)


def _workflow_text(data: dict[str, Any]) -> str:
    """Serialize a workflow for narrow textual policy checks."""
    return yaml.safe_dump(data, sort_keys=False)


def _needs_set(job: dict[str, Any]) -> set[str]:
    """Normalize a job's `needs` declaration to a set."""
    needs = job.get("needs", [])
    if isinstance(needs, str):
        return {needs}
    if isinstance(needs, list):
        return {str(item) for item in needs}
    return set()


def _required_input_present(inputs: dict[str, Any], name: str) -> bool:
    """Return whether a workflow_dispatch input is required."""
    config = inputs.get(name)
    return isinstance(config, dict) and config.get("required") is True


def _has_privileged_context_guard(job: dict[str, Any]) -> bool:
    """Check a privileged publish/finalize job is restricted to trusted release events."""
    guard = str(job.get("if", ""))
    has_repository_guard = f"github.repository == '{_CANONICAL_REPOSITORY}'" in guard
    has_tag_guard = (
        "github.event_name == 'push'" in guard and "startsWith(github.ref, 'refs/tags/v')" in guard
    )
    has_dispatch_guard = "github.event_name == 'workflow_dispatch'" in guard
    return (
        has_repository_guard
        and has_tag_guard
        and has_dispatch_guard
        and "pull_request" not in guard
    )


def _expect_text(text: str, required: tuple[str, ...], label: str) -> list[str]:
    """Return missing text fragments as policy failure messages."""
    return [f"{label}: missing {needle!r}" for needle in required if needle not in text]


def check_release_workflow_policy(workflow: Path, data: dict[str, Any]) -> list[str]:
    """Check the spec-143 release workflow supply-chain contract.

    The helper is deliberately narrow: it only validates the live Release
    workflow, leaving generic workflow checks reusable for the rest of CI.
    """
    failures: list[str] = []

    triggers = workflow_triggers(data)
    push_tags = (triggers.get("push") or {}).get("tags", [])
    if "v*" not in push_tags:
        failures.append(f"{workflow}: release workflow must trigger on push tags ['v*']")
    if "workflow_dispatch" not in triggers:
        failures.append(f"{workflow}: release workflow must keep protected workflow_dispatch")
    if "release" in triggers or "workflow_run" in triggers:
        failures.append(f"{workflow}: release workflow must not use release/workflow_run triggers")

    dispatch = triggers.get("workflow_dispatch") or {}
    dispatch_inputs = dispatch.get("inputs", {}) if isinstance(dispatch, dict) else {}
    if not isinstance(dispatch_inputs, dict):
        dispatch_inputs = {}
    for input_name in ("version", "recovery_reason"):
        if not _required_input_present(dispatch_inputs, input_name):
            failures.append(f"{workflow}: workflow_dispatch input {input_name!r} must be required")

    top_permissions = data.get("permissions", {})
    if isinstance(top_permissions, dict):
        for permission in ("id-token", "attestations", "contents"):
            if top_permissions.get(permission) == "write":
                failures.append(
                    f"{workflow}: top-level permissions must not grant {permission}: write"
                )

    concurrency_text = yaml.safe_dump(data.get("concurrency"), sort_keys=False)
    if "github.ref_name" not in concurrency_text and "version" not in concurrency_text:
        failures.append(f"{workflow}: concurrency must be keyed by tag/version")

    jobs = data.get("jobs", {})
    if not isinstance(jobs, dict):
        return [*failures, f"{workflow}: jobs must be a mapping"]

    if tuple(jobs.keys()) != _RELEASE_JOB_ORDER:
        failures.append(
            f"{workflow}: release jobs must appear in order {_RELEASE_JOB_ORDER}; "
            f"got {tuple(jobs.keys())}"
        )

    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        if "timeout-minutes" not in job:
            failures.append(f"{workflow}: job {job_name!r} missing timeout-minutes")

    expected_needs: dict[str, set[str]] = {
        "release-readiness": {"resolve-version"},
        "release-build": {"resolve-version", "release-readiness"},
        "attest-and-verify": {"resolve-version", "release-build"},
        "publish-testpypi": {
            "resolve-version",
            "release-readiness",
            "release-build",
            "attest-and-verify",
        },
        "verify-testpypi-install": {"resolve-version", "publish-testpypi"},
    }
    for job_name, expected in expected_needs.items():
        job = jobs.get(job_name)
        if isinstance(job, dict) and _needs_set(job) != expected:
            failures.append(f"{workflow}: job {job_name!r} needs {sorted(expected)}")

    publish_pypi = jobs.get("publish-pypi", {})
    if isinstance(publish_pypi, dict) and "verify-testpypi-install" not in _needs_set(publish_pypi):
        failures.append(f"{workflow}: publish-pypi must need verify-testpypi-install")
    finalize = jobs.get("finalize-release-packet", {})
    if isinstance(finalize, dict) and "publish-pypi" not in _needs_set(finalize):
        failures.append(f"{workflow}: finalize-release-packet must need publish-pypi")

    workflow_text = _workflow_text(data)
    forbidden_fragments = (
        "ci-build.yml",
        "gh run list",
        "github.event.workflow_run",
        "github.event.pull_request",
        "pull_request_target",
        "run-id:",
        "workflow_run:",
        "username:",
        "password:",
        "PYPI_TOKEN",
    )
    for fragment in forbidden_fragments:
        if fragment in workflow_text:
            failures.append(f"{workflow}: forbidden release workflow fragment {fragment!r}")

    release_build = jobs.get("release-build", {})
    if isinstance(release_build, dict):
        failures.extend(
            _expect_text(
                _steps_text(release_build),
                (
                    "uv build",
                    "METADATA",
                    "PKG-INFO",
                    "Version",
                    "ai-engineering==${VERSION}",
                    "cyclonedx-py",
                    "sbom.cdx.json",
                    "sha256sum dist/* sbom.cdx.json",
                    "CHECKSUMS-SHA256.txt",
                    "release-dists",
                    "release-supply-chain",
                ),
                f"{workflow}: release-build",
            )
        )

    attest = jobs.get("attest-and-verify", {})
    if isinstance(attest, dict):
        if attest.get("permissions") != {
            "contents": "read",
            "attestations": "write",
            "id-token": "write",
        }:
            failures.append(f"{workflow}: attest-and-verify permissions are not job-scoped")
        failures.extend(
            _expect_text(
                _steps_text(attest),
                (
                    "actions/attest-build-provenance",
                    "subject-path: dist/*",
                    "gh attestation verify",
                    "github-attestation-verify.log",
                ),
                f"{workflow}: attest-and-verify",
            )
        )

    for job_name, environment_name in (
        ("publish-testpypi", "testpypi"),
        ("publish-pypi", "pypi"),
    ):
        job = jobs.get(job_name, {})
        if not isinstance(job, dict):
            continue
        if job.get("permissions") != {"contents": "read", "id-token": "write"}:
            failures.append(f"{workflow}: {job_name} permissions must only grant OIDC")
        environment = job.get("environment", {})
        if not isinstance(environment, dict) or environment.get("name") != environment_name:
            failures.append(f"{workflow}: {job_name} must use environment {environment_name!r}")
        if not _has_privileged_context_guard(job):
            failures.append(f"{workflow}: {job_name} missing tag/recovery repository guard")

    testpypi = jobs.get("publish-testpypi", {})
    if isinstance(testpypi, dict):
        failures.extend(
            _expect_text(
                _steps_text(testpypi),
                (
                    "pypa/gh-action-pypi-publish",
                    "repository-url: https://test.pypi.org/legacy/",
                    "testpypi-proof.txt",
                ),
                f"{workflow}: publish-testpypi",
            )
        )

    verify_testpypi = jobs.get("verify-testpypi-install", {})
    if isinstance(verify_testpypi, dict):
        failures.extend(
            _expect_text(
                _steps_text(verify_testpypi),
                (
                    "--index-url",
                    "https://test.pypi.org/simple/",
                    "--extra-index-url",
                    "https://pypi.org/simple/",
                    "testpypi-install-proof.txt",
                ),
                f"{workflow}: verify-testpypi-install",
            )
        )

    pypi = jobs.get("publish-pypi", {})
    if isinstance(pypi, dict):
        failures.extend(
            _expect_text(
                _steps_text(pypi),
                ("pypa/gh-action-pypi-publish", "release-dists", "pypi-proof.txt"),
                f"{workflow}: publish-pypi",
            )
        )

    if isinstance(finalize, dict):
        if finalize.get("permissions") != {"contents": "write"}:
            failures.append(f"{workflow}: finalize-release-packet must only grant contents write")
        if not _has_privileged_context_guard(finalize):
            failures.append(
                f"{workflow}: finalize-release-packet missing tag/recovery repository guard"
            )
        failures.extend(
            _expect_text(
                _steps_text(finalize),
                (
                    "gh release create",
                    "gh release edit",
                    "gh release upload",
                    "--clobber",
                    "release-packet.json",
                    "release-notes.md",
                    "release-readiness.json",
                    "github-attestation-verify.log",
                    "testpypi-proof.txt",
                    "testpypi-install-proof.txt",
                    "pypi-proof.txt",
                    "ci_run_url",
                    "recovery",
                ),
                f"{workflow}: finalize-release-packet",
            )
        )

    readiness = jobs.get("release-readiness", {})
    if isinstance(readiness, dict):
        failures.extend(
            _expect_text(
                _steps_text(readiness),
                ("ai-eng verify --release", "--json", "release-readiness.json", "NO-GO"),
                f"{workflow}: release-readiness",
            )
        )

    return failures


def _check_sha_pinning(workflow: Path, data: dict) -> list[str]:
    """Check that third-party actions use SHA pinning."""
    failures: list[str] = []
    jobs = data.get("jobs", {})
    if not isinstance(jobs, dict):
        return failures

    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps", [])
        if not isinstance(steps, list):
            continue
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            uses = step.get("uses", "")
            if not isinstance(uses, str) or not uses:
                continue
            # Strip inline comments for matching (e.g., "owner/action@sha # v1.2.3")
            uses_clean = uses.split("#")[0].strip()
            # Skip first-party actions
            if any(uses_clean.startswith(prefix) for prefix in _FIRST_PARTY_PREFIXES):
                continue
            # Skip docker:// and local ./ references
            if uses_clean.startswith("docker://") or uses_clean.startswith("./"):
                continue
            # Must be SHA-pinned
            if not _SHA_PIN_RE.match(uses_clean):
                step_name = step.get("name", f"step {i}")
                failures.append(
                    f"{workflow}: job '{job_name}', {step_name}: "
                    f"third-party action '{uses_clean}' must use SHA pinning "
                    f"(owner/action@<sha> # vN.M.P)"
                )
    return failures


def main() -> int:
    workflows = sorted(p for p in Path(".github/workflows").glob("*.yml"))
    failures: list[str] = []

    for workflow in workflows:
        data = yaml.safe_load(workflow.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            failures.append(f"{workflow}: workflow root must be a mapping")
            continue

        # Keep the generic policy behavior unchanged for existing workflows.
        # The release-specific helper below normalizes PyYAML's boolean `on`
        # key because spec-143 needs precise trigger inspection for release.yml.
        triggers = data.get("on")
        if isinstance(triggers, dict) and "pull_request_target" in triggers:
            failures.append(f"{workflow}: 'pull_request_target' is not allowed")

        if "permissions" not in data:
            failures.append(f"{workflow}: missing top-level permissions block")

        # Concurrency required for workflows with pull_request trigger
        has_pr_trigger = (
            (isinstance(triggers, dict) and "pull_request" in triggers)
            or (isinstance(triggers, str) and triggers == "pull_request")
            or (isinstance(triggers, list) and "pull_request" in triggers)
        )

        if has_pr_trigger and "concurrency" not in data:
            failures.append(
                f"{workflow}: missing 'concurrency' key "
                f"(required for workflows with pull_request trigger)"
            )

        # Every job must have timeout-minutes
        jobs = data.get("jobs", {})
        if isinstance(jobs, dict):
            for job_name, job in jobs.items():
                if not isinstance(job, dict):
                    continue
                if "timeout-minutes" not in job:
                    failures.append(f"{workflow}: job '{job_name}' missing 'timeout-minutes'")

        # Third-party actions must use SHA pinning
        failures.extend(_check_sha_pinning(workflow, data))

        if workflow == _RELEASE_WORKFLOW:
            failures.extend(check_release_workflow_policy(workflow, data))

    if failures:
        print("workflow policy check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"workflow policy check passed ({len(workflows)} workflow files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
