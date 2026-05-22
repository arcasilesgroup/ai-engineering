import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_root_readme_declares_current_surfaces_and_brand() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Antigravity" in text
    for surface in (
        "Claude Code",
        "GitHub Copilot",
        "OpenAI Codex",
        "Antigravity",
        "OpenCode",
        "Cursor",
    ):
        assert surface in text
    assert "{ai} engineering" in text
    assert "/ai-brainstorm → /ai-plan → /ai-build → /ai-pr" in text
    for required in ("AGENTS.md", "CONSTITUTION.md", "CHANGELOG.md", "CONTRIBUTING.md"):
        assert required in text
    assert len(text.splitlines()) <= 120


def test_governance_readme_has_inline_quick_start_and_no_deleted_link() -> None:
    text = (ROOT / ".ai-engineering" / "README.md").read_text(encoding="utf-8")
    assert "GETTING_STARTED.md" not in text
    assert "## Quick Start" in text
    assert "ai-eng install" in text
    assert "/ai-start" in text
    assert "/ai-brainstorm → /ai-plan → /ai-build → /ai-pr" in text
    assert "four-tier" in text.lower()
    assert "docs/persistence-doctrine.md" in text
    assert re.search(r"(?<!dev )ai-eng sync(\s|$)", text) is None


def test_governance_readme_links_resolve() -> None:
    path = ROOT / ".ai-engineering" / "README.md"
    text = path.read_text(encoding="utf-8")
    for target in re.findall(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)", text):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        assert (path.parent / target).resolve().exists(), f"missing link target: {target}"
