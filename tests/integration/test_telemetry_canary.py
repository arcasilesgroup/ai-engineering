"""Canary tests for telemetry hook infrastructure.

Verifies that:
- Hook scripts exist and are executable
- Claude Code settings.json has hooks configured
- GitHub Copilot hooks.json exists and is valid
- ai-eng signals emit CLI works for skill/agent/guard events
"""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]


class TestHookScripts:
    """Verify hook scripts exist and are executable."""

    @pytest.mark.skipif(
        sys.platform == "win32", reason="Unix executable bit not available on Windows"
    )
    @pytest.mark.parametrize(
        "script",
        [
            ".ai-engineering/scripts/hooks/telemetry-skill.sh",
            ".ai-engineering/scripts/hooks/telemetry-session.sh",
        ],
    )
    def test_script_exists_and_executable(self, script: str) -> None:
        path = ROOT / script
        assert path.exists(), f"{script} does not exist"
        mode = os.stat(path).st_mode
        assert mode & stat.S_IXUSR, f"{script} is not executable"

    @pytest.mark.parametrize(
        "script",
        [
            ".ai-engineering/scripts/hooks/telemetry-skill.ps1",
            ".ai-engineering/scripts/hooks/telemetry-session.ps1",
        ],
    )
    def test_powershell_stub_exists(self, script: str) -> None:
        path = ROOT / script
        assert path.exists(), f"{script} does not exist"


class TestClaudeCodeHooks:
    """Verify Claude Code hook configuration."""

    def test_settings_has_hooks(self) -> None:
        settings_path = ROOT / ".claude" / "settings.json"
        assert settings_path.exists()
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        assert "hooks" in data, "settings.json missing 'hooks' key"

    def test_user_prompt_submit_skill_matcher(self) -> None:
        settings_path = ROOT / ".claude" / "settings.json"
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        prompt_hooks = data["hooks"].get("UserPromptSubmit", [])
        skill_matchers = [h for h in prompt_hooks if h.get("matcher") == "/ai-"]
        assert len(skill_matchers) >= 1, "No UserPromptSubmit hook with /ai- matcher"

    def test_stop_hook_exists(self) -> None:
        settings_path = ROOT / ".claude" / "settings.json"
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        stop_hooks = data["hooks"].get("Stop", [])
        assert len(stop_hooks) >= 1, "No Stop hook configured"


class TestCopilotHooks:
    """Verify GitHub Copilot hook configuration."""

    def test_hooks_json_exists(self) -> None:
        hooks_path = ROOT / ".github" / "hooks" / "hooks.json"
        assert hooks_path.exists(), ".github/hooks/hooks.json does not exist"

    def test_hooks_json_valid(self) -> None:
        hooks_path = ROOT / ".github" / "hooks" / "hooks.json"
        data = json.loads(hooks_path.read_text(encoding="utf-8"))
        assert "hooks" in data, "hooks.json missing 'hooks' key"
        assert len(data["hooks"]) >= 1, "No hooks defined"


class TestTemplateHookSync:
    """Verify templates include hook infrastructure for ai-eng install."""

    TEMPLATE_ROOT = ROOT / "src" / "ai_engineering" / "templates" / "project"

    def test_template_settings_has_hooks(self) -> None:
        path = self.TEMPLATE_ROOT / ".claude" / "settings.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "hooks" in data, "Template settings.json missing 'hooks' key"

    def test_template_hook_scripts_exist(self) -> None:
        for script in ("telemetry-skill.sh", "telemetry-session.sh"):
            path = self.TEMPLATE_ROOT / ".ai-engineering" / "scripts" / "hooks" / script
            assert path.exists(), f"Template missing {script}"

    def test_template_copilot_hooks_json(self) -> None:
        path = self.TEMPLATE_ROOT / "github_templates" / "hooks" / "hooks.json"
        assert path.exists(), "Template missing github_templates/hooks/hooks.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "hooks" in data

    def test_template_claude_md_has_observability(self) -> None:
        path = self.TEMPLATE_ROOT / "CLAUDE.md"
        content = path.read_text(encoding="utf-8")
        assert "Observability" in content, "Template CLAUDE.md missing Observability section"

    def test_template_copilot_instructions_has_observability(self) -> None:
        path = self.TEMPLATE_ROOT / "copilot-instructions.md"
        content = path.read_text(encoding="utf-8")
        assert "Observability" in content, "Template copilot-instructions.md missing Observability"


class TestEmitFunctions:
    """Verify all emit functions are importable."""

    def test_guard_emit_functions_exist(self) -> None:
        from ai_engineering.state.audit import (
            emit_guard_advisory,
            emit_guard_drift,
            emit_guard_gate,
        )

        assert callable(emit_guard_advisory)
        assert callable(emit_guard_gate)
        assert callable(emit_guard_drift)

    def test_guard_aggregators_exist(self) -> None:
        from ai_engineering.lib.signals import guard_advisory_from, guard_drift_from

        assert callable(guard_advisory_from)
        assert callable(guard_drift_from)
