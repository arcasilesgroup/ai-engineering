"""Phase pipeline infrastructure for ``ai-eng install``.

Defines the protocol every phase implements (plan / execute / verify),
the data-classes that flow between stages, and the install-mode enum
that drives behavioral branching.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol, runtime_checkable

from ai_engineering.state.models import InstallManifest

# ---------------------------------------------------------------------------
# Install mode
# ---------------------------------------------------------------------------


class InstallMode(Enum):
    """Determines how each phase behaves."""

    INSTALL = "install"
    FRESH = "fresh"
    REPAIR = "repair"
    RECONFIGURE = "reconfigure"


# ---------------------------------------------------------------------------
# Plan data-classes
# ---------------------------------------------------------------------------

_VALID_ACTION_TYPES = frozenset({"create", "overwrite", "merge", "skip", "delete"})


@dataclass
class PlannedAction:
    """A single file operation planned by a phase."""

    action_type: str
    source: str
    destination: str
    rationale: str

    def __post_init__(self) -> None:
        if self.action_type not in _VALID_ACTION_TYPES:
            msg = (
                f"Invalid action_type {self.action_type!r}. "
                f"Must be one of {sorted(_VALID_ACTION_TYPES)}"
            )
            raise ValueError(msg)


@dataclass
class PhasePlan:
    """The serializable plan produced by ``PhaseProtocol.plan()``."""

    phase_name: str
    actions: list[PlannedAction] = field(default_factory=list)

    def __post_init__(self) -> None:
        for action in self.actions:
            dest = action.destination
            if dest.startswith("/"):
                msg = (
                    f"Absolute destination path rejected: {dest!r} "
                    f"(phase={self.phase_name}, action={action.action_type}). "
                    "All paths must be relative to the target root."
                )
                raise ValueError(msg)
            if ".." in Path(dest).parts:
                msg = (
                    f"Path traversal rejected: {dest!r} "
                    f"(phase={self.phase_name}, action={action.action_type}). "
                    "Destination must not contain '..' components."
                )
                raise ValueError(msg)

    # -- Serialization -------------------------------------------------------

    def to_dict(self) -> dict:
        """Return a JSON-serializable dictionary."""
        return {
            "phase_name": self.phase_name,
            "actions": [
                {
                    "action_type": a.action_type,
                    "source": a.source,
                    "destination": a.destination,
                    "rationale": a.rationale,
                }
                for a in self.actions
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> PhasePlan:
        """Deserialize from a dictionary (inverse of ``to_dict``)."""
        actions = [PlannedAction(**a) for a in data.get("actions", [])]
        return cls(phase_name=data["phase_name"], actions=actions)


# ---------------------------------------------------------------------------
# Result / verdict data-classes
# ---------------------------------------------------------------------------


@dataclass
class PhaseResult:
    """Outcome of executing a phase plan."""

    phase_name: str
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class PhaseVerdict:
    """Verification outcome after phase execution."""

    phase_name: str
    passed: bool = True
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Install context
# ---------------------------------------------------------------------------


@dataclass
class InstallContext:
    """Shared context threaded through every phase."""

    target: Path
    mode: InstallMode
    providers: list[str] = field(default_factory=list)
    vcs_provider: str = "github"
    stacks: list[str] = field(default_factory=list)
    ides: list[str] = field(default_factory=list)
    existing_manifest: InstallManifest | None = None


# ---------------------------------------------------------------------------
# Phase protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class PhaseProtocol(Protocol):
    """Contract every install phase must satisfy."""

    @property
    def name(self) -> str: ...

    def plan(self, context: InstallContext) -> PhasePlan: ...

    def execute(self, plan: PhasePlan, context: InstallContext) -> PhaseResult: ...

    def verify(self, result: PhaseResult, context: InstallContext) -> PhaseVerdict: ...


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "InstallContext",
    "InstallMode",
    "PhasePlan",
    "PhaseProtocol",
    "PhaseResult",
    "PhaseVerdict",
    "PlannedAction",
]
