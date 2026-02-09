"""Ownership-safe updater for framework-managed content."""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any

from ai_engineering.__version__ import __version__
from ai_engineering.installer.templates import TEMPLATE_MAPPINGS
from ai_engineering.paths import repo_root, state_dir
from ai_engineering.state.io import append_ndjson, load_model
from ai_engineering.state.models import InstallManifest, OwnershipMap


def _candidate_paths(path: str) -> set[str]:
    candidates = {path}
    prefix = ".ai-engineering/"
    if path.startswith(prefix):
        candidates.add(path[len(prefix) :])
    else:
        candidates.add(prefix + path)
    return candidates


def _matches(pattern: str, path: str) -> bool:
    path_candidates = _candidate_paths(path)
    pattern_candidates = _candidate_paths(pattern)
    return any(
        fnmatch.fnmatch(candidate, candidate_pattern)
        for candidate in path_candidates
        for candidate_pattern in pattern_candidates
    )


def _rule_for_path(ownership: OwnershipMap, path: str) -> tuple[str, str] | None:
    for rule in ownership.paths:
        if _matches(rule.pattern, path):
            return rule.owner, rule.frameworkUpdate
    return None


def run_update(*, apply: bool) -> dict[str, Any]:
    """Run framework-managed update process.

    Updates only files allowed by ownership-map rules.
    """

    root = repo_root()
    st = state_dir(root)
    ownership = load_model(st / "ownership-map.json", OwnershipMap)
    manifest = load_model(st / "install-manifest.json", InstallManifest)

    entries: list[dict[str, str]] = []
    summary = {
        "updated": 0,
        "created": 0,
        "unchanged": 0,
        "skippedDenied": 0,
        "missingTemplate": 0,
    }

    for source_relative, destination_relative in TEMPLATE_MAPPINGS:
        source = Path(__file__).resolve().parent.parent / "templates" / source_relative
        destination = root / destination_relative
        rule = _rule_for_path(ownership, destination_relative)

        if not source.exists():
            summary["missingTemplate"] += 1
            entries.append({"path": destination_relative, "status": "missing-template"})
            continue

        if rule is None:
            summary["skippedDenied"] += 1
            entries.append({"path": destination_relative, "status": "skipped-no-rule"})
            continue

        owner, mode = rule
        if mode == "deny":
            summary["skippedDenied"] += 1
            entries.append({"path": destination_relative, "status": f"skipped-{owner}"})
            continue

        source_content = source.read_text(encoding="utf-8")
        if destination.exists():
            current_content = destination.read_text(encoding="utf-8")
            if current_content == source_content:
                summary["unchanged"] += 1
                entries.append({"path": destination_relative, "status": "unchanged"})
                continue
            if apply:
                destination.write_text(source_content, encoding="utf-8")
            summary["updated"] += 1
            entries.append({"path": destination_relative, "status": "updated"})
        else:
            if apply:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(source_content, encoding="utf-8")
            summary["created"] += 1
            entries.append({"path": destination_relative, "status": "created"})

    if apply:
        manifest.frameworkVersion = __version__
        manifest_path = st / "install-manifest.json"
        manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")

        append_ndjson(
            st / "audit-log.ndjson",
            {
                "event": "framework_update_applied",
                "actor": "updater",
                "details": {
                    "frameworkVersion": __version__,
                    "summary": summary,
                },
            },
        )

    return {
        "repo": str(root),
        "apply": apply,
        "frameworkVersion": __version__,
        "summary": summary,
        "entries": entries,
    }
