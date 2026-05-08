"""Skill conformance infrastructure adapters.

Hexagonal layer rule (D-127-09): this package implements ports declared
in :mod:`skill_app.ports`. It may import ``skill_domain`` read-only;
reverse imports from ``skill_app`` are forbidden.
"""

from __future__ import annotations
