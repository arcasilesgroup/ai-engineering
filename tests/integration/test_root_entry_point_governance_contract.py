"""RED-phase test for spec-116 T-2.1 - governed root-surface metadata contract.

Spec acceptance:
    The governed root entry-point surfaces ``AGENTS.md``, ``CLAUDE.md``,
    ``GEMINI.md``, and ``.github/copilot-instructions.md`` must remain modeled
    explicitly in ``ownership.root_entry_points`` for both the live manifest and
    the template manifest.

Verifiable by
``test_root_entry_points_have_explicit_ownership_and_sync_contract`` which
asserts:

1. ``ownership.root_entry_points`` lists exactly the four governed root
   surfaces.
2. Each entry still has non-empty ``owner`` and ``canonical_source`` fields.
3. The old prose-only sync contract is replaced by machine-readable metadata:
   non-empty ``runtime_role`` and a ``sync`` mapping with exact ``mode``,
   ``template_path``, and ``mirror_paths`` values.

Status: RED. The current manifests still expose ``sync_mechanism`` prose and do
not yet carry the structured ``runtime_role`` + ``sync`` contract, so this test
deliberately fails until spec-116 lands the manifest and sync updates.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST_PATH = REPO_ROOT / ".ai-engineering" / "manifest.yml"
TEMPLATE_MANIFEST_PATH = (
    REPO_ROOT / "src" / "ai_engineering" / "templates" / ".ai-engineering" / "manifest.yml"
)

EXPECTED_ROOT_ENTRY_POINTS = {
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".github/copilot-instructions.md",
}

REQUIRED_STRING_FIELDS = (
    "owner",
    "canonical_source",
)

EXPECTED_ROOT_ENTRY_POINT_METADATA = {
    "CLAUDE.md": {
        "runtime_role": "ide-overlay",
        "sync": {
            "mode": "copy",
            "template_path": "src/ai_engineering/templates/project/CLAUDE.md",
            "mirror_paths": [],
        },
    },
    "AGENTS.md": {
        "runtime_role": "shared-runtime-contract",
        "sync": {
            "mode": "generate",
            "template_path": "src/ai_engineering/templates/project/AGENTS.md",
            "mirror_paths": [],
        },
    },
    "GEMINI.md": {
        "runtime_role": "ide-overlay",
        "sync": {
            "mode": "render",
            "template_path": "src/ai_engineering/templates/project/GEMINI.md",
            "mirror_paths": [".gemini/GEMINI.md"],
        },
    },
    ".github/copilot-instructions.md": {
        "runtime_role": "ide-overlay",
        "sync": {
            "mode": "generate",
            "template_path": "src/ai_engineering/templates/project/copilot-instructions.md",
            "mirror_paths": [],
        },
    },
}


def _assert_root_entry_point_contract(manifest_path: Path, label: str) -> None:
    """Assert a manifest-like file carries the explicit root surface contract.

    The contract must live in ``ownership.root_entry_points`` because
    ``manifest.yml`` is the configuration source of truth and already owns the
    broader framework ownership model. Each governed root surface must appear
    exactly once with enough metadata to answer, deterministically:

    - who owns the surface,
    - what the canonical source is, and
    - what runtime role it serves, and
    - how structured sync metadata keeps it aligned.
    """
    assert manifest_path.is_file(), (
        f"Expected manifest source at {label}, but it is missing. The governed "
        "entry-point contract cannot be validated without the manifest source "
        "of truth."
    )

    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    ownership = manifest.get("ownership")

    assert isinstance(ownership, dict), (
        "Manifest must define an ownership section before governed root entry "
        "points can be validated."
    )

    root_entry_points = ownership.get("root_entry_points")
    assert isinstance(root_entry_points, dict), (
        "Manifest must define ownership.root_entry_points as an explicit "
        "mapping for governed root entry points. Expected exactly these keys: "
        "['.github/copilot-instructions.md', 'AGENTS.md', 'CLAUDE.md', "
        "'GEMINI.md'], each with owner, canonical_source, runtime_role, and a "
        "structured sync mapping. Broad ownership globs and prose-only sync "
        "metadata are not a sufficient contract for spec-116."
    )

    contract_issues: list[str] = []
    actual_paths = set(root_entry_points)

    missing_paths = sorted(EXPECTED_ROOT_ENTRY_POINTS - actual_paths)
    extra_paths = sorted(actual_paths - EXPECTED_ROOT_ENTRY_POINTS)

    if missing_paths:
        contract_issues.append(f"missing governed paths: {missing_paths}")
    if extra_paths:
        contract_issues.append(f"unexpected governed paths: {extra_paths}")

    for entry_path in sorted(EXPECTED_ROOT_ENTRY_POINTS & actual_paths):
        entry_contract = root_entry_points[entry_path]
        if not isinstance(entry_contract, dict):
            contract_issues.append(
                f"{entry_path}: expected mapping, found {type(entry_contract).__name__}"
            )
            continue

        missing_fields = [
            field
            for field in REQUIRED_STRING_FIELDS
            if not isinstance(entry_contract.get(field), str) or not entry_contract[field].strip()
        ]
        if missing_fields:
            contract_issues.append(
                f"{entry_path}: missing non-empty contract fields {missing_fields}"
            )

        expected_metadata = EXPECTED_ROOT_ENTRY_POINT_METADATA[entry_path]

        runtime_role = entry_contract.get("runtime_role")
        if not isinstance(runtime_role, str) or not runtime_role.strip():
            contract_issues.append(f"{entry_path}: missing non-empty runtime_role string")
        elif runtime_role != expected_metadata["runtime_role"]:
            contract_issues.append(
                f"{entry_path}: runtime_role={runtime_role!r}, expected "
                f"{expected_metadata['runtime_role']!r}"
            )

        sync_contract = entry_contract.get("sync")
        if not isinstance(sync_contract, dict):
            contract_issues.append(f"{entry_path}: missing structured sync mapping")
            continue

        expected_sync = expected_metadata["sync"]
        mode = sync_contract.get("mode")
        if not isinstance(mode, str) or not mode.strip():
            contract_issues.append(f"{entry_path}: sync.mode must be a non-empty string")
        elif mode != expected_sync["mode"]:
            contract_issues.append(
                f"{entry_path}: sync.mode={mode!r}, expected {expected_sync['mode']!r}"
            )

        template_path = sync_contract.get("template_path")
        if not isinstance(template_path, str) or not template_path.strip():
            contract_issues.append(f"{entry_path}: sync.template_path must be a non-empty string")
        elif template_path != expected_sync["template_path"]:
            contract_issues.append(
                f"{entry_path}: sync.template_path={template_path!r}, expected "
                f"{expected_sync['template_path']!r}"
            )

        mirror_paths = sync_contract.get("mirror_paths")
        if not isinstance(mirror_paths, list):
            contract_issues.append(f"{entry_path}: sync.mirror_paths must be a list")
        elif any(
            not isinstance(mirror_path, str) or not mirror_path.strip()
            for mirror_path in mirror_paths
        ):
            contract_issues.append(
                f"{entry_path}: sync.mirror_paths must contain only non-empty strings"
            )
        elif mirror_paths != expected_sync["mirror_paths"]:
            contract_issues.append(
                f"{entry_path}: sync.mirror_paths={mirror_paths!r}, expected "
                f"{expected_sync['mirror_paths']!r}"
            )

    assert not contract_issues, (
        "Governed root entry points must have exactly one explicit ownership "
        f"and sync contract in {label}. Found contract issues: "
        f"{contract_issues}."
    )


def test_root_entry_points_have_explicit_ownership_and_sync_contract() -> None:
    """The live repo manifest declares one explicit contract per root entry point."""
    _assert_root_entry_point_contract(
        MANIFEST_PATH,
        ".ai-engineering/manifest.yml",
    )


def test_template_manifest_carries_same_root_entry_point_contract() -> None:
    """The install template manifest carries the same root entry-point contract."""
    _assert_root_entry_point_contract(
        TEMPLATE_MANIFEST_PATH,
        "src/ai_engineering/templates/.ai-engineering/manifest.yml",
    )
