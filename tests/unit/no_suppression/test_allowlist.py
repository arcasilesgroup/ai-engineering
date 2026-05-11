"""Allowlist loader + evaluator tests."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from no_suppression.allowlist import (
    AllowlistEntry,
    evaluate,
    load_allowlist,
)
from no_suppression.scanner import Finding


def _make_finding(path: str, rule_id: str, rule_target: str = "") -> Finding:
    return Finding(
        path=Path(path),
        line=1,
        column=1,
        rule_id=rule_id,
        rule_target=rule_target,
        snippet=f"# {rule_id}",
    )


class TestLoadAllowlist:
    def test_missing_file_returns_empty_list(self, tmp_path: Path) -> None:
        assert load_allowlist(tmp_path / "absent.yml") == []

    def test_loads_minimal_entry(self, tmp_path: Path) -> None:
        path = tmp_path / "allowlist.yml"
        path.write_text(
            "entries:\n"
            "  - path: src/foo.py\n"
            "    rule: '*'\n"
            "    pattern: noqa\n"
            "    justification: legacy\n"
            "    spec_ref: spec-128\n",
            encoding="utf-8",
        )
        entries = load_allowlist(path)
        assert len(entries) == 1
        assert entries[0].path_glob == "src/foo.py"
        assert entries[0].rule_id == "*"
        assert entries[0].pattern == "noqa"

    def test_rejects_missing_required_keys(self, tmp_path: Path) -> None:
        path = tmp_path / "allowlist.yml"
        path.write_text(
            "entries:\n  - path: src/foo.py\n    rule: '*'\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="missing required keys"):
            load_allowlist(path)

    def test_rejects_top_level_non_list(self, tmp_path: Path) -> None:
        path = tmp_path / "allowlist.yml"
        path.write_text("entries: not-a-list\n", encoding="utf-8")
        with pytest.raises(ValueError, match="must contain a top-level 'entries' list"):
            load_allowlist(path)


class TestEvaluate:
    def test_unallowed_finding_is_denied(self) -> None:
        decisions = evaluate([_make_finding("src/foo.py", "noqa")], [])
        assert decisions[0].status == "denied"
        assert decisions[0].matched_entry is None

    def test_matching_entry_allows_finding(self, tmp_path: Path) -> None:
        entry = AllowlistEntry(
            path_glob="src/foo.py",
            rule_id="*",
            pattern="noqa",
            justification="x",
            spec_ref="spec-128",
        )
        decisions = evaluate(
            [_make_finding("src/foo.py", "noqa", "E501")],
            [entry],
            state_db=tmp_path / "absent.db",
        )
        assert decisions[0].status == "allowed"
        assert decisions[0].matched_entry is entry

    def test_expired_entry_blocks(self, tmp_path: Path) -> None:
        past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        entry = AllowlistEntry(
            path_glob="src/foo.py",
            rule_id="*",
            pattern="noqa",
            justification="x",
            spec_ref="spec-128",
            expires_at=past,
        )
        decisions = evaluate(
            [_make_finding("src/foo.py", "noqa", "E501")],
            [entry],
            state_db=tmp_path / "absent.db",
        )
        assert decisions[0].status == "expired"

    def test_exact_rule_match_required_when_set(self, tmp_path: Path) -> None:
        entry = AllowlistEntry(
            path_glob="src/foo.py",
            rule_id="E501",
            pattern="noqa",
            justification="x",
            spec_ref="spec-128",
        )
        decisions = evaluate(
            [_make_finding("src/foo.py", "noqa", "F401")],
            [entry],
            state_db=tmp_path / "absent.db",
        )
        assert decisions[0].status == "denied"

    def test_dec_id_must_exist_in_state_db(self, tmp_path: Path) -> None:
        entry = AllowlistEntry(
            path_glob="src/foo.py",
            rule_id="*",
            pattern="noqa",
            justification="x",
            spec_ref="spec-128",
            dec_id="DEC-999",
        )
        decisions = evaluate(
            [_make_finding("src/foo.py", "noqa", "E501")],
            [entry],
            state_db=tmp_path / "absent.db",
        )
        assert decisions[0].status == "dec_missing"

    def test_dec_active_and_not_expired_allows(self, tmp_path: Path) -> None:
        db = tmp_path / "state.db"
        with sqlite3.connect(db) as conn:
            conn.execute(
                "CREATE TABLE risk_acceptances ("
                "risk_id TEXT PRIMARY KEY, category TEXT, status TEXT, "
                "severity TEXT, accepted_by TEXT, rationale TEXT, "
                "expires_at TEXT, created_at TEXT, updated_at TEXT)"
            )
            future = (datetime.now(UTC) + timedelta(days=30)).isoformat()
            conn.execute(
                "INSERT INTO risk_acceptances VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("DEC-001", "suppression", "active", "low", "ci", "r", future, "", ""),
            )
            conn.commit()
        entry = AllowlistEntry(
            path_glob="src/foo.py",
            rule_id="*",
            pattern="noqa",
            justification="x",
            spec_ref="spec-128",
            dec_id="DEC-001",
        )
        decisions = evaluate(
            [_make_finding("src/foo.py", "noqa", "E501")],
            [entry],
            state_db=db,
        )
        assert decisions[0].status == "allowed"

    def test_dec_revoked_blocks(self, tmp_path: Path) -> None:
        db = tmp_path / "state.db"
        with sqlite3.connect(db) as conn:
            conn.execute(
                "CREATE TABLE risk_acceptances ("
                "risk_id TEXT PRIMARY KEY, category TEXT, status TEXT, "
                "severity TEXT, accepted_by TEXT, rationale TEXT, "
                "expires_at TEXT, created_at TEXT, updated_at TEXT)"
            )
            future = (datetime.now(UTC) + timedelta(days=30)).isoformat()
            conn.execute(
                "INSERT INTO risk_acceptances VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("DEC-002", "suppression", "revoked", "low", "ci", "r", future, "", ""),
            )
            conn.commit()
        entry = AllowlistEntry(
            path_glob="src/foo.py",
            rule_id="*",
            pattern="noqa",
            justification="x",
            spec_ref="spec-128",
            dec_id="DEC-002",
        )
        decisions = evaluate(
            [_make_finding("src/foo.py", "noqa", "E501")],
            [entry],
            state_db=db,
        )
        assert decisions[0].status == "dec_missing"
