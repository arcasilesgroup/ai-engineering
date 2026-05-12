"""Tests for spec-133 autodetect additions (D-133-06, D-133-12).

- New Surfaces: opencode, cursor, antigravity detected from .opencode/,
  .cursor/, .agent/ root markers.
- New stacks: react-native (package.json deps), flutter (pubspec.yaml
  flutter: block).
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.installer.autodetect import (
    detect_ai_providers,
    detect_stacks,
)


def test_detect_opencode_surface(tmp_path: Path) -> None:
    (tmp_path / ".opencode").mkdir()
    assert "opencode" in detect_ai_providers(tmp_path)


def test_detect_cursor_surface(tmp_path: Path) -> None:
    (tmp_path / ".cursor").mkdir()
    assert "cursor" in detect_ai_providers(tmp_path)


def test_detect_antigravity_surface(tmp_path: Path) -> None:
    (tmp_path / ".agent").mkdir()
    assert "antigravity" in detect_ai_providers(tmp_path)


def test_detect_all_seven_surfaces(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".gemini").mkdir()
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "copilot-instructions.md").write_text("")
    (tmp_path / ".opencode").mkdir()
    (tmp_path / ".cursor").mkdir()
    (tmp_path / ".agent").mkdir()
    detected = detect_ai_providers(tmp_path)
    assert set(detected) == {
        "claude-code",
        "codex",
        "gemini-cli",
        "github-copilot",
        "opencode",
        "cursor",
        "antigravity",
    }


def test_detect_react_native_from_package_json(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"dependencies": {"react-native": "^0.74.0"}}',
        encoding="utf-8",
    )
    stacks = detect_stacks(tmp_path)
    assert "react-native" in stacks


def test_detect_react_native_from_expo_dep(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"dependencies": {"expo": "~50.0.0"}}',
        encoding="utf-8",
    )
    stacks = detect_stacks(tmp_path)
    assert "react-native" in stacks


def test_detect_flutter_from_pubspec_flutter_block(tmp_path: Path) -> None:
    (tmp_path / "pubspec.yaml").write_text(
        "name: myapp\nflutter:\n  uses-material-design: true\n",
        encoding="utf-8",
    )
    stacks = detect_stacks(tmp_path)
    assert "flutter" in stacks
    # Flutter precedence: dart is dropped when flutter detected
    assert "dart" not in stacks


def test_detect_pubspec_without_flutter_falls_back_to_dart(tmp_path: Path) -> None:
    (tmp_path / "pubspec.yaml").write_text(
        "name: pure_dart_lib\nversion: 1.0.0\n",
        encoding="utf-8",
    )
    stacks = detect_stacks(tmp_path)
    assert "dart" in stacks
    assert "flutter" not in stacks


def test_detect_typescript_without_react_native(tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text("{}", encoding="utf-8")
    (tmp_path / "package.json").write_text(
        '{"name": "my-web-app", "dependencies": {"react": "^18"}}',
        encoding="utf-8",
    )
    stacks = detect_stacks(tmp_path)
    assert "typescript" in stacks
    assert "react-native" not in stacks
