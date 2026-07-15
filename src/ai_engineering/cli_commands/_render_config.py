"""Shared render helper for ``ai-eng config`` / ``status`` / install summary.

spec-133 D-133-16 hard-cut: a single :func:`render_config` produces the
canonical posture view consumed by every command that needs to surface
the user's current install. KISS + DRY: one function, one output
contract, three callers. Hexagonal: domain (:mod:`Surface`) provides the
closed catalog; this module composes available x selected and renders.
"""

from __future__ import annotations

from collections.abc import Iterable

from ai_engineering import __version__
from ai_engineering.config.manifest import ManifestConfig
from ai_engineering.core.output import Renderer
from ai_engineering.domain.surface import SURFACE_REGISTRY
from ai_engineering.installer.operations import get_available_stacks
from ai_engineering.version.compare import is_newer
from ai_engineering.version.framework_drift import framework_is_behind


def _latest_known_or_none() -> str | None:
    """Cached (non-blocking) latest-known version, or None offline / on error."""
    try:
        from ai_engineering.version import resolve_latest_known

        latest = resolve_latest_known()
        return latest if isinstance(latest, str) and latest else None
    except Exception:
        return None


def _format_checked_row(selected: bool, label: str, detail: str | None = None) -> str:
    """Render a single ``[✓] label [— detail]`` row."""
    marker = "[✓]" if selected else "[ ]"
    if detail:
        return f"  {marker} {label:<18} {detail}"
    return f"  {marker} {label}"


def _fw_row(label: str, version: str, note: str = "") -> str:
    """Render one aligned Framework version row (``label  version  · note``)."""
    line = f"  {label:<15}{version}"
    return f"{line}   · {note}" if note else line


def render_config(cfg: ManifestConfig, renderer: Renderer) -> None:
    """Render the user-facing posture (surfaces x stacks x VCS x policy).

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

    # spec-184 D-184-05: project-vs-installed framework version. The applied
    # value is the framework version that last wrote these files (advanced by
    # `ai-eng update`); `behind` means the installed package is newer. Text +
    # verb are the primary signal (no ⟳ glyph here — plain path may be piped /
    # Windows cp1252; see D-184-04). Advise-only, never blocks.
    # Full version chain, three axes in one place:
    #   latest (PyPI)  →  installed (this machine)  →  project (these files)
    # gap installed<latest  = run `ai-eng version upgrade` (upgrade the tool);
    # gap project<installed = run `ai-eng update` (update the project files).
    # Text + verb are the primary signal (no ⟳/◈ glyph — plain path may be
    # piped / Windows cp1252). Advise-only, never blocks. `latest` is the
    # cached, non-blocking resolver (may be None offline).
    applied = cfg.framework_version or "?"
    latest = _latest_known_or_none()
    project_behind = framework_is_behind(cfg.framework_version, __version__)
    upgrade_available = bool(latest and is_newer(latest, __version__))

    # Three human-labeled axes so it is self-evident which version is which:
    #   latest (PyPI)  ·  your ai-eng (this machine)  ·  this project (files here).
    # Each behind-row names its own fix. Labels + text are the signal — no
    # ↑/glyph (plain path may be piped / Windows cp1252, D-184-04). Advise-only.
    renderer.section("Framework")
    if latest:
        renderer.step(_fw_row("latest (PyPI)", latest))
    renderer.step(
        _fw_row(
            "your ai-eng",
            __version__,
            "upgrade available — run ai-eng version upgrade" if upgrade_available else "",
        )
    )
    renderer.step(
        _fw_row("this project", applied, "behind — run ai-eng update" if project_behind else "")
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
        "framework": {
            "applied": cfg.framework_version or None,
            "installed": __version__,
            "latest": _latest_known_or_none(),
            "behind": framework_is_behind(cfg.framework_version, __version__),
            "upgrade_available": bool(
                _latest_known_or_none() and is_newer(_latest_known_or_none() or "", __version__)
            ),
        },
    }


__all__: Iterable[str] = ("render_config", "render_config_payload")
