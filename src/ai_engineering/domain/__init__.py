"""Domain layer for ai-engineering (hexagonal core).

The ``domain`` package is the pure-Python core: zero infrastructure
imports (no ``typer``, ``sqlite3``, ``yaml``, ``requests``, etc.).
Defines the framework's domain primitives and ports.

Spec-133 D-133-15 introduces the ``Surface`` primitive — the single
domain abstraction that unifies AI-provider + IDE-integration concepts.
"""

from ai_engineering.domain.surface import (
    SURFACE_IDS,
    SURFACE_REGISTRY,
    Surface,
    SurfaceUnknownError,
    get_surface,
    iter_surfaces,
)

__all__ = [
    "SURFACE_IDS",
    "SURFACE_REGISTRY",
    "Surface",
    "SurfaceUnknownError",
    "get_surface",
    "iter_surfaces",
]
