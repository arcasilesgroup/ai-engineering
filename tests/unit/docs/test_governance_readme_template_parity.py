from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIVE = ROOT / ".ai-engineering" / "README.md"
TEMPLATE = ROOT / "src" / "ai_engineering" / "templates" / ".ai-engineering" / "README.md"


def _lf_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def test_governance_readme_template_is_byte_identical() -> None:
    assert LIVE.exists(), f"missing live governance README: {LIVE}"
    assert TEMPLATE.exists(), f"missing template governance README: {TEMPLATE}"
    assert _lf_bytes(LIVE) == _lf_bytes(TEMPLATE)
