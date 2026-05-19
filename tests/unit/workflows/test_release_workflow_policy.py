"""spec-143 release workflow policy drift gates.

These tests pin the Release workflow as the sole publish path:

* tag-triggered ``v*`` normal path with protected ``workflow_dispatch`` recovery;
* job-scoped OIDC/attestation/GitHub Release permissions;
* same-run build-once artifacts only;
* TestPyPI proof before production PyPI; and
* a finalized GitHub Release packet containing readiness/provenance evidence.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.check_workflow_policy import check_release_workflow_policy, workflow_triggers

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "release.yml"

REQUIRED_JOBS = [
    "resolve-version",
    "release-readiness",
    "release-build",
    "attest-and-verify",
    "publish-testpypi",
    "verify-testpypi-install",
    "publish-pypi",
    "finalize-release-packet",
]

PRIVILEGED_JOBS = {"publish-testpypi", "publish-pypi", "finalize-release-packet"}
PACKET_EVIDENCE = {
    "release-dists",
    "CHECKSUMS-SHA256.txt",
    "sbom.cdx.json",
    "github-attestation-verify.log",
    "testpypi-proof.txt",
    "testpypi-install-proof.txt",
    "pypi-proof.txt",
    "release-readiness.json",
    "release-notes.md",
    "ci_run_url",
    "recovery",
}


@pytest.fixture(scope="module")
def workflow() -> dict:
    """Parse the live Release workflow once for all drift gates."""
    assert WORKFLOW_PATH.exists(), f"missing workflow: {WORKFLOW_PATH}"
    data = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "release.yml must parse to a YAML mapping"
    return data


def _job(workflow: dict, name: str) -> dict:
    jobs = workflow.get("jobs") or {}
    assert name in jobs, f"release workflow missing job {name!r}; got {sorted(jobs)}"
    job = jobs[name]
    assert isinstance(job, dict), f"job {name!r} must be a mapping"
    return job


def _job_text(workflow: dict, name: str) -> str:
    return yaml.safe_dump(_job(workflow, name), sort_keys=False)


def _step_text(workflow: dict, name: str) -> str:
    steps = _job(workflow, name).get("steps") or []
    assert isinstance(steps, list), f"job {name!r} steps must be a list"
    return yaml.safe_dump(steps, sort_keys=False)


def _needs(workflow: dict, name: str) -> set[str]:
    needs = _job(workflow, name).get("needs", [])
    if isinstance(needs, str):
        return {needs}
    assert isinstance(needs, list), f"job {name!r} needs must be string/list"
    return {str(item) for item in needs}


def test_release_policy_helper_has_no_failures(workflow: dict) -> None:
    """The reusable policy helper is the broad one-shot gate used by CI."""
    failures = check_release_workflow_policy(WORKFLOW_PATH, workflow)
    assert failures == []


def test_release_workflow_starts_on_v_tags(workflow: dict) -> None:
    """T-6 — normal releases start from governed ``v*`` tags, not CI artifacts."""
    triggers = workflow_triggers(workflow)
    assert "push" in triggers, f"release workflow must declare push trigger; got {triggers}"
    assert "v*" in (triggers.get("push") or {}).get("tags", [])
    assert "workflow_dispatch" in triggers, "protected recovery dispatch must remain available"
    assert "release" not in triggers, "release.published must not be the normal path"
    assert "workflow_run" not in triggers, "ci-build.yml workflow_run must not drive releases"


def test_workflow_dispatch_requires_recovery_context(workflow: dict) -> None:
    """T-24 — manual recovery must be explicit and auditable."""
    dispatch = workflow_triggers(workflow)["workflow_dispatch"]
    inputs = dispatch.get("inputs") or {}
    assert inputs.get("version", {}).get("required") is True
    assert inputs.get("recovery_reason", {}).get("required") is True
    resolver_text = _step_text(workflow, "resolve-version")
    assert "RECOVERY_REASON" in resolver_text
    assert "recovery_reason" in resolver_text


def test_release_workflow_permissions_are_job_scoped(workflow: dict) -> None:
    """T-7 — OIDC, attestations, and release writes are least-privilege scoped."""
    top_permissions = workflow.get("permissions") or {}
    assert top_permissions.get("id-token") != "write"
    assert top_permissions.get("attestations") != "write"
    assert top_permissions.get("contents") != "write"

    assert _job(workflow, "attest-and-verify")["permissions"] == {
        "contents": "read",
        "attestations": "write",
        "id-token": "write",
    }
    assert _job(workflow, "publish-testpypi")["permissions"] == {
        "contents": "read",
        "id-token": "write",
    }
    assert _job(workflow, "publish-pypi")["permissions"] == {
        "contents": "read",
        "id-token": "write",
    }
    assert _job(workflow, "finalize-release-packet")["permissions"] == {
        "contents": "write",
    }

    for job_name, job in (workflow.get("jobs") or {}).items():
        assert "timeout-minutes" in job, f"job {job_name!r} must set timeout-minutes"
    assert _job(workflow, "release-readiness")["timeout-minutes"] >= 30

    concurrency = yaml.safe_dump(workflow.get("concurrency"), sort_keys=False)
    assert "github.ref_name" in concurrency or "version" in concurrency


def test_release_workflow_avoids_untrusted_artifact_reuse(workflow: dict) -> None:
    """T-8 — release artifacts must come from this tag-triggered workflow only."""
    workflow_text = yaml.safe_dump(workflow, sort_keys=False)
    forbidden = [
        "ci-build.yml",
        "gh run list",
        "github.event.workflow_run",
        "github.event.pull_request",
        "pull_request_target",
        "run-id:",
        "workflow_run:",
    ]
    present = [needle for needle in forbidden if needle in workflow_text]
    assert not present, f"release workflow reuses untrusted context/artifacts: {present}"

    for job_name in ("publish-testpypi", "publish-pypi", "finalize-release-packet"):
        text = _step_text(workflow, job_name)
        assert "actions/download-artifact" in text, f"{job_name} must use same-run artifacts"
        assert "run-id" not in text, f"{job_name} must not download artifacts from another run"


def test_release_packet_artifact_contract(workflow: dict) -> None:
    """T-9 — final packet contains every required release evidence file."""
    text = _step_text(workflow, "finalize-release-packet")
    missing = sorted(item for item in PACKET_EVIDENCE if item not in text)
    assert not missing, f"final packet is missing evidence entries: {missing}\n{text}"


def test_release_job_topology_builds_once_from_tag(workflow: dict) -> None:
    """T-12 — the DAG keeps build-once artifacts upstream of all publication."""
    assert list((workflow.get("jobs") or {}).keys()) == REQUIRED_JOBS
    assert _needs(workflow, "release-readiness") == {"resolve-version"}
    assert _needs(workflow, "release-build") == {"resolve-version", "release-readiness"}
    assert _needs(workflow, "attest-and-verify") == {"resolve-version", "release-build"}
    assert _needs(workflow, "publish-testpypi") == {
        "resolve-version",
        "release-readiness",
        "release-build",
        "attest-and-verify",
    }
    assert _needs(workflow, "verify-testpypi-install") == {"resolve-version", "publish-testpypi"}
    assert "verify-testpypi-install" in _needs(workflow, "publish-pypi")
    assert "publish-pypi" in _needs(workflow, "finalize-release-packet")

    build_text = _step_text(workflow, "release-build")
    assert build_text.count("uv build") == 1
    assert "release-dists" in build_text


def test_release_build_artifact_integrity(workflow: dict) -> None:
    """T-14 — build job verifies package metadata and supply-chain artifacts."""
    text = _step_text(workflow, "release-build")
    required = [
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
    ]
    missing = [needle for needle in required if needle not in text]
    assert not missing, f"release-build missing integrity command(s): {missing}\n{text}"


def test_github_artifact_attestation(workflow: dict) -> None:
    """T-16 — GitHub artifact attestations are generated and verified before publish."""
    job = _job(workflow, "attest-and-verify")
    assert job["permissions"] == {
        "contents": "read",
        "attestations": "write",
        "id-token": "write",
    }
    text = _step_text(workflow, "attest-and-verify")
    assert "actions/attest-build-provenance" in text
    assert "subject-path: dist/*" in text
    assert "gh attestation verify" in text
    assert "github-attestation-verify.log" in text


def test_testpypi_publish_and_install_gate(workflow: dict) -> None:
    """T-18 — TestPyPI publish and install proof gate production."""
    publish = _job(workflow, "publish-testpypi")
    assert publish["environment"]["name"] == "testpypi"
    assert publish["permissions"] == {"contents": "read", "id-token": "write"}
    publish_text = _step_text(workflow, "publish-testpypi")
    assert "pypa/gh-action-pypi-publish" in publish_text
    assert "repository-url: https://test.pypi.org/legacy/" in publish_text
    assert "testpypi-proof.txt" in publish_text

    install_text = _step_text(workflow, "verify-testpypi-install")
    assert "--index-url https://test.pypi.org/simple/" in install_text
    assert "--extra-index-url https://pypi.org/simple/" in install_text
    assert "ai-engineering==${VERSION}" in install_text
    assert "testpypi-install-proof.txt" in install_text


def test_production_pypi_publish_gate(workflow: dict) -> None:
    """T-20 — production PyPI uses Trusted Publishing after TestPyPI proof."""
    job = _job(workflow, "publish-pypi")
    assert "publish-testpypi" in _needs(workflow, "publish-pypi")
    assert "verify-testpypi-install" in _needs(workflow, "publish-pypi")
    assert job["environment"]["name"] == "pypi"
    assert job["permissions"] == {"contents": "read", "id-token": "write"}

    text = _step_text(workflow, "publish-pypi")
    assert "pypa/gh-action-pypi-publish" in text
    assert "release-dists" in text
    forbidden_credentials = ["username:", "password:", "PYPI_TOKEN", "API_TOKEN"]
    present = [needle for needle in forbidden_credentials if needle in text]
    assert not present, f"Trusted Publishing must not use long-lived credentials: {present}"


def test_github_release_packet_finalization(workflow: dict) -> None:
    """T-22 — GitHub Release is finalized after PyPI and uploads packet assets."""
    job = _job(workflow, "finalize-release-packet")
    assert job["permissions"] == {"contents": "write"}
    assert "publish-pypi" in _needs(workflow, "finalize-release-packet")

    text = _step_text(workflow, "finalize-release-packet")
    required = [
        "gh release create",
        "gh release edit",
        "gh release upload",
        "--clobber",
        "release-packet.json",
        "release-notes.md",
        "CHANGELOG.md",
        "ci_run_url",
    ]
    missing = [needle for needle in required if needle not in text]
    assert not missing, f"finalize-release-packet missing command(s): {missing}\n{text}"


def test_release_workflow_runs_readiness_before_publish(workflow: dict) -> None:
    """T-32 — readiness JSON is generated before either publish job."""
    text = _step_text(workflow, "release-readiness")
    assert "ai-eng --json verify --release" in text
    assert "--target release-source" in text
    assert "Checkout workflow tooling" in text
    assert "Checkout release tag source" in text
    assert "path: release-source" in text
    assert "Install gitleaks" in text
    assert "GITLEAKS_VERSION" in text
    assert "gitleaks version" in text
    assert "release-readiness-envelope.json" in text
    assert "find_readiness" in text
    assert "release_readiness" in text
    assert ".ai-engineering" in text
    assert "runtime" in text
    assert "release-readiness.json" in text
    assert "CONDITIONAL GO" in text
    assert "NO-GO" in text
    assert "release-readiness" in _needs(workflow, "publish-testpypi")
    assert "release-readiness" in _needs(workflow, "publish-pypi")


def test_privileged_publish_jobs_are_pr_fork_guarded(workflow: dict) -> None:
    """T-44 — privileged jobs are fail-closed to canonical tag/recovery events."""
    for job_name in PRIVILEGED_JOBS:
        guard = str(_job(workflow, job_name).get("if", ""))
        assert "github.repository == 'arcasilesgroup/ai-engineering'" in guard
        assert "github.event_name == 'push'" in guard
        assert "startsWith(github.ref, 'refs/tags/v')" in guard
        assert "github.event_name == 'workflow_dispatch'" in guard
        assert "pull_request" not in guard
