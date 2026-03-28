from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUNBOOK_ROOT = ROOT / ".ai-engineering" / "runbooks"
WORKFLOW_ROOT = ROOT / ".github" / "workflows"

PROVIDER_RUNBOOKS = (
    ("daily-triage", "ai-eng-daily-triage"),
    ("weekly-health", "ai-eng-weekly-health"),
    ("perf-audit", "ai-eng-perf-audit"),
)

REQUIRED_RUNBOOK_KEYS = {
    "runbook",
    "purpose",
    "host_adapters",
    "provider_scope",
    "feature_policy",
    "hierarchy_policy",
    "outputs",
    "handoff",
}

REQUIRED_SECTIONS = (
    "## Purpose",
    "## Host Adapter",
    "## Provider Actions",
    "## Guardrails",
    "## Procedure",
    "## Output",
)


def _split_frontmatter(path: Path) -> tuple[dict[str, object], str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} must start with YAML frontmatter"
    _delim, fm, body = text.split("---\n", 2)
    data = yaml.safe_load(fm)
    assert isinstance(data, dict), f"{path} frontmatter must parse as a mapping"
    return data, body


@pytest.mark.parametrize(("slug", "workflow_name"), PROVIDER_RUNBOOKS)
def test_provider_runbooks_are_self_contained_contracts(
    slug: str,
    workflow_name: str,
) -> None:
    path = RUNBOOK_ROOT / f"{slug}.md"
    frontmatter, body = _split_frontmatter(path)

    assert set(frontmatter) >= REQUIRED_RUNBOOK_KEYS
    assert frontmatter["runbook"] == slug
    assert frontmatter["feature_policy"] == "read-only"
    assert frontmatter["host_adapters"] == {"github_workflow": workflow_name}
    assert frontmatter["provider_scope"] == {
        "github": "issues",
        "azure_devops": "work_items",
    }

    outputs = frontmatter["outputs"]
    assert isinstance(outputs, dict)
    assert "provider_updates" in outputs
    assert "local_files" in outputs

    handoff = frontmatter["handoff"]
    assert isinstance(handoff, dict)
    assert handoff["lifecycle"] == "ready"
    assert handoff["local_execution"] == "manual only"

    for section in REQUIRED_SECTIONS:
        assert section in body


@pytest.mark.parametrize(("slug", "workflow_name"), PROVIDER_RUNBOOKS)
def test_github_workflow_adapters_reference_canonical_runbooks(
    slug: str,
    workflow_name: str,
) -> None:
    path = WORKFLOW_ROOT / f"{workflow_name}.md"
    frontmatter, body = _split_frontmatter(path)

    assert isinstance(frontmatter.get("name"), str)
    workflow_on = frontmatter.get("on", frontmatter.get(True))
    assert isinstance(workflow_on, dict)
    assert "workflow_dispatch" in workflow_on
    assert "permissions" in frontmatter
    assert f"Canonical contract: `.ai-engineering/runbooks/{slug}.md`" in body
    assert f"Read `.ai-engineering/runbooks/{slug}.md`." in body
    assert "local spec or plan" in body
