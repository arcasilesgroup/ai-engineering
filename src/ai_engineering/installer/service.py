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
from dataclasses import dataclass, field
from pathlib import Path

from ai_engineering.config.loader import load_manifest_config, update_manifest_field
from ai_engineering.detector.readiness import check_tools_for_stacks
from ai_engineering.hooks.manager import HookInstallResult, install_hooks
from ai_engineering.installer.phases import (
    PHASE_GOVERNANCE,
    PHASE_HOOKS,
    PHASE_IDE_CONFIG,
    PHASE_ORDER,
    PHASE_STATE,
    PHASE_TOOLS,
    InstallContext,
    InstallMode,
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
from ai_engineering.state.observability import (
    emit_framework_operation,
    write_framework_capabilities,
)
from ai_engineering.state.service import load_install_state, save_install_state
from ai_engineering.vcs.factory import get_provider

from .auth import check_vcs_auth
from .branch_policy import apply_branch_policy
from .templates import (
    CopyResult,
    copy_project_templates,
    copy_template_tree,
    get_ai_engineering_template_root,
)
from .tools import ensure_tool, provider_required_tools

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
        ai_providers: AI providers to enable. Defaults to ``["claude_code"]``.

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
        ai_providers: AI providers to enable. Defaults to ``["claude_code"]``.
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
    context = InstallContext(
        target=target,
        mode=mode,
        providers=ai_providers or [],
        vcs_provider=vcs_provider,
        stacks=stacks or [],
        ides=ides or [],
        existing_state=existing_state,
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
    phases = [_phase_classes[name]() for name in PHASE_ORDER]

    # Run the pipeline
    runner = PipelineRunner(phases)
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
        elif phase_result.phase_name in (PHASE_IDE_CONFIG, PHASE_HOOKS):
            project_created.extend(Path(p) for p in phase_result.created)
            project_skipped.extend(Path(p) for p in phase_result.skipped)
        elif phase_result.phase_name == PHASE_STATE:
            result.state_files = [Path(p) for p in phase_result.created]
        elif phase_result.phase_name == PHASE_TOOLS:
            result.manual_steps.extend(phase_result.warnings)

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
    except KeyError:
        logger.debug("providers key not found in manifest; skipping write")


def _write_ai_providers(target: Path, ai_providers: list[str] | None) -> None:
    """Persist the selected AI providers to manifest.yml.

    Called after governance templates are copied so that the manifest
    reflects the actual provider selection rather than template defaults.
    """
    providers = ai_providers or ["claude_code"]
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

    state_models = {
        _STATE_FILES["install-state"]: default_install_state(),
        _STATE_FILES["ownership-map"]: default_ownership_map(),
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

    # Phase 2: required tooling (provider-aware + stack-aware)
    stack_report = check_tools_for_stacks(config.providers.stacks)
    for tool in provider_required_tools(vcs_provider):
        install_result = ensure_tool(tool)
        tool_entry = state.tooling.get(tool)
        if tool_entry is not None:
            tool_entry.installed = install_result.available
            tool_entry.mode = "cli" if install_result.available else "api"
        else:
            from ai_engineering.state.models import ToolEntry

            state.tooling[tool] = ToolEntry(
                installed=install_result.available,
                mode="cli" if install_result.available else "api",
            )
        if not install_result.available:
            result.manual_steps.append(f"Install or enable `{tool}` CLI")

    for item in stack_report.tools:
        if not item.available and item.name in {"gitleaks", "semgrep"}:
            # Attempt auto-install before falling back to manual step
            sec_result = ensure_tool(item.name)
            if not sec_result.available:
                result.manual_steps.append(f"Install required security tool `{item.name}`")

    # Deferred setup for projects without stacks
    if not config.providers.stacks:
        result.manual_steps.append(
            "No stacks configured. Run 'ai-eng stack add <name>' to configure tooling."
        )

    # Phase 3: VCS auth
    provider = get_provider(target)
    auth_result = check_vcs_auth(vcs_provider, provider, target)
    tool_key = "gh" if vcs_provider == "github" else "az"
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
        provider_name=vcs_provider,
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

    save_install_state(state_dir, state)
