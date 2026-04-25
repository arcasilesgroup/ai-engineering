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

from ai_engineering.state.models import InstallState

# ---------------------------------------------------------------------------
# Phase name constants
# ---------------------------------------------------------------------------

PHASE_DETECT = "detect"
PHASE_GOVERNANCE = "governance"
PHASE_IDE_CONFIG = "ide_config"
PHASE_HOOKS = "hooks"
PHASE_STATE = "state"
PHASE_TOOLS = "tools"

# Canonical pipeline ordering.  StatePhase must run before both ToolsPhase and
# HooksPhase so that install-state.json exists for tool status and hook hashes.
# ToolsPhase must run before HooksPhase so that gate-required tools (gitleaks,
# ruff, etc.) are installed before hooks activate pre-commit/pre-push gates.
PHASE_ORDER: tuple[str, ...] = (
    PHASE_DETECT,
    PHASE_GOVERNANCE,
    PHASE_IDE_CONFIG,
    PHASE_STATE,
    PHASE_TOOLS,
    PHASE_HOOKS,
)

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

        # Validate source path (skip empty strings used by informational actions)
        if self.source:
            if self.source.startswith("/"):
                msg = f"Absolute source path rejected: {self.source!r}"
                raise ValueError(msg)
            if ".." in Path(self.source).parts:
                msg = f"Source path traversal rejected: {self.source!r}"
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
    deleted: list[str] = field(default_factory=list)


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
    existing_state: InstallState | None = None
    # spec-101 T-2.16: ``--force`` plumbing. When True, ToolsPhase bypasses
    # the D-101-07 skip predicate and re-installs every tool unconditionally.
    force: bool = False


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
    "PHASE_DETECT",
    "PHASE_GOVERNANCE",
    "PHASE_HOOKS",
    "PHASE_IDE_CONFIG",
    "PHASE_ORDER",
    "PHASE_STATE",
    "PHASE_TOOLS",
    "InstallContext",
    "InstallMode",
    "PhasePlan",
    "PhaseProtocol",
    "PhaseResult",
    "PhaseVerdict",
    "PlannedAction",
]
