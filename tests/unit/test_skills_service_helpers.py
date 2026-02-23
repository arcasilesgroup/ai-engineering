"""Additional branch coverage for skills.service helper paths."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ai_engineering.skills import service


def test_safe_load_helpers_and_frontmatter_errors(tmp_path: Path) -> None:
    assert service._safe_yaml_load(tmp_path / "missing.yml") == {}
    bad = tmp_path / "bad.yml"
    bad.write_text("- not-map", encoding="utf-8")
    assert service._safe_yaml_load(bad) == {}

    assert service._safe_json_load(tmp_path / "missing.json") == {}

    md = tmp_path / "skill.md"
    md.write_text("hello", encoding="utf-8")
    fm, err = service._load_skill_frontmatter(md)
    assert fm == {}
    assert "missing-frontmatter" in err[0]

    md.write_text("---\nname: x\n", encoding="utf-8")
    fm, err = service._load_skill_frontmatter(md)
    assert fm == {}
    assert "unterminated-frontmatter" in err[0]


def test_load_skill_frontmatter_invalid_yaml_and_mapping(tmp_path: Path) -> None:
    md = tmp_path / "skill.md"
    md.write_text("---\nname: [\n---\n", encoding="utf-8")
    fm, err = service._load_skill_frontmatter(md)
    assert fm == {}
    assert "invalid-frontmatter-yaml" in err[0]

    md.write_text("---\n- x\n---\n", encoding="utf-8")
    fm, err = service._load_skill_frontmatter(md)
    assert fm == {}
    assert "frontmatter-not-mapping" in err[0]


def test_config_path_truthy_and_platform_matches() -> None:
    assert service._config_path_truthy({"a": {"b": 1}}, "a.b") is True
    assert service._config_path_truthy({"a": {}}, "a.b") is False
    assert service._config_path_truthy({}, "") is False

    with patch("ai_engineering.skills.service.sys.platform", "darwin"):
        assert service._platform_matches(["darwin"]) is True
    with patch("ai_engineering.skills.service.sys.platform", "win32"):
        assert service._platform_matches(["win32"]) is True
    with patch("ai_engineering.skills.service.sys.platform", "linux"):
        assert service._platform_matches(["darwin"]) is False


def test_sync_sources_fallback_cache_exists(tmp_path: Path) -> None:
    from ai_engineering.installer.service import install
    from ai_engineering.skills.service import add_source, sync_sources

    install(tmp_path, stacks=["python"], ides=["vscode"])
    lock = add_source(tmp_path, "https://example.com/x.md")
    lock.default_remote_enabled = True
    from ai_engineering.state.io import write_json_model

    write_json_model(tmp_path / ".ai-engineering" / "state" / "sources.lock.json", lock)

    with patch("ai_engineering.skills.service._fetch_url", return_value=b"data"):
        sync_sources(tmp_path)
    with patch("ai_engineering.skills.service._fetch_url", return_value=None):
        result = sync_sources(tmp_path)
    assert "https://example.com/x.md" in result.cached
