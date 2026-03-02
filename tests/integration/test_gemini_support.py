"""Tests for Gemini CLI support.

Covers:
- GEMINI.md template mapping.
- GEMINI.md creation during install.
- GEMINI.md preservation during re-install.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.installer.service import install
from ai_engineering.installer.templates import copy_project_templates

pytestmark = pytest.mark.integration


class TestGeminiSupport:
    """Tests for Gemini CLI support in the installer."""

    def test_gemini_md_template_exists(self) -> None:
        """Verify the GEMINI.md template exists in the correct location."""
        from ai_engineering.installer.templates import get_project_template_root

        root = get_project_template_root()
        assert (root / "GEMINI.md").is_file()
        content = (root / "GEMINI.md").read_text()
        assert "# GEMINI.md" in content

    def test_install_creates_gemini_md(self, tmp_path: Path) -> None:
        """Verify install() creates GEMINI.md in the project root."""
        install(tmp_path)
        assert (tmp_path / "GEMINI.md").is_file()
        content = (tmp_path / "GEMINI.md").read_text()
        assert "Operational guide for Gemini assistant sessions" in content

    def test_preserves_custom_gemini_md(self, tmp_path: Path) -> None:
        """Verify install() does not overwrite existing GEMINI.md."""
        custom_content = "Custom Gemini Config"
        (tmp_path / "GEMINI.md").write_text(custom_content)

        install(tmp_path)

        assert (tmp_path / "GEMINI.md").read_text() == custom_content

    def test_copy_project_templates_includes_gemini(self, tmp_path: Path) -> None:
        """Verify copy_project_templates() explicitly handles GEMINI.md."""
        result = copy_project_templates(tmp_path)

        gemini_path = tmp_path / "GEMINI.md"
        assert gemini_path.is_file()
        assert gemini_path in result.created
