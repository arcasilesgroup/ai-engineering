"""spec-152 W5.T31 — StepSecurity harden-runner egress monitoring (D-152-19).

``step-security/harden-runner`` installs an eBPF egress monitor as the FIRST
step of a job. In ``egress-policy: audit`` it is non-blocking — it logs every
outbound connection without breaking the build, giving an egress baseline
before any future flip to ``block``.

This gate asserts harden-runner is wired into every CI workflow job in scope
(``ci-check.yml``, ``sbom.yml``, ``scorecard.yml``):

* it is the FIRST step of every job (a monitor installed after another step
  cannot observe that step's egress);
* it is SHA-pinned (D-152-05);
* it runs in ``egress-policy: audit`` (non-blocking baseline, OQ2).

``release.yml`` is intentionally OUT OF SCOPE for this wave (the release
publish path is hardened by a follow-up spec), so it is not asserted here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

HARDEN_RUNNER_ACTION = "step-security/harden-runner"
# CI workflows that must carry harden-runner on every job. release.yml is
# deliberately excluded (deferred to a follow-up release-hardening spec).
CI_WORKFLOWS = ("ci-check.yml", "sbom.yml", "scorecard.yml")
_SHA40 = 40


def _load(name: str) -> dict[str, Any]:
    path = WORKFLOWS_DIR / name
    assert path.exists(), f"missing workflow: {path}"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{name} must parse to a YAML mapping"
    return data


def _first_step(job: dict[str, Any]) -> dict[str, Any] | None:
    steps = job.get("steps") or []
    if not isinstance(steps, list) or not steps:
        return None
    first = steps[0]
    return first if isinstance(first, dict) else None


def _is_sha_pinned(use: str) -> bool:
    if "@" not in use:
        return False
    ref = use.rsplit("@", 1)[1]
    return len(ref) == _SHA40 and all(c in "0123456789abcdef" for c in ref)


def test_harden_runner_is_first_step_of_every_ci_job() -> None:
    """harden-runner is the FIRST step of every job in each CI workflow.

    A monitor that is not first cannot observe the egress of the steps that
    precede it (e.g. an early ``checkout`` or tool install).
    """
    errors: list[str] = []
    for name in CI_WORKFLOWS:
        data = _load(name)
        jobs = data.get("jobs", {})
        assert isinstance(jobs, dict) and jobs, f"{name} must declare jobs"
        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                continue
            first = _first_step(job)
            uses = (first or {}).get("uses", "")
            action = uses.split("#")[0].strip().split("@")[0] if isinstance(uses, str) else ""
            if action != HARDEN_RUNNER_ACTION:
                errors.append(
                    f"{name}: job '{job_name}' first step is {action or '(none)'!r}, "
                    f"expected {HARDEN_RUNNER_ACTION!r}"
                )
    assert not errors, (
        "harden-runner must be the first step of every CI job:\n  - " + "\n  - ".join(errors)
    )


def test_harden_runner_is_sha_pinned_in_every_ci_workflow() -> None:
    """Every harden-runner ``uses:`` is pinned to a 40-char commit SHA."""
    errors: list[str] = []
    for name in CI_WORKFLOWS:
        data = _load(name)
        for job_name, job in data.get("jobs", {}).items():
            if not isinstance(job, dict):
                continue
            for step in job.get("steps") or []:
                if not isinstance(step, dict):
                    continue
                uses = step.get("uses", "")
                if not isinstance(uses, str):
                    continue
                clean = uses.split("#")[0].strip()
                if clean.split("@")[0] == HARDEN_RUNNER_ACTION and not _is_sha_pinned(clean):
                    errors.append(f"{name}: job '{job_name}': {clean!r} is not SHA-pinned")
    assert not errors, "harden-runner refs must be SHA-pinned:\n  - " + "\n  - ".join(errors)


def test_harden_runner_uses_audit_egress_policy() -> None:
    """Each harden-runner step runs with ``egress-policy: audit`` (non-blocking)."""
    errors: list[str] = []
    for name in CI_WORKFLOWS:
        data = _load(name)
        for job_name, job in data.get("jobs", {}).items():
            if not isinstance(job, dict):
                continue
            first = _first_step(job)
            if first is None:
                continue
            uses = first.get("uses", "")
            action = uses.split("#")[0].strip().split("@")[0] if isinstance(uses, str) else ""
            if action != HARDEN_RUNNER_ACTION:
                continue
            with_block = first.get("with", {})
            policy = with_block.get("egress-policy") if isinstance(with_block, dict) else None
            if policy != "audit":
                errors.append(
                    f"{name}: job '{job_name}' harden-runner egress-policy is {policy!r}, "
                    "expected 'audit' (non-blocking baseline, OQ2)"
                )
    assert not errors, "harden-runner must run in audit mode:\n  - " + "\n  - ".join(errors)
