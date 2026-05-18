"""Tests for scripts/check_workflow_policy.py."""

from __future__ import annotations

from pathlib import Path

from scripts.check_workflow_policy import (
    _check_sha_pinning,
    check_release_workflow_policy,
    workflow_triggers,
)


class TestCheckShaPinning:
    """Test SHA pinning enforcement for third-party actions."""

    def test_sha_pinned_passes(self):
        data = {
            "jobs": {
                "build": {
                    "steps": [
                        {
                            "uses": "astral-sh/setup-uv"
                            "@d4b2f3b6ecc6e67c4457f6d3e41ec42d3d0fcb86 # v5.4.2"
                        }
                    ]
                }
            }
        }
        assert _check_sha_pinning(Path("test.yml"), data) == []

    def test_tag_only_fails(self):
        data = {
            "jobs": {
                "build": {"steps": [{"uses": "unknown-org/some-action@v5", "name": "Some Action"}]}
            }
        }
        failures = _check_sha_pinning(Path("test.yml"), data)
        assert len(failures) == 1
        assert "SHA pinning" in failures[0]

    def test_first_party_tag_passes(self):
        data = {"jobs": {"build": {"steps": [{"uses": "actions/checkout@v4"}]}}}
        assert _check_sha_pinning(Path("test.yml"), data) == []

    def test_local_action_skipped(self):
        data = {"jobs": {"build": {"steps": [{"uses": "./my-local-action"}]}}}
        assert _check_sha_pinning(Path("test.yml"), data) == []

    def test_docker_action_skipped(self):
        data = {"jobs": {"build": {"steps": [{"uses": "docker://alpine:3.18"}]}}}
        assert _check_sha_pinning(Path("test.yml"), data) == []

    def test_branch_ref_fails(self):
        data = {
            "jobs": {"build": {"steps": [{"uses": "some-org/some-action@main", "name": "Bad ref"}]}}
        }
        failures = _check_sha_pinning(Path("test.yml"), data)
        assert len(failures) == 1

    def test_step_without_uses_skipped(self):
        data = {
            "jobs": {
                "build": {
                    "steps": [
                        {"run": "echo hello"},
                        {"uses": "actions/checkout@v4"},
                    ]
                }
            }
        }
        assert _check_sha_pinning(Path("test.yml"), data) == []

    def test_multiple_jobs_checked(self):
        data = {
            "jobs": {
                "lint": {"steps": [{"uses": "some-org/lint@v1", "name": "Lint"}]},
                "test": {"steps": [{"uses": "some-org/test@v2", "name": "Test"}]},
            }
        }
        failures = _check_sha_pinning(Path("test.yml"), data)
        assert len(failures) == 2


def _minimal_release_workflow() -> dict:
    """Return a compact release workflow satisfying the spec-143 policy helper."""
    trusted_guard = (
        "github.repository == 'arcasilesgroup/ai-engineering' && "
        "((github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')) || "
        "github.event_name == 'workflow_dispatch')"
    )
    return {
        "on": {
            "push": {"tags": ["v*"]},
            "workflow_dispatch": {
                "inputs": {
                    "version": {"required": True},
                    "recovery_reason": {"required": True},
                }
            },
        },
        "permissions": {"contents": "read"},
        "concurrency": {"group": "release-${{ github.ref_name || github.event.inputs.version }}"},
        "jobs": {
            "resolve-version": {"runs-on": "ubuntu-latest", "timeout-minutes": 5, "steps": []},
            "release-readiness": {
                "runs-on": "ubuntu-latest",
                "timeout-minutes": 10,
                "needs": "resolve-version",
                "steps": [
                    {
                        "run": (
                            'uv run ai-eng verify --release "$VERSION" --json '
                            "> release-readiness.json\nNO-GO"
                        )
                    }
                ],
            },
            "release-build": {
                "runs-on": "ubuntu-latest",
                "timeout-minutes": 20,
                "needs": ["resolve-version", "release-readiness"],
                "steps": [
                    {
                        "run": (
                            "uv build\nMETADATA PKG-INFO Version\n"
                            'python -m pip install "ai-engineering==${VERSION}"\n'
                            "cyclonedx-py requirements requirements-prod.txt "
                            "--output-file sbom.cdx.json\n"
                            "sha256sum dist/* sbom.cdx.json > CHECKSUMS-SHA256.txt"
                        )
                    },
                    {"uses": "actions/upload-artifact@v4", "with": {"name": "release-dists"}},
                    {
                        "uses": "actions/upload-artifact@v4",
                        "with": {"name": "release-supply-chain"},
                    },
                ],
            },
            "attest-and-verify": {
                "runs-on": "ubuntu-latest",
                "timeout-minutes": 10,
                "needs": ["resolve-version", "release-build"],
                "permissions": {
                    "contents": "read",
                    "attestations": "write",
                    "id-token": "write",
                },
                "steps": [
                    {
                        "uses": "actions/attest-build-provenance@v1",
                        "with": {"subject-path": "dist/*"},
                    },
                    {"run": "gh attestation verify dist/a.whl > github-attestation-verify.log"},
                ],
            },
            "publish-testpypi": {
                "runs-on": "ubuntu-latest",
                "timeout-minutes": 10,
                "needs": [
                    "resolve-version",
                    "release-readiness",
                    "release-build",
                    "attest-and-verify",
                ],
                "if": trusted_guard,
                "permissions": {"contents": "read", "id-token": "write"},
                "environment": {"name": "testpypi"},
                "steps": [
                    {
                        "uses": "pypa/gh-action-pypi-publish@release/v1",
                        "with": {"repository-url": "https://test.pypi.org/legacy/"},
                    },
                    {"run": "echo ok > testpypi-proof.txt"},
                ],
            },
            "verify-testpypi-install": {
                "runs-on": "ubuntu-latest",
                "timeout-minutes": 10,
                "needs": ["resolve-version", "publish-testpypi"],
                "steps": [
                    {
                        "run": (
                            "python -m pip install --index-url https://test.pypi.org/simple/ "
                            "--extra-index-url https://pypi.org/simple/ "
                            "ai-engineering==${VERSION}\n"
                            "echo ok > testpypi-install-proof.txt"
                        )
                    }
                ],
            },
            "publish-pypi": {
                "runs-on": "ubuntu-latest",
                "timeout-minutes": 10,
                "needs": [
                    "resolve-version",
                    "release-readiness",
                    "release-build",
                    "attest-and-verify",
                    "publish-testpypi",
                    "verify-testpypi-install",
                ],
                "if": trusted_guard,
                "permissions": {"contents": "read", "id-token": "write"},
                "environment": {"name": "pypi"},
                "steps": [
                    {"uses": "actions/download-artifact@v4", "with": {"name": "release-dists"}},
                    {"uses": "pypa/gh-action-pypi-publish@release/v1"},
                    {"run": "echo ok > pypi-proof.txt"},
                ],
            },
            "finalize-release-packet": {
                "runs-on": "ubuntu-latest",
                "timeout-minutes": 10,
                "needs": [
                    "resolve-version",
                    "release-readiness",
                    "release-build",
                    "attest-and-verify",
                    "publish-testpypi",
                    "verify-testpypi-install",
                    "publish-pypi",
                ],
                "if": trusted_guard,
                "permissions": {"contents": "write"},
                "steps": [
                    {
                        "run": (
                            'gh release create "$TAG" --notes-file release-notes.md\n'
                            'gh release edit "$TAG" --notes-file release-notes.md\n'
                            'gh release upload "$TAG" dist/* --clobber\n'
                            "release-packet.json release-readiness.json "
                            "github-attestation-verify.log testpypi-proof.txt "
                            "testpypi-install-proof.txt pypi-proof.txt ci_run_url recovery"
                        )
                    }
                ],
            },
        },
    }


class TestReleaseWorkflowPolicy:
    """Unit tests for the narrow release policy helper."""

    def test_workflow_triggers_handles_pyyaml_boolean_on_key(self):
        data = {True: {"push": {"tags": ["v*"]}}}
        assert workflow_triggers(data) == {"push": {"tags": ["v*"]}}

    def test_minimal_valid_release_workflow_passes(self):
        failures = check_release_workflow_policy(
            Path(".github/workflows/release.yml"), _minimal_release_workflow()
        )
        assert failures == []

    def test_release_workflow_requires_tag_trigger(self):
        data = _minimal_release_workflow()
        data["on"]["push"]["tags"] = ["release-*"]
        failures = check_release_workflow_policy(Path(".github/workflows/release.yml"), data)
        assert any("push tags" in failure for failure in failures)

    def test_release_workflow_rejects_top_level_oidc_write(self):
        data = _minimal_release_workflow()
        data["permissions"]["id-token"] = "write"
        failures = check_release_workflow_policy(Path(".github/workflows/release.yml"), data)
        assert any("top-level permissions" in failure for failure in failures)

    def test_release_workflow_rejects_cross_run_artifact_download(self):
        data = _minimal_release_workflow()
        data["jobs"]["publish-pypi"]["steps"].insert(
            0, {"uses": "actions/download-artifact@v4", "with": {"run-id": "${{ github.run_id }}"}}
        )
        failures = check_release_workflow_policy(Path(".github/workflows/release.yml"), data)
        assert any("run-id:" in failure for failure in failures)
