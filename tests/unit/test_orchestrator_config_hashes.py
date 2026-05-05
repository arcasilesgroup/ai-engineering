from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from ai_engineering.policy.orchestrator import _config_hashes_for


def test_spec_verify_hashes_use_resolved_work_plane_paths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    legacy_specs_dir = tmp_path / ".ai-engineering" / "specs"
    legacy_specs_dir.mkdir(parents=True)
    (legacy_specs_dir / "spec.md").write_text("legacy-spec", encoding="utf-8")
    (legacy_specs_dir / "plan.md").write_text("legacy-plan", encoding="utf-8")
    pointer_payload = json.dumps({"specsDir": "resolved-work-plane"})
    (legacy_specs_dir / "active-work-plane.json").write_text(pointer_payload, encoding="utf-8")

    resolved_dir = tmp_path / "resolved-work-plane"
    resolved_dir.mkdir()
    resolved_spec = resolved_dir / "spec.md"
    resolved_plan = resolved_dir / "plan.md"
    resolved_spec.write_text("resolved-spec", encoding="utf-8")
    resolved_plan.write_text("resolved-plan", encoding="utf-8")

    monkeypatch.setattr(
        "ai_engineering.policy.orchestrator.resolve_active_work_plane",
        lambda _root: SimpleNamespace(spec_path=resolved_spec, plan_path=resolved_plan),
    )

    result = _config_hashes_for("spec-verify", tmp_path)

    assert result == {
        ".ai-engineering/specs/spec.md": hashlib.sha256(b"resolved-spec").hexdigest(),
        ".ai-engineering/specs/plan.md": hashlib.sha256(b"resolved-plan").hexdigest(),
        ".ai-engineering/specs/active-work-plane.json": hashlib.sha256(
            pointer_payload.encode("utf-8")
        ).hexdigest(),
    }


def test_validate_hashes_use_resolved_work_plane_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    # Spec-123: dropped task-ledger.json + current-summary.md +
    # history-summary.md + handoffs/ + evidence/. Canonical three-file
    # contract is spec.md, plan.md, _history.md.
    ai_dir = tmp_path / ".ai-engineering"
    legacy_specs_dir = ai_dir / "specs"
    legacy_specs_dir.mkdir(parents=True)
    (ai_dir / "manifest.yml").write_text("name: test\n", encoding="utf-8")
    pointer_payload = json.dumps({"specsDir": "resolved-work-plane"})
    (legacy_specs_dir / "active-work-plane.json").write_text(pointer_payload, encoding="utf-8")

    resolved_dir = tmp_path / "resolved-work-plane"
    resolved_dir.mkdir()
    resolved_spec = resolved_dir / "spec.md"
    resolved_plan = resolved_dir / "plan.md"
    resolved_history = resolved_dir / "_history.md"

    resolved_spec.write_text("resolved-spec", encoding="utf-8")
    resolved_plan.write_text("resolved-plan", encoding="utf-8")
    resolved_history.write_text("resolved-history", encoding="utf-8")

    monkeypatch.setattr(
        "ai_engineering.policy.orchestrator.resolve_active_work_plane",
        lambda _root: SimpleNamespace(
            spec_path=resolved_spec,
            plan_path=resolved_plan,
            history_path=resolved_history,
        ),
    )

    result = _config_hashes_for("validate", tmp_path)

    assert result == {
        ".ai-engineering/manifest.yml": hashlib.sha256(b"name: test\n").hexdigest(),
        ".ai-engineering/specs/spec.md": hashlib.sha256(b"resolved-spec").hexdigest(),
        ".ai-engineering/specs/plan.md": hashlib.sha256(b"resolved-plan").hexdigest(),
        ".ai-engineering/specs/_history.md": hashlib.sha256(b"resolved-history").hexdigest(),
        ".ai-engineering/specs/active-work-plane.json": hashlib.sha256(
            pointer_payload.encode("utf-8")
        ).hexdigest(),
    }
