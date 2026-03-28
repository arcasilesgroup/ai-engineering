"""Workflow policy sanity checks for GitHub Actions files.

Current enforced policies:
- No use of `pull_request_target` trigger.
- Top-level `permissions` key must be present.
- Every job must have `timeout-minutes`.
- Workflows with `pull_request` trigger must have `concurrency` key.
- Third-party actions (not `actions/*`) must use SHA pinning.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

# First-party GitHub action orgs whose major-version tags are acceptable
_FIRST_PARTY_PREFIXES = ("actions/",)

# Pattern: owner/action@<40-hex-char SHA>
_SHA_PIN_RE = re.compile(r"^[^/]+/[^@]+@[0-9a-f]{40}$")


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

    if failures:
        print("workflow policy check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"workflow policy check passed ({len(workflows)} workflow files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
