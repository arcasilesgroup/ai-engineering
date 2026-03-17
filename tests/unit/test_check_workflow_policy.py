"""Tests for scripts/check_workflow_policy.py."""

from __future__ import annotations

from pathlib import Path

from scripts.check_workflow_policy import _check_sha_pinning


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
            "jobs": {"build": {"steps": [{"uses": "astral-sh/setup-uv@v5", "name": "Setup UV"}]}}
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
