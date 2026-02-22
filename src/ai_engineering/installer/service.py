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

from ai_engineering.hooks.manager import HookInstallResult, install_hooks
from ai_engineering.state.defaults import (
    default_decision_store,
    default_install_manifest,
    default_ownership_map,
    default_sources_lock,
)
from ai_engineering.state.io import append_ndjson, write_json_model
from ai_engineering.state.models import AuditEntry

from .templates import (
    CopyResult,
    copy_project_templates,
    copy_template_tree,
    get_ai_engineering_template_root,
)

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
