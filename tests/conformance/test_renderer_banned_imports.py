"""Conformance gate: cli_commands/* import surface for legacy output modules.

# Phase 1 (sub-002): baseline + regression guard.
# Phase 2 (sub-004): tighten to zero once command migration completes.

After spec-132 D-132-12 introduces the Renderer (``ai_engineering.core.output``)
as the single source of truth for command output, every module under
``src/ai_engineering/cli_commands/`` must reach output through the Renderer
rather than importing the legacy four modules directly:

* ``ai_engineering.cli_envelope``
* ``ai_engineering.cli_ui``
* ``ai_engineering.cli_progress``
* ``ai_engineering.cli_output``

Sub-002 only ships the Renderer plus this conformance gate; the actual
command migration happens in sub-004. To support that staged rollout the
test runs in two modes:

1. **Baseline mode** (HEAD on sub-002): records the current import count and
   asserts the scan engine works. New direct imports are blocked via a
   regression guard so the population can only shrink.
2. **Strict mode** (sub-004 onward): the constant ``EXPECTED_VIOLATIONS_BASELINE``
   drops to ``0`` and the test fails on any direct import.

The dial is intentionally numeric (not a feature flag) so the migration
PR's diff is a single integer change that reviewers can read in seconds.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# Repo root resolved relative to this test file's location: tests/conformance/.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_CLI_COMMANDS = _REPO_ROOT / "src" / "ai_engineering" / "cli_commands"

# Modules whose direct import from cli_commands/ is banned post-migration.
_BANNED_TAILS: frozenset[str] = frozenset({"cli_envelope", "cli_ui", "cli_progress", "cli_output"})

# Baseline as of sub-002 landing (count gathered from `ast.walk` over all
# `.py` files under cli_commands/, excluding ``__init__.py``). Sub-004 drops
# this to ``0`` after migrating every command module to the Renderer.
EXPECTED_VIOLATIONS_BASELINE: int = 59


def _iter_command_modules() -> list[Path]:
    """Yield every command module under ``cli_commands/`` except ``__init__``."""
    return [
        path
        for path in sorted(_CLI_COMMANDS.rglob("*.py"))
        if path.name != "__init__.py" and "__pycache__" not in path.parts
    ]


def _scan_violations(module_path: Path) -> list[str]:
    """Return human-readable banned-import strings for one module."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            tail = module_name.rsplit(".", 1)[-1]
            if tail in _BANNED_TAILS:
                violations.append(
                    f"{module_path.relative_to(_REPO_ROOT)}: from {module_name} import ..."
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                tail = alias.name.rsplit(".", 1)[-1]
                if tail in _BANNED_TAILS:
                    violations.append(f"{module_path.relative_to(_REPO_ROOT)}: import {alias.name}")
    return violations


def _all_violations() -> list[str]:
    """All banned-import occurrences across every cli_commands/ module."""
    out: list[str] = []
    for module in _iter_command_modules():
        out.extend(_scan_violations(module))
    return out


def test_cli_commands_directory_exists() -> None:
    """Guard: the scan target must exist; without it the gate is meaningless."""
    assert _CLI_COMMANDS.is_dir(), (
        f"Expected {_CLI_COMMANDS!s} to exist; renderer ban scan cannot run."
    )


def test_scan_engine_detects_at_least_one_banned_import() -> None:
    """Sanity check that ``ast.walk`` actually finds something on HEAD.

    If sub-004 lands and this assertion fails because every command has been
    migrated to the Renderer, the failure is the cue to drop
    ``EXPECTED_VIOLATIONS_BASELINE`` to ``0`` and delete this sanity check
    in the same commit.
    """
    violations = _all_violations()
    assert violations, (
        "Renderer ban scan returned zero violations on HEAD; either every "
        "cli_commands/ module has been migrated (drop EXPECTED_VIOLATIONS_BASELINE "
        "to 0 and remove this sanity test) or the scan logic regressed."
    )


def test_banned_import_count_matches_or_decreases() -> None:
    """Regression guard: the cli_commands/* banned-import count must never grow.

    New PRs may NOT introduce additional direct imports of the legacy four
    output modules from inside ``cli_commands/``. They are free to remove them
    (decreasing the count) — when the count reaches ``0`` the sub-004 PR will
    drop ``EXPECTED_VIOLATIONS_BASELINE`` accordingly.
    """
    violations = _all_violations()
    actual = len(violations)
    if actual > EXPECTED_VIOLATIONS_BASELINE:
        delta = actual - EXPECTED_VIOLATIONS_BASELINE
        pytest.fail(
            "Renderer ban: new direct imports of cli_envelope/cli_ui/cli_progress/cli_output "
            f"from cli_commands/ detected (+{delta}). Route output through "
            "ai_engineering.core.output.Renderer instead.\n\n"
            "All current violations:\n" + "\n".join(violations)
        )
    # The count is allowed to drop below the baseline; sub-004 will rebase it
    # to the new floor (eventually 0).
    assert actual <= EXPECTED_VIOLATIONS_BASELINE
