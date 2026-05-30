"""Unit tests for settings.json merge."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_engineering.installer.merge import merge_settings, validate_settings_structure

# ---------------------------------------------------------------------------
# merge_settings
# ---------------------------------------------------------------------------


class TestMergeSettings:
    def test_adds_missing_hooks(self, tmp_path: Path) -> None:
        """Template hooks are added when missing from target."""
        template_data = {
            "permissions": {"allow": [], "deny": []},
            "hooks": {
                "UserPromptSubmit": [
                    {
                        "matcher": "/ai-",
                        "hooks": [{"type": "command", "command": "test", "timeout": 10}],
                    }
                ],
                "Stop": [
                    {
                        "matcher": "",
                        "hooks": [{"type": "command", "command": "cost", "timeout": 10}],
                    }
                ],
            },
        }
        target = tmp_path / "target.json"
        target.write_text(
            json.dumps(
                {
                    "permissions": {"allow": [], "deny": []},
                    "hooks": {
                        "UserPromptSubmit": [
                            {
                                "matcher": "/ai-",
                                "hooks": [{"type": "command", "command": "custom", "timeout": 5}],
                            }
                        ],
                    },
                }
            )
        )
        merge_settings(template_data, target, base=tmp_path)
        result = json.loads(target.read_text())
        assert "Stop" in result["hooks"]  # Added from template
        # User's existing hook preserved (same matcher)
        assert result["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"] == "custom"

    def test_preserves_user_hooks(self, tmp_path: Path) -> None:
        """User-added hooks with unique matchers are preserved."""
        template_data = {
            "permissions": {"allow": [], "deny": []},
            "hooks": {"Stop": [{"matcher": "", "hooks": []}]},
        }
        target = tmp_path / "target.json"
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
        merge_settings(template_data, target, base=tmp_path)
        result = json.loads(target.read_text())
        matchers = [h["matcher"] for h in result["hooks"]["Stop"]]
        assert "custom" in matchers

    def test_preserves_user_permissions(self, tmp_path: Path) -> None:
        """User-added permission rules are preserved."""
        template_data = {
            "permissions": {"allow": ["Bash(ruff *)"], "deny": ["Bash(rm -rf *)"]},
            "hooks": {},
        }
        target = tmp_path / "target.json"
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
        merge_settings(template_data, target, base=tmp_path)
        result = json.loads(target.read_text())
        assert "Bash(ruff *)" in result["permissions"]["allow"]
        assert "Bash(custom *)" in result["permissions"]["allow"]
        assert "Bash(drop *)" in result["permissions"]["deny"]

    def test_preserves_user_top_level_keys(self, tmp_path: Path) -> None:
        """User-added top-level keys are preserved."""
        template_data = {"permissions": {"allow": [], "deny": []}, "hooks": {}}
        target = tmp_path / "target.json"
        target.write_text(
            json.dumps(
                {
                    "permissions": {"allow": [], "deny": []},
                    "hooks": {},
                    "custom": "value",
                }
            )
        )
        merge_settings(template_data, target, base=tmp_path)
        result = json.loads(target.read_text())
        assert result.get("custom") == "value"

    def test_malformed_target_fallback(self, tmp_path: Path) -> None:
        """Malformed target JSON falls back to template copy."""
        template_data = {"permissions": {"allow": [], "deny": []}, "hooks": {"Stop": []}}
        target = tmp_path / "target.json"
        target.write_text("not json {{{")
        merge_settings(template_data, target, base=tmp_path)
        result = json.loads(target.read_text())
        assert "Stop" in result["hooks"]

    def test_malformed_target_creates_backup(self, tmp_path: Path) -> None:
        """Malformed target creates .json.bak before replacement."""
        template_data = {"permissions": {"allow": [], "deny": []}, "hooks": {}}
        target = tmp_path / "target.json"
        malformed_content = "not json {{{"
        target.write_text(malformed_content)
        merge_settings(template_data, target, base=tmp_path)

        backup = target.with_suffix(".json.bak")
        assert backup.exists()
        assert backup.read_text() == malformed_content

    def test_path_traversal_rejected(self, tmp_path: Path) -> None:
        """target_path outside base raises ValueError (CWE-22)."""
        base = tmp_path / "project"
        base.mkdir()
        outside = tmp_path / "outside.json"
        outside.write_text(json.dumps({"permissions": {}, "hooks": {}}))
        with pytest.raises(ValueError, match="Path traversal rejected"):
            merge_settings({"permissions": {}, "hooks": {}}, outside, base=base)

    def test_global_home_settings_merge_preserves_user_keys(self, tmp_path: Path) -> None:
        """sub-003 D9/D10/R3: a global merge into ~/.claude/settings.json keeps user keys.

        Simulates the global install path where the settings file lives under a
        home ``.claude`` directory and the trusted base is its own parent. The
        framework hooks/permissions are added, but the operator's bespoke top-level
        key, custom permission rule, and custom hook matcher all survive.
        """
        home_claude = tmp_path / "home" / ".claude"
        home_claude.mkdir(parents=True)
        target = home_claude / "settings.json"
        target.write_text(
            json.dumps(
                {
                    "permissions": {
                        "allow": ["Bash(my-tool *)"],
                        "deny": ["Bash(rm -rf *)"],
                    },
                    "hooks": {
                        "UserPromptSubmit": [
                            {"matcher": "/me-", "hooks": [{"type": "command", "command": "mine"}]}
                        ]
                    },
                    "theme": "operator-dark",
                }
            )
        )
        template_data = {
            "permissions": {"allow": ["Bash(ruff *)"], "deny": ["Bash(rm -rf *)"]},
            "hooks": {
                "Stop": [{"matcher": "", "hooks": [{"type": "command", "command": "cost"}]}],
                "UserPromptSubmit": [
                    {"matcher": "/ai-", "hooks": [{"type": "command", "command": "fw"}]}
                ],
            },
        }

        # Base is the settings file's own parent (the home .claude dir), the same
        # contract HooksPhase uses for global scope -- never the repo root.
        merge_settings(template_data, target, base=target.parent)

        result = json.loads(target.read_text())
        # User customizations survive.
        assert result["theme"] == "operator-dark"
        assert "Bash(my-tool *)" in result["permissions"]["allow"]
        user_matchers = [h["matcher"] for h in result["hooks"]["UserPromptSubmit"]]
        assert "/me-" in user_matchers
        # Framework additions land.
        assert "Bash(ruff *)" in result["permissions"]["allow"]
        assert "Stop" in result["hooks"]
        assert "/ai-" in user_matchers


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
