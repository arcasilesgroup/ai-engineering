"""Install orchestrator for the ai-engineering framework.

Provides the top-level ``install`` function that bootstraps a complete
``.ai-engineering/`` governance structure in a target project directory.

Steps performed by ``install()``:
1. Copy ``.ai-engineering/`` governance templates (create-only).
2. Copy project-level IDE agent templates (CLAUDE.md, .github/copilot/, etc.).
3. Generate state files from defaults (install-manifest, ownership-map,
   decision-store, sources.lock).
4. Append an audit-log entry recording the installation.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from pathlib import Path

from ai_engineering.detector.readiness import check_tools_for_stacks
from ai_engineering.hooks.manager import HookInstallResult, install_hooks
from ai_engineering.state.defaults import (
    default_decision_store,
    default_install_manifest,
    default_ownership_map,
    default_sources_lock,
)
from ai_engineering.state.io import append_ndjson, read_json_model, write_json_model
from ai_engineering.state.models import AuditEntry, InstallManifest
from ai_engineering.vcs.factory import get_provider

from .auth import check_vcs_auth
from .branch_policy import apply_branch_policy
from .cicd import generate_pipelines
from .templates import (
    CopyResult,
    copy_project_templates,
    copy_template_tree,
    get_ai_engineering_template_root,
)
from .tools import ensure_tool, provider_required_tools

# Relative paths under ``.ai-engineering/`` for each state file.
_STATE_FILES: dict[str, str] = {
    "install-manifest": "state/install-manifest.json",
    "ownership-map": "state/ownership-map.json",
    "decision-store": "state/decision-store.json",
    "sources-lock": "state/sources.lock.json",
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
) -> InstallResult:
    """Bootstrap the ai-engineering framework in a target project.

    Copies governance templates, IDE agent configs, and generates state
    files.  Uses create-only semantics: existing files are never overwritten.

    Args:
        target: Root directory of the target project.
        stacks: Initial stacks to install. Defaults to ``["python"]``.
        ides: Initial IDEs to configure. Defaults to ``["terminal"]``.
        vcs_provider: Primary VCS provider. Defaults to ``"github"``.

    Returns:
        InstallResult with details of created and skipped files.
    """
    result = InstallResult()
    ai_eng_dir = target / ".ai-engineering"

    # 1. Copy governance templates
    src_root = get_ai_engineering_template_root()
    result.governance_files = copy_template_tree(src_root, ai_eng_dir)

    # 2. Copy project-level templates (CLAUDE.md, .github/copilot/, etc.)
    result.project_files = copy_project_templates(target)

    # 3. Generate state files (create-only)
    result.state_files = _generate_state_files(
        ai_eng_dir,
        stacks=stacks,
        ides=ides,
        vcs_provider=vcs_provider,
    )

    # If no state files were generated, installation was already present
    if not result.state_files and not result.governance_files.created:
        result.already_installed = True

    # 4. Audit log entry
    _log_install_event(ai_eng_dir, result)

    # 5. Install git hooks (skip silently if not a git repo)
    with contextlib.suppress(FileNotFoundError):
        result.hooks = install_hooks(target)

    # 6. Install-to-operational phases (tooling/auth/cicd/policy)
    _run_operational_phases(target, vcs_provider=vcs_provider, result=result)

    return result


def _generate_state_files(
    ai_eng_dir: Path,
    *,
    stacks: list[str] | None,
    ides: list[str] | None,
    vcs_provider: str = "github",
) -> list[Path]:
    """Generate default state files if they don't already exist.

    Args:
        ai_eng_dir: Path to the ``.ai-engineering/`` directory.
        stacks: Stacks to include in the install manifest.
        ides: IDEs to include in the install manifest.
        vcs_provider: Primary VCS provider.

    Returns:
        List of state file paths that were created.
    """
    created: list[Path] = []

    state_models = {
        _STATE_FILES["install-manifest"]: default_install_manifest(
            stacks=stacks,
            ides=ides,
            vcs_provider=vcs_provider,
        ),
        _STATE_FILES["ownership-map"]: default_ownership_map(),
        _STATE_FILES["decision-store"]: default_decision_store(),
        _STATE_FILES["sources-lock"]: default_sources_lock(),
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
    entry = AuditEntry(
        event="install",
        actor="ai-engineering-cli",
        detail=(
            f"created={result.total_created} "
            f"skipped={result.total_skipped} "
            f"state_files={len(result.state_files)}"
        ),
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
            result.manual_steps.append(f"Install required security tool `{item.name}`")

    # Phase 3: VCS auth
    provider = get_provider(target)
    auth_result = check_vcs_auth(vcs_provider, provider, target)
    status = getattr(manifest.tooling_readiness, "gh" if vcs_provider == "github" else "az")
    status.authenticated = auth_result.authenticated
    status.mode = auth_result.mode
    status.message = auth_result.message
    if not auth_result.authenticated:
        result.manual_steps.append(auth_result.message)

    # Phase 4: CI/CD generation
    cicd_result = generate_pipelines(
        target,
        provider=vcs_provider,
        stacks=manifest.installed_stacks,
    )
    manifest.cicd.generated = bool(cicd_result.created or cicd_result.skipped)
    manifest.cicd.provider = vcs_provider
    manifest.cicd.files = [
        str(p.relative_to(target)) for p in (cicd_result.created + cicd_result.skipped)
    ]

    # Phase 5: branch policy apply + manual fallback
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
        manifest.branch_policy.manual_guide = str(policy_result.manual_guide.relative_to(target))
        result.manual_steps.append(
            f"Apply manual branch policy guide: {manifest.branch_policy.manual_guide}"
        )

    if not result.manual_steps:
        result.readiness_status = "READY"
    elif manifest.cicd.generated:
        result.readiness_status = "READY WITH MANUAL STEPS"
    else:
        result.readiness_status = "FAILED"
    manifest.operational_readiness.status = result.readiness_status
    manifest.operational_readiness.manual_steps_required = bool(result.manual_steps)
    manifest.operational_readiness.manual_steps = result.manual_steps

    write_json_model(manifest_path, manifest)
