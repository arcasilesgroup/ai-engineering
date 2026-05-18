"""Read-only accessor for ``.ai-engineering/manifest.yml`` (spec-129 T-2).

This module is the GREEN-phase implementation of the contract pinned in
``tests/unit/scripts/_lib/test_manifest_reader.py`` (T-1). It exposes a
narrow, side-effect-free surface that the three new hot-path scripts
(``standup_render``, ``cleanup_run``, ``resolve_classify``) and the
three existing scripts (``session_bootstrap``, ``commit_compose``,
``pr_body_compose``) consume in Phase 2.

Resolver precedence for ``resolve_stack``:

1. ``stack.language`` — explicit per-stack override block at the top
   level. If present and non-empty, it wins. This shape is reserved for
   future per-stack mode configuration (none of the existing fixtures
   use it yet).
2. ``providers.stacks[0]`` — first declared stack in the providers
   block. This is the path the canonical manifest exercises today
   (``providers.stacks: [python]``).
3. Otherwise, raise ``InvalidManifestError`` with a descriptive
   message — a manifest with neither resolution path is malformed
   for the purposes of stack-aware tooling.

All I/O is bounded: a single ``Path.read_text`` plus one
``yaml.safe_load`` call per public function invocation. No caching, no
global state, no mutation of loaded structures. Perf floor: under 50 ms
per call on a warm filesystem (the test enforces a 5 s ceiling for 100
sequential calls as a CI-noise-tolerant proxy).

Errors are surfaced as typed subclasses rather than bare
``FileNotFoundError`` / ``yaml.YAMLError`` so callers can build their
own UX around them without ``isinstance`` chains against stdlib types.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

_HAS_YAML = importlib.util.find_spec("yaml") is not None
if _HAS_YAML:
    import yaml

__all__ = [
    "InvalidManifestError",
    "MissingManifestError",
    "read_work_items",
    "resolve_stack",
]


class MissingManifestError(FileNotFoundError):
    """Raised when the manifest path does not exist on disk.

    Subclasses ``FileNotFoundError`` so that callers who only care
    about "file is missing" can still catch via the stdlib type. The
    typed subclass lets new code branch on manifest-specific failure
    without ambiguous ``isinstance`` checks against unrelated I/O.
    """


class InvalidManifestError(ValueError):
    """Raised when the manifest exists but cannot be parsed as YAML.

    Subclasses ``ValueError`` because the file content is the input
    being validated. Wraps any ``yaml.YAMLError`` plus the
    "no resolvable stack" case so the resolver surfaces a single error
    contract regardless of root cause.
    """


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    """Read and parse ``manifest_path`` into a dict.

    Centralised loader so ``resolve_stack`` and ``read_work_items``
    share identical error-mapping behaviour. Pure function: no
    side-effects beyond the single read of ``manifest_path``.

    Raises:
        MissingManifestError: ``manifest_path`` does not exist.
        InvalidManifestError: file exists but ``yaml.safe_load`` fails
            or the top-level structure is not a mapping.
    """
    if not manifest_path.is_file():
        raise MissingManifestError(f"manifest not found: {manifest_path}")

    if not _HAS_YAML:
        raise InvalidManifestError(
            f"pyyaml is not installed — manifest cannot be parsed: {manifest_path}"
        )

    try:
        raw = manifest_path.read_text(encoding="utf-8")
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError as err:
        raise InvalidManifestError(f"manifest YAML parse failed: {manifest_path}") from err

    if not isinstance(loaded, dict):
        raise InvalidManifestError(
            f"manifest top-level must be a mapping, got {type(loaded).__name__}: {manifest_path}"
        )

    return loaded


def resolve_stack(manifest_path: Path) -> str:
    """Return the configured primary stack string for the project.

    Precedence is documented at module level: ``stack.language``
    first, then ``providers.stacks[0]``. Both branches must yield a
    non-empty string; anything else raises ``InvalidManifestError``.

    Args:
        manifest_path: Filesystem path to a YAML manifest file.

    Returns:
        The resolved stack identifier, e.g. ``"python"``.

    Raises:
        MissingManifestError: Path does not exist.
        InvalidManifestError: YAML malformed or no resolvable stack.
    """
    data = _load_manifest(manifest_path)

    stack_block = data.get("stack")
    if isinstance(stack_block, dict):
        language = stack_block.get("language")
        if isinstance(language, str) and language:
            return language

    providers = data.get("providers")
    if isinstance(providers, dict):
        stacks = providers.get("stacks")
        if isinstance(stacks, list) and stacks:
            first = stacks[0]
            if isinstance(first, str) and first:
                return first

    raise InvalidManifestError(
        f"manifest has no resolvable stack "
        f"(checked stack.language and providers.stacks[0]): {manifest_path}"
    )


def read_work_items(manifest_path: Path) -> dict[str, Any]:
    """Return the ``work_items`` block as a plain dict.

    The returned dict is the value parsed by ``yaml.safe_load`` — the
    caller receives a fresh mapping each invocation (no shared cache)
    so downstream mutation cannot leak between callers.

    Args:
        manifest_path: Filesystem path to a YAML manifest file.

    Returns:
        The ``work_items`` block. Empty dict when the key is absent
        but the manifest is otherwise well-formed.

    Raises:
        MissingManifestError: Path does not exist.
        InvalidManifestError: YAML malformed or ``work_items`` value
            is not a mapping.
    """
    data = _load_manifest(manifest_path)
    work_items = data.get("work_items", {})

    if not isinstance(work_items, dict):
        raise InvalidManifestError(
            f"manifest.work_items must be a mapping, "
            f"got {type(work_items).__name__}: {manifest_path}"
        )

    return work_items
