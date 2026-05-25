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
    # Length cap — raised 120 -> 170 to match tests/docs/test_links.py for the
    # expanded per-tool-manager install section (uv/pipx/pip + PyPI update flow).
    assert len(text.splitlines()) <= 170


def test_governance_readme_is_client_manual_with_quick_wins() -> None:
    # spec-153 D-153-11/14: .ai-engineering/README.md is the post-install client
    # manual — a quick-win path plus the generated catalog — NOT a maintainer
    # reference. The stale "Four-Tier Persistence" table and every state.db
    # reference are deleted (state.db was removed by spec-148); the doc points
    # to the canonical three-tier doctrine instead of restating tiers inline.
    text = (ROOT / ".ai-engineering" / "README.md").read_text(encoding="utf-8")
    assert "GETTING_STARTED.md" not in text
    assert "## Quick wins" in text
    assert "/ai-start" in text
    assert "/ai-brainstorm → /ai-plan → /ai-build → /ai-pr" in text
    assert "docs/persistence-doctrine.md" in text
    # The generated capability catalog is the heart of the manual.
    assert "<!-- catalog:start -->" in text
    assert "<!-- catalog:end -->" in text
    # D-153-14: no stale four-tier / state.db persistence claim survives.
    assert "four-tier" not in text.lower()
    assert "state.db" not in text.lower()
    assert re.search(r"(?<!dev )ai-eng sync(\s|$)", text) is None


def test_governance_readme_links_resolve() -> None:
    path = ROOT / ".ai-engineering" / "README.md"
    text = path.read_text(encoding="utf-8")
    for target in re.findall(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)", text):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        assert (path.parent / target).resolve().exists(), f"missing link target: {target}"
