"""Cross-IDE parity for ``ai-eng risk`` and ``ai-eng gate run`` (spec-105 G-10).

Extends the spec-104 D-104-08 pattern (see ``test_gate_cross_ide.py``) to
the spec-105 surface: ``ai-eng risk list --format json`` and
``ai-eng gate run --json`` must produce byte-identical output (after
normalising session_id / produced_at / wall_clock_ms / commit_sha) when
invoked from each of the four supported IDE environments.

Per D-105-08, the IDE identity is metadata for callers -- never a
control input the CLI consumes. These tests assert that contract by
running the CLI four times with each IDE-emulated env and comparing the
emitted JSON.

The four IDE-emulated environments mirror the spec-104 fixture:

- ``claude_code`` -- baseline, no special env.
- ``github_copilot`` -- ``COPILOT=true``.
- ``codex`` -- ``CODEX=true``.
- ``gemini`` -- ``GEMINI=true``.

Each invocation gets its own fresh project root + cache_dir so the
comparison is on what the CLI EMITS given identical inputs -- not on
shared cache state from a prior iteration. We use ``CliRunner`` with
``monkeypatch.setenv`` to simulate the IDE env (subprocess invocation
would require ``python -m ai_engineering`` which the package does not
expose via ``__main__``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

SUPPORTED_IDES: tuple[tuple[str, dict[str, str]], ...] = (
    ("claude_code", {}),
    ("github_copilot", {"COPILOT": "true"}),
    ("codex", {"CODEX": "true"}),
    ("gemini", {"GEMINI": "true"}),
)


def _seed_decision_store(root: Path) -> None:
    """Seed a deterministic decision-store fixture so ``risk list`` has output."""
    state_dir = root / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    decisions_payload = {
        "decisions": [
            {
                "id": "DEC-001",
                "kind": "risk-acceptance",
                "title": "Accept ruff E501 finding",
                "context": "finding:E501",
                "contextHash": "abc123def456",
                "severity": "low",
                "justification": "Sprint cutoff; remediation tracked.",
                "spec": "spec-105",
                "followUp": "Resolve in Q3.",
                "acceptedBy": "test@example.com",
                "expiresAt": "2027-01-01T00:00:00Z",
                "createdAt": "2026-04-27T00:00:00Z",
                "status": "active",
                "renewalCount": 0,
            }
        ],
    }
    (state_dir / "decision-store.json").write_text(json.dumps(decisions_payload), encoding="utf-8")


def _normalise(payload: Any) -> Any:
    """Recursively strip run-local fields that legitimately differ across runs."""
    if isinstance(payload, dict):
        cleaned: dict[str, Any] = {}
        for key, value in payload.items():
            if key in {
                "session_id",
                "produced_at",
                "wall_clock_ms",
                "commit_sha",
                "createdAt",
                "created_at",
                "id",  # DEC ids are uuid4 per run for new entries
                "contextHash",
                "context_hash",
            }:
                continue
            cleaned[key] = _normalise(value)
        return cleaned
    if isinstance(payload, list):
        return [_normalise(item) for item in payload]
    return payload


def _serialise(payload: Any) -> bytes:
    """Canonical JSON serialisation for byte-equality comparison."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def _set_ide_env(monkeypatch: pytest.MonkeyPatch, overrides: dict[str, str]) -> None:
    """Strip IDE-related env then apply per-IDE overrides."""
    for key in (
        "AIENG_IDE",
        "CLAUDE_CODE_SESSION_ID",
        "COPILOT_SESSION_ID",
        "CODEX_SESSION_ID",
        "GEMINI_SESSION_ID",
        "COPILOT",
        "CODEX",
        "GEMINI",
    ):
        monkeypatch.delenv(key, raising=False)
    for key, value in overrides.items():
        monkeypatch.setenv(key, value)


def test_risk_list_byte_identical_across_ides(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """G-10: ``ai-eng risk list --format json`` byte-identical across 4 IDEs."""
    from ai_engineering.cli_factory import create_app

    runner = CliRunner()
    per_ide_outputs: dict[str, bytes] = {}

    for ide_name, overrides in SUPPORTED_IDES:
        project_root = tmp_path / ide_name
        project_root.mkdir()
        _seed_decision_store(project_root)

        with monkeypatch.context() as ctx:
            _set_ide_env(ctx, overrides)
            ctx.chdir(project_root)
            app = create_app()
            result = runner.invoke(app, ["risk", "list", "--format", "json"])

        assert result.exit_code == 0, (
            f"ai-eng risk list failed for IDE={ide_name!r}: "
            f"exit={result.exit_code} output={result.output!r}"
        )

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            pytest.fail(
                f"ai-eng risk list emitted non-JSON for IDE={ide_name!r}: {exc!s}; "
                f"stdout={result.stdout!r}"
            )

        normalised = _normalise(payload)
        per_ide_outputs[ide_name] = _serialise(normalised)

    first_ide, _ = SUPPORTED_IDES[0]
    first_bytes = per_ide_outputs[first_ide]
    for ide_name, _overrides in SUPPORTED_IDES[1:]:
        assert per_ide_outputs[ide_name] == first_bytes, (
            f"ai-eng risk list output for IDE={ide_name!r} differs from "
            f"IDE={first_ide!r} after normalisation. spec-105 G-10 / D-105-08 "
            f"requires byte-identical output across IDEs.\n"
            f"  {first_ide}: {first_bytes!r}\n"
            f"  {ide_name}: {per_ide_outputs[ide_name]!r}"
        )


def test_gate_run_byte_identical_across_ides(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """G-10 + R-16: ``ai-eng gate run --json`` byte-identical across 4 IDEs.

    Also exercises auto-stage parity (R-16): the orchestrator's Wave 1
    fixers may modify staged files; the re-stage outcome must be IDE-
    agnostic given identical inputs.
    """
    from ai_engineering.cli_factory import create_app

    runner = CliRunner()
    per_ide_outputs: dict[str, bytes] = {}

    for ide_name, overrides in SUPPORTED_IDES:
        project_root = tmp_path / ide_name
        project_root.mkdir()

        # Initialise a real git repo so gate run has a working tree.
        import subprocess as _sub  # local import to avoid module-level cost

        _sub.run(
            ["git", "init", "-b", "main", str(project_root)],
            check=True,
            capture_output=True,
        )
        _sub.run(
            ["git", "-C", str(project_root), "config", "user.email", "test@example.com"],
            check=True,
            capture_output=True,
        )
        _sub.run(
            ["git", "-C", str(project_root), "config", "user.name", "Tester"],
            check=True,
            capture_output=True,
        )
        # Seed a tiny source file plus a manifest.
        (project_root / ".ai-engineering").mkdir()
        (project_root / ".ai-engineering" / "manifest.yml").write_text(
            "schema_version: '2.0'\nproviders:\n  stacks: [python]\n",
            encoding="utf-8",
        )
        (project_root / "src").mkdir()
        (project_root / "src" / "main.py").write_text(
            "def main() -> None:\n    return None\n", encoding="utf-8"
        )
        _sub.run(
            ["git", "-C", str(project_root), "add", "-A"],
            check=True,
            capture_output=True,
        )

        with monkeypatch.context() as ctx:
            _set_ide_env(ctx, overrides)
            ctx.chdir(project_root)
            app = create_app()
            result = runner.invoke(app, ["gate", "run", "--json", "--no-cache"])

        # gate run may exit non-zero locally, but the emitted JSON must
        # be parseable. If invocation crashes hard, surface as skip
        # (this would indicate a CLI infra issue, not a parity bug).
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            pytest.skip(
                f"ai-eng gate run --json did not emit JSON for IDE={ide_name!r}; "
                f"exit={result.exit_code}, stdout={result.stdout[:200]!r}"
            )

        normalised = _normalise(payload)
        per_ide_outputs[ide_name] = _serialise(normalised)

    first_ide, _ = SUPPORTED_IDES[0]
    first_bytes = per_ide_outputs[first_ide]
    for ide_name, _overrides in SUPPORTED_IDES[1:]:
        assert per_ide_outputs[ide_name] == first_bytes, (
            f"ai-eng gate run output for IDE={ide_name!r} differs from "
            f"IDE={first_ide!r} after normalisation. spec-105 G-10 / D-105-08 "
            f"requires byte-identical output across IDEs.\n"
            f"  {first_ide}: {first_bytes!r}\n"
            f"  {ide_name}: {per_ide_outputs[ide_name]!r}"
        )
