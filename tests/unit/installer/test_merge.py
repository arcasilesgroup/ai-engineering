"""Unit tests for settings.json merge."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_engineering.installer.merge import merge_settings, validate_settings_structure

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# merge_settings
# ---------------------------------------------------------------------------


class TestMergeSettings:
    def test_adds_missing_hooks(self, tmp_path: Path) -> None:
        """Template hooks are added when missing from target."""
        template = tmp_path / "template.json"
        target = tmp_path / "target.json"
        template.write_text(
            json.dumps(
                {
                    "permissions": {"allow": [], "deny": []},
                    "hooks": {
                        "UserPromptSubmit": [
                            {
                                "matcher": "/ai-",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": "test",
                                        "timeout": 10,
                                    }
                                ],
                            }
                        ],
                        "Stop": [
                            {
                                "matcher": "",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": "cost",
                                        "timeout": 10,
                                    }
                                ],
                            }
                        ],
                    },
                }
            )
        )
        target.write_text(
            json.dumps(
                {
                    "permissions": {"allow": [], "deny": []},
                    "hooks": {
                        "UserPromptSubmit": [
                            {
                                "matcher": "/ai-",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": "custom",
                                        "timeout": 5,
                                    }
                                ],
                            }
                        ],
                    },
                }
            )
        )
        merge_settings(template, target)
        result = json.loads(target.read_text())
        assert "Stop" in result["hooks"]  # Added from template
        # User's existing hook preserved (same matcher)
        assert result["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"] == "custom"

    def test_preserves_user_hooks(self, tmp_path: Path) -> None:
        """User-added hooks with unique matchers are preserved."""
        template = tmp_path / "template.json"
        target = tmp_path / "target.json"
        template.write_text(
            json.dumps(
                {
                    "permissions": {"allow": [], "deny": []},
                    "hooks": {"Stop": [{"matcher": "", "hooks": []}]},
                }
            )
        )
        target.write_text(
            json.dumps(
                {
                    "permissions": {"allow": [], "deny": []},
                    "hooks": {
                        "Stop": [
                            {"matcher": "", "hooks": []},
                            {"matcher": "custom", "hooks": []},
                        ],
                    },
                }
            )
        )
        merge_settings(template, target)
        result = json.loads(target.read_text())
        matchers = [h["matcher"] for h in result["hooks"]["Stop"]]
        assert "custom" in matchers

    def test_preserves_user_permissions(self, tmp_path: Path) -> None:
        """User-added permission rules are preserved."""
        template = tmp_path / "template.json"
        target = tmp_path / "target.json"
        template.write_text(
            json.dumps(
                {
                    "permissions": {
                        "allow": ["Bash(ruff *)"],
                        "deny": ["Bash(rm -rf *)"],
                    },
                    "hooks": {},
                }
            )
        )
        target.write_text(
            json.dumps(
                {
                    "permissions": {
                        "allow": ["Bash(custom *)"],
                        "deny": ["Bash(rm -rf *)", "Bash(drop *)"],
                    },
                    "hooks": {},
                }
            )
        )
        merge_settings(template, target)
        result = json.loads(target.read_text())
        assert "Bash(ruff *)" in result["permissions"]["allow"]
        assert "Bash(custom *)" in result["permissions"]["allow"]
        assert "Bash(drop *)" in result["permissions"]["deny"]

    def test_preserves_user_top_level_keys(self, tmp_path: Path) -> None:
        """User-added top-level keys are preserved."""
        template = tmp_path / "template.json"
        target = tmp_path / "target.json"
        template.write_text(json.dumps({"permissions": {"allow": [], "deny": []}, "hooks": {}}))
        target.write_text(
            json.dumps(
                {
                    "permissions": {"allow": [], "deny": []},
                    "hooks": {},
                    "custom": "value",
                }
            )
        )
        merge_settings(template, target)
        result = json.loads(target.read_text())
        assert result.get("custom") == "value"

    def test_malformed_target_fallback(self, tmp_path: Path) -> None:
        """Malformed target JSON falls back to template copy."""
        template = tmp_path / "template.json"
        target = tmp_path / "target.json"
        template.write_text(
            json.dumps(
                {
                    "permissions": {"allow": [], "deny": []},
                    "hooks": {"Stop": []},
                }
            )
        )
        target.write_text("not json {{{")
        merge_settings(template, target)
        result = json.loads(target.read_text())
        assert "Stop" in result["hooks"]


# ---------------------------------------------------------------------------
# validate_settings_structure
# ---------------------------------------------------------------------------


class TestValidateSettingsStructure:
    def test_valid_structure(self) -> None:
        """Valid settings passes validation."""
        warnings = validate_settings_structure(
            {
                "permissions": {"allow": [], "deny": []},
                "hooks": {"Stop": []},
            }
        )
        assert len(warnings) == 0

    def test_missing_permissions(self) -> None:
        """Missing permissions key produces warning."""
        warnings = validate_settings_structure({"hooks": {}})
        assert len(warnings) > 0
