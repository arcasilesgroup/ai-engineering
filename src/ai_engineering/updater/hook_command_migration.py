"""Migrate Claude Code hook commands inside the protected settings.json.

spec-158 concern A. spec-154 rewired the template ``.claude/settings.json`` so
every hook command runs through ``_lib/run-hook.sh`` (which resolves a Python
>=3.11 interpreter). Fresh installs are born correct, but existing installs
never get the fix: ``.claude/settings.json`` is ownership-protected, so
``ai-eng update`` preserves it verbatim and its legacy
``python3 ".../hooks/X.py"`` commands keep failing on hosts whose bare
``python3`` is < 3.11.

This module is a **framework-owned field migration** (D-158-04): it rewrites
ONLY the exact-shape framework hook command strings, leaving every user
customization untouched. It deliberately does NOT flow through the
``FileChange``/reconciler path (which would mark the protected file
``skip-denied``); it is called directly from ``update()`` and reports through
``UpdateResult.hook_migration``.

Design:

* **Exact-shape detection (D-158-02).** Only
  ``python3 "$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/<file>.py"[ args]``
  is rewritten. Anything else that points into the framework hooks dir
  (different interpreter, absolute path, extra flags, a custom wrapper) is
  reported ``skipped`` for manual review, never guessed at.
* **Idempotent (D-158-05).** A command already routed through
  ``run-hook.sh`` is left alone and not counted.
* **Minimum-diff (D-158-06).** The rewrite is a literal ``json.dumps`` string
  replacement on the raw file text, so matchers, timeouts, key order,
  whitespace and ``permissions.deny`` survive byte-for-byte.
* **Safe (D-158-03).** A timestamped backup is written before any mutation;
  dry-run computes the plan without writing.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

_HOOKS_PREFIX = "$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/"
_RUN_HOOK = _HOOKS_PREFIX + "_lib/run-hook.sh"

# Exact legacy shape: ``python3 "<prefix><script>.py"[ <args>]``.
_LEGACY_CMD = re.compile(
    r'^python3 "\$CLAUDE_PROJECT_DIR/\.ai-engineering/scripts/hooks/'
    r'(?P<script>[^"]+\.py)"(?P<args>.*)$'
)


@dataclass
class HookMigrationReport:
    """Outcome of a settings.json hook-command migration."""

    migrated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    backup_path: Path | None = None
    applied: bool = False

    @property
    def migrated_count(self) -> int:
        return len(self.migrated)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped)

    def to_dict(self) -> dict[str, object]:
        return {
            "migrated": self.migrated_count,
            "skipped": self.skipped_count,
            "skipped_commands": list(self.skipped),
            "backup_path": str(self.backup_path) if self.backup_path is not None else None,
            "applied": self.applied,
        }


def _iter_commands(settings: Mapping) -> list[str]:
    """Yield every ``command`` string under ``settings["hooks"][event][*].hooks[*]``."""
    commands: list[str] = []
    hooks = settings.get("hooks")
    if not isinstance(hooks, Mapping):
        return commands
    for groups in hooks.values():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, Mapping):
                continue
            entries = group.get("hooks")
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, Mapping):
                    command = entry.get("command")
                    if isinstance(command, str):
                        commands.append(command)
    return commands


def plan_command_rewrites(settings: Mapping) -> tuple[list[tuple[str, str]], list[str]]:
    """Return ``(rewrites, skipped)`` for *settings* (pure; no IO).

    ``rewrites`` is an ordered, de-duplicated list of ``(old, new)`` command
    pairs. ``skipped`` lists framework-hook commands that do not match the
    exact legacy shape and need manual review.
    """
    rewrites: list[tuple[str, str]] = []
    skipped: list[str] = []
    seen_rewrite: set[str] = set()
    seen_skip: set[str] = set()

    for command in _iter_commands(settings):
        if _RUN_HOOK in command:
            # Already routed through the resolver — idempotent, not counted.
            continue
        match = _LEGACY_CMD.match(command)
        if match is not None:
            if command in seen_rewrite:
                continue
            seen_rewrite.add(command)
            new = f'bash "{_RUN_HOOK}" "{_HOOKS_PREFIX}{match["script"]}"{match["args"]}'
            rewrites.append((command, new))
        elif _HOOKS_PREFIX in command:
            # Points into the framework hooks dir but is not the canonical
            # shape — never guessed at; reported for manual review.
            if command not in seen_skip:
                seen_skip.add(command)
                skipped.append(command)
    return rewrites, skipped


def _run_hook_present(target: Path) -> bool:
    """True iff the resolver wrapper exists under *target* (D-158-08/AC8)."""
    return (target / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "run-hook.sh").is_file()


def migrate_hook_commands(target: Path, *, dry_run: bool) -> HookMigrationReport:
    """Migrate framework hook commands in ``target/.claude/settings.json``.

    Computes the plan always (dry-run visibility); writes + backs up only when
    ``dry_run`` is False. Returns a :class:`HookMigrationReport`. Never raises
    on a missing / malformed settings file (returns an empty report).
    """
    settings = target / ".claude" / "settings.json"
    if not settings.is_file():
        return HookMigrationReport()

    raw = settings.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return HookMigrationReport()

    rewrites, skipped = plan_command_rewrites(data)

    # AC8: never wire commands to a wrapper that is not on disk yet.
    if rewrites and not _run_hook_present(target):
        return HookMigrationReport(migrated=[], skipped=skipped + [old for old, _ in rewrites])

    migrated = [old for old, _ in rewrites]
    if dry_run or not rewrites:
        return HookMigrationReport(migrated=migrated, skipped=skipped, applied=False)

    new_raw = raw
    applied: list[str] = []
    for old, new in rewrites:
        old_literal = json.dumps(old)
        if old_literal in new_raw:
            new_raw = new_raw.replace(old_literal, json.dumps(new))
            applied.append(old)
        else:
            skipped.append(old)

    # Validate the result is still JSON before touching disk.
    try:
        json.loads(new_raw)
    except (json.JSONDecodeError, ValueError):
        return HookMigrationReport(migrated=[], skipped=skipped + applied, applied=False)

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup = settings.with_name(f"settings.json.bak-{stamp}")
    shutil.copy2(settings, backup)

    tmp = settings.with_name("settings.json.aieng-tmp")
    tmp.write_text(new_raw, encoding="utf-8")
    os.replace(tmp, settings)

    return HookMigrationReport(migrated=applied, skipped=skipped, backup_path=backup, applied=True)
