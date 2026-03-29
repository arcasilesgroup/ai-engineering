from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUNBOOK_ROOT = ROOT / ".ai-engineering" / "runbooks"
TEMPLATE_ROOT = ROOT / "src" / "ai_engineering" / "templates" / ".ai-engineering" / "runbooks"

# spec-085: 12 runbooks with minimal frontmatter schema
ALL_RUNBOOKS = [
    "triage",
    "refine",
    "feature-scanner",
    "stale-issues",
    "dependency-health",
    "code-quality",
    "consolidate",
    "security-scan",
    "docs-freshness",
    "performance",
    "governance-drift",
    "architecture-drift",
    "wiring-scanner",
]

REQUIRED_CONTRACT_KEYS = {
    "name",
    "description",
    "type",
    "cadence",
}

VALID_TYPES = {"intake", "operational"}
VALID_CADENCES = {"daily", "weekly"}

REQUIRED_SECTIONS = (
    "## Objetivo",
    "## Precondiciones",
    "## Procedimiento",
    "## Output",
    "## Guardrails",
)


def _split_frontmatter(path: Path) -> tuple[dict[str, object], str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} must start with YAML frontmatter"
    _delim, fm, body = text.split("---\n", 2)
    data = yaml.safe_load(fm)
    assert isinstance(data, dict), f"{path} frontmatter must parse as a mapping"
    return data, body


@pytest.mark.parametrize("slug", ALL_RUNBOOKS)
def test_runbook_exists(slug: str) -> None:
    path = RUNBOOK_ROOT / f"{slug}.md"
    assert path.exists(), f"Runbook {slug}.md not found"


@pytest.mark.parametrize("slug", ALL_RUNBOOKS)
def test_template_mirror_exists(slug: str) -> None:
    path = TEMPLATE_ROOT / f"{slug}.md"
    assert path.exists(), f"Template mirror {slug}.md not found"


@pytest.mark.parametrize("slug", ALL_RUNBOOKS)
def test_runbook_contract_schema(slug: str) -> None:
    path = RUNBOOK_ROOT / f"{slug}.md"
    frontmatter, body = _split_frontmatter(path)

    missing = REQUIRED_CONTRACT_KEYS - set(frontmatter)
    assert not missing, f"{slug}: missing contract keys: {missing}"
    unexpected = set(frontmatter) - REQUIRED_CONTRACT_KEYS
    assert not unexpected, f"{slug}: unexpected contract keys: {unexpected}"

    assert frontmatter["name"] == slug
    assert isinstance(frontmatter["description"], str)
    assert frontmatter["description"], f"{slug}: description must be non-empty"
    assert frontmatter["type"] in VALID_TYPES
    assert frontmatter["cadence"] in VALID_CADENCES

    for section in REQUIRED_SECTIONS:
        assert section in body, f"{slug}: missing section '{section}'"


@pytest.mark.parametrize("slug", ALL_RUNBOOKS)
def test_template_matches_canonical(slug: str) -> None:
    canonical = (RUNBOOK_ROOT / f"{slug}.md").read_bytes()
    template = (TEMPLATE_ROOT / f"{slug}.md").read_bytes()
    assert canonical == template, f"{slug}: template and canonical differ"


def test_runbook_count() -> None:
    actual = sorted(p.stem for p in RUNBOOK_ROOT.glob("*.md"))
    assert actual == sorted(ALL_RUNBOOKS), (
        f"Expected {len(ALL_RUNBOOKS)} runbooks, got {len(actual)}: {actual}"
    )


def test_no_legacy_runbooks() -> None:
    legacy = {
        "daily-triage",
        "weekly-health",
        "perf-audit",
        "code-simplifier",
        "dependency-upgrade",
        "governance-drift-repair",
        "incident-response",
        "security-incident",
    }
    actual = {p.stem for p in RUNBOOK_ROOT.glob("*.md")}
    overlap = legacy & actual
    assert not overlap, f"Legacy runbooks still present: {overlap}"


def test_no_workflow_adapters() -> None:
    adapters = list((ROOT / ".github" / "workflows").glob("ai-eng-*.md"))
    assert not adapters, f"Workflow adapters should be deleted: {[p.name for p in adapters]}"
