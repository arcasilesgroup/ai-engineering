"""Phase-0 stack-context resolver (spec-139 M3).

Resolves the project's stack list and the per-stack test / format / lint
commands from ``.ai-engineering/manifest.yml`` exactly **once** per
``/ai-autopilot`` run. The resolved dictionary is then propagated to
every downstream dispatch (Phase 2 / Phase 4 / Phase 5) via the
``STACK_CONTEXT`` variable in the dispatch prompt, replacing the N
redundant manifest reads (each followed by an 8-hook fan-out) that used
to happen per dispatched agent.

Design constraints (per brief §4.3 and plan M3):

* Pure stdlib — no third-party imports so the resolver can fire from any
  context (incl. hook handlers and pre-commit short-circuits).
* Fail-open — when ``manifest.yml`` is missing, malformed, or carries no
  ``providers.stacks`` key, return a degraded default rather than raise.
  Autopilot itself decides whether to abort; the resolver never crashes.
* Idempotent — two calls in the same process yield equivalent dicts.
* Side-effect free unless :func:`write_stack_context` is invoked
  explicitly; reading the manifest does **not** create the runtime dir.

Default command tables match the post-edit validation matrix in
``.claude/agents/ai-build.md`` § "Stack validation" so the dispatched
``ai-build`` agent can pick the right runner without re-reading agent
guidance from disk.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

DEFAULT_MANIFEST_PATH: Final[Path] = Path(".ai-engineering/manifest.yml")
DEFAULT_RUNTIME_DIR: Final[Path] = Path(".ai-engineering/runtime/autopilot")
"""Parent directory; the resolver writes to ``<DEFAULT_RUNTIME_DIR>/<active>/``."""

# Per-stack command table. Keys mirror the manifest's
# ``providers.stacks`` accepted tokens (spec-128 D-128-09); values are
# the deterministic shell strings each downstream agent should invoke.
# When a stack token is not in this table the resolver emits empty
# strings rather than raising — agents must read the stack override
# file directly if they need a non-default invocation.
_STACK_COMMANDS: Final[dict[str, dict[str, str]]] = {
    "python": {
        "test_command": ".venv/bin/python -m pytest",
        "format_command": ".venv/bin/python -m ruff format",
        "lint_command": ".venv/bin/python -m ruff check",
    },
    "typescript": {
        "test_command": "npm test",
        "format_command": "npx prettier --check .",
        "lint_command": "npx tsc --noEmit",
    },
    "javascript": {
        "test_command": "npm test",
        "format_command": "npx prettier --check .",
        "lint_command": "npx eslint .",
    },
    "node": {
        "test_command": "npm test",
        "format_command": "npx prettier --check .",
        "lint_command": "npx eslint .",
    },
    "go": {
        "test_command": "go test ./...",
        "format_command": "gofmt -l .",
        "lint_command": "go vet ./...",
    },
    "rust": {
        "test_command": "cargo test",
        "format_command": "cargo fmt --check",
        "lint_command": "cargo clippy -- -D warnings",
    },
    "csharp": {
        "test_command": "dotnet test",
        "format_command": "dotnet format --verify-no-changes",
        "lint_command": "dotnet build --no-restore",
    },
    "kotlin": {
        "test_command": "./gradlew test",
        "format_command": "./gradlew ktlintCheck",
        "lint_command": "./gradlew detekt",
    },
    "swift": {
        "test_command": "swift test",
        "format_command": "swift-format lint -r .",
        "lint_command": "swiftlint",
    },
    "java": {
        "test_command": "./gradlew test",
        "format_command": "./gradlew spotlessCheck",
        "lint_command": "./gradlew check",
    },
    "ruby": {
        "test_command": "bundle exec rspec",
        "format_command": "bundle exec rubocop",
        "lint_command": "bundle exec rubocop --lint",
    },
    "php": {
        "test_command": "vendor/bin/phpunit",
        "format_command": "vendor/bin/php-cs-fixer fix --dry-run",
        "lint_command": "vendor/bin/phpstan analyse",
    },
    "flutter": {
        "test_command": "flutter test",
        "format_command": "dart format --output=none --set-exit-if-changed .",
        "lint_command": "flutter analyze",
    },
    "react-native": {
        "test_command": "npm test",
        "format_command": "npx prettier --check .",
        "lint_command": "npx eslint .",
    },
}

# Degraded default returned when ``manifest.yml`` is unreadable. ``[]``
# signals "no stacks resolved"; commands collapse to empty strings so
# downstream agents can detect the degraded mode without crashing.
_DEGRADED_DEFAULT: Final[dict[str, Any]] = {
    "stacks": [],
    "test_command": {},
    "format_command": {},
    "lint_command": {},
    "degraded": True,
}


# ---------------------------------------------------------------------------
# Minimal manifest parser
# ---------------------------------------------------------------------------


def _extract_stacks(text: str) -> list[str]:
    """Return ``providers.stacks`` as a list[str] using regex only.

    Pure-stdlib parse so we do not pull in ``yaml`` for what is
    effectively a single-line list extraction. Supports the two shapes
    the manifest schema permits today:

    * Flow style: ``stacks: [python, typescript]``
    * Block style::

          stacks:
            - python
            - typescript

    Returns ``[]`` when ``providers:`` is absent, when ``stacks:`` is
    not nested under ``providers:``, or when the value is empty. Tokens
    are lower-cased so ``[Python]`` and ``[python]`` resolve
    identically (the manifest schema is case-insensitive at the loader
    boundary).
    """
    # Find the ``providers:`` block, then the ``stacks:`` key under it.
    providers_match = re.search(r"(?m)^providers:\s*$", text)
    if providers_match is None:
        return []
    # Slice to the next top-level key (a line that starts in column 0
    # with a non-space, non-``#``).
    start = providers_match.end()
    rest = text[start:]
    end_match = re.search(r"(?m)^[^\s#]", rest)
    block = rest[: end_match.start()] if end_match else rest

    flow = re.search(r"(?m)^\s+stacks:\s*\[([^\]]*)\]\s*$", block)
    if flow:
        return [s.strip().lower() for s in flow.group(1).split(",") if s.strip()]

    block_match = re.search(r"(?m)^\s+stacks:\s*$", block)
    if block_match is None:
        return []
    after = block[block_match.end() :]
    items: list[str] = []
    for line in after.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:].strip().strip("'\"").lower())
            continue
        if stripped == "" or stripped.startswith("#"):
            continue
        # First non-list line ends the block.
        break
    return items


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------


def resolve_stack_context(
    manifest_path: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Resolve the stack context once.

    Parameters
    ----------
    manifest_path:
        Optional override; defaults to ``.ai-engineering/manifest.yml``
        relative to the current working directory (matching every other
        framework helper).

    Returns
    -------
    dict
        ``{"stacks": [...], "test_command": {stack: cmd}, ...}`` keyed
        exactly the way the dispatch-prompt schema in
        ``phase-deep-plan.md`` § Step 0 documents.

    Notes
    -----
    Fail-open. Any IO error, parse error, or missing key collapses to
    :data:`_DEGRADED_DEFAULT`. Callers detect degraded mode via the
    explicit ``degraded`` flag on the returned dict.
    """
    path = Path(manifest_path) if manifest_path is not None else DEFAULT_MANIFEST_PATH
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, IsADirectoryError, PermissionError, OSError):
        return dict(_DEGRADED_DEFAULT)

    try:
        stacks = _extract_stacks(text)
    except re.error:  # pragma: no cover — regex is static; defence in depth
        return dict(_DEGRADED_DEFAULT)

    if not stacks:
        return dict(_DEGRADED_DEFAULT)

    test_command: dict[str, str] = {}
    format_command: dict[str, str] = {}
    lint_command: dict[str, str] = {}
    for stack in stacks:
        cmds = _STACK_COMMANDS.get(stack, {})
        test_command[stack] = cmds.get("test_command", "")
        format_command[stack] = cmds.get("format_command", "")
        lint_command[stack] = cmds.get("lint_command", "")

    return {
        "stacks": list(stacks),
        "test_command": test_command,
        "format_command": format_command,
        "lint_command": lint_command,
        "degraded": False,
    }


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def write_stack_context(
    context: Mapping[str, Any],
    *,
    active: str,
    runtime_dir: str | os.PathLike[str] | None = None,
) -> Path:
    """Persist the resolved context for downstream agent dispatch.

    Writes ``<runtime_dir>/<active>/stack-context.json``. The path lives
    under ``.ai-engineering/runtime/`` which is gitignored — this file
    is session state, not source of truth.

    Parameters
    ----------
    context:
        Mapping produced by :func:`resolve_stack_context` (or a manual
        equivalent in tests). Serialised via :func:`json.dumps` with
        ``sort_keys=True`` for byte-stable output.
    active:
        The active autopilot subdirectory (typically the spec slug or
        a parent-spec id). Resolves to
        ``<runtime_dir>/<active>/stack-context.json``.
    runtime_dir:
        Optional override; defaults to
        ``.ai-engineering/runtime/autopilot``.

    Returns
    -------
    pathlib.Path
        Absolute path to the file just written.
    """
    base = Path(runtime_dir) if runtime_dir is not None else DEFAULT_RUNTIME_DIR
    target_dir = base / active
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "stack-context.json"
    target.write_text(
        json.dumps(dict(context), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return target.resolve()


__all__ = [
    "DEFAULT_MANIFEST_PATH",
    "DEFAULT_RUNTIME_DIR",
    "resolve_stack_context",
    "write_stack_context",
]
