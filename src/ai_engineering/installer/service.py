"""Installer service for .ai-engineering bootstrap."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.__version__ import __version__
from ai_engineering.hooks.manager import install_placeholder_hooks
from ai_engineering.paths import ai_engineering_root, repo_root, state_dir
from ai_engineering.installer.templates import sync_templates
from ai_engineering.state.defaults import (
    decision_store_default,
    install_manifest_default,
    ownership_map_default,
    sources_lock_default,
)
from ai_engineering.state.io import append_ndjson, write_json


def ensure_layout(root: Path) -> Path:
    """Ensure baseline directory layout exists."""
    ae_root = ai_engineering_root(root)
    for relative in (
        "context/product",
        "context/delivery",
        "context/backlog",
        "standards/framework/stacks",
        "standards/framework/quality",
        "standards/team/stacks",
        "skills/utils",
        "skills/validation",
        "state",
    ):
        (ae_root / relative).mkdir(parents=True, exist_ok=True)
    return ae_root


def bootstrap_state_files(root: Path) -> dict[str, str]:
    """Create missing system-managed state files."""
    st = state_dir(root)
    created: dict[str, str] = {}
    payloads = {
        "install-manifest.json": install_manifest_default(framework_version=__version__),
        "ownership-map.json": ownership_map_default(),
        "sources.lock.json": sources_lock_default(),
        "decision-store.json": decision_store_default(),
    }
    for file_name, payload in payloads.items():
        destination = st / file_name
        if not destination.exists():
            write_json(destination, payload)
            created[file_name] = "created"
        else:
            created[file_name] = "exists"

    audit_path = st / "audit-log.ndjson"
    if not audit_path.exists():
        append_ndjson(
            audit_path,
            {
                "event": "state_initialized",
                "actor": "installer",
                "details": {"files": list(payloads.keys()) + ["audit-log.ndjson"]},
            },
        )
        created["audit-log.ndjson"] = "created"
    else:
        created["audit-log.ndjson"] = "exists"
    return created


def install() -> dict[str, object]:
    """Run installer flow for current repository."""
    root = repo_root()
    ae_root = ensure_layout(root)
    created_state = bootstrap_state_files(root)
    template_result = sync_templates(root)
    install_placeholder_hooks(root)
    return {
        "repo": str(root),
        "aiEngineeringRoot": str(ae_root),
        "state": created_state,
        "templates": template_result,
    }
