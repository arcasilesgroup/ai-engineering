import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BRAND = ROOT / ".ai-engineering" / "reference" / "brand-voice.md"

PII_PATTERNS = (
    r"/Users/[a-z][a-z0-9_-]+/",
    r"/home/(?!runner/)[a-z][a-z0-9_-]+/",
    r"C:\\Users\\[A-Za-z][A-Za-z0-9_-]+\\",
    r"the operator (said|reported|noted|asked|wants|requested)",
    r"the user (said|reported|noted|asked|wants|requested)",
    r"in conversation with",
)


def test_brand_voice_reference_exists_and_cites_design_sources() -> None:
    text = BRAND.read_text(encoding="utf-8")
    for needle in (
        "docs/design.pen:",
        "docs/untitled.pen:",
        # spec-153 W3: the design-intent doc was reaped into the uniform
        # per-spec archive directory (D-153-06); the brand-voice reference
        # tracks its canonical archived home.
        ".ai-engineering/specs/archive/spec-144-readme-rewrite-and-branch-cleanup-rename/design-intent.md",
    ):
        assert needle in text


def test_brand_voice_declares_terminal_native_rules() -> None:
    text = BRAND.read_text(encoding="utf-8")
    for needle in (
        "{ai} engineering",
        "code-comment headers",
        "mid-dot stat line",
        "[PASS]",
        "[WARN]",
        "[FAIL]",
        "[PENDING]",
        "no emoji",
        "bash fences",
        "yaml fences",
    ):
        assert needle in text


def test_brand_voice_uses_anonymous_content() -> None:
    text = BRAND.read_text(encoding="utf-8")
    for pattern in PII_PATTERNS:
        assert re.search(pattern, text) is None, f"forbidden anonymous-content pattern: {pattern}"
