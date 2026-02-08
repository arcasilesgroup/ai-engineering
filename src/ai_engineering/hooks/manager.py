"""Git hook installation and readiness checks."""

from __future__ import annotations

from pathlib import Path


HOOKS = ("pre-commit", "commit-msg", "pre-push")


def hooks_dir(repo_root: Path) -> Path:
    """Return `.git/hooks` directory for repository."""
    return repo_root / ".git" / "hooks"


def install_placeholder_hooks(repo_root: Path) -> None:
    """Install placeholder hooks for MVP bootstrap."""
    directory = hooks_dir(repo_root)
    directory.mkdir(parents=True, exist_ok=True)
    for hook in HOOKS:
        hook_path = directory / hook
        content = "#!/bin/sh\n# ai-engineering hook placeholder\nexit 0\n"
        hook_path.write_text(content, encoding="utf-8")
        hook_path.chmod(0o755)


def detect_hook_readiness(repo_root: Path) -> dict[str, bool]:
    """Detect if required hooks exist and are executable."""
    directory = hooks_dir(repo_root)
    if not directory.exists():
        return {"installed": False, "integrityVerified": False}

    checks: list[bool] = []
    for hook in HOOKS:
        hook_path = directory / hook
        checks.append(hook_path.exists() and hook_path.stat().st_mode & 0o111 != 0)
    ok = all(checks)
    return {"installed": ok, "integrityVerified": ok}
