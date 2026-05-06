"""Install orchestrator for the ai-engineering framework.

Provides two entry points:

- ``install()`` — legacy orchestrator that bootstraps a complete
  ``.ai-engineering/`` governance structure.  Preserved for backward
  compatibility with existing callers and tests.
- ``install_with_pipeline()`` — new phase-pipeline orchestrator that
  supports all install modes (INSTALL, FRESH, REPAIR, RECONFIGURE).

Steps performed by the pipeline:
1. Detect environment (VCS, tools, existing install, legacy paths).
2. Copy ``.ai-engineering/`` governance templates.
3. Deploy IDE-specific configuration files.
4. Install hook scripts and merge settings.json.
5. Generate state files (manifest, ownership, decisions).
6. Verify/install required CLI tools.
"""

from __future__ import annotations

import json
import logging
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from ai_engineering.config.loader import (
    load_manifest_config,
    load_manifest_root_entry_points,
    update_manifest_field,
)
from ai_engineering.detector.readiness import check_tools_for_stacks
from ai_engineering.doctor.models import DoctorContext
from ai_engineering.doctor.remediation import RemediationEngine
from ai_engineering.doctor.runtime.feeds import validate_feeds_for_install
from ai_engineering.hooks.manager import HookInstallResult, install_hooks
from ai_engineering.installer.phases import (
    PHASE_GOVERNANCE,
    PHASE_HOOKS,
    PHASE_IDE_CONFIG,
    PHASE_ORDER,
    PHASE_STATE,
    InstallContext,
    InstallMode,
    PhaseProtocol,
)
from ai_engineering.installer.phases.detect import DetectPhase
from ai_engineering.installer.phases.governance import GovernancePhase
from ai_engineering.installer.phases.hooks import HooksPhase
from ai_engineering.installer.phases.ide_config import IdeConfigPhase
from ai_engineering.installer.phases.pipeline import PipelineRunner, PipelineSummary
from ai_engineering.installer.phases.state import StatePhase
from ai_engineering.installer.phases.tools import ToolsPhase
from ai_engineering.state.defaults import (
    default_decision_store,
    default_install_state,
    default_ownership_map,
)
from ai_engineering.state.instincts import ensure_instinct_artifacts
from ai_engineering.state.io import write_json_model
from ai_engineering.state.manifest import compute_tool_spec_hash
from ai_engineering.state.models import DecisionStatus, InstallState, RiskCategory
from ai_engineering.state.observability import (
    emit_framework_operation,
    write_framework_capabilities,
)
from ai_engineering.state.service import (
    StateService,
    load_install_state,
    save_install_state,
)
from ai_engineering.vcs.factory import get_provider

from .auth import check_vcs_auth
from .branch_policy import apply_branch_policy
from .templates import (
    CopyResult,
    copy_project_templates,
    copy_template_tree,
    get_ai_engineering_template_root,
)
from .tools import (
    ToolInstallResult,
    can_auto_install_tool,
    ensure_tool,
    manual_install_step,
    provider_required_tools,
)

logger = logging.getLogger(__name__)

# Relative paths under ``.ai-engineering/`` for each state file.
_STATE_FILES: dict[str, str] = {
    "install-state": "state/install-state.json",
    "ownership-map": "state/ownership-map.json",
    "decision-store": "state/decision-store.json",
    "framework-capabilities": "state/framework-capabilities.json",
    "instinct-observations": "state/instinct-observations.ndjson",
    "instincts": "instincts/instincts.yml",
    "instinct-meta": "instincts/meta.json",
}


@dataclass
class InstallResult:
    """Summary of an installation operation."""

    governance_files: CopyResult = field(default_factory=CopyResult)
    project_files: CopyResult = field(default_factory=CopyResult)
    state_files: list[Path] = field(default_factory=list)
    hooks: HookInstallResult = field(default_factory=HookInstallResult)
    already_installed: bool = False
    readiness_status: str = "pending"
    manual_steps: list[str] = field(default_factory=list)
    guide_text: str | None = None

    @property
    def total_created(self) -> int:
        """Total number of files created across all categories."""
        return (
            len(self.governance_files.created)
            + len(self.project_files.created)
            + len(self.state_files)
        )

    @property
    def total_skipped(self) -> int:
        """Total number of files skipped (already existed)."""
        return len(self.governance_files.skipped) + len(self.project_files.skipped)


def install(
    target: Path,
    *,
    stacks: list[str] | None = None,
    ides: list[str] | None = None,
    vcs_provider: str = "github",
    ai_providers: list[str] | None = None,
    external_references: dict[str, str] | None = None,
) -> InstallResult:
    """Bootstrap the ai-engineering framework in a target project.

    Copies governance templates, IDE agent configs, and generates state
    files.  Uses create-only semantics: existing files are never overwritten.

    Args:
        target: Root directory of the target project.
        stacks: Initial stacks to install. Defaults to ``["python"]``.
        ides: Initial IDEs to configure. Defaults to ``["terminal"]``.
        vcs_provider: Primary VCS provider. Defaults to ``"github"``.
        ai_providers: AI providers to enable. Defaults to ``["claude-code"]``.

    Returns:
        InstallResult with details of created and skipped files.
    """
    result = InstallResult()
    ai_eng_dir = target / ".ai-engineering"

    # 1. Copy governance templates
    src_root = get_ai_engineering_template_root()
    result.governance_files = copy_template_tree(
        src_root, ai_eng_dir, exclude=["agents/", "skills/"]
    )

    # 2. Copy project-level templates (provider-aware)
    result.project_files = copy_project_templates(target, providers=ai_providers)

    # 2b. Persist ai_providers selection to manifest
    _write_ai_providers(target, ai_providers)
    _write_providers(target, stacks=stacks, ides=ides, vcs_provider=vcs_provider)

    # 3. Generate state files (create-only)
    result.state_files = _generate_state_files(
        ai_eng_dir,
        stacks=stacks,
        ides=ides,
        vcs_provider=vcs_provider,
        ai_providers=ai_providers,
        external_references=external_references,
    )

    # If no state files were generated, installation was already present
    if not result.state_files and not result.governance_files.created:
        result.already_installed = True

    # 4. Canonical framework event entry
    _log_install_event(ai_eng_dir, result)

    # 5. Ensure git repo exists, then install hooks
    if not (target / ".git").is_dir():
        subprocess.run(["git", "init", "-b", "main"], cwd=target, capture_output=True, check=True)
    result.hooks = install_hooks(target)

    # 6. Install-to-operational phases (tooling/auth/policy)
    _run_operational_phases(target, vcs_provider=vcs_provider, result=result)

    return result


def install_with_pipeline(
    target: Path,
    *,
    mode: InstallMode = InstallMode.INSTALL,
    stacks: list[str] | None = None,
    ides: list[str] | None = None,
    vcs_provider: str = "github",
    ai_providers: list[str] | None = None,
    external_references: dict[str, str] | None = None,
    dry_run: bool = False,
    force: bool = False,
    progress_callback: Callable[[str], None] | None = None,
) -> tuple[InstallResult, PipelineSummary]:
    """Run the install pipeline and return both legacy and pipeline results.

    This is the new entry point that orchestrates install through the
    6-phase pipeline (detect, governance, ide_config, hooks, state, tools).
    Returns a tuple of ``(InstallResult, PipelineSummary)`` so that
    callers can use either the legacy result format or the richer
    pipeline summary.

    Args:
        target: Root directory of the target project.
        mode: Install mode. Defaults to ``INSTALL``.
        stacks: Initial stacks to install. Defaults to ``["python"]``.
        ides: Initial IDEs to configure. Defaults to ``["terminal"]``.
        vcs_provider: Primary VCS provider. Defaults to ``"github"``.
        ai_providers: AI providers to enable. Defaults to ``["claude-code"]``.
        external_references: External reference URLs for the manifest.
        dry_run: When True, only plan without writing files.

    Returns:
        Tuple of (InstallResult, PipelineSummary).
    """
    # Load existing state for REPAIR/RECONFIGURE modes
    existing_state = None
    if mode in (InstallMode.REPAIR, InstallMode.RECONFIGURE):
        state_dir = target / ".ai-engineering" / "state"
        try:
            existing_state = load_install_state(state_dir)
        except (json.JSONDecodeError, ValueError, OSError) as exc:
            logger.warning("Cannot read existing install state: %s", exc)

    # Build context
    # spec-124 D-124-03: thread the same ``progress_callback`` into the
    # context so phases (ToolsPhase / HooksPhase) can emit per-sub-step
    # events (e.g. ``tool_started:ruff``) alongside the pipeline-level
    # phase events (``[5/6] tools``). The CLI surface translates both
    # into Rich Status spinner updates.
    context = InstallContext(
        target=target,
        mode=mode,
        providers=ai_providers or [],
        vcs_provider=vcs_provider,
        stacks=stacks or [],
        ides=ides or [],
        existing_state=existing_state,
        force=force,
        progress_callback=progress_callback,
    )

    if not dry_run:
        feed_preflight = validate_feeds_for_install(
            DoctorContext(target=target, install_state=existing_state),
            mode=mode.value,
        )
        if feed_preflight.status == "blocked":
            return (
                InstallResult(
                    readiness_status="blocked",
                    manual_steps=[
                        feed_preflight.message,
                        *[
                            f"Validate feed access before retrying install: {feed}"
                            for feed in feed_preflight.feeds
                        ],
                    ],
                ),
                PipelineSummary(failed_phase="feed_preflight", dry_run=False),
            )

    # Build phases in PHASE_ORDER (canonical ordering defined in phases/__init__.py).
    _phase_classes = {
        "detect": DetectPhase,
        "governance": GovernancePhase,
        "ide_config": IdeConfigPhase,
        "state": StatePhase,
        "hooks": HooksPhase,
        "tools": ToolsPhase,
    }
    # ty (0.x) cannot narrow the dict-value union back to PhaseProtocol on
    # comprehension; cast each instance explicitly so the declared type
    # matches the inferred type. Each phase class implements PhaseProtocol
    # by structural typing -- the cast is documentation, not coercion.
    phases: list[PhaseProtocol] = [
        cast(PhaseProtocol, _phase_classes[name]()) for name in PHASE_ORDER
    ]

    # Run the pipeline (spec-109 D-109-07: optional progress_callback for
    # live multi-step UX in the CLI; backward-compatible default None).
    runner = PipelineRunner(phases, progress_callback=progress_callback)
    summary = runner.run(context, dry_run=dry_run)

    # Convert PipelineSummary to InstallResult
    result = _summary_to_install_result(summary, mode)

    # Persist selected stacks, ides, and ai_providers to manifest.yml
    if not dry_run:
        _write_providers(target, stacks=stacks, ides=ides, vcs_provider=vcs_provider)
        _write_ai_providers(target, ai_providers)

    # Run operational phases (VCS auth, branch policy, tooling readiness)
    if not dry_run:
        _run_operational_phases(target, vcs_provider=vcs_provider, result=result)

    return result, summary


def _summary_to_install_result(
    summary: PipelineSummary,
    mode: InstallMode,
) -> InstallResult:
    """Convert a PipelineSummary into a legacy InstallResult.

    Aggregates created/skipped files from phase results into the
    governance_files and project_files CopyResult fields.

    Args:
        summary: The pipeline summary to convert.
        mode: The install mode that was used.

    Returns:
        An InstallResult populated from the pipeline summary.
    """
    result = InstallResult()

    governance_created: list[Path] = []
    governance_skipped: list[Path] = []
    project_created: list[Path] = []
    project_skipped: list[Path] = []

    for phase_result in summary.results:
        if phase_result.phase_name == PHASE_GOVERNANCE:
            governance_created.extend(Path(p) for p in phase_result.created)
            governance_skipped.extend(Path(p) for p in phase_result.skipped)
        elif phase_result.phase_name == PHASE_HOOKS:
            # spec-124 D-124-05: HOOKS phase output populates BOTH project_files
            # (so file_count math is right) AND result.hooks.installed (so the
            # Install Complete summary reports a true hook count instead of 0).
            project_created.extend(Path(p) for p in phase_result.created)
            project_skipped.extend(Path(p) for p in phase_result.skipped)
            # Each hook phase emits two artifacts per hook (Bash dispatcher +
            # PowerShell companion). Dedupe to canonical hook names by stem.
            hook_names = sorted(
                {Path(p).name for p in phase_result.created if not str(p).endswith(".ps1")}
            )
            result.hooks.installed = hook_names
        elif phase_result.phase_name == PHASE_IDE_CONFIG:
            project_created.extend(Path(p) for p in phase_result.created)
            project_skipped.extend(Path(p) for p in phase_result.skipped)
        elif phase_result.phase_name == PHASE_STATE:
            result.state_files = [Path(p) for p in phase_result.created]
    result.governance_files = CopyResult(
        created=governance_created,
        skipped=governance_skipped,
    )
    result.project_files = CopyResult(
        created=project_created,
        skipped=project_skipped,
    )

    # Set already_installed if mode was detected as existing
    if (
        mode in (InstallMode.REPAIR, InstallMode.RECONFIGURE)
        and not governance_created
        and not result.state_files
    ):
        result.already_installed = True

    return result


def _write_providers(
    target: Path,
    *,
    stacks: list[str] | None,
    ides: list[str] | None,
    vcs_provider: str = "github",
) -> None:
    """Persist stacks, ides, and vcs to manifest.yml after template copy."""
    manifest_path = target / ".ai-engineering" / "manifest.yml"
    if not manifest_path.is_file():
        return
    try:
        if stacks is not None:
            update_manifest_field(target, "providers.stacks", stacks)
        if ides is not None:
            update_manifest_field(target, "providers.ides", ides)
        if vcs_provider != "github":
            update_manifest_field(target, "providers.vcs", vcs_provider)
            update_manifest_field(target, "work_items.provider", vcs_provider)
    except KeyError:
        logger.debug("providers key not found in manifest; skipping write")


def _write_ai_providers(target: Path, ai_providers: list[str] | None) -> None:
    """Persist the selected AI providers to manifest.yml.

    Called after governance templates are copied so that the manifest
    reflects the actual provider selection rather than template defaults.
    """
    providers = ai_providers or ["claude-code"]
    manifest_path = target / ".ai-engineering" / "manifest.yml"
    if not manifest_path.is_file():
        return
    try:
        update_manifest_field(target, "ai_providers.enabled", providers)
        update_manifest_field(target, "ai_providers.primary", providers[0])
    except KeyError:
        logger.debug("ai_providers key not found in manifest; skipping write")


def _generate_state_files(
    ai_eng_dir: Path,
    *,
    stacks: list[str] | None,
    ides: list[str] | None,
    vcs_provider: str = "github",
    ai_providers: list[str] | None = None,
    external_references: dict[str, str] | None = None,
) -> list[Path]:
    """Generate default state files if they don't already exist.

    Args:
        ai_eng_dir: Path to the ``.ai-engineering/`` directory.
        stacks: Stacks to include in the install manifest.
        ides: IDEs to include in the install manifest.
        vcs_provider: Primary VCS provider.
        ai_providers: AI providers to enable.

    Returns:
        List of state file paths that were created.
    """
    created: list[Path] = []
    root_entry_points = load_manifest_root_entry_points(ai_eng_dir.parent)

    state_models = {
        _STATE_FILES["install-state"]: default_install_state(),
        _STATE_FILES["ownership-map"]: default_ownership_map(
            root_entry_points=root_entry_points,
        ),
        _STATE_FILES["decision-store"]: default_decision_store(),
    }

    for relative_path, model in state_models.items():
        dest = ai_eng_dir / relative_path
        if dest.exists():
            continue
        write_json_model(dest, model)
        created.append(dest)

    capabilities_path = ai_eng_dir / _STATE_FILES["framework-capabilities"]
    if not capabilities_path.exists():
        write_framework_capabilities(ai_eng_dir.parent)
        created.append(capabilities_path)

    instinct_paths = [
        ai_eng_dir / _STATE_FILES["instinct-observations"],
        ai_eng_dir / _STATE_FILES["instincts"],
        ai_eng_dir / _STATE_FILES["instinct-meta"],
    ]
    if not all(path.exists() for path in instinct_paths):
        ensure_instinct_artifacts(ai_eng_dir.parent)
        for path in instinct_paths:
            if path not in created:
                created.append(path)

    return created


def _log_install_event(ai_eng_dir: Path, result: InstallResult) -> None:
    """Emit a canonical framework operation event for install."""
    project_root = ai_eng_dir.parent
    emit_framework_operation(
        project_root,
        operation="install",
        component="installer",
        source="cli",
        metadata={
            "created": result.total_created,
            "skipped": result.total_skipped,
            "state_files": len(result.state_files),
            "manual_steps": len(result.manual_steps),
        },
    )


def _run_operational_phases(target: Path, *, vcs_provider: str, result: InstallResult) -> None:
    state_dir = target / ".ai-engineering" / "state"
    state = load_install_state(state_dir)

    # Read stacks from manifest.yml config (not from state)
    config = load_manifest_config(target)
    configured_vcs = config.providers.vcs or vcs_provider
    provider_tools = set(provider_required_tools(configured_vcs))
    remediation_engine = RemediationEngine(
        tool_capability=can_auto_install_tool,
        tool_manual_step=manual_install_step,
    )

    # Phase 2: required tooling (provider-aware + stack-aware)
    stack_report = check_tools_for_stacks(
        config.providers.stacks,
        vcs_provider=configured_vcs,
    )
    provider_results = _remediate_tools(provider_tools, remediation_engine)
    for tool in provider_tools:
        install_result = provider_results.get(tool)
        is_available = install_result.available if install_result is not None else False
        tool_entry = state.tooling.get(tool)
        if tool_entry is not None:
            tool_entry.installed = is_available
            tool_entry.mode = "cli" if is_available else "api"
        else:
            from ai_engineering.state.models import ToolEntry

            state.tooling[tool] = ToolEntry(
                installed=is_available,
                mode="cli" if is_available else "api",
            )
    _extend_manual_steps(
        result.manual_steps,
        [
            manual_install_step(tool)
            for tool in provider_tools
            if not provider_results.get(
                tool,
                ToolInstallResult(tool, False, False, False),
            ).available
        ],
    )

    missing_stack_tools = [
        item.name
        for item in stack_report.tools
        if not item.available and item.name not in provider_tools
    ]
    stack_results = _remediate_tools(missing_stack_tools, remediation_engine)
    for item in stack_report.tools:
        if item.name in provider_tools:
            continue
        stack_result = stack_results.get(item.name)
        if not item.available and (stack_result is None or not stack_result.available):
            _extend_manual_steps(result.manual_steps, [manual_install_step(item.name)])

    # Deferred setup for projects without stacks
    if not config.providers.stacks:
        result.manual_steps.append(
            "No stacks configured. Run 'ai-eng stack add <name>' to configure tooling."
        )

    # Phase 3: VCS auth
    provider = get_provider(target)
    auth_result = check_vcs_auth(configured_vcs, provider, target)
    tool_key = "gh" if configured_vcs == "github" else "az"
    vcs_entry = state.tooling.get(tool_key)
    if vcs_entry is not None:
        vcs_entry.authenticated = auth_result.authenticated
        vcs_entry.mode = auth_result.mode
    else:
        from ai_engineering.state.models import ToolEntry

        state.tooling[tool_key] = ToolEntry(
            authenticated=auth_result.authenticated,
            mode=auth_result.mode,
        )
    if not auth_result.authenticated:
        result.manual_steps.append(auth_result.message)

    # Phase 4: branch policy apply + manual fallback
    policy_result = apply_branch_policy(
        provider_name=configured_vcs,
        provider=provider,
        project_root=target,
        branch="main",
        required_checks=["ai-eng-gate", "ai-pr-review", "ci"],
        mode=auth_result.mode,
    )
    state.branch_policy.applied = policy_result.applied
    state.branch_policy.mode = policy_result.mode
    state.branch_policy.message = policy_result.message
    if policy_result.manual_guide is not None:
        state.branch_policy.manual_guide = policy_result.manual_guide
        result.guide_text = policy_result.manual_guide
        result.manual_steps.append("Run 'ai-eng guide' to view branch policy setup instructions")

    if not result.manual_steps:
        result.readiness_status = "READY"
    else:
        result.readiness_status = "READY WITH MANUAL STEPS"
    state.operational_readiness.status = result.readiness_status
    state.operational_readiness.pending_steps = list(result.manual_steps)
    state.vcs_provider = configured_vcs

    # spec-107 D-107-09 (H1) — detect tool-spec rug-pulls.
    _check_tool_spec_hashes(target, state, manual_steps=result.manual_steps)

    save_install_state(state_dir, state)


def _check_tool_spec_hashes(
    target: Path,
    state: InstallState,
    *,
    manual_steps: list[str],
) -> None:
    """Spec-107 D-107-09 (H1) — rug-pull detection via SHA256 tool-spec hashing.

    Walks the resolved ``required_tools`` block once per install, computing
    ``compute_tool_spec_hash`` for each ``ToolSpec`` and comparing it against
    ``state.tool_spec_hashes``. Behavior:

    - **First run** (``state.tool_spec_hashes`` is empty): populate baseline
      silently. No banner, no manual step. The intent is to anchor the
      "known-good" snapshot the moment the project first installs.
    - **Subsequent run, no mismatch**: silent no-op (most common path).
    - **Subsequent run, mismatch detected**: lookup an active risk-acceptance
      DEC for ``finding_id="tool-spec-mismatch-<stack>-<tool>"``. If found,
      permit + update baseline + log telemetry. If absent, append a CLI
      banner to ``manual_steps`` so the installer surfaces the mismatch.

    The check is fail-open: any exception (manifest unreadable, decision-store
    corrupt, etc.) is logged at debug-level and skipped. This mirrors the
    spec-107 D-107-06 fail-open philosophy ("missed detection annoying,
    broken installer worse").

    Args:
        target: Project root.
        state: Mutable :class:`InstallState`. ``tool_spec_hashes`` is updated
            in-place when first-run or DEC-permitted-mismatch.
        manual_steps: Mutable list; H1 banner is appended when a mismatch is
            detected without an active DEC.
    """
    try:
        config = load_manifest_config(target)
        stacks = list(config.providers.stacks)
        if not stacks:
            return
    except (OSError, ValueError, KeyError) as exc:
        logger.debug("H1 tool-spec hash check skipped: %s", exc)
        return

    # Build current hash map: "<stack>:<tool>" -> sha256. We re-walk the raw
    # block to keep stack provenance per tool. "baseline" is the canonical
    # stack-name for baseline tools so the composite key remains stable across
    # stack reorderings.
    current_hashes: dict[str, str] = {}
    try:
        from ai_engineering.state.manifest import (
            _read_raw_manifest,
            _resolve_required_tools_block,
        )

        block = _resolve_required_tools_block(_read_raw_manifest(target))
        if block is not None:
            for tool in block.baseline.tools:
                current_hashes[f"baseline:{tool.name}"] = compute_tool_spec_hash(tool)
            for stack_name in stacks:
                stack_spec = getattr(block, stack_name, None)
                if stack_spec is None:
                    continue
                for tool in stack_spec.tools:
                    current_hashes[f"{stack_name}:{tool.name}"] = compute_tool_spec_hash(tool)
    except (OSError, ValueError, KeyError, AttributeError) as exc:
        logger.debug("H1 tool-spec hash walk skipped: %s", exc)
        return

    if not current_hashes:
        return

    baseline = state.tool_spec_hashes
    if not baseline:
        # First-run: populate baseline silently per T-5.11.
        state.tool_spec_hashes = dict(current_hashes)
        return

    # Subsequent run: detect mismatches and resolve via DEC lookup.
    try:
        store = StateService(target).load_decisions()
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        logger.debug("H1 DEC store load skipped: %s", exc)
        store = None

    for key, current_hash in current_hashes.items():
        baseline_hash = baseline.get(key)
        if baseline_hash is None:
            # New tool added since baseline; treat as additive (no alert).
            state.tool_spec_hashes[key] = current_hash
            continue
        if baseline_hash == current_hash:
            continue

        # Mismatch detected — D-107-09 protocol.
        finding_id = f"tool-spec-mismatch-{key.replace(':', '-')}"
        if store is not None and _has_active_finding_dec(store, finding_id):
            # DEC active → permit + update baseline + emit telemetry.
            state.tool_spec_hashes[key] = current_hash
            try:
                emit_framework_operation(
                    target / ".ai-engineering",
                    operation="tool_spec_mismatch_accepted",
                    component="installer",
                    source="installer.h1",
                    metadata={
                        "stack_tool": key,
                        "finding_id": finding_id,
                        "baseline_hash": baseline_hash[:12],
                        "current_hash": current_hash[:12],
                    },
                )
            except (OSError, ValueError, KeyError) as exc:
                logger.debug("H1 telemetry emit skipped: %s", exc)
            continue

        # No active DEC → append CLI banner to manual_steps.
        banner = _format_tool_spec_mismatch_banner(
            stack_tool=key,
            baseline_hash=baseline_hash,
            current_hash=current_hash,
            finding_id=finding_id,
        )
        if banner not in manual_steps:
            manual_steps.append(banner)


def _has_active_finding_dec(store: object, finding_id: str) -> bool:
    """Return True when ``store`` carries an active risk-acceptance for ``finding_id``.

    Mirrors the spec-105 ``find_active_risk_acceptance`` semantics but matches
    by ``finding_id`` directly (H1 uses canonical IDs, not gate-finding rule IDs):

    - ``status == ACTIVE``
    - ``risk_category == RISK_ACCEPTANCE``
    - ``expires_at is None or expires_at > now``
    - ``finding_id`` (or alias ``findingId``) equals the canonical H1 ID
    """
    from datetime import UTC, datetime

    decisions = getattr(store, "decisions", None)
    if not decisions:
        return False
    now = datetime.now(tz=UTC)
    for d in decisions:
        if getattr(d, "finding_id", None) != finding_id:
            continue
        if getattr(d, "status", None) != DecisionStatus.ACTIVE:
            continue
        if getattr(d, "risk_category", None) != RiskCategory.RISK_ACCEPTANCE:
            continue
        expires_at = getattr(d, "expires_at", None)
        if expires_at is not None and expires_at <= now:
            continue
        return True
    return False


def _format_tool_spec_mismatch_banner(
    *,
    stack_tool: str,
    baseline_hash: str,
    current_hash: str,
    finding_id: str,
) -> str:
    """Render the canonical Tool Spec Mismatch CLI banner per D-107-09."""
    return (
        f"Tool Spec Mismatch detected for {stack_tool} "
        f"(baseline {baseline_hash[:12]} -> current {current_hash[:12]}). "
        "This may indicate legitimate manifest update OR silent tampering. "
        "To accept consciously: ai-eng risk accept "
        f"--finding-id {finding_id} --severity high "
        '--justification "..." --spec spec-107 --follow-up "..."'
    )


def _remediate_tools(
    tool_names: set[str] | list[str],
    remediation_engine: RemediationEngine,
) -> dict[str, ToolInstallResult]:
    install_results: dict[str, ToolInstallResult] = {}

    def _installer(tool: str) -> bool:
        install_result = ensure_tool(tool, allow_install=True)
        install_results[tool] = install_result
        return install_result.available

    remediation_engine.tool_installer = _installer
    remediation_engine.remediate_missing_tools(
        sorted(set(tool_names)),
        source="installer.operational",
    )
    return install_results


def _extend_manual_steps(existing: list[str], steps: list[str]) -> None:
    for step in steps:
        if step not in existing:
            existing.append(step)
