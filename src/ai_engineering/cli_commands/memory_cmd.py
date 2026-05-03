"""spec-118 -- thin shim that exposes the canonical memory CLI.

The canonical `memory/` module lives at `.ai-engineering/scripts/memory/`
(per Article V SSOT). This shim adds that directory to `sys.path` exactly
once and re-exports the Typer app so `ai-eng memory ...` resolves to the
same code path as `python3 -m memory.cli`.

Keeping the implementation in `.ai-engineering/scripts/memory/` keeps the
hook critical path stdlib-only (hooks shell to `python3 -m memory.cli ...`
without going through the `ai_engineering` package). The shim is the only
bridge required for IDE-side users who type `ai-eng memory ...`.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _resolve_canonical_scripts_dir() -> Path:
    """Locate `.ai-engineering/scripts/` from the package install location.

    Walks up from this file until the framework root is found. Falls back to
    `Path.cwd()` for editable installs where the package is imported from a
    development checkout.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / ".ai-engineering" / "scripts"
        if candidate.exists() and (candidate / "memory").exists():
            return candidate
    cwd_candidate = Path.cwd() / ".ai-engineering" / "scripts"
    return cwd_candidate


_SCRIPTS_DIR = _resolve_canonical_scripts_dir()
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# Re-export the canonical Typer app under the shim's name so cli_factory can
# wire it as a sub-app.
try:
    from memory.cli import app as memory_app  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover -- only hits when scripts/memory missing
    import typer

    memory_app = typer.Typer(
        name="memory",
        help=(
            "spec-118 memory layer (unavailable). Install the optional dependency "
            "group with `uv sync --extra memory` and ensure "
            "`.ai-engineering/scripts/memory/` exists."
        ),
    )

    @memory_app.callback()
    def _unavailable() -> None:
        typer.echo(f"memory CLI failed to load: {exc}")
        raise typer.Exit(code=1)
