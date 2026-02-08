"""Unit tests for maintenance report generation."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.maintenance.report import create_pr_from_payload, generate_report


def test_generate_report_creates_local_report(temp_repo: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    (temp_repo / ".git").mkdir()
    (temp_repo / ".ai-engineering" / "context" / "delivery").mkdir(parents=True)
    (temp_repo / ".ai-engineering" / "context" / "delivery" / "planning.md").write_text(
        "# Planning\n", encoding="utf-8"
    )
    (temp_repo / ".ai-engineering" / "state").mkdir(parents=True)

    monkeypatch.setattr("ai_engineering.maintenance.report.repo_root", lambda: temp_repo)

    payload = generate_report(approve_pr=False)

    assert payload["approved"] is False
    report_path = Path(str(payload["reportPath"]))
    assert report_path.exists()


def test_generate_report_writes_pr_payload_when_approved(temp_repo: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    (temp_repo / ".git").mkdir()
    (temp_repo / ".ai-engineering" / "context" / "product").mkdir(parents=True)
    (temp_repo / ".ai-engineering" / "context" / "product" / "vision.md").write_text(
        "# Vision\n", encoding="utf-8"
    )
    (temp_repo / ".ai-engineering" / "state").mkdir(parents=True)

    monkeypatch.setattr("ai_engineering.maintenance.report.repo_root", lambda: temp_repo)

    payload = generate_report(approve_pr=True)

    assert payload["approved"] is True
    pr_payload = Path(str(payload["payloadPath"]))
    assert pr_payload.exists()


def test_create_pr_from_payload_requires_approval(temp_repo: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    (temp_repo / ".git").mkdir()
    state = temp_repo / ".ai-engineering" / "state"
    state.mkdir(parents=True)
    (state / "maintenance_pr_payload.json").write_text(
        '{"approved": false, "title": "x", "body": "y", "base": "main", "head": "feature/x"}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("ai_engineering.maintenance.report.repo_root", lambda: temp_repo)

    ok, message = create_pr_from_payload()

    assert not ok
    assert "not approved" in message


def test_create_pr_from_payload_invokes_gh_when_approved(temp_repo: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    (temp_repo / ".git").mkdir()
    state = temp_repo / ".ai-engineering" / "state"
    state.mkdir(parents=True)
    (state / "maintenance_pr_payload.json").write_text(
        '{"approved": true, "title": "x", "body": "y", "base": "main", "head": "feature/x"}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("ai_engineering.maintenance.report.repo_root", lambda: temp_repo)

    class Proc:
        returncode = 0
        stdout = "https://github.com/org/repo/pull/1"
        stderr = ""

    monkeypatch.setattr(
        "ai_engineering.maintenance.report.subprocess.run", lambda *args, **kwargs: Proc()
    )

    ok, message = create_pr_from_payload()

    assert ok
    assert "pull" in message
