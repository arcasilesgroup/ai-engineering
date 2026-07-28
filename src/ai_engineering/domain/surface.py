"""Surface domain primitive — spec-133 D-133-15.

A **Surface** is the single first-class domain abstraction that fuses
``AI Provider`` + ``IDE Integration`` into one capability matrix. It
collapses the legacy split between ``providers.ides`` and
``ai_providers.enabled`` (manifest schema sub-002 deletes both, replaces
with ``surfaces.enabled``).

The registry is the authoritative source of the 6 supported surfaces:

* ``claude-code`` — Anthropic Claude Code (full surface, native hooks)
* ``codex`` — OpenAI Codex CLI (full surface)
* ``github-copilot`` — GitHub Copilot (full surface)
* ``opencode`` — sst/opencode (full surface, plugin engine)
* ``cursor`` — Cursor 1.7+ (full surface, stdio JSON hook engine)
* ``antigravity`` — Google Antigravity app plus ``agy`` CLI (first-class, partial audit)

Surface is a frozen dataclass — registry mutations are forbidden at
runtime. ``domain.surface`` has zero infrastructure imports and lives
on the innermost hexagonal layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

HookEngine = Literal["native", "plugin", "stdio", "none"]
AuditCapability = Literal["full", "partial", "none"]


class SurfaceUnknownError(KeyError):
    """Raised when ``get_surface`` is invoked with an unknown surface id."""


@dataclass(frozen=True, slots=True)
class Surface:
    """A Surface is a deterministic instruction + hook target.

    Fields:
        id: Canonical surface identifier (e.g. ``"claude-code"``).
        display_name: Human-readable name (e.g. ``"Claude Code"``).
        instruction_files: Tuple of relative paths the surface reads
            for its persistent instructions (CLAUDE.md, AGENTS.md,
            ``.cursor/rules/*.mdc`` always-included patterns, etc.).
            Per-skill on-demand files (``.claude/skills/<name>/SKILL.md``
            for Claude Code, ``.agents/skills/<name>/SKILL.md`` for every
            other surface per spec-201 D-201-04) are NOT listed here —
            they are lazy-loaded by the agent, not always-included.
        tree_dir: Relative path to the surface's tree-root directory
            (e.g. ``".claude/"``, ``".cursor/"``).
        hook_engine: ``"native"`` (Claude Code stdio JSON or compatible
            host-native hook/config surface), ``"plugin"`` (OpenCode JS/TS
            plugin API), ``"stdio"`` (Cursor stdio JSON), or ``"none"``.
        audit_capability: ``"full"`` if the surface can emit
            ``framework-events.ndjson`` envelopes via a deterministic
            CLI probe; ``"partial"`` if only some events flow;
            ``"none"`` for mirror-only surfaces.
        autodetect_marker: Optional tuple of relative paths whose
            presence signals the surface is in use (e.g. ``(".claude/",)``).
            ``None`` for surfaces without a project-level marker.
    """

    id: str
    display_name: str
    instruction_files: tuple[str, ...]
    tree_dir: str
    hook_engine: HookEngine
    audit_capability: AuditCapability
    autodetect_marker: tuple[str, ...] | None


# ---------------------------------------------------------------------------
# Canonical registry — single source of truth for the 6 Surfaces.
# ---------------------------------------------------------------------------

SURFACE_REGISTRY: Final[dict[str, Surface]] = {
    "claude-code": Surface(
        id="claude-code",
        display_name="Claude Code",
        instruction_files=("CLAUDE.md",),
        tree_dir=".claude/",
        hook_engine="native",
        audit_capability="full",
        autodetect_marker=(".claude/",),
    ),
    "codex": Surface(
        id="codex",
        display_name="Codex CLI",
        instruction_files=("AGENTS.md",),
        tree_dir=".codex/",
        hook_engine="native",
        audit_capability="full",
        autodetect_marker=(".codex/", ".config/codex/"),
    ),
    "github-copilot": Surface(
        id="github-copilot",
        display_name="GitHub Copilot",
        instruction_files=(".github/copilot-instructions.md",),
        tree_dir=".github/",
        hook_engine="native",
        audit_capability="partial",
        autodetect_marker=(".github/copilot-instructions.md",),
    ),
    "opencode": Surface(
        id="opencode",
        display_name="OpenCode",
        instruction_files=("AGENTS.md", "CLAUDE.md"),
        tree_dir=".opencode/",
        hook_engine="plugin",
        audit_capability="full",
        autodetect_marker=(".opencode/",),
    ),
    "cursor": Surface(
        id="cursor",
        display_name="Cursor",
        instruction_files=(".cursor/rules/",),
        tree_dir=".cursor/",
        hook_engine="stdio",
        audit_capability="full",
        autodetect_marker=(".cursor/",),
    ),
    "antigravity": Surface(
        id="antigravity",
        display_name="Antigravity",
        instruction_files=("AGENTS.md",),
        tree_dir=".agents/",
        hook_engine="native",
        audit_capability="partial",
        autodetect_marker=(".agents/",),
    ),
}

SURFACE_IDS: Final[tuple[str, ...]] = tuple(SURFACE_REGISTRY.keys())


def iter_surfaces() -> tuple[Surface, ...]:
    """Return the registry contents in canonical order (frozen tuple)."""
    return tuple(SURFACE_REGISTRY.values())


def get_surface(surface_id: str) -> Surface:
    """Look up a surface by id. Raises ``SurfaceUnknownError`` on miss."""
    try:
        return SURFACE_REGISTRY[surface_id]
    except KeyError as exc:
        raise SurfaceUnknownError(
            f"Unknown surface id: {surface_id!r}. Known: {sorted(SURFACE_REGISTRY)}"
        ) from exc
