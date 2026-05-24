"""Coupling guard: the tag-triggered release workflow's deployment
environments MUST be documented with their ``v*`` policy requirement.

spec-152 made ``release.yml`` tag-triggered; a deployment environment that
restricts deploys to branches then rejects the tag-triggered publish (the
0.8.0 near-miss). The environment policy lives in GitHub settings, so it
cannot be enforced by committed code — but its *documentation* can be.

This gate fails CI when ``release.yml`` stays tag-triggered while any
environment it deploys through is left undocumented in
``docs/ci-branch-protection.md``. Adding a new publish environment to the
workflow therefore forces a matching policy note. The live setting itself
is checked by the ``release-env-policy`` doctor probe; the tag trigger is
held in place by ``scripts/check_workflow_policy.py``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
RELEASE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release.yml"
BRANCH_PROTECTION_DOC = REPO_ROOT / "docs" / "ci-branch-protection.md"


def _load_release() -> dict[str, Any]:
    data = yaml.safe_load(RELEASE_WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "release.yml did not parse to a mapping"
    return data


def _tag_globs(data: dict[str, Any]) -> list[str]:
    # PyYAML parses the bare ``on:`` key as the boolean True.
    triggers = data.get("on", data.get(True))
    assert isinstance(triggers, dict), "release.yml has no trigger mapping"
    push = triggers.get("push")
    if not isinstance(push, dict):
        return []
    tags = push.get("tags")
    if isinstance(tags, str):
        return [tags]
    if isinstance(tags, list):
        return [str(item) for item in tags]
    return []


def _environment_names(data: dict[str, Any]) -> set[str]:
    jobs = data.get("jobs", {})
    assert isinstance(jobs, dict)
    names: set[str] = set()
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        environment = job.get("environment")
        if isinstance(environment, str) and "${{" not in environment:
            names.add(environment)
        elif isinstance(environment, dict):
            name = environment.get("name")
            if isinstance(name, str) and "${{" not in name:
                names.add(name)
    return names


def test_release_workflow_is_tag_triggered() -> None:
    """Premise of the coupling: the publish path fires on ``v*`` tags."""
    assert "v*" in _tag_globs(_load_release()), (
        "release.yml must trigger on push tags ['v*']; if this changed, the "
        "environment deployment-policy coupling below must be revisited"
    )


def test_release_workflow_uses_expected_environments() -> None:
    """Lock the documented environment set so a silent addition is caught."""
    assert _environment_names(_load_release()) == {"pypi", "testpypi", "github-release"}


def test_every_release_environment_is_documented() -> None:
    doc = BRANCH_PROTECTION_DOC.read_text(encoding="utf-8")
    for env in _environment_names(_load_release()):
        assert f"`{env}`" in doc, (
            f"deployment environment {env!r} is used by release.yml but is not "
            f"documented in {BRANCH_PROTECTION_DOC.relative_to(REPO_ROOT)}"
        )


def test_doc_records_v_star_tag_policy_and_remediation() -> None:
    doc = BRANCH_PROTECTION_DOC.read_text(encoding="utf-8")
    assert "v*" in doc, "branch-protection doc must record the v* tag pattern"
    assert "deployment-branch-policies" in doc, (
        "branch-protection doc must include the gh deployment-branch-policies remediation command"
    )
    assert "release-env-policy" in doc, (
        "branch-protection doc must reference the release-env-policy doctor guard"
    )
    assert "tag-protection-v" in doc, (
        "branch-protection doc must document the tag-protection-v ruleset coupling"
    )
