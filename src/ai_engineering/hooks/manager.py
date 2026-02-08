"""Git hook installation and readiness checks."""

from __future__ import annotations

from pathlib import Path


HOOKS = ("pre-commit", "commit-msg", "pre-push")


def _hook_script(stage: str) -> str:
    """Return hook script content for stage."""
    command = f"gate {stage}"
    if stage == "commit-msg":
        command = 'gate commit-msg "$1"'
    return (
        "#!/bin/sh\n"
        "# ai-engineering managed hook\n"
        "if [ -x .venv/bin/python ]; then\n"
        "  PYTHONPATH=src .venv/bin/python -m ai_engineering.cli "
        f"{command}\n"
        "else\n"
        f"  ai {command}\n"
        "fi\n"
    )


def hooks_dir(repo_root: Path) -> Path:
    """Return `.git/hooks` directory for repository."""
    return repo_root / ".git" / "hooks"


def install_placeholder_hooks(repo_root: Path) -> None:
    """Install managed hooks for MVP bootstrap."""
    directory = hooks_dir(repo_root)
    directory.mkdir(parents=True, exist_ok=True)
    for hook in HOOKS:
        hook_path = directory / hook
        content = _hook_script(hook)
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
        if not (hook_path.exists() and hook_path.stat().st_mode & 0o111 != 0):
            checks.append(False)
            continue
        content = hook_path.read_text(encoding="utf-8")
        checks.append("ai-engineering managed hook" in content)
    ok = all(checks)
    return {"installed": ok, "integrityVerified": ok}
