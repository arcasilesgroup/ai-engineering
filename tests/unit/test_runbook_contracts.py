from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUNBOOK_ROOT = ROOT / ".ai-engineering" / "runbooks"
TEMPLATE_ROOT = ROOT / "src" / "ai_engineering" / "templates" / ".ai-engineering" / "runbooks"
RUNBOOK_INDEX = ROOT / ".ai-engineering" / "reference" / "runbook-index.md"
RUNBOOK_INDEX_TEMPLATE = (
    ROOT
    / "src"
    / "ai_engineering"
    / "templates"
    / ".ai-engineering"
    / "reference"
    / "runbook-index.md"
)

# spec-085 + spec-091: 14 runbooks with minimal frontmatter schema
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
    "work-item-audit",
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
    "## Objective",
    "## Prerequisites",
    "## Procedure",
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


@pytest.mark.parametrize("name", ALL_RUNBOOKS)
def test_runbook_template_byte_parity(name: str) -> None:
    """Each live runbook must be byte-identical to its install-template twin.

    Guards the silent drift fixed in PR #585: a live edit (e.g. a header
    translation) that never reached ``src/ai_engineering/templates/`` would
    ship stale content (Spanish headers) to downstream installs. The two trees
    have no auto-sync, so only this assertion catches the gap.
    (spec runbook-template-parity D-runbook-template-parity-02.)
    """
    live = RUNBOOK_ROOT / f"{name}.md"
    template = TEMPLATE_ROOT / f"{name}.md"
    assert live.read_bytes() == template.read_bytes(), (
        f"runbook drift: {name}.md differs between .ai-engineering/runbooks/ "
        f"and the install template at "
        f"src/ai_engineering/templates/.ai-engineering/runbooks/ — "
        f"re-sync the template twin."
    )


# spec-187 W4: a discovery index ties every runbook to its type/cadence/purpose
# so the 14 consumer-shipped survivors are not operationally orphaned.
_INDEX_LINK_RE = re.compile(r"\]\(\.\./runbooks/([a-z0-9-]+)\.md\)")


def test_runbook_index_exists() -> None:
    assert RUNBOOK_INDEX.is_file(), f"runbook discovery index missing: {RUNBOOK_INDEX}"


def test_runbook_index_lists_all_survivors() -> None:
    """The index must link exactly the 14 ALL_RUNBOOKS survivors, no extras."""
    text = RUNBOOK_INDEX.read_text(encoding="utf-8")
    linked = {m.group(1) for m in _INDEX_LINK_RE.finditer(text)}
    assert linked == set(ALL_RUNBOOKS), (
        f"runbook-index drift: linked {sorted(linked)} != survivors {sorted(ALL_RUNBOOKS)}"
    )


def test_runbook_index_links_resolve() -> None:
    """Every runbook linked from the index resolves to a real file."""
    text = RUNBOOK_INDEX.read_text(encoding="utf-8")
    for stem in _INDEX_LINK_RE.findall(text):
        target = (RUNBOOK_INDEX.parent / ".." / "runbooks" / f"{stem}.md").resolve()
        assert target.is_file(), f"runbook-index links missing file: {stem}.md"


def test_runbook_index_ascii_only() -> None:
    """The index is ASCII-only (D-187-10 safe-output posture)."""
    text = RUNBOOK_INDEX.read_text(encoding="utf-8")
    assert text.isascii(), "runbook-index.md must be ASCII-only"


def test_runbook_index_template_byte_parity() -> None:
    """The index and its install-template twin must be byte-identical."""
    assert RUNBOOK_INDEX_TEMPLATE.is_file(), (
        f"runbook-index template twin missing: {RUNBOOK_INDEX_TEMPLATE}"
    )
    assert RUNBOOK_INDEX.read_bytes() == RUNBOOK_INDEX_TEMPLATE.read_bytes(), (
        "runbook-index.md differs from its install-template twin — re-sync."
    )
