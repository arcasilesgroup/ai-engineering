"""Ports package — abstract Protocols the application layer depends on.

Spec-127 D-127-09 hexagonal seams. Each module under this package
declares a single ``typing.Protocol`` (or a small cohesive cluster)
that an infrastructure adapter implements. Use cases in
:mod:`skill_app` accept these ports via constructor injection so the
domain stays free of I/O.

Re-exports follow the brief §22 split contract: importing a port from
``skill_app.ports`` resolves to the same class as importing it from
its dedicated submodule (``skill_app.ports.skill``, etc.). The
top-level ``skill_app.ports`` module (the legacy ``ports.py`` shim
kept for backward compatibility) re-exports from this package.
"""

from __future__ import annotations

from skill_app.ports.agent import AgentScannerPort
from skill_app.ports.board import BoardPort
from skill_app.ports.hook import HookPort
from skill_app.ports.memory import MemoryPort
from skill_app.ports.mirror import MirrorPort, ReporterPort
from skill_app.ports.research import ResearchPort
from skill_app.ports.skill import SkillScannerPort
from skill_app.ports.telemetry import TelemetryPort

__all__ = [
    "AgentScannerPort",
    "BoardPort",
    "HookPort",
    "MemoryPort",
    "MirrorPort",
    "ReporterPort",
    "ResearchPort",
    "SkillScannerPort",
    "TelemetryPort",
]
