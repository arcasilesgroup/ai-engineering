"""Tests for the release version-surface CI guard."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from ai_engineering.policy import release_version_guard


def test_detect_changed_version_surfaces_ignores_unrelated_manifest_version() -> None:
    diff_by_file = {
        ".ai-engineering/manifest.yml": '@@ -1 +1 @@\n-version: "1.0.0"\n+version: "1.1.0"\n'
    }

    result = release_version_guard.detect_changed_version_surfaces(diff_by_file)

    assert result == set()


def test_evaluate_release_version_guard_skips_non_pull_request() -> None:
    passed, message = release_version_guard.evaluate_release_version_guard(
        ["pyproject.toml"],
        {"pyproject.version"},
        event_name="push",
        head_ref="main",
    )

    assert passed is True
    assert "skipped" in message


def test_evaluate_release_version_guard_fails_outside_release_branch() -> None:
    passed, message = release_version_guard.evaluate_release_version_guard(
        ["pyproject.toml"],
        {"pyproject.version"},
        event_name="pull_request",
        head_ref="feature/version-bump",
    )

    assert passed is False
    assert "outside a release PR" in message


def test_evaluate_release_version_guard_fails_when_release_file_set_is_incomplete() -> None:
    changed_files = [
        "pyproject.toml",
        "src/ai_engineering/version/registry.json",
        ".ai-engineering/manifest.yml",
        "CHANGELOG.md",
    ]

    passed, message = release_version_guard.evaluate_release_version_guard(
        changed_files,
        {
            "pyproject.version",
            "version-registry",
            "root-manifest.framework_version",
        },
        event_name="pull_request",
        head_ref="release/v0.5.0",
    )

    assert passed is False
    assert "Missing" in message
    assert "src/ai_engineering/templates/.ai-engineering/manifest.yml" in message


def test_evaluate_release_version_guard_passes_for_release_pr() -> None:
    changed_files = [
        "pyproject.toml",
        "src/ai_engineering/version/registry.json",
        ".ai-engineering/manifest.yml",
        "src/ai_engineering/templates/.ai-engineering/manifest.yml",
        "CHANGELOG.md",
    ]
    changed_surfaces = {
        "pyproject.version",
        "version-registry",
        "root-manifest.framework_version",
        "template-manifest.framework_version",
    }

    passed, message = release_version_guard.evaluate_release_version_guard(
        changed_files,
        changed_surfaces,
        event_name="pull_request",
        head_ref="release/v0.5.0",
    )

    assert passed is True
    assert "passed" in message


def test_main_reads_pr_context_and_passes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "release-version-guard",
            "--project-root",
            str(tmp_path),
            "--event-name",
            "pull_request",
            "--head-ref",
            "release/v0.5.0",
            "--base-ref",
            "main",
        ],
    )
    monkeypatch.setattr(
        release_version_guard,
        "get_changed_files",
        lambda _project_root, _base_ref: [
            "pyproject.toml",
            "src/ai_engineering/version/registry.json",
            ".ai-engineering/manifest.yml",
            "src/ai_engineering/templates/.ai-engineering/manifest.yml",
            "CHANGELOG.md",
        ],
    )
    monkeypatch.setattr(
        release_version_guard,
        "get_merge_base",
        lambda _project_root, _base_ref: "abc123",
    )

    diffs = {
        "pyproject.toml": '@@ -2 +2 @@\n-version = "0.4.0"\n+version = "0.5.0"\n',
        ".ai-engineering/manifest.yml": (
            '@@ -1 +1 @@\n-framework_version: "0.4.0"\n+framework_version: "0.5.0"\n'
        ),
        "src/ai_engineering/templates/.ai-engineering/manifest.yml": (
            '@@ -1 +1 @@\n-framework_version: "0.4.0"\n+framework_version: "0.5.0"\n'
        ),
        "src/ai_engineering/version/registry.json": (
            '@@ -3 +3 @@\n-  "version": "0.4.0"\n+  "version": "0.5.0"\n'
        ),
    }

    def fake_run_git(args: list[str], _cwd: Path, *, timeout: int = 30) -> tuple[bool, str]:
        del timeout
        file_path = str(args[-1])
        return True, diffs[file_path]

    monkeypatch.setattr(release_version_guard, "run_git", fake_run_git)

    exit_code = release_version_guard.main()

    assert exit_code == 0


def test_main_fails_when_pull_request_context_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    # CI runners expose GITHUB_BASE_REF / GITHUB_EVENT_NAME / GITHUB_HEAD_REF
    # via the workflow runtime; argparse defaults consult ``os.getenv`` so
    # the missing-context guard would silently use those values. Clear them
    # to exercise the truly-empty branch.
    for env_var in ("GITHUB_BASE_REF", "GITHUB_HEAD_REF", "GITHUB_EVENT_NAME"):
        monkeypatch.delenv(env_var, raising=False)

    monkeypatch.setattr(
        sys,
        "argv",
        ["release-version-guard", "--event-name", "pull_request", "--head-ref", "release/v0.5.0"],
    )

    exit_code = release_version_guard.main()

    assert exit_code == 1
