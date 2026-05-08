"""Focused HX-04 T-4.1 tests for adapter-owned sequencing rules."""

from __future__ import annotations

import contextlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

import ai_engineering.cli_commands.gate as gate_module
import ai_engineering.cli_commands.sync as sync_module
import ai_engineering.cli_commands.validate as validate_module
import ai_engineering.cli_commands.verify_cmd as verify_cmd_module
import ai_engineering.state.observability as observability_module
from ai_engineering.state.models import FrameworkEvent, GateFindingsDocument


def _lock_spy(calls: list[tuple[Path, str]]):
    @contextlib.contextmanager
    def _spy(project_root: Path, artifact_name: str):
        calls.append((project_root, artifact_name))
        yield project_root / ".ai-engineering" / "state" / "locks" / f"{artifact_name}.lock"

    return _spy


def _gate_document() -> GateFindingsDocument:
    return GateFindingsDocument.model_validate(
        {
            "schema": "ai-engineering/gate-findings/v1",
            "session_id": str(uuid.uuid4()),
            "produced_by": "ai-commit",
            "produced_at": datetime.now(UTC).isoformat(),
            "branch": "feature/hx04",
            "commit_sha": "0" * 40,
            "findings": [],
            "auto_fixed": [],
            "cache_hits": [],
            "cache_misses": [],
            "wall_clock_ms": {"wave1_fixers": 10, "wave2_checkers": 20, "total": 30},
        }
    )


def test_sync_uses_mirror_lock(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script = tmp_path / "scripts" / "sync_command_mirrors.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("print('ok')\n", encoding="utf-8")

    calls: list[tuple[Path, str]] = []
    monkeypatch.setattr(sync_module, "artifact_lock", _lock_spy(calls))
    monkeypatch.setattr(sync_module, "resolve_project_root", lambda _target: tmp_path)
    monkeypatch.setattr(sync_module, "is_json_mode", lambda: False)
    monkeypatch.setattr(sync_module, "spinner", lambda _action: contextlib.nullcontext())
    monkeypatch.setattr(
        sync_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )
    monkeypatch.setattr(sync_module, "result_header", lambda *args: None)
    monkeypatch.setattr(sync_module, "status_line", lambda *args: None)

    sync_module.sync_cmd(check=True)

    assert calls == [(tmp_path, "mirror-sync")]


def test_validate_all_categories_uses_mirror_lock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[Path, str]] = []
    monkeypatch.setattr(validate_module, "artifact_lock", _lock_spy(calls))
    monkeypatch.setattr(validate_module, "spinner", lambda _action: contextlib.nullcontext())

    report = SimpleNamespace(
        passed=True,
        to_dict=lambda: {"passed": True},
        by_category=lambda: {},
        category_passed=lambda _cat: True,
    )
    monkeypatch.setattr(
        validate_module, "validate_content_integrity", lambda *_args, **_kwargs: report
    )

    validate_module.validate_cmd(target=tmp_path, output_json=True)

    assert calls == [(tmp_path, "mirror-sync")]


def test_validate_non_mirror_category_skips_mirror_lock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[Path, str]] = []
    monkeypatch.setattr(validate_module, "artifact_lock", _lock_spy(calls))
    monkeypatch.setattr(validate_module, "spinner", lambda _action: contextlib.nullcontext())

    report = SimpleNamespace(
        passed=True,
        to_dict=lambda: {"passed": True},
        by_category=lambda: {},
        category_passed=lambda _cat: True,
    )
    monkeypatch.setattr(
        validate_module, "validate_content_integrity", lambda *_args, **_kwargs: report
    )

    validate_module.validate_cmd(target=tmp_path, category="file-existence", output_json=True)

    assert calls == []


def test_verify_governance_uses_mirror_lock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[Path, str]] = []
    monkeypatch.setattr(verify_cmd_module, "artifact_lock", _lock_spy(calls))
    monkeypatch.setattr(verify_cmd_module, "spinner", lambda _action: contextlib.nullcontext())

    result = SimpleNamespace(
        profile="normal",
        score=100,
        verdict=SimpleNamespace(value="PASS"),
        summary=lambda: {},
        specialists=[],
        findings=[],
        findings_for_specialist=lambda _name: [],
    )
    monkeypatch.setitem(verify_cmd_module.MODES, "governance", lambda *_args, **_kwargs: result)

    verify_cmd_module.verify_cmd("governance", target=tmp_path, output_json=True)

    assert calls == [(tmp_path, "mirror-sync")]


def test_append_framework_event_uses_framework_events_lock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[Path, str]] = []
    monkeypatch.setattr(observability_module, "artifact_lock", _lock_spy(calls))

    entry = FrameworkEvent(
        project="demo-project",
        engine="github_copilot",
        kind="skill_invoked",
        outcome="success",
        component="hook.skill",
        correlationId="corr-1",
        detail={"skill": "ai-dispatch"},
    )

    observability_module.append_framework_event(tmp_path, entry)

    assert calls == [(tmp_path, "framework-events")]
    payload = json.loads(
        (tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson").read_text(
            encoding="utf-8"
        )
    )
    assert payload["kind"] == "skill_invoked"


def test_gate_findings_persist_uses_gate_findings_lock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[Path, str]] = []
    monkeypatch.setattr(gate_module.orchestrator_module, "artifact_lock", _lock_spy(calls))

    output_path = gate_module._persist_gate_findings(_gate_document(), tmp_path)

    assert calls == [(tmp_path, "gate-findings")]
    assert output_path == tmp_path / ".ai-engineering" / "state" / "gate-findings.json"
    assert output_path.exists()
