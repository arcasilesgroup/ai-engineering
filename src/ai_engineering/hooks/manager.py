"""Git hook generation and installation for ai-engineering.

Provides:
- Cross-OS hook script generation (Bash + PowerShell dispatcher).
- Installation into ``.git/hooks/`` with create-only semantics.
- Conflict detection for third-party hook managers (husky, lefthook, pre-commit).
- Hook integrity verification.
"""

from __future__ import annotations

import hashlib
import stat
from dataclasses import dataclass, field
from pathlib import Path

from ai_engineering.state.models import GateHook, PythonEnvMode

# Third-party hook managers that may conflict with our hooks.
_KNOWN_HOOK_MANAGERS: dict[str, list[str]] = {
    "husky": [".husky"],
    "lefthook": ["lefthook.yml", "lefthook.yaml", ".lefthook.yml", ".lefthook.yaml"],
    "pre-commit": [".pre-commit-config.yaml", ".pre-commit-config.yml"],
}

# Marker line embedded in generated hooks so we can identify our own scripts.
_HOOK_MARKER: str = "# ai-engineering-managed-hook"

# Gate commands per hook type.  These are the CLI commands that each hook
# invokes.  The actual check logic lives in ``policy.gates``.
_GATE_COMMANDS: dict[GateHook, str] = {
    GateHook.PRE_COMMIT: "ai-eng gate pre-commit",
    GateHook.COMMIT_MSG: "ai-eng gate commit-msg",
    GateHook.PRE_PUSH: "ai-eng gate pre-push",
}


@dataclass
class HookConflict:
    """Describes a detected third-party hook manager."""

    manager: str
    indicator: str


@dataclass
class HookInstallResult:
    """Summary of a hook installation operation."""

    installed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    conflicts: list[HookConflict] = field(default_factory=list)


def _bash_preamble_for_mode(mode: PythonEnvMode) -> str:
    """Return the bash environment preamble for a given ``PythonEnvMode``.

    Per spec-101 D-101-12 each mode needs a different shape:

    * ``UV_TOOL`` -- no project venv exists; emit no preamble. The user-scope
      ``uv tool install`` prefix is already on PATH via the operator's
      shell rc (or surfaced via ``emit_path_snippet`` at install time).
    * ``VENV`` -- legacy per-cwd ``.venv/``; prepend its bin/Scripts dir to
      PATH so GUI git clients can resolve ``ai-eng`` even without an active
      shell session.
    * ``SHARED_PARENT`` -- export ``UV_PROJECT_ENVIRONMENT`` so ``uv run``
      resolves the same shared venv from every worktree of the repo.
    """
    if mode is PythonEnvMode.UV_TOOL:
        # Empty string -- no PATH preamble. The leading newline below in
        # the bash template absorbs cleanly so the generated script stays
        # readable even with an empty preamble.
        return ""
    if mode is PythonEnvMode.VENV:
        # Legacy behaviour preserved verbatim for backwards-compat.
        return (
            "# Put project venv on PATH so ai-eng is available even from GUI git clients.\n"
            "# Uses PATH prepend instead of source-activate to avoid setting VIRTUAL_ENV,\n"
            "# which conflicts with uv run when CWD differs (e.g. git worktrees).\n"
            'ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"\n'
            'if [ -d "$ROOT_DIR/.venv/bin" ]; then\n'
            '  export PATH="$ROOT_DIR/.venv/bin:$PATH"\n'
            'elif [ -d "$ROOT_DIR/.venv/Scripts" ]; then\n'
            '  export PATH="$ROOT_DIR/.venv/Scripts:$PATH"\n'
            "fi\n"
        )
    # SHARED_PARENT -- the shared venv lives at git_common_dir/../.venv;
    # ``uv run`` honours UV_PROJECT_ENVIRONMENT so every worktree converges
    # on the same Python install. Computed at hook-execution time so the
    # value tracks the active worktree and survives `git worktree add`.
    return (
        "# Worktree-aware shared venv (spec-101 D-101-12 mode=shared-parent).\n"
        "# Compute the venv path at hook-execution time so every worktree\n"
        "# resolves the same shared root via the UV_PROJECT_ENVIRONMENT var.\n"
        'export UV_PROJECT_ENVIRONMENT="$(git rev-parse --git-common-dir)/../.venv"\n'
    )


def _powershell_preamble_for_mode(mode: PythonEnvMode) -> str:
    """Return the PowerShell environment preamble for a given ``PythonEnvMode``.

    Mirror of :func:`_bash_preamble_for_mode` but in pwsh syntax.
    """
    if mode is PythonEnvMode.UV_TOOL:
        return ""
    if mode is PythonEnvMode.VENV:
        return (
            "# Put project venv on PATH so ai-eng is available even from GUI git clients.\n"
            "# Uses PATH prepend instead of Activate.ps1 to avoid setting VIRTUAL_ENV,\n"
            "# which conflicts with uv run when CWD differs (e.g. git worktrees).\n"
            '$RootDir = (Resolve-Path "$PSScriptRoot/../..").Path\n'
            "$VenvBin = Join-Path $RootDir '.venv/Scripts'\n"
            'if (Test-Path $VenvBin) { $env:PATH = "$VenvBin;$env:PATH" }\n'
        )
    # SHARED_PARENT -- pwsh subexpression invokes git rev-parse and joins
    # the parent .venv/ path. Single quotes are deliberately avoided around
    # the value so `$(...)` evaluates at hook-execution time.
    return (
        "# Worktree-aware shared venv (spec-101 D-101-12 mode=shared-parent).\n"
        "# Compute the venv path at hook-execution time so every worktree\n"
        "# resolves the same shared root via the UV_PROJECT_ENVIRONMENT var.\n"
        '$env:UV_PROJECT_ENVIRONMENT = "$(git rev-parse --git-common-dir)/../.venv"\n'
    )


def generate_bash_hook(hook: GateHook, mode: PythonEnvMode = PythonEnvMode.UV_TOOL) -> str:
    """Generate a Bash hook script for the given gate.

    The script invokes ``ai-eng gate <hook-type>`` and forwards
    ``$@`` only for hooks that accept positional arguments (commit-msg
    receives the message file path).  pre-push receives remote name and
    URL from git which ``ai-eng gate pre-push`` does not accept, so
    arguments are not forwarded for that hook.

    The environment preamble branches on ``mode`` per spec-101 D-101-12 --
    see :func:`_bash_preamble_for_mode` for the per-mode shapes.

    Args:
        hook: The gate hook type to generate.
        mode: The active :class:`PythonEnvMode`. Defaults to
            ``UV_TOOL`` so callers that have not yet plumbed the mode
            through pick up the default contract.

    Returns:
        Complete Bash script content.
    """
    command = _GATE_COMMANDS[hook]
    # commit-msg needs $@ (message file path); pre-push must not
    # receive git's extra args (remote name + URL).
    args_suffix = ' "$@"' if hook == GateHook.COMMIT_MSG else ""
    preamble = _bash_preamble_for_mode(mode)
    # When the preamble is empty (uv-tool) we still want a single blank
    # line between the strict-mode setup and the gate invocation so the
    # script reads consistently across modes.
    preamble_block = f"\n{preamble}\n" if preamble else "\n"
    return f"""\
#!/usr/bin/env bash
{_HOOK_MARKER}
# Auto-generated by ai-engineering. Do not edit manually.
set -euo pipefail
{preamble_block}{command}{args_suffix}
"""


def generate_powershell_hook(hook: GateHook, mode: PythonEnvMode = PythonEnvMode.UV_TOOL) -> str:
    """Generate a PowerShell hook script for the given gate.

    The environment preamble branches on ``mode`` per spec-101 D-101-12 --
    see :func:`_powershell_preamble_for_mode` for the per-mode shapes.

    Args:
        hook: The gate hook type to generate.
        mode: The active :class:`PythonEnvMode`. Defaults to ``UV_TOOL``.

    Returns:
        Complete PowerShell script content.
    """
    command = _GATE_COMMANDS[hook]
    args_suffix = " $args" if hook == GateHook.COMMIT_MSG else ""
    preamble = _powershell_preamble_for_mode(mode)
    preamble_block = f"\n{preamble}\n" if preamble else "\n"
    return f"""\
{_HOOK_MARKER}
# Auto-generated by ai-engineering. Do not edit manually.
$ErrorActionPreference = 'Stop'
{preamble_block}{command}{args_suffix}
if ($LASTEXITCODE -ne 0) {{ exit $LASTEXITCODE }}
"""


def generate_dispatcher_hook(hook: GateHook, mode: PythonEnvMode = PythonEnvMode.UV_TOOL) -> str:
    """Generate a cross-OS dispatcher hook script.

    Git on Windows uses Git Bash to execute hooks, so a Bash script
    works as the dispatcher.  The script detects the OS and delegates
    to the appropriate implementation.

    For simplicity and maximum compatibility, we generate a single Bash
    script that works on all platforms (Git for Windows ships with Bash).

    Args:
        hook: The gate hook type to generate.
        mode: The active :class:`PythonEnvMode`. Forwarded to
            :func:`generate_bash_hook` so the dispatcher honours D-101-12.

    Returns:
        Complete dispatcher script (Bash).
    """
    return generate_bash_hook(hook, mode=mode)


def detect_conflicts(project_root: Path) -> list[HookConflict]:
    """Detect third-party hook managers that may conflict.

    Searches the project root for configuration files and directories
    associated with husky, lefthook, and pre-commit.

    Args:
        project_root: Root directory of the target project.

    Returns:
        List of detected conflicts (empty if none found).
    """
    conflicts: list[HookConflict] = []
    for manager, indicators in _KNOWN_HOOK_MANAGERS.items():
        for indicator in indicators:
            candidate = project_root / indicator
            if candidate.exists():
                conflicts.append(HookConflict(manager=manager, indicator=indicator))
    return conflicts


def is_managed_hook(hook_path: Path) -> bool:
    """Check if a hook file was generated by ai-engineering.

    Args:
        hook_path: Path to the hook file.

    Returns:
        True if the hook contains the ai-engineering marker.
    """
    if not hook_path.is_file():
        return False
    try:
        content = hook_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return _HOOK_MARKER in content


def _resolve_python_env_mode(project_root: Path) -> PythonEnvMode:
    """Read ``manifest.python_env.mode`` for ``project_root``; default UV_TOOL.

    Total -- never raises. Any manifest read error falls through to the
    safe default so hook installation never fails on a malformed manifest.
    """
    try:
        from ai_engineering.state.manifest import load_python_env_mode

        return load_python_env_mode(project_root)
    except Exception:  # pragma: no cover - defensive: never block hook install
        return PythonEnvMode.UV_TOOL


def install_hooks(
    project_root: Path,
    *,
    hooks: list[GateHook] | None = None,
    force: bool = False,
    mode: PythonEnvMode | None = None,
) -> HookInstallResult:
    """Install git hook scripts into ``.git/hooks/``.

    By default, installs all three gate hooks (pre-commit, commit-msg,
    pre-push).  Uses create-only semantics: existing hooks that were NOT
    generated by ai-engineering are never overwritten unless ``force=True``.

    Args:
        project_root: Root directory of the git repository.
        hooks: Specific hooks to install. Defaults to all gate hooks.
        force: If True, overwrite existing non-managed hooks.
        mode: Optional :class:`PythonEnvMode` override. When ``None``, the
            mode is read from ``manifest.python_env.mode`` (D-101-12) and
            falls back to ``UV_TOOL`` when the manifest is absent.

    Returns:
        HookInstallResult with installed, skipped, and conflict details.

    Raises:
        FileNotFoundError: If ``.git/hooks/`` directory does not exist.
    """
    hooks_dir = project_root / ".git" / "hooks"
    if not hooks_dir.is_dir():
        msg = f"Git hooks directory not found: {hooks_dir}. Is this a git repository?"
        raise FileNotFoundError(msg)

    target_hooks = hooks or list(GateHook)
    result = HookInstallResult()
    result.conflicts = detect_conflicts(project_root)

    resolved_mode = mode if mode is not None else _resolve_python_env_mode(project_root)

    for hook in target_hooks:
        hook_path = hooks_dir / hook.value
        ps_path = hooks_dir / f"{hook.value}.ps1"

        if hook_path.exists() and not is_managed_hook(hook_path) and not force:
            result.skipped.append(hook.value)
            continue

        # Write Bash dispatcher (primary)
        content = generate_dispatcher_hook(hook, mode=resolved_mode)
        hook_path.write_text(content, encoding="utf-8")
        _make_executable(hook_path)

        # Write PowerShell companion
        ps_content = generate_powershell_hook(hook, mode=resolved_mode)
        ps_path.write_text(ps_content, encoding="utf-8")

        result.installed.append(hook.value)

    _record_hook_hashes(project_root)

    return result


def uninstall_hooks(
    project_root: Path,
    *,
    hooks: list[GateHook] | None = None,
) -> list[str]:
    """Remove ai-engineering-managed hooks from ``.git/hooks/``.

    Only removes hooks that contain the ai-engineering marker.
    Third-party or user-created hooks are left untouched.

    Args:
        project_root: Root directory of the git repository.
        hooks: Specific hooks to remove. Defaults to all gate hooks.

    Returns:
        List of hook names that were removed.
    """
    hooks_dir = project_root / ".git" / "hooks"
    if not hooks_dir.is_dir():
        return []

    target_hooks = hooks or list(GateHook)
    removed: list[str] = []

    for hook in target_hooks:
        hook_path = hooks_dir / hook.value
        ps_path = hooks_dir / f"{hook.value}.ps1"

        if is_managed_hook(hook_path):
            hook_path.unlink()
            removed.append(hook.value)

        if ps_path.is_file():
            ps_path.unlink()

    return removed


def verify_hooks(project_root: Path) -> dict[str, bool]:
    """Verify that all required hooks are installed and managed.

    Args:
        project_root: Root directory of the git repository.

    Returns:
        Dict mapping hook name to verification status (True = valid).
    """
    hooks_dir = project_root / ".git" / "hooks"
    status: dict[str, bool] = {}

    expected_hashes = _load_expected_hook_hashes(project_root)

    for hook in GateHook:
        hook_path = hooks_dir / hook.value
        managed = is_managed_hook(hook_path)
        if not managed:
            status[hook.value] = False
            continue

        expected_hash = expected_hashes.get(hook.value)
        if expected_hash:
            status[hook.value] = _hook_sha256(hook_path) == expected_hash
        else:
            # No hash recorded in manifest — hook integrity cannot be verified.
            # Fail-closed: treat as unverified.
            status[hook.value] = False

    return status


def _make_executable(path: Path) -> None:
    """Add executable permission bits to a file (Unix-like systems).

    On Windows this is a no-op since file permissions work differently,
    but Git for Windows respects the executable bit in the index.

    Args:
        path: Path to the file to make executable.
    """
    try:
        current = path.stat().st_mode
        path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        pass  # Windows or permission-restricted environment


def _hook_sha256(path: Path) -> str:
    """Compute SHA-256 for a hook file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record_hook_hashes(project_root: Path) -> None:
    """Persist installed hook hashes into install-state when available."""
    from ai_engineering.state.models import ToolEntry
    from ai_engineering.state.service import load_install_state, save_install_state

    state_dir = project_root / ".ai-engineering" / "state"
    state_path = state_dir / "install-state.json"
    hooks_dir = project_root / ".git" / "hooks"
    if not state_path.is_file() or not hooks_dir.is_dir():
        return

    try:
        state = load_install_state(state_dir)
    except (OSError, ValueError):
        return

    hook_hashes: dict[str, str] = {}
    for hook in GateHook:
        hook_path = hooks_dir / hook.value
        if hook_path.is_file() and is_managed_hook(hook_path):
            hook_hashes[hook.value] = _hook_sha256(hook_path)

    # Store hook state in the tooling dict under "git_hooks"
    state.tooling["git_hooks"] = ToolEntry(
        installed=bool(hook_hashes),
        integrity_verified=bool(hook_hashes),
        scopes=list(hook_hashes.keys()),
    )
    # Also store the hashes for integrity verification in a top-level key.
    # We use a convention: store hash values as JSON in the mode field is too
    # restrictive, so instead we store each hook hash as a separate tool entry.
    for hook_name, hash_value in hook_hashes.items():
        state.tooling[f"hook_hash:{hook_name}"] = ToolEntry(
            installed=True,
            mode=hash_value,
        )

    save_install_state(state_dir, state)


def _load_expected_hook_hashes(project_root: Path) -> dict[str, str]:
    """Load expected hook hashes from install-state."""
    from ai_engineering.state.service import load_install_state

    state_dir = project_root / ".ai-engineering" / "state"
    state_path = state_dir / "install-state.json"
    if not state_path.is_file():
        return {}

    try:
        state = load_install_state(state_dir)
    except (OSError, ValueError):
        return {}

    # Read hook hashes from tool entries with "hook_hash:" prefix
    hashes: dict[str, str] = {}
    for key, entry in state.tooling.items():
        if key.startswith("hook_hash:"):
            hook_name = key.removeprefix("hook_hash:")
            hashes[hook_name] = entry.mode
    return hashes
