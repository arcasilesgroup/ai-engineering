"""Deterministic stack-to-overrides router.

App-layer pure function; resolves a build task to its overrides prose
directory under ``.ai-engineering/overrides/<stack>/``. Stdlib only — no
domain or infra deps. Hot-path budget: p95 < 50 ms over 1000 calls.

Resolution order:

1. Explicit ``spec_stack`` argument (e.g. spec frontmatter declares it).
2. File-extension inference from ``task_path``.
3. ``UnknownStackError`` when neither yields a supported stack.

Spec ref: spec-127 sub-008 (M7 adapter library), D-127-06, D-127-11.
spec-128 D-128-01: ``adapters/`` renamed to ``overrides/``.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["UnknownStackError", "resolve_adapter"]


class UnknownStackError(ValueError):
    """Raised when neither ``spec_stack`` nor path inference resolves."""


_REPO_ROOT = Path(__file__).resolve().parents[2]
_OVERRIDES_ROOT = _REPO_ROOT / ".ai-engineering" / "overrides"

_SUPPORTED_STACKS: frozenset[str] = frozenset(
    {"typescript", "python", "go", "rust", "swift", "csharp", "kotlin"}
)

_EXT_TO_STACK: dict[str, str] = {
    ".ts": "typescript",
    ".tsx": "typescript",
    ".py": "python",
    ".go": "go",
    ".rs": "rust",
    ".swift": "swift",
    ".cs": "csharp",
    ".kt": "kotlin",
}


def resolve_adapter(task_path: Path, spec_stack: str | None) -> Path:
    """Return the adapter directory for the given task.

    Args:
        task_path: Path to a file the build task targets. Used for
            extension-based stack inference when ``spec_stack`` is None.
        spec_stack: Explicit stack hint from the spec; takes precedence
            over inference. ``None`` triggers inference.

    Returns:
        Path under ``.ai-engineering/overrides/<stack>/``.

    Raises:
        UnknownStackError: when ``spec_stack`` is unsupported, or
            ``spec_stack`` is None and the path extension is unknown.
    """
    if spec_stack is not None:
        if spec_stack not in _SUPPORTED_STACKS:
            raise UnknownStackError(
                f"unsupported spec_stack {spec_stack!r}; "
                f"expected one of {sorted(_SUPPORTED_STACKS)}"
            )
        return _OVERRIDES_ROOT / spec_stack

    inferred = _EXT_TO_STACK.get(task_path.suffix)
    if inferred is None:
        raise UnknownStackError(
            f"cannot infer stack from path {task_path!s} (no spec_stack, unsupported extension)"
        )
    return _OVERRIDES_ROOT / inferred
