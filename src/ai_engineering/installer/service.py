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

import contextlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from ai_engineering.detector.readiness import check_tools_for_stacks
from ai_engineering.git.context import get_git_context
from ai_engineering.hooks.manager import HookInstallResult, install_hooks
from ai_engineering.installer.phases import (
    PHASE_GOVERNANCE,
    PHASE_HOOKS,
    PHASE_IDE_CONFIG,
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
    default_install_manifest,
    default_ownership_map,
)
from ai_engineering.state.io import append_ndjson, read_json_model, write_json_model
from ai_engineering.state.models import AuditEntry, InstallManifest
from ai_engineering.vcs.factory import get_provider
from ai_engineering.vcs.repo_context import get_repo_context

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
    "install-manifest": "state/install-manifest.json",
    "ownership-map": "state/ownership-map.json",
    "decision-store": "state/decision-store.json",
}

_AUDIT_LOG_PATH: str = "state/audit-log.ndjson"


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

    # 4. Audit log entry
    _log_install_event(ai_eng_dir, result)

    # 5. Install git hooks (skip silently if not a git repo)
    with contextlib.suppress(FileNotFoundError):
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
    # Auto-detect mode when caller uses the default
    if mode is InstallMode.INSTALL:
        manifest_path = target / ".ai-engineering" / "state" / "install-manifest.json"
        if manifest_path.exists():
            mode = InstallMode.REPAIR

    # Load existing manifest for REPAIR/RECONFIGURE modes
    existing_manifest = None
    if mode in (InstallMode.REPAIR, InstallMode.RECONFIGURE):
        manifest_path = target / ".ai-engineering" / "state" / "install-manifest.json"
        if manifest_path.exists():
            try:
                existing_manifest = read_json_model(manifest_path, InstallManifest)
            except (json.JSONDecodeError, ValueError, OSError) as exc:
                logger.warning("Cannot read existing manifest: %s", exc)

    # Build context
    context = InstallContext(
        target=target,
        mode=mode,
        providers=ai_providers or [],
        vcs_provider=vcs_provider,
        stacks=stacks or [],
        ides=ides or [],
        existing_manifest=existing_manifest,
    )

    # Create the 6 phases in order
    # StatePhase must run before HooksPhase so that _record_hook_hashes()
    # can find the install-manifest.json when saving hook integrity hashes.
    phases = [
        DetectPhase(),
        GovernancePhase(),
        IdeConfigPhase(),
        StatePhase(),
        HooksPhase(),
        ToolsPhase(),
    ]

    # Run the pipeline
    runner = PipelineRunner(phases)
    summary = runner.run(context, dry_run=dry_run)

    # Convert PipelineSummary to InstallResult
    result = _summary_to_install_result(summary, mode)

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
        _STATE_FILES["install-manifest"]: default_install_manifest(
            stacks=stacks,
            ides=ides,
            vcs_provider=vcs_provider,
            ai_providers=ai_providers,
            external_references=external_references,
        ),
        _STATE_FILES["ownership-map"]: default_ownership_map(),
        _STATE_FILES["decision-store"]: default_decision_store(),
    }

    for relative_path, model in state_models.items():
        dest = ai_eng_dir / relative_path
        if dest.exists():
            continue
        write_json_model(dest, model)
        created.append(dest)

    return created


def _log_install_event(ai_eng_dir: Path, result: InstallResult) -> None:
    """Append an audit-log entry for the install operation.

    Args:
        ai_eng_dir: Path to the ``.ai-engineering/`` directory.
        result: The install result to log.
    """
    audit_path = ai_eng_dir / _AUDIT_LOG_PATH
    project_root = ai_eng_dir.parent
    repo_ctx = get_repo_context(project_root)
    git_ctx = get_git_context(project_root)
    entry = AuditEntry(
        event="install",
        actor="ai-engineering-cli",
        detail={
            "created": result.total_created,
            "skipped": result.total_skipped,
            "state_files": len(result.state_files),
        },
        vcs_provider=repo_ctx.provider if repo_ctx else None,
        vcs_organization=repo_ctx.organization if repo_ctx else None,
        vcs_project=repo_ctx.project if repo_ctx else None,
        vcs_repository=repo_ctx.repository if repo_ctx else None,
        branch=git_ctx.branch if git_ctx else None,
        commit_sha=git_ctx.commit_sha if git_ctx else None,
    )
    append_ndjson(audit_path, entry)


def _run_operational_phases(target: Path, *, vcs_provider: str, result: InstallResult) -> None:
    manifest_path = target / ".ai-engineering" / "state" / "install-manifest.json"
    if not manifest_path.exists():
        return

    manifest = read_json_model(manifest_path, InstallManifest)

    # Phase 2: required tooling (provider-aware + stack-aware)
    stack_report = check_tools_for_stacks(manifest.installed_stacks)
    for tool in provider_required_tools(vcs_provider):
        install_result = ensure_tool(tool)
        status = getattr(manifest.tooling_readiness, tool, None)
        if status is not None:
            status.installed = install_result.available
            status.required_now = True
            status.mode = "cli" if install_result.available else "api"
            status.message = install_result.detail
        if not install_result.available:
            result.manual_steps.append(f"Install or enable `{tool}` CLI")

    for item in stack_report.tools:
        if not item.available and item.name in {"gitleaks", "semgrep"}:
            # Attempt auto-install before falling back to manual step
            sec_result = ensure_tool(item.name)
            if not sec_result.available:
                result.manual_steps.append(f"Install required security tool `{item.name}`")

    # Deferred setup for projects without stacks
    if not manifest.installed_stacks:
        manifest.operational_readiness.deferred_setup = True
        result.manual_steps.append(
            "No stacks configured. Run 'ai-eng stack add <name>' to configure tooling."
        )

    # Phase 3: VCS auth
    provider = get_provider(target)
    auth_result = check_vcs_auth(vcs_provider, provider, target)
    status = getattr(manifest.tooling_readiness, "gh" if vcs_provider == "github" else "az")
    status.authenticated = auth_result.authenticated
    status.mode = auth_result.mode
    status.message = auth_result.message
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
    manifest.branch_policy.applied = policy_result.applied
    manifest.branch_policy.mode = policy_result.mode
    manifest.branch_policy.message = policy_result.message
    if policy_result.manual_guide is not None:
        manifest.branch_policy.manual_guide = policy_result.manual_guide
        result.guide_text = policy_result.manual_guide
        result.manual_steps.append("Run 'ai-eng guide' to view branch policy setup instructions")

    if not result.manual_steps:
        result.readiness_status = "READY"
    else:
        result.readiness_status = "READY WITH MANUAL STEPS"
    manifest.operational_readiness.status = result.readiness_status
    manifest.operational_readiness.manual_steps_required = bool(result.manual_steps)
    manifest.operational_readiness.manual_steps = result.manual_steps

    write_json_model(manifest_path, manifest)
