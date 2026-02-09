"""Stack and IDE management operations for installer runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_engineering.paths import repo_root, state_dir, template_root
from ai_engineering.state.io import load_model, write_json
from ai_engineering.state.models import InstallManifest

from .templates import PROJECT_TEMPLATE_BY_IDE, available_stack_templates


SUPPORTED_IDES = {"terminal", "vscode", "claude", "codex", "copilot"}


def _manifest(root: Path) -> InstallManifest:
    return load_model(state_dir(root) / "install-manifest.json", InstallManifest)


def _save_manifest(root: Path, manifest: InstallManifest) -> None:
    write_json(state_dir(root) / "install-manifest.json", manifest.model_dump())


def _copy_if_missing(source: Path, destination: Path) -> str:
    if destination.exists():
        return "exists"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return "created"


def _remove_if_safe(destination: Path, template_content: str) -> str:
    if not destination.exists():
        return "missing"
    current = destination.read_text(encoding="utf-8")
    if current != template_content:
        return "skipped-customized"
    destination.unlink()
    return "removed"


def add_stack(name: str) -> dict[str, Any]:
    """Install stack-specific framework and team templates."""
    root = repo_root()
    available = set(available_stack_templates())
    if name not in available:
        return {
            "ok": False,
            "message": f"unsupported stack: {name}",
            "availableStacks": sorted(available),
        }

    templates = template_root() / ".ai-engineering" / "standards"
    framework_source = templates / "framework" / "stacks" / f"{name}.md"
    team_source = templates / "team" / "stacks" / f"{name}.md"

    framework_destination = (
        root / ".ai-engineering" / "standards" / "framework" / "stacks" / f"{name}.md"
    )
    team_destination = root / ".ai-engineering" / "standards" / "team" / "stacks" / f"{name}.md"

    result = {
        "framework": _copy_if_missing(framework_source, framework_destination),
        "team": _copy_if_missing(team_source, team_destination),
    }

    manifest = _manifest(root)
    stacks = set(manifest.installedStacks)
    stacks.add(name)
    manifest.installedStacks = sorted(stacks)
    _save_manifest(root, manifest)

    return {
        "ok": True,
        "stack": name,
        "result": result,
        "installedStacks": manifest.installedStacks,
    }


def remove_stack(name: str) -> dict[str, Any]:
    """Remove stack templates with safe cleanup semantics."""
    root = repo_root()
    templates = template_root() / ".ai-engineering" / "standards"
    framework_source = templates / "framework" / "stacks" / f"{name}.md"
    team_source = templates / "team" / "stacks" / f"{name}.md"

    if not framework_source.exists() or not team_source.exists():
        return {"ok": False, "message": f"unsupported stack: {name}"}

    framework_destination = (
        root / ".ai-engineering" / "standards" / "framework" / "stacks" / f"{name}.md"
    )
    team_destination = root / ".ai-engineering" / "standards" / "team" / "stacks" / f"{name}.md"

    framework_status = _remove_if_safe(
        framework_destination, framework_source.read_text(encoding="utf-8")
    )
    team_status = _remove_if_safe(team_destination, team_source.read_text(encoding="utf-8"))

    manifest = _manifest(root)
    stacks = set(manifest.installedStacks)
    stacks.discard(name)
    manifest.installedStacks = sorted(stacks)
    _save_manifest(root, manifest)

    return {
        "ok": True,
        "stack": name,
        "result": {"framework": framework_status, "team": team_status},
        "installedStacks": manifest.installedStacks,
    }


def add_ide(name: str) -> dict[str, Any]:
    """Install IDE-specific instruction templates where applicable."""
    root = repo_root()
    if name not in SUPPORTED_IDES:
        return {
            "ok": False,
            "message": f"unsupported ide: {name}",
            "availableIdes": sorted(SUPPORTED_IDES),
        }

    result = "recorded"
    mapping = PROJECT_TEMPLATE_BY_IDE.get(name)
    if mapping is not None:
        source_relative, destination_relative = mapping
        source = template_root() / source_relative
        destination = root / destination_relative
        result = _copy_if_missing(source, destination)

    manifest = _manifest(root)
    ides = set(manifest.installedIdes)
    ides.add(name)
    manifest.installedIdes = sorted(ides)
    _save_manifest(root, manifest)

    return {"ok": True, "ide": name, "result": result, "installedIdes": manifest.installedIdes}


def remove_ide(name: str) -> dict[str, Any]:
    """Remove IDE-specific instruction templates with safe cleanup semantics."""
    root = repo_root()
    if name not in SUPPORTED_IDES:
        return {
            "ok": False,
            "message": f"unsupported ide: {name}",
            "availableIdes": sorted(SUPPORTED_IDES),
        }

    status = "recorded"
    mapping = PROJECT_TEMPLATE_BY_IDE.get(name)
    if mapping is not None:
        source_relative, destination_relative = mapping
        source = template_root() / source_relative
        destination = root / destination_relative
        status = _remove_if_safe(destination, source.read_text(encoding="utf-8"))
        if destination_relative.startswith(".github/"):
            github_dir = root / ".github"
            if github_dir.exists() and not any(github_dir.iterdir()):
                github_dir.rmdir()

    manifest = _manifest(root)
    ides = set(manifest.installedIdes)
    ides.discard(name)
    manifest.installedIdes = sorted(ides)
    _save_manifest(root, manifest)

    return {"ok": True, "ide": name, "result": status, "installedIdes": manifest.installedIdes}


def list_stack_ide_status() -> dict[str, Any]:
    """Return installed and supported stack/IDE status."""
    root = repo_root()
    manifest = _manifest(root)
    return {
        "installedStacks": manifest.installedStacks,
        "installedIdes": manifest.installedIdes,
        "availableStacks": available_stack_templates(),
        "availableIdes": sorted(SUPPORTED_IDES),
    }
