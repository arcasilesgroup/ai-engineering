"""Intelligent merge for Claude Code ``settings.json``.

Merges framework-provided hooks and permissions into an existing
user configuration without overwriting user customizations.
User wins on conflicts; framework additions are appended.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def merge_settings(template_path: Path, target_path: Path, *, base: Path) -> Path:
    """Merge a framework template ``settings.json`` into an existing target.

    Merge semantics:
    - **hooks**: for each event, new matchers are added; existing matchers
      (matched by ``matcher`` value) keep the user version.
    - **permissions.deny / permissions.allow**: missing rules are added;
      existing rules are preserved.
    - All other top-level keys present in the target but absent in the
      template are preserved.

    If the target file contains malformed JSON a warning is logged and the
    template is copied as-is.

    Args:
        template_path: Path to the framework template file.
        target_path: Path to the user's existing settings file.
        base: Trusted root directory; ``target_path`` must resolve within it (CWE-22).

    Returns:
        The path that was written (always *target_path*).

    Raises:
        ValueError: If ``target_path`` resolves outside ``base``.
    """
    # Resolve to canonical paths and validate against the trusted base (CWE-22)
    template_path = template_path.resolve()
    target_path = target_path.resolve()
    base = base.resolve()
    try:
        target_path.relative_to(base)
    except ValueError:
        msg = f"Path traversal rejected: {target_path!r} is outside trusted base {base!r}"
        raise ValueError(msg) from None

    template_data = json.loads(template_path.read_text(encoding="utf-8"))

    try:
        target_data = json.loads(target_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        backup = target_path.with_suffix(".json.bak")
        shutil.copy2(target_path, backup)
        logger.warning(
            "Malformed settings.json at %s; backed up to %s. Custom deny rules may have been lost.",
            target_path,
            backup,
        )
        target_path.write_text(json.dumps(template_data, indent=2) + "\n", encoding="utf-8")
        return target_path

    merged = dict(target_data)

    # -- hooks --
    template_hooks = template_data.get("hooks", {})
    target_hooks = merged.setdefault("hooks", {})
    for event, template_entries in template_hooks.items():
        if not isinstance(template_entries, list):
            continue
        existing = target_hooks.get(event, [])
        if not isinstance(existing, list):
            existing = []
        existing_matchers = {e.get("matcher") for e in existing if isinstance(e, dict)}
        for entry in template_entries:
            if isinstance(entry, dict) and entry.get("matcher") not in existing_matchers:
                existing.append(entry)
        target_hooks[event] = existing

    # -- permissions --
    template_perms = template_data.get("permissions", {})
    target_perms = merged.setdefault("permissions", {})
    for key in ("deny", "allow"):
        template_rules = template_perms.get(key, [])
        target_rules = target_perms.get(key, [])
        if isinstance(template_rules, list) and isinstance(target_rules, list):
            existing_set = set(target_rules)
            for rule in template_rules:
                if rule not in existing_set:
                    target_rules.append(rule)
            target_perms[key] = target_rules

    target_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    return target_path


def validate_settings_structure(data: dict) -> list[str]:
    """Check structural validity of a parsed ``settings.json``.

    Args:
        data: Parsed JSON dictionary.

    Returns:
        List of warning strings (empty means valid).
    """
    warnings: list[str] = []

    permissions = data.get("permissions")
    if permissions is None:
        warnings.append("Missing 'permissions' key")
    elif not isinstance(permissions, dict):
        warnings.append("'permissions' must be a dict")

    hooks = data.get("hooks")
    if hooks is None:
        warnings.append("Missing 'hooks' key")
    elif not isinstance(hooks, dict):
        warnings.append("'hooks' must be a dict")
    else:
        for event, entries in hooks.items():
            if not isinstance(entries, list):
                warnings.append(f"hooks[{event!r}] must be a list")

    return warnings
