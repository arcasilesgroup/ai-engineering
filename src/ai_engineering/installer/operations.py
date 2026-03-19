"""Stack and IDE add/remove/list operations for ai-engineering.

Operates on the install manifest to manage which stacks and IDEs are
configured for a project.  All mutations persist immediately to the
``install-manifest.json`` state file and log to the audit trail.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.git.context import get_git_context
from ai_engineering.state.io import append_ndjson, read_json_model, write_json_model
from ai_engineering.state.models import AuditEntry, InstallManifest
from ai_engineering.vcs.repo_context import get_repo_context

from .templates import TEMPLATES_ROOT, copy_project_templates, remove_provider_templates

# Known IDE identifiers recognised by the framework.
_KNOWN_IDES: frozenset[str] = frozenset({"terminal", "vscode", "jetbrains", "cursor"})

# Valid AI provider identifiers.
_VALID_AI_PROVIDERS: frozenset[str] = frozenset(
    {
        "claude_code",
        "github_copilot",
        "gemini",
        "codex",
    }
)

_MANIFEST_RELATIVE: str = "state/install-manifest.json"
_AUDIT_LOG_RELATIVE: str = "state/audit-log.ndjson"


class InstallerError(Exception):
    """Raised when an installer operation cannot proceed."""


def get_available_stacks() -> list[str]:
    """Return the list of stack names that have bundled instruction files.

    Scans the ``contexts/languages/`` template directory for
    ``.md`` files and returns their stems as valid stack identifiers.

    Returns:
        Sorted list of available stack names (e.g. ``["python"]``).
    """
    stacks_dir = TEMPLATES_ROOT / ".ai-engineering" / "contexts" / "languages"
    if not stacks_dir.is_dir():
        return []
    return sorted(p.stem for p in stacks_dir.glob("*.md"))


def get_available_ides() -> list[str]:
    """Return the list of recognised IDE identifiers.

    Returns:
        Sorted list of known IDE names.
    """
    return sorted(_KNOWN_IDES)


def _resolve_paths(target: Path) -> tuple[Path, Path]:
    """Resolve manifest and audit-log paths from the target project root.

    Args:
        target: Root directory of the target project.

    Returns:
        Tuple of (manifest_path, audit_log_path).

    Raises:
        InstallerError: If the ``.ai-engineering/`` directory does not exist.
    """
    ai_eng_dir = target / ".ai-engineering"
    if not ai_eng_dir.is_dir():
        msg = f"Framework not installed at {target}. Run 'ai-eng install' first."
        raise InstallerError(msg)
    return (
        ai_eng_dir / _MANIFEST_RELATIVE,
        ai_eng_dir / _AUDIT_LOG_RELATIVE,
    )


def _load_manifest(manifest_path: Path) -> InstallManifest:
    """Load the install manifest from disk.

    Args:
        manifest_path: Path to the install-manifest.json file.

    Returns:
        Parsed InstallManifest.

    Raises:
        InstallerError: If the manifest file does not exist.
    """
    if not manifest_path.exists():
        msg = f"Install manifest not found: {manifest_path}"
        raise InstallerError(msg)
    return read_json_model(manifest_path, InstallManifest)


def _save_manifest_and_log(
    manifest: InstallManifest,
    manifest_path: Path,
    audit_path: Path,
    *,
    event: str,
    detail: str,
) -> None:
    """Persist manifest changes and append an audit entry.

    Args:
        manifest: Updated manifest model.
        manifest_path: Path to write the manifest.
        audit_path: Path to the audit log.
        event: Audit event name.
        detail: Audit detail string.
    """
    write_json_model(manifest_path, manifest)
    # audit_path is <project>/.ai-engineering/state/audit-log.ndjson
    project_root = audit_path.parent.parent.parent
    repo_ctx = get_repo_context(project_root)
    git_ctx = get_git_context(project_root)
    entry = AuditEntry(
        event=event,
        actor="ai-engineering-cli",
        detail={"message": detail},
        vcs_provider=repo_ctx.provider if repo_ctx else None,
        vcs_organization=repo_ctx.organization if repo_ctx else None,
        vcs_project=repo_ctx.project if repo_ctx else None,
        vcs_repository=repo_ctx.repository if repo_ctx else None,
        branch=git_ctx.branch if git_ctx else None,
        commit_sha=git_ctx.commit_sha if git_ctx else None,
    )
    append_ndjson(audit_path, entry)


def add_stack(target: Path, stack: str) -> InstallManifest:
    """Add a stack to the install manifest.

    Args:
        target: Root directory of the target project.
        stack: Stack identifier to add (e.g., ``"python"``).

    Returns:
        Updated InstallManifest.

    Raises:
        InstallerError: If the framework is not installed, stack already exists,
            or stack name is not recognised.
    """
    available = get_available_stacks()
    if available and stack not in available:
        msg = f"Unknown stack '{stack}'. Available stacks: {', '.join(available)}"
        raise InstallerError(msg)

    manifest_path, audit_path = _resolve_paths(target)
    manifest = _load_manifest(manifest_path)

    if stack in manifest.installed_stacks:
        msg = f"Stack '{stack}' is already installed."
        raise InstallerError(msg)

    manifest.installed_stacks.append(stack)
    _save_manifest_and_log(
        manifest,
        manifest_path,
        audit_path,
        event="stack-add",
        detail=f"added stack: {stack}",
    )
    return manifest


def remove_stack(target: Path, stack: str) -> InstallManifest:
    """Remove a stack from the install manifest.

    Args:
        target: Root directory of the target project.
        stack: Stack identifier to remove.

    Returns:
        Updated InstallManifest.

    Raises:
        InstallerError: If the framework is not installed or stack not found.
    """
    manifest_path, audit_path = _resolve_paths(target)
    manifest = _load_manifest(manifest_path)

    if stack not in manifest.installed_stacks:
        msg = f"Stack '{stack}' is not installed."
        raise InstallerError(msg)

    manifest.installed_stacks.remove(stack)
    _save_manifest_and_log(
        manifest,
        manifest_path,
        audit_path,
        event="stack-remove",
        detail=f"removed stack: {stack}",
    )
    return manifest


def add_ide(target: Path, ide: str) -> InstallManifest:
    """Add an IDE to the install manifest.

    Args:
        target: Root directory of the target project.
        ide: IDE identifier to add (e.g., ``"vscode"``).

    Returns:
        Updated InstallManifest.

    Raises:
        InstallerError: If the framework is not installed, IDE already exists,
            or IDE name is not recognised.
    """
    available = get_available_ides()
    if ide not in available:
        msg = f"Unknown IDE '{ide}'. Available IDEs: {', '.join(available)}"
        raise InstallerError(msg)

    manifest_path, audit_path = _resolve_paths(target)
    manifest = _load_manifest(manifest_path)

    if ide in manifest.installed_ides:
        msg = f"IDE '{ide}' is already installed."
        raise InstallerError(msg)

    manifest.installed_ides.append(ide)
    _save_manifest_and_log(
        manifest,
        manifest_path,
        audit_path,
        event="ide-add",
        detail=f"added IDE: {ide}",
    )
    return manifest


def remove_ide(target: Path, ide: str) -> InstallManifest:
    """Remove an IDE from the install manifest.

    Args:
        target: Root directory of the target project.
        ide: IDE identifier to remove.

    Returns:
        Updated InstallManifest.

    Raises:
        InstallerError: If the framework is not installed or IDE not found.
    """
    manifest_path, audit_path = _resolve_paths(target)
    manifest = _load_manifest(manifest_path)

    if ide not in manifest.installed_ides:
        msg = f"IDE '{ide}' is not installed."
        raise InstallerError(msg)

    manifest.installed_ides.remove(ide)
    _save_manifest_and_log(
        manifest,
        manifest_path,
        audit_path,
        event="ide-remove",
        detail=f"removed IDE: {ide}",
    )
    return manifest


def list_status(target: Path) -> InstallManifest:
    """Load and return the current install manifest.

    Args:
        target: Root directory of the target project.

    Returns:
        Current InstallManifest.

    Raises:
        InstallerError: If the framework is not installed.
    """
    manifest_path, _ = _resolve_paths(target)
    return _load_manifest(manifest_path)


# ---------------------------------------------------------------------------
# AI Provider operations
# ---------------------------------------------------------------------------


def add_provider(target: Path, provider: str) -> InstallManifest:
    """Add an AI provider to the install manifest and copy its templates.

    Args:
        target: Root directory of the target project.
        provider: Provider identifier to add (e.g., ``"github_copilot"``).

    Returns:
        Updated InstallManifest.

    Raises:
        InstallerError: If the framework is not installed, provider already
            exists, or provider name is not recognised.
    """
    if provider not in _VALID_AI_PROVIDERS:
        msg = f"Unknown provider '{provider}'. Available: {', '.join(sorted(_VALID_AI_PROVIDERS))}"
        raise InstallerError(msg)

    manifest_path, audit_path = _resolve_paths(target)
    manifest = _load_manifest(manifest_path)

    if provider in manifest.ai_providers.enabled:
        msg = f"Provider '{provider}' is already enabled."
        raise InstallerError(msg)

    # Copy provider templates
    copy_project_templates(target, providers=[provider])

    manifest.ai_providers.enabled.append(provider)
    _save_manifest_and_log(
        manifest,
        manifest_path,
        audit_path,
        event="provider-add",
        detail=f"added AI provider: {provider}",
    )
    return manifest


def remove_provider(target: Path, provider: str) -> InstallManifest:
    """Remove an AI provider from the install manifest and delete its templates.

    Does not allow removing the last provider.

    Args:
        target: Root directory of the target project.
        provider: Provider identifier to remove.

    Returns:
        Updated InstallManifest.

    Raises:
        InstallerError: If the framework is not installed, provider not found,
            or it is the last remaining provider.
    """
    manifest_path, audit_path = _resolve_paths(target)
    manifest = _load_manifest(manifest_path)

    if provider not in manifest.ai_providers.enabled:
        msg = f"Provider '{provider}' is not enabled."
        raise InstallerError(msg)

    if len(manifest.ai_providers.enabled) <= 1:
        msg = "Cannot remove the last AI provider."
        raise InstallerError(msg)

    # Determine remaining providers after removal
    remaining = [p for p in manifest.ai_providers.enabled if p != provider]

    # Remove provider templates (respects shared files)
    remove_provider_templates(target, provider, remaining)

    manifest.ai_providers.enabled.remove(provider)

    # If the removed provider was primary, promote the first remaining
    if manifest.ai_providers.primary == provider:
        manifest.ai_providers.primary = manifest.ai_providers.enabled[0]

    _save_manifest_and_log(
        manifest,
        manifest_path,
        audit_path,
        event="provider-remove",
        detail=f"removed AI provider: {provider}",
    )
    return manifest
