"""Stack and IDE add/remove/list operations for ai-engineering.

Operates on ``manifest.yml`` (via ManifestConfig) to manage which
stacks, IDEs, and AI providers are configured for a project.
All mutations persist to ``manifest.yml`` via ``update_manifest_field``
and log to the audit trail.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.config.loader import load_manifest_config, update_manifest_field
from ai_engineering.config.manifest import ManifestConfig
from ai_engineering.git.context import get_git_context
from ai_engineering.state.io import append_ndjson
from ai_engineering.state.models import AuditEntry
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


def _resolve_audit_path(target: Path) -> Path:
    """Resolve audit-log path from the target project root.

    Args:
        target: Root directory of the target project.

    Returns:
        Path to the audit log.

    Raises:
        InstallerError: If the ``.ai-engineering/`` directory does not exist.
    """
    ai_eng_dir = target / ".ai-engineering"
    if not ai_eng_dir.is_dir():
        msg = f"Framework not installed at {target}. Run 'ai-eng install' first."
        raise InstallerError(msg)
    return ai_eng_dir / _AUDIT_LOG_RELATIVE


def _load_config(target: Path) -> ManifestConfig:
    """Load the manifest config from manifest.yml.

    Args:
        target: Root directory of the target project.

    Returns:
        Parsed ManifestConfig.

    Raises:
        InstallerError: If the ``.ai-engineering/`` directory does not exist.
    """
    ai_eng_dir = target / ".ai-engineering"
    if not ai_eng_dir.is_dir():
        msg = f"Framework not installed at {target}. Run 'ai-eng install' first."
        raise InstallerError(msg)
    return load_manifest_config(target)


def _log_audit(
    audit_path: Path,
    *,
    event: str,
    detail: str,
) -> None:
    """Append an audit entry.

    Args:
        audit_path: Path to the audit log.
        event: Audit event name.
        detail: Audit detail string.
    """
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


def add_stack(target: Path, stack: str) -> ManifestConfig:
    """Add a stack to the manifest config.

    Args:
        target: Root directory of the target project.
        stack: Stack identifier to add (e.g., ``"python"``).

    Returns:
        Updated ManifestConfig.

    Raises:
        InstallerError: If the framework is not installed, stack already exists,
            or stack name is not recognised.
    """
    available = get_available_stacks()
    if available and stack not in available:
        msg = f"Unknown stack '{stack}'. Available stacks: {', '.join(available)}"
        raise InstallerError(msg)

    audit_path = _resolve_audit_path(target)
    config = _load_config(target)

    if stack in config.providers.stacks:
        msg = f"Stack '{stack}' is already installed."
        raise InstallerError(msg)

    new_stacks = [*config.providers.stacks, stack]
    update_manifest_field(target, "providers.stacks", new_stacks)
    _log_audit(audit_path, event="stack-add", detail=f"added stack: {stack}")

    # Re-read to return updated config
    return load_manifest_config(target)


def remove_stack(target: Path, stack: str) -> ManifestConfig:
    """Remove a stack from the manifest config.

    Args:
        target: Root directory of the target project.
        stack: Stack identifier to remove.

    Returns:
        Updated ManifestConfig.

    Raises:
        InstallerError: If the framework is not installed or stack not found.
    """
    audit_path = _resolve_audit_path(target)
    config = _load_config(target)

    if stack not in config.providers.stacks:
        msg = f"Stack '{stack}' is not installed."
        raise InstallerError(msg)

    new_stacks = [s for s in config.providers.stacks if s != stack]
    update_manifest_field(target, "providers.stacks", new_stacks)
    _log_audit(audit_path, event="stack-remove", detail=f"removed stack: {stack}")

    return load_manifest_config(target)


def add_ide(target: Path, ide: str) -> ManifestConfig:
    """Add an IDE to the manifest config.

    Args:
        target: Root directory of the target project.
        ide: IDE identifier to add (e.g., ``"vscode"``).

    Returns:
        Updated ManifestConfig.

    Raises:
        InstallerError: If the framework is not installed, IDE already exists,
            or IDE name is not recognised.
    """
    available = get_available_ides()
    if ide not in available:
        msg = f"Unknown IDE '{ide}'. Available IDEs: {', '.join(available)}"
        raise InstallerError(msg)

    audit_path = _resolve_audit_path(target)
    config = _load_config(target)

    if ide in config.providers.ides:
        msg = f"IDE '{ide}' is already installed."
        raise InstallerError(msg)

    new_ides = [*config.providers.ides, ide]
    update_manifest_field(target, "providers.ides", new_ides)
    _log_audit(audit_path, event="ide-add", detail=f"added IDE: {ide}")

    return load_manifest_config(target)


def remove_ide(target: Path, ide: str) -> ManifestConfig:
    """Remove an IDE from the manifest config.

    Args:
        target: Root directory of the target project.
        ide: IDE identifier to remove.

    Returns:
        Updated ManifestConfig.

    Raises:
        InstallerError: If the framework is not installed or IDE not found.
    """
    audit_path = _resolve_audit_path(target)
    config = _load_config(target)

    if ide not in config.providers.ides:
        msg = f"IDE '{ide}' is not installed."
        raise InstallerError(msg)

    new_ides = [i for i in config.providers.ides if i != ide]
    update_manifest_field(target, "providers.ides", new_ides)
    _log_audit(audit_path, event="ide-remove", detail=f"removed IDE: {ide}")

    return load_manifest_config(target)


def list_status(target: Path) -> ManifestConfig:
    """Load and return the current manifest config.

    Args:
        target: Root directory of the target project.

    Returns:
        Current ManifestConfig.

    Raises:
        InstallerError: If the framework is not installed.
    """
    return _load_config(target)


# ---------------------------------------------------------------------------
# AI Provider operations
# ---------------------------------------------------------------------------


def add_provider(target: Path, provider: str) -> ManifestConfig:
    """Add an AI provider to the manifest config and copy its templates.

    Args:
        target: Root directory of the target project.
        provider: Provider identifier to add (e.g., ``"github_copilot"``).

    Returns:
        Updated ManifestConfig.

    Raises:
        InstallerError: If the framework is not installed, provider already
            exists, or provider name is not recognised.
    """
    if provider not in _VALID_AI_PROVIDERS:
        msg = f"Unknown provider '{provider}'. Available: {', '.join(sorted(_VALID_AI_PROVIDERS))}"
        raise InstallerError(msg)

    audit_path = _resolve_audit_path(target)
    config = _load_config(target)

    if provider in config.providers.ai_providers.enabled:
        msg = f"Provider '{provider}' is already enabled."
        raise InstallerError(msg)

    # Copy provider templates
    copy_project_templates(target, providers=[provider])

    new_enabled = [*config.providers.ai_providers.enabled, provider]
    update_manifest_field(target, "providers.ai_providers.enabled", new_enabled)
    _log_audit(audit_path, event="provider-add", detail=f"added AI provider: {provider}")

    return load_manifest_config(target)


def remove_provider(target: Path, provider: str) -> ManifestConfig:
    """Remove an AI provider and delete its templates.

    Does not allow removing the last provider.

    Args:
        target: Root directory of the target project.
        provider: Provider identifier to remove.

    Returns:
        Updated ManifestConfig.

    Raises:
        InstallerError: If the framework is not installed, provider not found,
            or it is the last remaining provider.
    """
    audit_path = _resolve_audit_path(target)
    config = _load_config(target)

    if provider not in config.providers.ai_providers.enabled:
        msg = f"Provider '{provider}' is not enabled."
        raise InstallerError(msg)

    remaining = [p for p in config.providers.ai_providers.enabled if p != provider]
    if not remaining:
        msg = f"Cannot remove the last AI provider '{provider}'."
        raise InstallerError(msg)

    # Remove provider templates (respects shared files)
    remove_provider_templates(target, provider, remaining)

    update_manifest_field(target, "providers.ai_providers.enabled", remaining)
    if config.providers.ai_providers.primary == provider:
        update_manifest_field(target, "providers.ai_providers.primary", remaining[0])

    _log_audit(audit_path, event="provider-remove", detail=f"removed AI provider: {provider}")

    return load_manifest_config(target)
