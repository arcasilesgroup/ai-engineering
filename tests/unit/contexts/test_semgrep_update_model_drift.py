"""spec-141 M4 — `semgrep-update-model.md` drift gate.

External research (see brief §3 and §12) confirmed that the prior doc
described **invented** Semgrep YAML:

- `extends:` is NOT a documented Semgrep top-level YAML key. The
  canonical mechanism for combining packs is repeated `--config` flags
  (https://semgrep.dev/docs/running-rules).
- `p/<name>@1.96.0` version pinning is NOT documented Semgrep syntax.
  Pack aliases resolve to the live HEAD of `semgrep/semgrep-rules`;
  reproducibility comes from pinning the Semgrep CLI version.

This test forbids the forbidden patterns from re-entering the doc on
any future edit. Failing the test = the doc has drifted back to
inventions and the spec-141 M4 rewrite is being silently undone.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

DOC_PATHS = [
    REPO_ROOT / ".ai-engineering" / "reference" / "semgrep-update-model.md",
    REPO_ROOT
    / "src"
    / "ai_engineering"
    / "templates"
    / ".ai-engineering"
    / "reference"
    / "semgrep-update-model.md",
]


def test_no_extends_block_in_semgrep_doc() -> None:
    """spec-141 M4 — `extends:` is not documented Semgrep syntax."""
    hits: list[str] = []
    for path in DOC_PATHS:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        if "extends:" in content:
            hits.append(str(path.relative_to(REPO_ROOT)))
    assert not hits, (
        f"Forbidden `extends:` pattern in semgrep doc(s): {hits}. "
        "Per spec-141 D-141-01, the canonical multi-pack syntax is "
        "repeated `--config p/<name>` flags, not a YAML extends block. "
        "See https://semgrep.dev/docs/running-rules."
    )


def test_no_version_pin_pattern_in_semgrep_doc() -> None:
    """spec-141 M4 — `p/<name>@1.<n>` is not documented Semgrep syntax."""
    hits: list[str] = []
    for path in DOC_PATHS:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        if "@1." in content:
            hits.append(str(path.relative_to(REPO_ROOT)))
    assert not hits, (
        f"Forbidden `@1.<n>` pack-version-pin pattern in semgrep doc(s): {hits}. "
        "Per spec-141 D-141-01, pack aliases roll forward from HEAD; "
        "the deterministic anchor is pinning the Semgrep CLI version, "
        "not the pack alias. See https://semgrep.dev/docs/cli-reference."
    )
