"""Adapter layer for ai-engineering (Hexagonal Architecture §10.8).

This package hosts platform-specific or external-dependency adapters
that implement domain ports without leaking infrastructure concerns
into the core. Adapters live OUTSIDE the inner ring -- they may import
from ``ai_engineering.config`` / ``ai_engineering.state`` / ``ai_engineering.paths``
but the inner ring must not import from here.

Subpackages
-----------

* ``host`` -- resource preflight probe (spec-139 M2, D-139-09). Dispatch
  by ``sys.platform`` to darwin / linux / windows backends; returns a
  :class:`ai_engineering.config.HostProbe` dataclass with cores / free
  RAM / memory pressure / swap utilisation.
"""
