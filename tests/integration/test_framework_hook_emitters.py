"""Integration tests for canonical hook emitters across Claude and Copilot."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from ai_engineering.state.io import read_ndjson_entries
from ai_engineering.state.models import FrameworkEvent, InstinctObservation

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_ROOT = REPO_ROOT / ".ai-engineering" / "scripts" / "hooks"


def _prepare_project(tmp_path: Path) -> Path:
    hooks_dir = tmp_path / ".ai-engineering" / "scripts" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(HOOKS_ROOT / "_lib", hooks_dir / "_lib")

    for script_name in (
        "telemetry-skill.py",
        "observe.py",
        "instinct-observe.py",
        "instinct-extract.py",
        "copilot-adapter.py",
        "copilot-skill.sh",
        "copilot-agent.sh",
        "copilot-error.sh",
        "copilot-instinct-observe.sh",
        "copilot-instinct-extract.sh",
    ):
        target = hooks_dir / script_name
        shutil.copy2(HOOKS_ROOT / script_name, target)
        target.chmod(target.stat().st_mode | stat.S_IXUSR)

    manifest_path = tmp_path / ".ai-engineering" / "manifest.yml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("name: demo-project\n", encoding="utf-8")
    return tmp_path


def _framework_events_path(project_root: Path) -> Path:
    return project_root / ".ai-engineering" / "state" / "framework-events.ndjson"


def _audit_log_path(project_root: Path) -> Path:
    return project_root / ".ai-engineering" / "state" / "audit-log.ndjson"


class TestClaudeHookEmitters:
    def test_skill_hook_writes_canonical_framework_event(self, tmp_path: Path) -> None:
        project_root = _prepare_project(tmp_path)
        script = project_root / ".ai-engineering" / "scripts" / "hooks" / "telemetry-skill.py"
        env = os.environ | {
            "CLAUDE_PROJECT_DIR": str(project_root),
            "CLAUDE_SESSION_ID": "session-1",
            "PYTHONPATH": str(REPO_ROOT / "src"),
            "HOME": str(project_root),
        }

        result = subprocess.run(
            [sys.executable, str(script)],
            input=json.dumps({"prompt": "/ai-brainstorm"}),
            text=True,
            capture_output=True,
            cwd=project_root,
            env=env,
            check=False,
        )

        assert result.returncode == 0
        entries = read_ndjson_entries(_framework_events_path(project_root), FrameworkEvent)
        skill_event = next(entry for entry in entries if entry.kind == "skill_invoked")
        context_events = [entry for entry in entries if entry.kind == "context_load"]
        assert skill_event.engine == "claude_code"
        assert skill_event.detail["skill"] == "ai-brainstorm"
        assert context_events
        assert not _audit_log_path(project_root).exists()

    def test_agent_hook_writes_canonical_framework_event(self, tmp_path: Path) -> None:
        project_root = _prepare_project(tmp_path)
        script = project_root / ".ai-engineering" / "scripts" / "hooks" / "observe.py"
        env = os.environ | {
            "CLAUDE_PROJECT_DIR": str(project_root),
            "CLAUDE_SESSION_ID": "session-2",
            "CLAUDE_HOOK_EVENT_NAME": "PostToolUse",
            "CLAUDE_CODE_ENTRYPOINT": "cli",
            "PYTHONPATH": str(REPO_ROOT / "src"),
            "HOME": str(project_root),
        }

        payload = {
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "build", "description": "Run checks"},
        }
        result = subprocess.run(
            [sys.executable, str(script)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=project_root,
            env=env,
            check=False,
        )

        assert result.returncode == 0
        entries = read_ndjson_entries(_framework_events_path(project_root), FrameworkEvent)
        agent_event = next(entry for entry in entries if entry.kind == "agent_dispatched")
        hook_event = next(entry for entry in entries if entry.kind == "ide_hook")
        assert agent_event.engine == "claude_code"
        assert agent_event.detail["agent"] == "ai-build"
        assert hook_event.detail["hook_kind"] == "post-tool-use"
        assert not _audit_log_path(project_root).exists()

    def test_instinct_hooks_capture_observations_and_extract_store(self, tmp_path: Path) -> None:
        project_root = _prepare_project(tmp_path)
        observe_script = (
            project_root / ".ai-engineering" / "scripts" / "hooks" / "instinct-observe.py"
        )
        extract_script = (
            project_root / ".ai-engineering" / "scripts" / "hooks" / "instinct-extract.py"
        )
        env = os.environ | {
            "CLAUDE_PROJECT_DIR": str(project_root),
            "CLAUDE_SESSION_ID": "session-3",
            "PYTHONPATH": str(REPO_ROOT / "src"),
            "HOME": str(project_root),
        }

        for hook_event, payload in (
            ("PreToolUse", {"tool_name": "Read", "tool_input": {"file_path": "README.md"}}),
            ("PostToolUse", {"tool_name": "Bash", "result": {"message": "failed with error"}}),
            ("PreToolUse", {"tool_name": "Grep", "tool_input": {"pattern": "TODO"}}),
        ):
            result = subprocess.run(
                [sys.executable, str(observe_script)],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                cwd=project_root,
                env=env | {"CLAUDE_HOOK_EVENT_NAME": hook_event},
                check=False,
            )
            assert result.returncode == 0

        extract = subprocess.run(
            [sys.executable, str(extract_script)],
            input="{}",
            text=True,
            capture_output=True,
            cwd=project_root,
            env=env | {"CLAUDE_HOOK_EVENT_NAME": "Stop"},
            check=False,
        )

        assert extract.returncode == 0
        instincts = (project_root / ".ai-engineering" / "instincts" / "instincts.yml").read_text(
            encoding="utf-8"
        )
        observations = read_ndjson_entries(
            project_root / ".ai-engineering" / "state" / "instinct-observations.ndjson",
            InstinctObservation,
        )
        assert observations
        assert "Read -> Grep" in instincts

    def test_onboard_skill_consolidates_pending_instinct_delta(self, tmp_path: Path) -> None:
        project_root = _prepare_project(tmp_path)
        observe_script = (
            project_root / ".ai-engineering" / "scripts" / "hooks" / "instinct-observe.py"
        )
        skill_script = project_root / ".ai-engineering" / "scripts" / "hooks" / "telemetry-skill.py"
        env = os.environ | {
            "CLAUDE_PROJECT_DIR": str(project_root),
            "CLAUDE_SESSION_ID": "session-onboard",
            "PYTHONPATH": str(REPO_ROOT / "src"),
            "HOME": str(project_root),
        }

        for hook_event, payload in (
            ("PreToolUse", {"tool_name": "Read", "tool_input": {"file_path": "README.md"}}),
            ("PostToolUse", {"tool_name": "Bash", "result": {"message": "failed with error"}}),
            ("PreToolUse", {"tool_name": "Grep", "tool_input": {"pattern": "TODO"}}),
        ):
            result = subprocess.run(
                [sys.executable, str(observe_script)],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                cwd=project_root,
                env=env | {"CLAUDE_HOOK_EVENT_NAME": hook_event},
                check=False,
            )
            assert result.returncode == 0

        onboard = subprocess.run(
            [sys.executable, str(skill_script)],
            input=json.dumps({"prompt": "/ai-onboard"}),
            text=True,
            capture_output=True,
            cwd=project_root,
            env=env,
            check=False,
        )

        assert onboard.returncode == 0
        assert "Read -> Grep" in (
            project_root / ".ai-engineering" / "instincts" / "instincts.yml"
        ).read_text(encoding="utf-8")
        assert "Read -> Grep" in (
            project_root / ".ai-engineering" / "instincts" / "context.md"
        ).read_text(encoding="utf-8")


class TestCopilotHookEmitters:
    def test_skill_hook_writes_canonical_framework_event(self, tmp_path: Path) -> None:
        project_root = _prepare_project(tmp_path)
        script = project_root / ".ai-engineering" / "scripts" / "hooks" / "copilot-skill.sh"
        env = os.environ | {
            "PYTHONPATH": str(REPO_ROOT / "src"),
            "HOME": str(project_root),
        }

        result = subprocess.run(
            ["bash", str(script)],
            input=json.dumps({"prompt": "/ai-dispatch"}),
            text=True,
            capture_output=True,
            cwd=project_root,
            env=env,
            check=False,
        )

        assert result.returncode == 0
        entries = read_ndjson_entries(_framework_events_path(project_root), FrameworkEvent)
        skill_event = next(entry for entry in entries if entry.kind == "skill_invoked")
        context_events = [entry for entry in entries if entry.kind == "context_load"]
        assert skill_event.engine == "github_copilot"
        assert skill_event.detail["skill"] == "ai-dispatch"
        assert context_events
        assert not _audit_log_path(project_root).exists()

    def test_agent_hook_writes_canonical_framework_event(self, tmp_path: Path) -> None:
        project_root = _prepare_project(tmp_path)
        script = project_root / ".ai-engineering" / "scripts" / "hooks" / "copilot-agent.sh"
        env = os.environ | {
            "PYTHONPATH": str(REPO_ROOT / "src"),
            "HOME": str(project_root),
        }

        payload = {"toolName": "Build", "toolArgs": {}}
        result = subprocess.run(
            ["bash", str(script)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=project_root,
            env=env,
            check=False,
        )

        assert result.returncode == 0
        entries = read_ndjson_entries(_framework_events_path(project_root), FrameworkEvent)
        agent_event = next(entry for entry in entries if entry.kind == "agent_dispatched")
        hook_event = next(entry for entry in entries if entry.kind == "ide_hook")
        assert agent_event.engine == "github_copilot"
        assert agent_event.detail["agent"] == "ai-build"
        assert hook_event.detail["hook_kind"] == "post-tool-use"
        assert not _audit_log_path(project_root).exists()

    def test_error_hook_writes_framework_error_without_audit_log(self, tmp_path: Path) -> None:
        project_root = _prepare_project(tmp_path)
        script = project_root / ".ai-engineering" / "scripts" / "hooks" / "copilot-error.sh"
        env = os.environ | {
            "PYTHONPATH": str(REPO_ROOT / "src"),
            "HOME": str(project_root),
        }

        payload = {
            "error": {"name": "HookFailure", "message": 'token="local-test-placeholder" exploded'}
        }
        result = subprocess.run(
            ["bash", str(script)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            cwd=project_root,
            env=env,
            check=False,
        )

        assert result.returncode == 0
        entries = read_ndjson_entries(_framework_events_path(project_root), FrameworkEvent)
        error_event = next(entry for entry in entries if entry.kind == "framework_error")
        assert error_event.detail["error_code"] == "HookFailure"
        assert "[REDACTED]" in error_event.detail["summary"]
        assert not _audit_log_path(project_root).exists()

    def test_instinct_hooks_capture_observations_and_extract_store(self, tmp_path: Path) -> None:
        project_root = _prepare_project(tmp_path)
        observe_script = (
            project_root / ".ai-engineering" / "scripts" / "hooks" / "copilot-instinct-observe.sh"
        )
        extract_script = (
            project_root / ".ai-engineering" / "scripts" / "hooks" / "copilot-instinct-extract.sh"
        )
        env = os.environ | {
            "PYTHONPATH": str(REPO_ROOT / "src"),
            "HOME": str(project_root),
        }

        for phase, payload in (
            ("pre", {"toolName": "Read", "toolArgs": {"filePath": "README.md"}}),
            ("post", {"toolName": "Bash", "result": {"message": "failed with error"}}),
            ("pre", {"toolName": "Grep", "toolArgs": {"pattern": "TODO"}}),
        ):
            result = subprocess.run(
                ["bash", str(observe_script), phase],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                cwd=project_root,
                env=env,
                check=False,
            )
            assert result.returncode == 0

        extract = subprocess.run(
            ["bash", str(extract_script)],
            input="{}",
            text=True,
            capture_output=True,
            cwd=project_root,
            env=env,
            check=False,
        )

        assert extract.returncode == 0
        instincts = (project_root / ".ai-engineering" / "instincts" / "instincts.yml").read_text(
            encoding="utf-8"
        )
        observations = read_ndjson_entries(
            project_root / ".ai-engineering" / "state" / "instinct-observations.ndjson",
            InstinctObservation,
        )
        assert observations
        assert "Read -> Grep" in instincts

    def test_onboard_skill_consolidates_pending_instinct_delta(self, tmp_path: Path) -> None:
        project_root = _prepare_project(tmp_path)
        observe_script = (
            project_root / ".ai-engineering" / "scripts" / "hooks" / "copilot-instinct-observe.sh"
        )
        skill_script = project_root / ".ai-engineering" / "scripts" / "hooks" / "copilot-skill.sh"
        env = os.environ | {
            "PYTHONPATH": str(REPO_ROOT / "src"),
            "HOME": str(project_root),
        }

        for phase, payload in (
            ("pre", {"toolName": "Read", "toolArgs": {"filePath": "README.md"}}),
            ("post", {"toolName": "Bash", "result": {"message": "failed with error"}}),
            ("pre", {"toolName": "Grep", "toolArgs": {"pattern": "TODO"}}),
        ):
            result = subprocess.run(
                ["bash", str(observe_script), phase],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                cwd=project_root,
                env=env,
                check=False,
            )
            assert result.returncode == 0

        onboard = subprocess.run(
            ["bash", str(skill_script)],
            input=json.dumps({"prompt": "/ai-onboard"}),
            text=True,
            capture_output=True,
            cwd=project_root,
            env=env,
            check=False,
        )

        assert onboard.returncode == 0
        assert "Read -> Grep" in (
            project_root / ".ai-engineering" / "instincts" / "instincts.yml"
        ).read_text(encoding="utf-8")
        assert "Read -> Grep" in (
            project_root / ".ai-engineering" / "instincts" / "context.md"
        ).read_text(encoding="utf-8")
