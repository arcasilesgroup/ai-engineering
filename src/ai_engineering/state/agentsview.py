"""agentsview source contract artifacts for spec-082.

Spec-125: the framework capability catalog moved from
``framework-capabilities.json`` to the ``tool_capabilities`` singleton
row in state.db. The agentsview fixture-bundle exporter materializes a
snapshot of the row into a JSON file inside *output_dir* so external
tools that consume the bundle still see a discoverable artifact -- but
the canonical source-of-truth lives in state.db.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ai_engineering.state.observability import (
    FRAMEWORK_EVENTS_REL,
    framework_events_path,
    write_framework_capabilities,
)

AGENTSVIEW_CONTRACT_VERSION = "1.0"
AGENTSVIEW_SOURCE_NAME = "ai-engineering-framework-events"

# Spec-125: framework capabilities now live in the ``tool_capabilities``
# singleton row inside state.db. The agentsview contract advertises the
# canonical SQLite projection so downstream consumers point at the
# source-of-truth; fixture-bundle exports still materialize a portable
# JSON snapshot via ``_materialize_capabilities_snapshot`` for offline
# viewers, but the contract URI itself references state.db.
_FRAMEWORK_CAPABILITIES_ARTIFACT_REL = ".ai-engineering/state/state.db"
_FRAMEWORK_CAPABILITIES_SNAPSHOT_FILENAME = "framework-capabilities.json"


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
            "capabilities": _FRAMEWORK_CAPABILITIES_ARTIFACT_REL,
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


def _materialize_capabilities_snapshot(project_root: Path, dest: Path) -> Path:
    """Write a JSON snapshot of the tool_capabilities row to *dest*.

    Spec-125: source-of-truth lives in state.db; this exports a
    point-in-time snapshot for fixture-bundle consumers.
    """
    from ai_engineering.state.repository import DurableStateRepository

    catalog = DurableStateRepository(project_root).load_framework_capabilities()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(catalog.model_dump_json(by_alias=True, indent=2) + "\n", encoding="utf-8")
    return dest


def write_agentsview_fixture_bundle(project_root: Path, output_dir: Path) -> dict[str, Path]:
    """Write a fixture bundle containing the contract and canonical artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)

    events_path = framework_events_path(project_root)
    # Always refresh the state.db row so the snapshot is current; the
    # writer is idempotent thanks to the singleton UPSERT contract.
    write_framework_capabilities(project_root)
    if not events_path.exists():
        msg = f"Missing framework events at {events_path}"
        raise FileNotFoundError(msg)

    contract_path = write_agentsview_contract(output_dir / "agentsview-source-contract.json")
    copied_events = output_dir / "framework-events.ndjson"
    copied_capabilities = output_dir / "framework-capabilities.json"
    shutil.copy2(events_path, copied_events)
    _materialize_capabilities_snapshot(project_root, copied_capabilities)
    return {
        "contract": contract_path,
        "events": copied_events,
        "capabilities": copied_capabilities,
    }
