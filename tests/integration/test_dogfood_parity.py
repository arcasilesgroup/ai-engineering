"""Acceptance gate: source-repo dogfooded configs match shipped templates.

spec-132 D-132-16: the source repo MUST dogfood its own consumer-facing
secret-scan and SAST configuration. ``.gitleaks.toml`` and ``.semgrep.yml``
at the source-repo root are required to be byte-equivalent to the versions
shipped under ``src/ai_engineering/templates/project/`` so that a fresh
consumer install can never pass a stricter ruleset than the framework
itself enforces internally.

Intentional drift is allowed only when BOTH files contain a marker line of
the shape ``# AIENG_DOGFOOD_DRIFT_OK: <reason>`` with matching reason text
in the source-repo file and the template. Any other divergence fails this
test and surfaces during ``pytest tests/integration/`` so the dogfood
guarantee cannot regress silently.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_ROOT = REPO_ROOT / "src" / "ai_engineering" / "templates" / "project"

_DRIFT_MARKER = re.compile(r"#\s*AIENG_DOGFOOD_DRIFT_OK:\s*(?P<reason>.+)$", re.MULTILINE)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _drift_reason(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    match = _DRIFT_MARKER.search(text)
    return match.group("reason").strip() if match else None


@pytest.mark.parametrize(
    ("source_relpath", "template_relpath"),
    [
        (".gitleaks.toml", "src/ai_engineering/templates/project/.gitleaks.toml"),
        (".semgrep.yml", "src/ai_engineering/templates/project/.semgrep.yml"),
        ("SOUL.md", "src/ai_engineering/templates/project/SOUL.md"),
    ],
    ids=["gitleaks", "semgrep", "soul"],
)
def test_source_config_matches_template(source_relpath: str, template_relpath: str) -> None:
    """spec-132 D-132-16: source-repo configs are byte-equivalent to templates."""
    source = REPO_ROOT / source_relpath
    template = REPO_ROOT / template_relpath

    assert source.exists(), f"Source-repo config missing: {source_relpath}"
    assert template.exists(), f"Template config missing: {template_relpath}"

    source_hash = _sha256(source)
    template_hash = _sha256(template)

    if source_hash == template_hash:
        return

    # Drift permitted only when BOTH files carry a matching reason marker.
    source_reason = _drift_reason(source)
    template_reason = _drift_reason(template)

    assert source_reason is not None and template_reason is not None, (
        f"Dogfood parity broken: {source_relpath} (sha256={source_hash}) differs from "
        f"{template_relpath} (sha256={template_hash}). Sync the source-repo file to "
        "match the template, or add matching `# AIENG_DOGFOOD_DRIFT_OK: <reason>` "
        "markers in BOTH files (spec-132 D-132-16)."
    )
    assert source_reason == template_reason, (
        f"Dogfood drift reason mismatch for {source_relpath}: "
        f"source='{source_reason}' vs template='{template_reason}'. "
        "Both files must carry the same reason text."
    )
