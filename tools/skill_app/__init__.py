"""Skill conformance application layer — use cases and ports.

Hexagonal layer rule (D-127-09): this package may import
``skill_domain`` and the standard library. It MUST NOT import
``skill_infra``; infrastructure is supplied via ports defined in
:mod:`skill_app.ports`.
"""

from __future__ import annotations
