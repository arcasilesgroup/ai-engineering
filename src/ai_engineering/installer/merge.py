"""Intelligent merge for Claude Code ``settings.json``.

Merges framework-provided hooks and permissions into an existing
user configuration without overwriting user customizations.
User wins on conflicts; framework additions are appended.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def merge_settings(template_data: dict, target_path: Path, *, base: Path) -> Path:
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
        template_data: Pre-parsed template dict (caller loads from package
            resources; not a user-controlled path).
        target_path: Path to the user's existing settings file.
        base: Trusted root directory; ``target_path`` must resolve within it (CWE-22).

    Returns:
        The path that was written (always *target_path*).

    Raises:
        ValueError: If ``target_path`` resolves outside ``base``.
    """
    # Validate target_path is within the trusted base (CWE-22 / S2083).
    # Use os.path.realpath + string-prefix so the safe variable is derived
    # from validated strings, not from the tainted parameter.
    real_base = os.path.realpath(base)
    real_target = os.path.realpath(target_path)
    if real_target != real_base and not real_target.startswith(real_base + os.sep):
        msg = f"Path traversal rejected: {target_path!r} is outside trusted base {base!r}"
        raise ValueError(msg)

    # Use the realpath-derived safe variable for all I/O from here on.
    safe_target = Path(real_target)

    try:
        target_data = json.loads(safe_target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        backup = safe_target.with_suffix(".json.bak")
        shutil.copy2(safe_target, backup)
        logger.warning(
            "Malformed settings.json at %s; backed up to %s. Custom deny rules may have been lost.",
            safe_target,
            backup,
        )
        safe_target.write_text(json.dumps(template_data, indent=2) + "\n", encoding="utf-8")
        return safe_target

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

    safe_target.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    return safe_target


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
