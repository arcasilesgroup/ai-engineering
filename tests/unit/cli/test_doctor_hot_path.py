"""Tests for `ai-eng doctor --check hot-path` (spec-114 T-2.7..T-2.8).

The hot-path subcommand reads the rolling window of `ide_hook` events
from `.ai-engineering/state/framework-events.ndjson`, groups by
`detail.hook_kind` (or `component`), computes p95 of `detail.duration_ms`,
and compares against the manifest budget.

Per D-114-03 the check is *advisory* through 2026-05-31 — violations
print a structured warning but exit 0 so flaky CI from a transient slow
run does not block PRs. Violations also append a `hot_path_violation`
event with `detail.bug_tag = "infra:slow-hook"`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer
import yaml
from typer.testing import CliRunner


def _make_event(
    *,
    component: str,
    hook_kind: str,
    duration_ms: int,
    outcome: str = "success",
    timestamp: str = "2026-04-29T00:00:00Z",
) -> dict:
    """Shape an `ide_hook` heartbeat as written by run_hook_safe."""
    return {
        "kind": "ide_hook",
        "engine": "claude_code",
        "timestamp": timestamp,
        "component": component,
        "outcome": outcome,
        "correlationId": f"corr-{component}-{duration_ms}",
        "schemaVersion": "1.0",
        "project": "test-114",
        "source": "hook",
        "detail": {
            "hook_kind": hook_kind,
            "outcome": outcome,
            "duration_ms": duration_ms,
        },
    }


def _seed_ndjson(project_root: Path, events: list[dict]) -> None:
    state_dir = project_root / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / "framework-events.ndjson"
    path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")


def _seed_manifest(project_root: Path, slos: dict | None = None) -> None:
    """Drop a minimal manifest carrying hot_path_slos for the doctor to read."""
    ai_dir = project_root / ".ai-engineering"
    ai_dir.mkdir(parents=True, exist_ok=True)
    body: dict = {
        "schema_version": "2.0",
        "name": "test-114",
        "providers": {"vcs": "github", "ides": ["terminal"], "stacks": ["python"]},
    }
    if slos is not None:
        body["hot_path_slos"] = slos
    (ai_dir / "manifest.yml").write_text(yaml.safe_dump(body), encoding="utf-8")


@pytest.fixture()
def app() -> typer.Typer:
    from ai_engineering.cli_factory import create_app

    return create_app()


# ---------------------------------------------------------------------------
# T-2.7 RED — doctor --check hot-path reads NDJSON and computes p95
# ---------------------------------------------------------------------------


class TestDoctorCheckHotPath:
    def test_doctor_check_hot_path_reads_ndjson(self, app: typer.Typer, tmp_path: Path) -> None:
        """100 fast events, p95 ≈ fast → PASS, exit 0, structured table on stdout."""
        _seed_manifest(tmp_path)
        events = [
            _make_event(component=f"hook.test-{i % 5}", hook_kind="pre-commit", duration_ms=50 + i)
            for i in range(100)
        ]
        _seed_ndjson(tmp_path, events)

        result = CliRunner().invoke(app, ["doctor", "--check", "hot-path", str(tmp_path)])

        assert result.exit_code == 0, result.output
        # Structured table headers must appear so operators can grep output.
        for header in ("hook", "p95_ms", "budget_ms", "status"):
            assert header in result.output, f"missing column header {header}: {result.output}"
        # All 5 components must appear in the table.
        for i in range(5):
            assert f"hook.test-{i}" in result.output

    def test_violation_emits_hot_path_violation_event(
        self, app: typer.Typer, tmp_path: Path
    ) -> None:
        """When p95 exceeds the budget a hot_path_violation event is appended."""
        _seed_manifest(tmp_path, slos={"pre_commit_p95_ms": 100, "rolling_window_events": 50})
        # 50 slow events, p95 = ~5000 ms, budget = 100 ms → violation.
        events = [
            _make_event(component="hook.slow", hook_kind="pre-commit", duration_ms=4900 + i)
            for i in range(50)
        ]
        _seed_ndjson(tmp_path, events)

        result = CliRunner().invoke(app, ["doctor", "--check", "hot-path", str(tmp_path)])

        # Advisory: still exit 0 per D-114-03.
        assert result.exit_code == 0, result.output

        ndjson = (tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson").read_text(
            encoding="utf-8"
        )
        violations = [
            json.loads(line)
            for line in ndjson.splitlines()
            if line and json.loads(line).get("kind") == "hot_path_violation"
        ]
        assert violations, "violation must produce hot_path_violation event"
        violation = violations[-1]
        assert violation["detail"].get("bug_tag") == "infra:slow-hook"
        assert violation["detail"].get("hook") == "hook.slow"
        assert violation["detail"].get("budget_ms") == 100
        assert violation["detail"].get("observed_p95_ms") >= 4900

    def test_no_events_reports_clean(self, app: typer.Typer, tmp_path: Path) -> None:
        """Empty NDJSON → doctor reports nothing to evaluate, exit 0."""
        _seed_manifest(tmp_path)
        # Don't seed an NDJSON; the file simply does not exist.

        result = CliRunner().invoke(app, ["doctor", "--check", "hot-path", str(tmp_path)])

        assert result.exit_code == 0
        # Output should mention there is no data — operators must not see a
        # blank table.
        assert "no" in result.output.lower() or "0 events" in result.output.lower()

    def test_p95_ignores_non_ide_hook_events(self, app: typer.Typer, tmp_path: Path) -> None:
        """skill_invoked / framework_error events are not part of p95."""
        _seed_manifest(tmp_path)
        events = [
            _make_event(component="hook.x", hook_kind="pre-commit", duration_ms=10)
            for _ in range(10)
        ]
        # Add 10 unrelated events with high duration_ms but kind != ide_hook.
        for _ in range(10):
            events.append(
                {
                    "kind": "skill_invoked",
                    "engine": "claude_code",
                    "timestamp": "2026-04-29T00:00:00Z",
                    "component": "hook.skills",
                    "outcome": "success",
                    "correlationId": "x",
                    "schemaVersion": "1.0",
                    "project": "test-114",
                    "detail": {"skill": "ai-test", "duration_ms": 9999},
                }
            )
        _seed_ndjson(tmp_path, events)

        result = CliRunner().invoke(app, ["doctor", "--check", "hot-path", str(tmp_path)])
        assert result.exit_code == 0
        # The skill_invoked component must not appear because it is not an ide_hook.
        assert "hook.skills" not in result.output
