"""Ownership-map read helpers for ``state.db``.

Spec-146 pins the read side that ``ai-eng update`` uses after the JSON
sidecar was retired: diagnostics can inspect raw SQLite rows while the
updater gets an ``OwnershipMap`` view with enum semantics preserved.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.state.models import FrameworkUpdatePolicy, OwnershipLevel
from ai_engineering.state.state_db import (
    list_ownership_rows,
    load_ownership_map,
    upsert_ownership_rows_raw,
)


def test_list_ownership_rows_decodes_json_columns(tmp_path: Path) -> None:
    upsert_ownership_rows_raw(
        tmp_path,
        [
            {
                "path_pattern": ".ai-engineering/team/**",
                "owners": ["team-managed"],
                "severity": "deny",
                "reviewers": ["security", "platform"],
            },
            {
                "path_pattern": ".codex/**",
                "owners": ["framework-managed"],
                "severity": "allow",
                "reviewers": [],
            },
        ],
    )

    rows = list_ownership_rows(tmp_path)

    assert [row["path_pattern"] for row in rows] == [
        ".ai-engineering/team/**",
        ".codex/**",
    ]
    assert rows[0]["owners"] == ["team-managed"]
    assert rows[0]["reviewers"] == ["security", "platform"]
    assert rows[0]["severity"] == "deny"
    assert isinstance(rows[0]["updated_at"], str)
    assert "owners_json" not in rows[0]
    assert "reviewers_json" not in rows[0]


def test_list_ownership_rows_returns_empty_for_missing_db(tmp_path: Path) -> None:
    assert list_ownership_rows(tmp_path) == []


def test_load_ownership_map_reconstructs_updater_model(tmp_path: Path) -> None:
    upsert_ownership_rows_raw(
        tmp_path,
        [
            {
                "path_pattern": ".ai-engineering/manifest.yml",
                "owners": ["team-managed"],
                "severity": "deny",
                "reviewers": [],
            },
            {
                "path_pattern": ".ai-engineering/LESSONS.md",
                "owners": ["team-managed"],
                "severity": "append-only",
                "reviewers": [],
            },
            {
                "path_pattern": ".codex/**",
                "owners": ["framework-managed"],
                "severity": "allow",
                "reviewers": [],
            },
            {
                "path_pattern": ".ai-engineering/state/framework-events.ndjson",
                "owners": ["system-managed"],
                "severity": "append-only",
                "reviewers": [],
            },
        ],
    )

    ownership = load_ownership_map(tmp_path)

    assert [entry.pattern for entry in ownership.paths] == [
        ".ai-engineering/manifest.yml",
        ".ai-engineering/LESSONS.md",
        ".codex/**",
        ".ai-engineering/state/framework-events.ndjson",
    ]
    by_pattern = {entry.pattern: entry for entry in ownership.paths}
    assert by_pattern[".ai-engineering/manifest.yml"].owner is OwnershipLevel.TEAM_MANAGED
    assert by_pattern[".ai-engineering/manifest.yml"].framework_update is FrameworkUpdatePolicy.DENY
    assert (
        by_pattern[".ai-engineering/LESSONS.md"].framework_update
        is FrameworkUpdatePolicy.APPEND_ONLY
    )
    assert by_pattern[".codex/**"].owner is OwnershipLevel.FRAMEWORK_MANAGED
    assert by_pattern[".codex/**"].framework_update is FrameworkUpdatePolicy.ALLOW
    assert by_pattern[".ai-engineering/state/framework-events.ndjson"].owner is (
        OwnershipLevel.SYSTEM_MANAGED
    )


def test_load_ownership_map_returns_empty_model_without_rows(tmp_path: Path) -> None:
    assert load_ownership_map(tmp_path).paths == []
