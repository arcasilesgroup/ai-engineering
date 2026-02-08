"""Unit tests for git cleanup workflow."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.git import cleanup


class _Proc:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode
        self.stdout = ""
        self.stderr = ""


def test_git_cleanup_dry_run_reports_candidates(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    state = tmp_path / ".ai-engineering" / "state"
    state.mkdir(parents=True)
    (state / "audit-log.ndjson").write_text("", encoding="utf-8")

    monkeypatch.setattr(cleanup, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(cleanup, "current_branch", lambda _root: "feature/x")
    monkeypatch.setattr(cleanup, "_default_branch", lambda _root: "main")
    monkeypatch.setattr(cleanup, "_local_merged", lambda _r, _d, _c: ["feature/old"])
    monkeypatch.setattr(cleanup, "_local_gone", lambda _r, _d, _c: ["feature/gone"])
    monkeypatch.setattr(cleanup, "_remote_merged", lambda _r, _d: ["feature/remote"])
    monkeypatch.setattr(cleanup, "_run", lambda _r, _a: _Proc())

    payload = cleanup.run_git_cleanup(apply=False, include_remote=True, checkout_default=True)

    assert payload["apply"] is False
    assert payload["candidates"]["localTotal"] == ["feature/gone", "feature/old"]
    assert payload["candidates"]["remoteMerged"] == ["feature/remote"]
    assert payload["deleted"]["local"] == []


def test_git_cleanup_apply_executes_deletions(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    state = tmp_path / ".ai-engineering" / "state"
    state.mkdir(parents=True)
    (state / "audit-log.ndjson").write_text("", encoding="utf-8")

    monkeypatch.setattr(cleanup, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(cleanup, "current_branch", lambda _root: "feature/x")
    monkeypatch.setattr(cleanup, "_default_branch", lambda _root: "main")
    monkeypatch.setattr(cleanup, "_local_merged", lambda _r, _d, _c: ["feature/old"])
    monkeypatch.setattr(cleanup, "_local_gone", lambda _r, _d, _c: [])
    monkeypatch.setattr(cleanup, "_remote_merged", lambda _r, _d: ["feature/remote"])
    monkeypatch.setattr(cleanup, "_run", lambda _r, _a: _Proc())
    monkeypatch.setattr(cleanup, "_delete_local", lambda _r, _b: (["feature/old"], []))
    monkeypatch.setattr(cleanup, "_delete_remote", lambda _r, _b: (["feature/remote"], []))

    payload = cleanup.run_git_cleanup(apply=True, include_remote=True, checkout_default=True)

    assert payload["deleted"]["local"] == ["feature/old"]
    assert payload["deleted"]["remote"] == ["feature/remote"]
