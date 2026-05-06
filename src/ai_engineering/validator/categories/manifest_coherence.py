"""Category 6: Manifest Coherence — control-plane snapshots and manifests stay aligned."""

from __future__ import annotations

import re
from itertools import combinations
from pathlib import Path

import yaml

from ai_engineering.config.loader import load_manifest_root_entry_points
from ai_engineering.release.version_bump import detect_current_version
from ai_engineering.state.capabilities import (
    infer_mutation_classes,
    validate_task_packet_acceptance,
)
from ai_engineering.state.context_packs import (
    build_context_pack,
    context_pack_path,
    validate_context_pack_manifest,
)
from ai_engineering.state.defaults import default_ownership_map
from ai_engineering.state.io import read_json_model
from ai_engineering.state.models import (
    CapabilityKind,
    CapabilityTaskPacket,
    ContextPackManifest,
    FrameworkCapabilitiesCatalog,
    OwnershipMap,
    TaskLedger,
    TaskLedgerTask,
    TaskLifecycleState,
)
from ai_engineering.state.observability import build_framework_capabilities
from ai_engineering.state.work_plane import read_task_ledger, resolve_active_work_plane
from ai_engineering.validator._shared import (
    IntegrityCategory,
    IntegrityCheckResult,
    IntegrityReport,
    IntegrityStatus,
)

_AI_ENGINEERING_DIRNAME = ".ai-engineering"
_MANIFEST_FILENAME = "manifest.yml"
_TASK_LEDGER_FILE_PATH = "specs/task-ledger.json"
_PLAN_FILE_PATH = "specs/plan.md"
_AI_ENGINEERING_PATH_PREFIX = f"{_AI_ENGINEERING_DIRNAME}/"
_EXPECTED_SESSION_CONTEXT_FILES = [
    ".ai-engineering/LESSONS.md",
    "CONSTITUTION.md",
    ".ai-engineering/manifest.yml",
    ".ai-engineering/state/decision-store.json",
]
_EXPECTED_CONTROL_PLANE = {
    "constitutional_authority": {
        "primary": "CONSTITUTION.md",
        "compatibility_aliases": [],
    },
    "manifest_field_roles": {
        "canonical_input": [
            "providers",
            "ai_providers",
            "artifact_feeds",
            "work_items",
            "quality",
            "documentation",
            "cicd",
            "contexts.precedence",
            "session.context_files",
            "ownership.framework",
            "ownership.root_entry_points",
            "telemetry",
            "gates",
            "hot_path_slos",
        ],
        "generated_projection": ["skills", "agents"],
        "descriptive_metadata": ["schema_version", "framework_version", "name", "version"],
    },
}


def _read_framework_version(manifest_path: Path) -> str | None:
    if not manifest_path.is_file():
        return None

    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("framework_version:"):
            continue
        _, _, raw_value = stripped.partition(":")
        value = raw_value.strip().strip('"').strip("'")
        return value or None
    return None


def _template_manifest_path(target: Path) -> Path:
    return (
        target
        / "src"
        / "ai_engineering"
        / "templates"
        / _AI_ENGINEERING_DIRNAME
        / _MANIFEST_FILENAME
    )


def _read_manifest_payload(manifest_path: Path) -> dict[str, object]:
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Manifest payload must be a mapping: {manifest_path}")
    return payload


def _check_source_repo_control_plane_contract(target: Path, report: IntegrityReport) -> None:
    """Verify source-repo manifests carry the normalized control-plane contract."""
    template_manifest_path = _template_manifest_path(target)
    if not template_manifest_path.is_file():
        return

    manifest_path = target / _AI_ENGINEERING_DIRNAME / _MANIFEST_FILENAME
    try:
        root_manifest = _read_manifest_payload(manifest_path)
        template_manifest = _read_manifest_payload(template_manifest_path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="control-plane-authority-contract",
                status=IntegrityStatus.FAIL,
                message=f"Unable to read normalized control-plane manifest contract: {exc}",
                file_path=str(manifest_path.relative_to(target)),
            )
        )
        return

    mismatches: list[str] = []
    root_context = root_manifest.get("session", {}).get("context_files")
    if root_context != _EXPECTED_SESSION_CONTEXT_FILES:
        mismatches.append(
            "root manifest session.context_files drifted from the normalized authority contract"
        )

    template_context = template_manifest.get("session", {}).get("context_files")
    if template_context != _EXPECTED_SESSION_CONTEXT_FILES:
        mismatches.append(
            "template manifest session.context_files drifted from the normalized authority contract"
        )

    root_control_plane = root_manifest.get("control_plane")
    if root_control_plane != _EXPECTED_CONTROL_PLANE:
        mismatches.append(
            "root manifest control_plane table drifted from the normalized authority contract"
        )

    template_control_plane = template_manifest.get("control_plane")
    if template_control_plane != _EXPECTED_CONTROL_PLANE:
        mismatches.append(
            "template manifest control_plane table drifted from the normalized authority contract"
        )

    if mismatches:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="control-plane-authority-contract",
                status=IntegrityStatus.FAIL,
                message="; ".join(mismatches),
                file_path=str(manifest_path.relative_to(target)),
            )
        )
        return

    report.checks.append(
        IntegrityCheckResult(
            category=IntegrityCategory.MANIFEST_COHERENCE,
            name="control-plane-authority-contract",
            status=IntegrityStatus.OK,
            message="Root and template manifests carry the normalized control-plane authority contract",
        )
    )


def _check_source_repo_framework_versions(target: Path, report: IntegrityReport) -> None:
    """Verify bundled framework manifests match the package version in source checkouts."""
    template_manifest_path = _template_manifest_path(target)
    if not template_manifest_path.is_file():
        return

    try:
        package_version = detect_current_version(target)
    except (FileNotFoundError, ValueError) as exc:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="framework-version-source",
                status=IntegrityStatus.FAIL,
                message=f"Unable to read framework package version: {exc}",
                file_path="pyproject.toml",
            )
        )
        return

    manifests = [
        (target / _AI_ENGINEERING_DIRNAME / _MANIFEST_FILENAME, "framework-version-root"),
        (template_manifest_path, "framework-version-template"),
    ]
    for file_path, check_name in manifests:
        framework_version = _read_framework_version(file_path)
        relative_path = str(file_path.relative_to(target))
        if framework_version is None:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MANIFEST_COHERENCE,
                    name=check_name,
                    status=IntegrityStatus.FAIL,
                    message=f"framework_version not found in {relative_path}",
                    file_path=relative_path,
                )
            )
            continue

        if framework_version != package_version:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MANIFEST_COHERENCE,
                    name=check_name,
                    status=IntegrityStatus.FAIL,
                    message=(
                        f"{relative_path} framework_version is {framework_version}, "
                        f"expected {package_version} from pyproject.toml"
                    ),
                    file_path=relative_path,
                )
            )
            continue

        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name=check_name,
                status=IntegrityStatus.OK,
                message=f"{relative_path} framework_version matches pyproject.toml",
            )
        )


def _check_source_repo_ownership_snapshot(target: Path, report: IntegrityReport) -> None:
    """Verify the committed ownership snapshot matches the executable contract in source repos.

    spec-124 D-124-12: After ownership-map.json deletion, the canonical
    snapshot lives in state.db.ownership_map. When the JSON projection is
    absent we report OK (state.db is authoritative); when present we
    still validate JSON↔contract parity for backward compat.
    """
    template_manifest_path = _template_manifest_path(target)
    if not template_manifest_path.is_file():
        return

    ownership_path = target / _AI_ENGINEERING_DIRNAME / "state" / "ownership-map.json"
    relative_path = str(ownership_path.relative_to(target))
    if not ownership_path.exists():
        # JSON fallback was deleted in spec-124 wave 5; state.db is canonical.
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="ownership-map-snapshot",
                status=IntegrityStatus.OK,
                message=(
                    f"{relative_path} absent (spec-124 D-124-12); "
                    "state.db.ownership_map is canonical"
                ),
            )
        )
        return
    try:
        snapshot = read_json_model(ownership_path, OwnershipMap)
    except (OSError, ValueError) as exc:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="ownership-map-snapshot",
                status=IntegrityStatus.FAIL,
                message=f"Unable to read committed ownership snapshot: {exc}",
                file_path=relative_path,
            )
        )
        return

    expected = default_ownership_map(
        root_entry_points=load_manifest_root_entry_points(target),
    )
    if snapshot.model_dump(by_alias=True, exclude_none=True) != expected.model_dump(
        by_alias=True,
        exclude_none=True,
    ):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="ownership-map-snapshot",
                status=IntegrityStatus.FAIL,
                message=(f"{relative_path} does not match the computed default ownership contract"),
                file_path=relative_path,
            )
        )
        return

    report.checks.append(
        IntegrityCheckResult(
            category=IntegrityCategory.MANIFEST_COHERENCE,
            name="ownership-map-snapshot",
            status=IntegrityStatus.OK,
            message=f"{relative_path} matches the computed default ownership contract",
        )
    )


def _catalog_payload_without_timestamp(catalog: FrameworkCapabilitiesCatalog) -> dict[str, object]:
    """Normalize framework capabilities catalogs for semantic snapshot comparison."""
    payload = catalog.model_dump(by_alias=True, exclude_none=True)
    payload.pop("generatedAt", None)
    return payload


def _context_pack_payload_without_timestamp(pack: ContextPackManifest) -> dict[str, object]:
    """Normalize context-pack manifests for semantic snapshot comparison."""
    payload = pack.model_dump(by_alias=True, exclude_none=True)
    payload.pop("generatedAt", None)
    return payload


def _check_source_repo_framework_capabilities_snapshot(
    target: Path,
    report: IntegrityReport,
) -> None:
    """Verify the framework capabilities catalog stored in state.db matches the semantic builder output.

    Spec-125 D-125-01: the framework-capabilities catalog moved from a JSON
    snapshot at `state/framework-capabilities.json` to the
    `tool_capabilities` singleton row in state.db.
    """
    template_manifest_path = _template_manifest_path(target)
    if not template_manifest_path.is_file():
        return

    from ai_engineering.state.repository import DurableStateRepository

    relative_path = ".ai-engineering/state/state.db (tool_capabilities)"
    try:
        snapshot = DurableStateRepository(target).load_framework_capabilities()
    except (OSError, ValueError) as exc:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="framework-capabilities-snapshot",
                status=IntegrityStatus.FAIL,
                message=f"Unable to read framework capabilities from state.db: {exc}",
                file_path=relative_path,
            )
        )
        return

    expected = build_framework_capabilities(target)
    if _catalog_payload_without_timestamp(snapshot) != _catalog_payload_without_timestamp(expected):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="framework-capabilities-snapshot",
                status=IntegrityStatus.FAIL,
                message=(
                    f"{relative_path} does not match the computed framework capabilities contract"
                ),
                file_path=relative_path,
            )
        )
        return

    report.checks.append(
        IntegrityCheckResult(
            category=IntegrityCategory.MANIFEST_COHERENCE,
            name="framework-capabilities-snapshot",
            status=IntegrityStatus.OK,
            message=(f"{relative_path} matches the computed framework capabilities contract"),
        )
    )


def _check_source_repo_capability_card_contract(target: Path, report: IntegrityReport) -> None:
    """Verify generated capability cards cover every first-class skill and agent."""
    template_manifest_path = _template_manifest_path(target)
    if not template_manifest_path.is_file():
        return

    catalog = build_framework_capabilities(target)
    expected_skill_names = {entry.name for entry in catalog.skills}
    expected_agent_names = {entry.name for entry in catalog.agents}
    actual_skill_names = {
        card.name
        for card in catalog.capability_cards
        if card.capability_kind == CapabilityKind.SKILL
    }
    actual_agent_names = {
        card.name
        for card in catalog.capability_cards
        if card.capability_kind == CapabilityKind.AGENT
    }

    mismatches: list[str] = []
    missing_skills = sorted(expected_skill_names - actual_skill_names)
    if missing_skills:
        mismatches.append("missing skill cards: " + ", ".join(missing_skills))
    extra_skills = sorted(actual_skill_names - expected_skill_names)
    if extra_skills:
        mismatches.append("extra skill cards: " + ", ".join(extra_skills))
    missing_agents = sorted(expected_agent_names - actual_agent_names)
    if missing_agents:
        mismatches.append("missing agent cards: " + ", ".join(missing_agents))
    extra_agents = sorted(actual_agent_names - expected_agent_names)
    if extra_agents:
        mismatches.append("extra agent cards: " + ", ".join(extra_agents))

    if mismatches:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="capability-card-contract",
                status=IntegrityStatus.FAIL,
                message="; ".join(mismatches),
                file_path=f"{_AI_ENGINEERING_PATH_PREFIX}manifest.yml",
            )
        )
        return

    report.checks.append(
        IntegrityCheckResult(
            category=IntegrityCategory.MANIFEST_COHERENCE,
            name="capability-card-contract",
            status=IntegrityStatus.OK,
            message="Capability cards cover every manifest skill and first-class agent",
        )
    )


def _check_manifest_coherence(target: Path, report: IntegrityReport, **_kwargs: object) -> None:
    """Verify manifest ownership globs and active spec pointer."""
    ai_dir = target / _AI_ENGINEERING_DIRNAME
    manifest_path = ai_dir / _MANIFEST_FILENAME

    if not manifest_path.exists():
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="manifest-missing",
                status=IntegrityStatus.FAIL,
                message=f"{_MANIFEST_FILENAME} not found",
            )
        )
        return

    # Check ownership directory structure exists
    # Note: skills/ and agents/ no longer live under .ai-engineering/ —
    # they have moved to IDE-specific directories (.claude/, .codex/, .gemini/).
    ownership_dirs = [
        ("contexts", "framework_managed"),
        ("state", "system_managed"),
    ]

    for dir_rel, category in ownership_dirs:
        dir_path = ai_dir / dir_rel
        if not dir_path.is_dir():
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MANIFEST_COHERENCE,
                    name=f"missing-dir-{dir_rel}",
                    status=IntegrityStatus.FAIL,
                    message=f"{category} directory not found: {dir_rel}",
                    file_path=f"{_AI_ENGINEERING_PATH_PREFIX}{dir_rel}",
                )
            )
        else:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MANIFEST_COHERENCE,
                    name=f"dir-{dir_rel}",
                    status=IntegrityStatus.OK,
                    message=f"{category} directory exists: {dir_rel}",
                )
            )

    _check_source_repo_framework_versions(target, report)
    _check_source_repo_control_plane_contract(target, report)
    _check_source_repo_ownership_snapshot(target, report)
    _check_source_repo_framework_capabilities_snapshot(target, report)
    _check_source_repo_capability_card_contract(target, report)

    # Verify Working Buffer spec file
    spec_path = resolve_active_work_plane(target).spec_path
    if spec_path.exists():
        content = spec_path.read_text(encoding="utf-8", errors="replace")
        if content.strip().startswith("# No active spec"):
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MANIFEST_COHERENCE,
                    name="active-spec",
                    status=IntegrityStatus.OK,
                    message="No active spec (idle)",
                )
            )
            _record_placeholder_spec_ledger_coherence(target, report)
        else:
            report.checks.append(
                IntegrityCheckResult(
                    category=IntegrityCategory.MANIFEST_COHERENCE,
                    name="active-spec",
                    status=IntegrityStatus.OK,
                    message="Active spec present in specs/spec.md",
                )
            )
            _record_active_spec_plan_coherence(target, report)
            _record_task_ledger_activity(target, report)
    else:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="active-spec-pointer",
                status=IntegrityStatus.WARN,
                message="specs/spec.md not found",
            )
        )


def _record_placeholder_spec_ledger_coherence(target: Path, report: IntegrityReport) -> None:
    # Spec-123: task ledger removed. Function retained as defensive shim;
    # read_task_ledger always returns None so the body short-circuits.
    ledger = read_task_ledger(target)
    if ledger is None:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="active-task-ledger",
                status=IntegrityStatus.WARN,
                message="Active spec has no readable task-ledger.json",
                file_path=_TASK_LEDGER_FILE_PATH,
            )
        )
        return

    if any(task.status != TaskLifecycleState.DONE for task in ledger.tasks):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="active-spec-ledger-coherence",
                status=IntegrityStatus.FAIL,
                message=(
                    "Placeholder active spec conflicts with task-ledger.json "
                    "containing non-done tasks"
                ),
                file_path=_TASK_LEDGER_FILE_PATH,
            )
        )


def _record_task_ledger_activity(target: Path, report: IntegrityReport) -> None:
    # Spec-123: task ledger removed. read_task_ledger returns None
    # unconditionally; this function is retained as a defensive shim that
    # short-circuits cleanly so call sites need not be edited individually.
    ledger = read_task_ledger(target)
    if ledger is None:
        return

    if any(task.status != TaskLifecycleState.DONE for task in ledger.tasks):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="active-task-ledger",
                status=IntegrityStatus.OK,
                message="Active spec has at least one non-done task in task-ledger.json",
                file_path=_TASK_LEDGER_FILE_PATH,
            )
        )
    else:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="active-task-ledger",
                status=IntegrityStatus.WARN,
                message="Active spec has no non-done tasks in task-ledger.json",
                file_path=_TASK_LEDGER_FILE_PATH,
            )
        )

    _record_task_artifact_reference_validation(target, ledger, report)
    _record_task_write_scope_duplicate_validation(ledger, report)
    _record_task_lifecycle_artifact_validation(ledger, report)
    _record_task_capability_acceptance_validation(target, ledger, report)
    _record_context_pack_manifest_validation(target, ledger, report)

    if _record_task_dependency_validation(ledger, report):
        _record_task_state_consistency(ledger, report)


def _record_context_pack_manifest_validation(
    target: Path,
    ledger: TaskLedger,
    report: IntegrityReport,
) -> None:
    active_tasks = [task for task in ledger.tasks if task.status != TaskLifecycleState.DONE]
    if not active_tasks:
        return

    missing: list[str] = []
    failures: list[str] = []
    checked = 0
    for task in active_tasks:
        pack_path = context_pack_path(target, task.id)
        relative_path = _project_relative_path(target, pack_path)
        if not pack_path.is_file():
            missing.append(f"{task.id}: {relative_path}")
            continue

        try:
            actual = validate_context_pack_manifest(read_json_model(pack_path, ContextPackManifest))
            expected = build_context_pack(target, task_id=task.id)
        except (OSError, ValueError) as exc:
            failures.append(f"{task.id}: unable to read context pack: {exc}")
            continue

        if _context_pack_payload_without_timestamp(
            actual
        ) != _context_pack_payload_without_timestamp(expected):
            failures.append(f"{task.id}: {relative_path} does not match deterministic pack output")
            continue
        checked += 1

    if failures:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="context-pack-manifest-contract",
                status=IntegrityStatus.FAIL,
                message="; ".join(failures),
                file_path=_TASK_LEDGER_FILE_PATH,
            )
        )
        return

    if missing:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="context-pack-manifest-contract",
                status=IntegrityStatus.WARN,
                message="Missing generated context packs: " + "; ".join(missing),
                file_path=_TASK_LEDGER_FILE_PATH,
            )
        )
        return

    report.checks.append(
        IntegrityCheckResult(
            category=IntegrityCategory.MANIFEST_COHERENCE,
            name="context-pack-manifest-contract",
            status=IntegrityStatus.OK,
            message=f"Validated deterministic context packs for {checked} active task(s)",
            file_path=_TASK_LEDGER_FILE_PATH,
        )
    )


def _read_frontmatter_mapping(content: str) -> dict[str, object]:
    if not content.startswith("---\n"):
        return {}

    _, separator, remainder = content.partition("---\n")
    if not separator:
        return {}
    frontmatter, closing_separator, _body = remainder.partition("\n---")
    if not closing_separator:
        return {}

    try:
        payload = yaml.safe_load(frontmatter) or {}
    except yaml.YAMLError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _string_frontmatter_value(content: str, *keys: str) -> str | None:
    frontmatter = _read_frontmatter_mapping(content)
    for key in keys:
        value = frontmatter.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _spec_declared_id(spec_text: str) -> str | None:
    frontmatter_id = _string_frontmatter_value(spec_text, "spec", "id")
    if frontmatter_id:
        return frontmatter_id

    match = re.search(r"^#\s+Spec\s+([^\n]+)", spec_text, re.MULTILINE)
    if not match:
        return None
    heading_value = match.group(1).strip()
    return heading_value.split(" - ", 1)[0].strip() or None


def _plan_declared_spec_id(plan_text: str) -> str | None:
    frontmatter_id = _string_frontmatter_value(plan_text, "spec", "specId", "spec_id")
    if frontmatter_id:
        return frontmatter_id

    match = re.search(r"^#\s+Plan:\s+([^\n]+)", plan_text, re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip().split()[0] or None


def _project_relative_path(target: Path, path: Path) -> str:
    try:
        return path.relative_to(target).as_posix()
    except ValueError:
        return path.as_posix()


def _record_active_spec_plan_coherence(target: Path, report: IntegrityReport) -> None:
    work_plane = resolve_active_work_plane(target)
    plan_path = work_plane.plan_path
    if not plan_path.exists():
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="active-spec-plan-coherence",
                status=IntegrityStatus.FAIL,
                message="Active spec exists without specs/plan.md",
                file_path=_PLAN_FILE_PATH,
            )
        )
        return

    spec_text = work_plane.spec_path.read_text(encoding="utf-8", errors="replace")
    plan_text = plan_path.read_text(encoding="utf-8", errors="replace")
    if plan_text.strip().startswith("# No active plan"):
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="active-spec-plan-coherence",
                status=IntegrityStatus.FAIL,
                message="Active spec exists but specs/plan.md is an idle placeholder",
                file_path=_project_relative_path(target, plan_path),
            )
        )
        return

    spec_id = _spec_declared_id(spec_text)
    plan_spec_id = _plan_declared_spec_id(plan_text)
    if spec_id and plan_spec_id and spec_id != plan_spec_id:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="active-spec-plan-coherence",
                status=IntegrityStatus.FAIL,
                message=(
                    "Active spec and plan declare different work items: "
                    f"spec.md={spec_id}, plan.md={plan_spec_id}"
                ),
                file_path=_project_relative_path(target, plan_path),
            )
        )
        return

    report.checks.append(
        IntegrityCheckResult(
            category=IntegrityCategory.MANIFEST_COHERENCE,
            name="active-spec-plan-coherence",
            status=IntegrityStatus.OK,
            message="Active spec and plan have no declared identity mismatch",
            file_path=_project_relative_path(target, plan_path),
        )
    )


def _normalize_write_scope(scope: str) -> str:
    normalized = scope.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.rstrip("/")


def _static_scope_prefix(scope: str) -> str:
    normalized = _normalize_write_scope(scope)
    wildcard_positions = [
        position for marker in ("*", "?", "[") if (position := normalized.find(marker)) != -1
    ]
    if not wildcard_positions:
        return normalized
    return normalized[: min(wildcard_positions)].rstrip("/")


def _scope_covers(candidate_cover: str, candidate_child: str) -> bool:
    cover = _normalize_write_scope(candidate_cover)
    child_prefix = _static_scope_prefix(candidate_child)
    if cover in {"*", "**"}:
        return True
    if cover.endswith("/**"):
        cover_prefix = cover[:-3].rstrip("/")
        return child_prefix == cover_prefix or child_prefix.startswith(f"{cover_prefix}/")
    return False


def _write_scopes_overlap(first_scope: str, second_scope: str) -> bool:
    first = _normalize_write_scope(first_scope)
    second = _normalize_write_scope(second_scope)
    return first == second or _scope_covers(first, second) or _scope_covers(second, first)


def _collect_in_progress_write_scopes(ledger: TaskLedger) -> list[tuple[str, str]]:
    scopes: list[tuple[str, str]] = []

    for task in ledger.tasks:
        if task.status != TaskLifecycleState.IN_PROGRESS:
            continue
        for scope in task.write_scope:
            scopes.append((task.id, scope))

    return scopes


def _overlapping_write_scopes(scopes: list[tuple[str, str]]) -> list[tuple[str, str, str, str]]:
    overlaps: list[tuple[str, str, str, str]] = []
    for (first_task_id, first_scope), (second_task_id, second_scope) in combinations(scopes, 2):
        if first_task_id == second_task_id:
            continue
        if _write_scopes_overlap(first_scope, second_scope):
            overlaps.append((first_scope, second_scope, first_task_id, second_task_id))
    return overlaps


def _format_overlapping_write_scopes(
    overlapping_scopes: list[tuple[str, str, str, str]],
) -> str:
    return ", ".join(
        f"{first_scope} ({first_task_id}) overlaps {second_scope} ({second_task_id})"
        for first_scope, second_scope, first_task_id, second_task_id in sorted(overlapping_scopes)
    )


def _record_task_write_scope_duplicate_validation(
    ledger: TaskLedger, report: IntegrityReport
) -> None:
    overlapping_scopes = _overlapping_write_scopes(_collect_in_progress_write_scopes(ledger))

    if overlapping_scopes:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="task-write-scope-duplicate-validation",
                status=IntegrityStatus.FAIL,
                message=(
                    "Active spec task-ledger.json declares overlapping writeScope patterns "
                    "across in-progress tasks: "
                    f"{_format_overlapping_write_scopes(overlapping_scopes)}"
                ),
                file_path=_TASK_LEDGER_FILE_PATH,
            )
        )
        return

    report.checks.append(
        IntegrityCheckResult(
            category=IntegrityCategory.MANIFEST_COHERENCE,
            name="task-write-scope-duplicate-validation",
            status=IntegrityStatus.OK,
            message=(
                "Active spec task-ledger.json has no overlapping writeScope patterns "
                "across in-progress tasks"
            ),
            file_path=_TASK_LEDGER_FILE_PATH,
        )
    )


def _record_task_lifecycle_artifact_validation(ledger: TaskLedger, report: IntegrityReport) -> None:
    missing_requirements: list[str] = []

    for task in ledger.tasks:
        if (
            task.status
            in {
                TaskLifecycleState.REVIEW,
                TaskLifecycleState.VERIFY,
                TaskLifecycleState.DONE,
            }
            and not task.handoffs
        ):
            missing_requirements.append(f"{task.id} ({task.status}) has no handoff ref")
        if (
            task.status in {TaskLifecycleState.VERIFY, TaskLifecycleState.DONE}
            and not task.evidence
        ):
            missing_requirements.append(f"{task.id} ({task.status}) has no evidence ref")

    if missing_requirements:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="task-lifecycle-artifact-validation",
                status=IntegrityStatus.FAIL,
                message=(
                    "Active spec task-ledger.json has lifecycle states missing mandatory "
                    "handoff or evidence refs: " + ", ".join(missing_requirements)
                ),
                file_path=_TASK_LEDGER_FILE_PATH,
            )
        )
        return

    report.checks.append(
        IntegrityCheckResult(
            category=IntegrityCategory.MANIFEST_COHERENCE,
            name="task-lifecycle-artifact-validation",
            status=IntegrityStatus.OK,
            message="Active spec task-ledger.json lifecycle states carry required artifact refs",
            file_path=_TASK_LEDGER_FILE_PATH,
        )
    )


def _record_task_capability_acceptance_validation(
    target: Path,
    ledger: TaskLedger,
    report: IntegrityReport,
) -> None:
    catalog = build_framework_capabilities(target)
    if not catalog.capability_cards:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="task-capability-acceptance-validation",
                status=IntegrityStatus.WARN,
                message="No capability cards available; task-packet acceptance skipped",
                file_path=_TASK_LEDGER_FILE_PATH,
            )
        )
        return

    active_tasks = [task for task in ledger.tasks if task.status != TaskLifecycleState.DONE]
    if not active_tasks:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="task-capability-acceptance-validation",
                status=IntegrityStatus.OK,
                message="Active spec has no non-done task packets to validate",
                file_path=_TASK_LEDGER_FILE_PATH,
            )
        )
        return

    errors: list[str] = []
    warnings: list[str] = []
    for task in active_tasks:
        try:
            packet = _task_to_capability_packet(task)
        except ValueError as exc:
            errors.append(f"{task.id}: invalid capability task-packet metadata: {exc}")
            continue
        result = validate_task_packet_acceptance(catalog.capability_cards, packet)
        errors.extend(result.errors)
        warnings.extend(result.warnings)

    if errors:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="task-capability-acceptance-validation",
                status=IntegrityStatus.FAIL,
                message=(
                    "Active spec task-ledger.json has task packets rejected by "
                    "capability cards: " + "; ".join(errors)
                ),
                file_path=_TASK_LEDGER_FILE_PATH,
            )
        )
        return

    if warnings:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="task-capability-acceptance-validation",
                status=IntegrityStatus.WARN,
                message=(
                    "Active spec task packets passed capability-card gates with advisory "
                    "warnings: " + "; ".join(warnings)
                ),
                file_path=_TASK_LEDGER_FILE_PATH,
            )
        )
        return

    report.checks.append(
        IntegrityCheckResult(
            category=IntegrityCategory.MANIFEST_COHERENCE,
            name="task-capability-acceptance-validation",
            status=IntegrityStatus.OK,
            message="Active spec task packets are accepted by capability cards",
            file_path=_TASK_LEDGER_FILE_PATH,
        )
    )


def _task_to_capability_packet(task: TaskLedgerTask) -> CapabilityTaskPacket:
    mutation_classes = _task_extra_list(task, "mutationClasses", "mutation_classes")
    tool_requests = _task_extra_list(task, "toolRequests", "tool_requests")
    provider = _task_extra_scalar(task, "provider")

    return CapabilityTaskPacket(
        taskId=task.id,
        ownerRole=task.owner_role,
        mutationClasses=mutation_classes or infer_mutation_classes(task.write_scope),
        writeScope=task.write_scope,
        toolRequests=tool_requests,
        provider=provider,
        dependencies=task.dependencies,
        handoffs=[handoff.path for handoff in task.handoffs],
    )


def _task_extra_list(task: TaskLedgerTask, *keys: str) -> list[str]:
    extra = task.model_extra or {}
    for key in keys:
        if key not in extra:
            continue
        value = extra[key]
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]
    return []


def _task_extra_scalar(task: TaskLedgerTask, key: str) -> str | None:
    extra = task.model_extra or {}
    value = extra.get(key)
    if value is None:
        return None
    return str(value)


def _iter_task_artifact_refs(ledger: TaskLedger):
    for task in ledger.tasks:
        for artifact_kind, refs in (("handoff", task.handoffs), ("evidence", task.evidence)):
            for ref in refs:
                yield task.id, artifact_kind, ref.path


def _path_resolves_inside_root(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def _artifact_ref_candidates(
    declared_path: Path,
    work_plane_root: Path,
    project_root: Path,
) -> list[Path]:
    candidates: list[Path] = []
    for base_dir in (work_plane_root, project_root):
        candidate = (base_dir / declared_path).resolve()
        if _path_resolves_inside_root(candidate, work_plane_root):
            candidates.append(candidate)
    return candidates


def _invalid_artifact_ref_reason(
    task_id: str,
    artifact_kind: str,
    ref_path: str,
    work_plane_root: Path,
    project_root: Path,
) -> str | None:
    declared_path = Path(ref_path)
    if declared_path.is_absolute():
        return f"{task_id} {artifact_kind} {ref_path} is absolute"

    candidates = _artifact_ref_candidates(declared_path, work_plane_root, project_root)
    if not candidates:
        return f"{task_id} {artifact_kind} {ref_path} escapes the active work plane"

    if not any(candidate.exists() for candidate in candidates):
        return f"{task_id} {artifact_kind} {ref_path} does not exist under the active work plane"

    return None


def _record_task_artifact_reference_validation(
    target: Path,
    ledger: TaskLedger,
    report: IntegrityReport,
) -> None:
    project_root = target.resolve()
    work_plane_root = resolve_active_work_plane(target).specs_dir.resolve()
    invalid_refs = [
        reason
        for task_id, artifact_kind, ref_path in _iter_task_artifact_refs(ledger)
        if (
            reason := _invalid_artifact_ref_reason(
                task_id,
                artifact_kind,
                ref_path,
                work_plane_root,
                project_root,
            )
        )
    ]

    if invalid_refs:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="task-artifact-reference-validation",
                status=IntegrityStatus.FAIL,
                message=(
                    "Active spec task-ledger.json has task artifact refs that do not "
                    "resolve inside the active work plane: " + ", ".join(invalid_refs)
                ),
                file_path=_TASK_LEDGER_FILE_PATH,
            )
        )
        return

    report.checks.append(
        IntegrityCheckResult(
            category=IntegrityCategory.MANIFEST_COHERENCE,
            name="task-artifact-reference-validation",
            status=IntegrityStatus.OK,
            message=(
                "Active spec task-ledger.json handoff and evidence refs resolve inside "
                "the active work plane"
            ),
            file_path=_TASK_LEDGER_FILE_PATH,
        )
    )


def _record_task_dependency_validation(ledger: TaskLedger, report: IntegrityReport) -> bool:
    task_ids = {task.id for task in ledger.tasks}
    missing_dependencies = [
        f"{task.id} -> {dependency_id}"
        for task in ledger.tasks
        for dependency_id in task.dependencies
        if dependency_id not in task_ids
    ]

    if missing_dependencies:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="task-dependency-validation",
                status=IntegrityStatus.FAIL,
                message=(
                    "Active spec task-ledger.json references unknown task ids: "
                    + ", ".join(missing_dependencies)
                ),
                file_path=_TASK_LEDGER_FILE_PATH,
            )
        )
        return False

    report.checks.append(
        IntegrityCheckResult(
            category=IntegrityCategory.MANIFEST_COHERENCE,
            name="task-dependency-validation",
            status=IntegrityStatus.OK,
            message="Active spec task-ledger.json dependency refs resolve within the ledger",
            file_path=_TASK_LEDGER_FILE_PATH,
        )
    )
    return True


def _record_task_state_consistency(ledger: TaskLedger, report: IntegrityReport) -> None:
    task_status_by_id = {task.id: task.status for task in ledger.tasks}
    inconsistent_done_dependencies = [
        f"{task.id} -> {dependency_id} ({task_status_by_id[dependency_id]})"
        for task in ledger.tasks
        if task.status == TaskLifecycleState.DONE
        for dependency_id in task.dependencies
        if task_status_by_id[dependency_id] != TaskLifecycleState.DONE
    ]

    if inconsistent_done_dependencies:
        report.checks.append(
            IntegrityCheckResult(
                category=IntegrityCategory.MANIFEST_COHERENCE,
                name="task-state-consistency",
                status=IntegrityStatus.FAIL,
                message=(
                    "Active spec task-ledger.json marks done tasks before dependencies are done: "
                    + ", ".join(inconsistent_done_dependencies)
                ),
                file_path=_TASK_LEDGER_FILE_PATH,
            )
        )
        return

    report.checks.append(
        IntegrityCheckResult(
            category=IntegrityCategory.MANIFEST_COHERENCE,
            name="task-state-consistency",
            status=IntegrityStatus.OK,
            message="Active spec task-ledger.json done tasks depend only on done tasks",
            file_path=_TASK_LEDGER_FILE_PATH,
        )
    )
