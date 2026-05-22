"""Contract test: quality-loop STOP verdict is reproducible (spec-149 D-149-04).

`quality.md` Step 2d condition 4 (remediation eligibility — "does not require a
product decision …") is the one LLM-judged element that could otherwise flip
the STOP/PASS verdict. D-149-04 makes it **advisory + conservative**: when
eligibility under it is uncertain the finding is treated as ineligible and
escalated (it can never silently auto-pass), so the same diff yields the same
STOP verdict — the verdict itself is a deterministic count of remaining
blocker/critical/high findings.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BUILD_HANDLER_REL = Path("skills/ai-build/handlers/quality.md")
ROOT_SURFACES = (".claude", ".codex", ".agents", ".github")
TEMPLATE_HANDLER_SURFACES = (".claude", ".codex", ".agents", ".github")

_ADVISORY_MARKERS = (
    "Advisory + conservative",
    "can never silently auto-pass",
    "same diff yields the same STOP verdict",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_cond4_is_advisory_and_conservative() -> None:
    text = _read(REPO_ROOT / ".claude" / BUILD_HANDLER_REL)
    for marker in _ADVISORY_MARKERS:
        assert marker in text, marker


def test_stop_verdict_is_a_deterministic_count() -> None:
    text = _read(REPO_ROOT / ".claude" / BUILD_HANDLER_REL)
    assert "deterministic count of remaining blocker/critical/high" in text
    assert "0 blockers + 0 criticals + 0 highs" in text


def test_cond4_advisory_propagates_to_root_handler_mirrors() -> None:
    for surface in ROOT_SURFACES:
        text = _read(REPO_ROOT / surface / BUILD_HANDLER_REL)
        for marker in _ADVISORY_MARKERS:
            assert marker in text, f"{surface}:{marker}"


def test_cond4_advisory_propagates_to_template_handler_mirrors() -> None:
    template_root = REPO_ROOT / "src" / "ai_engineering" / "templates" / "project"
    for surface in TEMPLATE_HANDLER_SURFACES:
        text = _read(template_root / surface / BUILD_HANDLER_REL)
        for marker in _ADVISORY_MARKERS:
            assert marker in text, f"{surface}:{marker}"
