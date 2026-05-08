"""RED tests for HX-04 T-4.2 publish-path and residual-output hardening."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import ai_engineering.cli_commands.gate as gate_module
import ai_engineering.policy.watch_residuals as watch_residuals_module
from ai_engineering.state.models import GateFindingsDocument, GateProducedBy


def _make_document(
    *,
    produced_by: str = "ai-pr",
    cache_hits: list[str] | None = None,
    cache_misses: list[str] | None = None,
) -> GateFindingsDocument:
    payload: dict[str, Any] = {
        "schema": "ai-engineering/gate-findings/v1",
        "session_id": str(uuid.uuid4()),
        "produced_by": produced_by,
        "produced_at": datetime.now(UTC).isoformat(),
        "branch": "feature/hx04",
        "commit_sha": "0" * 40,
        "findings": [],
        "auto_fixed": [],
        "cache_hits": cache_hits if cache_hits is not None else ["gitleaks"],
        "cache_misses": cache_misses if cache_misses is not None else ["ruff-check"],
        "wall_clock_ms": {"wave1_fixers": 10, "wave2_checkers": 20, "total": 30},
    }
    return GateFindingsDocument.model_validate(payload)


def _failed_check(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "check": "ruff",
        "rule_id": "E501",
        "file": "src/example.py",
        "line": 12,
        "column": 1,
        "severity": "medium",
        "message": "line too long",
        "auto_fixable": False,
        "auto_fix_command": None,
    }
    payload.update(overrides)
    return payload


def test_publish_gate_document_defaults_to_gate_findings_and_preserves_cache_metadata(
    tmp_path: Path,
) -> None:
    from ai_engineering.policy.orchestrator import publish_gate_document

    document = _make_document(cache_hits=["ty"], cache_misses=["validate"])

    output_path = publish_gate_document(document, tmp_path)

    assert output_path == tmp_path / ".ai-engineering" / "state" / "gate-findings.json"
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["cache_hits"] == ["ty"]
    assert payload["cache_misses"] == ["validate"]


def test_publish_gate_document_supports_residual_output_name(tmp_path: Path) -> None:
    from ai_engineering.policy.orchestrator import publish_gate_document

    document = _make_document(produced_by="watch-loop", cache_hits=[], cache_misses=[])

    output_path = publish_gate_document(document, tmp_path, output_name="watch-residuals.json")

    assert output_path == tmp_path / ".ai-engineering" / "state" / "watch-residuals.json"
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["produced_by"] == "watch-loop"


def test_gate_cli_persist_delegates_to_shared_publish_helper(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[GateFindingsDocument, Path, str]] = []

    def fake_publish(
        document: GateFindingsDocument,
        project_root: Path,
        *,
        output_name: str = "gate-findings.json",
    ) -> Path:
        calls.append((document, project_root, output_name))
        return project_root / ".ai-engineering" / "state" / output_name

    monkeypatch.setattr(
        gate_module.orchestrator_module, "publish_gate_document", fake_publish, raising=False
    )

    document = _make_document()
    output_path = gate_module._persist_gate_findings(document, tmp_path)

    assert output_path == tmp_path / ".ai-engineering" / "state" / "gate-findings.json"
    assert calls == [(document, tmp_path, "gate-findings.json")]


def test_watch_residuals_emit_delegates_to_shared_publish_helper(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[GateFindingsDocument, Path, str]] = []

    def fake_publish(
        document: GateFindingsDocument,
        project_root: Path,
        *,
        output_name: str = "gate-findings.json",
    ) -> Path:
        calls.append((document, project_root, output_name))
        return project_root / ".ai-engineering" / "state" / output_name

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(watch_residuals_module, "_git_branch", lambda: "feature/hx04")
    monkeypatch.setattr(watch_residuals_module, "_git_sha", lambda: "1" * 40)
    monkeypatch.setattr(
        watch_residuals_module.orchestrator_module,
        "publish_gate_document",
        fake_publish,
        raising=False,
    )

    output_path = watch_residuals_module.emit([_failed_check()])

    assert output_path == tmp_path / ".ai-engineering" / "state" / "watch-residuals.json"
    assert len(calls) == 1
    document, project_root, output_name = calls[0]
    assert project_root == tmp_path
    assert output_name == "watch-residuals.json"
    assert document.produced_by is GateProducedBy.WATCH_LOOP
