"""Scope-aware destination resolver for global / local installs (sub-003).

``ai-eng install --local`` (default) writes every surface into the target
repository, exactly as before. ``--global`` writes each home-capable surface
into its canonical home directory per the D9 per-surface map:

- **brain** (``.ai-engineering/`` tree)  -> ``~/.ai-engineering/``
- **claude-code** (``.claude/`` + ``CLAUDE.md``) -> ``~/.claude/``
- **codex** (``AGENTS.md``)               -> ``~/.codex/``
- **opencode** (``AGENTS.md`` + tree)     -> ``~/.config/opencode/``
- **antigravity** (``AGENTS.md``)         -> ``~/.gemini/`` (never ``GEMINI.md``,
  which would collide with the retired Gemini CLI -- issue #16058)

**Cursor** and **GitHub Copilot** have no canonical home file. For global scope
they return a :class:`GuidanceSentinel` so the installer prints the content
location and exact wire-up steps instead of writing a home file (D9 / OQ1).

Precedence (D10) -- local file wins over global -- is enforced by the resolution
and dual-scope update code, not here; this module only computes *where* a given
surface writes for a given scope.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

LOCAL = "local"
GLOBAL = "global"

VALID_SCOPES = frozenset({LOCAL, GLOBAL})

# Logical "brain" surface id for the ``.ai-engineering/`` governance tree.
# It is not a member of the Surface registry (that axis covers IDE/provider
# skins), but the resolver treats it as a first-class scope target so the
# governance phase can honor ``--global`` the same way the skin phases do.
BRAIN = "brain"


@dataclass(frozen=True)
class GuidanceSentinel:
    """Returned for surfaces that have no canonical home destination.

    The installer prints :attr:`message` and the ordered :attr:`steps` so the
    operator can wire the emitted content into the IDE manually.
    """

    surface: str
    message: str
    steps: tuple[str, ...] = field(default_factory=tuple)


# Surfaces with no home destination: emit content + wire-up guidance instead.
_GUIDANCE: dict[str, GuidanceSentinel] = {
    "cursor": GuidanceSentinel(
        surface="cursor",
        message=(
            "Cursor has no machine-wide rules file. The framework content was "
            "emitted to your project; copy it into Cursor User Rules to apply it "
            "across projects."
        ),
        steps=(
            "Open Cursor -> Settings -> Rules -> User Rules.",
            "Paste the contents of the generated .cursor/rules into the User Rules box.",
            "Save; the rules now apply to every Cursor project on this machine.",
        ),
    ),
    "github-copilot": GuidanceSentinel(
        surface="github-copilot",
        message=(
            "GitHub Copilot has no machine-wide instructions file. The framework "
            "content was emitted to your project; wire it in via VS Code settings "
            "to apply it across workspaces."
        ),
        steps=(
            "Open VS Code -> Settings -> search 'github.copilot.chat.codeGeneration.instructions'.",
            "Add a file reference to the generated .github/copilot-instructions.md.",
            "Reload the window; Copilot now uses the framework instructions.",
        ),
    ),
}

# Per-surface global root + the local prefix that root replaces. For a relative
# destination ``rel`` the global path is ``home_root / strip(rel, local_prefix)``.
# ``local_prefix`` is the leading path segment(s) the surface owns under the
# repo; replacing it with the home root keeps the rest of the relative path
# (skills/, agents/, AGENTS.md, etc.) intact.
_GLOBAL_ROOTS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    # surface -> (home_root_parts, local_prefix_parts_to_strip)
    BRAIN: ((), ()),  # ~/ + ".ai-engineering/..." keeps the prefix verbatim
    # ~/.claude/ owns both the ".claude/" tree and the root "CLAUDE.md" file.
    # Strip a leading ".claude" tree segment, then re-root under ~/.claude so
    # tree files (~/.claude/skills/x) and the instruction file (~/.claude/CLAUDE.md)
    # both land correctly.
    "claude-code": ((".claude",), (".claude",)),
    "codex": ((".codex",), ()),  # ~/.codex/ + "AGENTS.md"
    "opencode": ((".config", "opencode"), (".opencode",)),  # strip ".opencode" tree prefix
    "antigravity": ((".gemini",), (".agents",)),  # ~/.gemini/ + "AGENTS.md"; strip ".agents" tree
}


def dest(surface: str, scope: str, target: Path, rel: str) -> Path | GuidanceSentinel:
    """Resolve the absolute destination for *rel* under *surface* and *scope*.

    Args:
        surface: Surface id (or :data:`BRAIN` for the governance tree).
        scope: :data:`LOCAL` or :data:`GLOBAL`.
        target: The repository root (used verbatim for local scope).
        rel: POSIX-style relative destination the phase computed for the
            repo-rooted (local) layout, e.g. ``.claude/skills/x``, ``CLAUDE.md``,
            ``AGENTS.md``, ``.ai-engineering/manifest.yml``.

    Returns:
        The absolute destination :class:`~pathlib.Path`, or a
        :class:`GuidanceSentinel` when the surface has no global home file.

    Raises:
        ValueError: If *scope* is not one of :data:`VALID_SCOPES`.
    """
    if scope not in VALID_SCOPES:
        msg = f"Invalid scope {scope!r}. Must be one of {sorted(VALID_SCOPES)}"
        raise ValueError(msg)

    if scope == LOCAL:
        return target / rel

    if surface in _GUIDANCE:
        return _GUIDANCE[surface]

    mapping = _GLOBAL_ROOTS.get(surface)
    if mapping is None:
        # Unknown surface in global scope: fall back to repo-rooted to avoid a
        # silent mis-write to home. The installer treats this defensively.
        return target / rel

    home_root_parts, strip_parts = mapping
    rel_parts = Path(rel).parts
    if strip_parts and rel_parts[: len(strip_parts)] == strip_parts:
        rel_parts = rel_parts[len(strip_parts) :]

    home = Path.home()
    for part in home_root_parts:
        home = home / part
    for part in rel_parts:
        home = home / part
    return home


def brain_dest(scope: str, target: Path, rel: str) -> Path:
    """Resolve a brain (``.ai-engineering/``) destination as a concrete path.

    The brain is never a guidance surface, so this is a typed convenience over
    :func:`dest` that always returns a :class:`~pathlib.Path` -- callers in the
    governance phase avoid an ``isinstance`` narrowing dance.
    """
    if scope == GLOBAL:
        return Path.home() / rel
    return target / rel


def is_guidance(value: Path | GuidanceSentinel) -> bool:
    """Return True when *value* is a :class:`GuidanceSentinel`."""
    return isinstance(value, GuidanceSentinel)
