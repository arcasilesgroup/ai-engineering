"""Shared render helper for ``ai-eng config`` / ``status`` / install summary.

spec-133 D-133-16 hard-cut: a single :func:`render_config` produces the
canonical posture view consumed by every command that needs to surface
the user's current install. KISS + DRY: one function, one output
contract, three callers. Hexagonal: domain (:mod:`Surface`) provides the
closed catalog; this module composes available × selected and renders.
"""

from __future__ import annotations

from collections.abc import Iterable

from ai_engineering.config.manifest import ManifestConfig
from ai_engineering.core.output import Renderer
from ai_engineering.domain.surface import SURFACE_REGISTRY
from ai_engineering.installer.operations import get_available_stacks


def _format_checked_row(selected: bool, label: str, detail: str | None = None) -> str:
    """Render a single ``[✓] label [— detail]`` row."""
    marker = "[✓]" if selected else "[ ]"
    if detail:
        return f"  {marker} {label:<18} {detail}"
    return f"  {marker} {label}"


def render_config(cfg: ManifestConfig, renderer: Renderer) -> None:
    """Render the user-facing posture (surfaces × stacks × VCS × policy).

    Consumed by ``ai-eng install`` (post-install + already-installed),
    ``ai-eng status``, and ``ai-eng config`` (default callback). Output
    intentionally honest: shows ONLY the available catalog and which
    entries are selected — no derived counts, no fabricated metrics.
    """
    enabled_surfaces = set(cfg.surfaces.enabled or [])

    renderer.section(f"Surfaces ({len(SURFACE_REGISTRY)} available)")
    for surface_id, surface in SURFACE_REGISTRY.items():
        detail = f"{surface.display_name:<18} {surface.hook_engine} hooks"
        renderer.step(_format_checked_row(surface_id in enabled_surfaces, surface_id, detail))

    available_stacks = get_available_stacks()
    selected_stacks = set(cfg.providers.stacks or [])
    renderer.section(f"Stacks ({len(available_stacks)} available)")
    for stack in available_stacks:
        renderer.step(_format_checked_row(stack in selected_stacks, stack))

    renderer.section("Policy")
    renderer.kv("VCS", cfg.providers.vcs)
    renderer.kv(
        "Quality",
        f"coverage={cfg.quality.coverage}% · duplication={cfg.quality.duplication} · "
        f"cyclomatic={cfg.quality.cyclomatic} · cognitive={cfg.quality.cognitive}",
    )
    renderer.kv("Gates", cfg.gates.mode)
    renderer.kv("CI/CD", cfg.cicd.standards_url or "<not set>")
    renderer.kv(
        "Telemetry",
        f"{cfg.telemetry.consent} · default={cfg.telemetry.default}",
    )


def render_config_payload(cfg: ManifestConfig) -> dict[str, object]:
    """Return the same posture as :func:`render_config` as a JSON-friendly dict.

    Used by ``--json`` mode of the consuming commands.
    """
    available_stacks = get_available_stacks()
    enabled_surfaces = list(cfg.surfaces.enabled or [])
    selected_stacks = list(cfg.providers.stacks or [])
    return {
        "surfaces": {
            "available": list(SURFACE_REGISTRY.keys()),
            "enabled": enabled_surfaces,
        },
        "stacks": {
            "available": available_stacks,
            "enabled": selected_stacks,
        },
        "vcs": cfg.providers.vcs,
        "quality": {
            "coverage": cfg.quality.coverage,
            "duplication": cfg.quality.duplication,
            "cyclomatic": cfg.quality.cyclomatic,
            "cognitive": cfg.quality.cognitive,
        },
        "gates": cfg.gates.mode,
        "cicd_standards_url": cfg.cicd.standards_url,
        "telemetry": {
            "consent": cfg.telemetry.consent,
            "default": cfg.telemetry.default,
        },
    }


__all__: Iterable[str] = ("render_config", "render_config_payload")
