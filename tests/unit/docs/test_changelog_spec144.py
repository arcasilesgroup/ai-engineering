from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CHANGELOG = ROOT / "CHANGELOG.md"
OLD_BRANCH_CLEANUP_SKILL = "/" + "-".join(("ai", "repo", "tidy"))


def _unreleased() -> str:
    text = CHANGELOG.read_text(encoding="utf-8")
    start = text.index("## [Unreleased]")
    next_release = text.find("\n## [", start + len("## [Unreleased]"))
    return text[start : next_release if next_release != -1 else None]


def _section(block: str, heading: str) -> str:
    marker = f"### {heading}"
    assert marker in block, f"missing {marker} in Unreleased"
    start = block.index(marker) + len(marker)
    next_section = block.find("\n### ", start)
    return block[start : next_section if next_section != -1 else None]


def test_unreleased_records_branch_cleanup_breaking_rename() -> None:
    breaking = _section(_unreleased(), "BREAKING")
    assert OLD_BRANCH_CLEANUP_SKILL in breaking
    assert "/ai-branch-cleanup" in breaking
    assert "no alias" in breaking.lower() or "no shim" in breaking.lower()


def test_unreleased_records_readme_brand_change() -> None:
    changed = _section(_unreleased(), "Changed")
    lowered = changed.lower()
    assert "readme" in lowered
    assert "brand" in lowered
