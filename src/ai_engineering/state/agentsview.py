"""agentsview source contract artifacts for spec-082."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ai_engineering.state.observability import (
    FRAMEWORK_CAPABILITIES_REL,
    FRAMEWORK_EVENTS_REL,
    framework_capabilities_path,
    framework_events_path,
    write_framework_capabilities,
)

AGENTSVIEW_CONTRACT_VERSION = "1.0"
AGENTSVIEW_SOURCE_NAME = "ai-engineering-framework-events"


def build_agentsview_contract() -> dict[str, object]:
    """Return the native source contract expected by agentsview."""
    return {
        "version": AGENTSVIEW_CONTRACT_VERSION,
        "source": AGENTSVIEW_SOURCE_NAME,
        "independent_install": True,
        "requires_project_config": False,
        "project_marker": ".ai-engineering/state",
        "artifacts": {
            "events": FRAMEWORK_EVENTS_REL.as_posix(),
            "capabilities": FRAMEWORK_CAPABILITIES_REL.as_posix(),
        },
        "privacy": {
            "includes_transcripts": False,
            "includes_raw_payloads": False,
            "network_export_by_default": False,
        },
        "discovery": {
            "expect_standard_ai_eng_install": True,
            "viewer_managed_by_ai_engineering": False,
        },
    }


def write_agentsview_contract(path: Path) -> Path:
    """Persist the agentsview contract as JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_agentsview_contract(), indent=2) + "\n", encoding="utf-8")
    return path


def write_agentsview_fixture_bundle(project_root: Path, output_dir: Path) -> dict[str, Path]:
    """Write a fixture bundle containing the contract and canonical artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)

    events_path = framework_events_path(project_root)
    capabilities_path = framework_capabilities_path(project_root)
    if not capabilities_path.exists():
        write_framework_capabilities(project_root)
    if not events_path.exists():
        msg = f"Missing framework events at {events_path}"
        raise FileNotFoundError(msg)

    contract_path = write_agentsview_contract(output_dir / "agentsview-source-contract.json")
    copied_events = output_dir / "framework-events.ndjson"
    copied_capabilities = output_dir / "framework-capabilities.json"
    shutil.copy2(events_path, copied_events)
    shutil.copy2(capabilities_path, copied_capabilities)
    return {
        "contract": contract_path,
        "events": copied_events,
        "capabilities": copied_capabilities,
    }
