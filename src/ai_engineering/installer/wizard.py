"""Interactive install wizard — spec-133 D-133-17 collapsed to 1 question.

The single Surface question replaces the four legacy prompts
(``Select technology stacks`` / ``Select AI providers`` /
``Select IDE integrations`` / ``Select VCS provider``). Stack and VCS
auto-detect silently; CLI flags ``--stack`` and ``--vcs`` override
without prompting.

D-133-17 amendment (option 3): when VCS autodetect is ambiguous (no
``origin`` remote configured), a secondary VCS prompt fires so the
operator can choose explicitly between github and azure_devops. Common
case (remote present) remains 1-question.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import questionary

from ai_engineering.domain.surface import SURFACE_IDS
from ai_engineering.installer.autodetect import (
    _VCS_POPULARITY,
    DetectionResult,
    _order_by_popularity,
)


@dataclass
class WizardResult:
    """User selections from the install wizard.

    spec-133 D-133-16 hard-cut: the legacy ``providers`` / ``ides`` fields
    were deleted. ``surfaces`` is the single canonical axis.
    """

    stacks: list[str]
    surfaces: list[str]
    vcs: str


_VCS_CHOICES: list[str] = _order_by_popularity(
    ["github", "azure_devops"],
    _VCS_POPULARITY,
)

_PROMPT_SURFACES = "Which Surface(s) do you use?"
_PROMPT_VCS = "Which VCS provider? (no git remote detected — choose explicitly)"


def _build_surface_choices(detected_surfaces: list[str]) -> list[questionary.Choice]:
    """One ``Choice`` per Surface, preselected only when autodetect marker matched."""
    detected_set: set[str] = {sid for sid in SURFACE_IDS if sid in detected_surfaces}
    return [
        questionary.Choice(
            sid,
            checked=(sid in detected_set),
        )
        for sid in SURFACE_IDS
    ]


def _checkbox_validate(selection: list[str]) -> bool | str:
    if selection:
        return True
    return "Please select at least one Surface (use spacebar to toggle)"


def _ask_vcs() -> str:
    """Prompt VCS provider selection. Aborts (Ctrl+C) → ``"github"`` default.

    Fires only when ``detected.vcs`` is empty (no ``origin`` remote) and no
    ``--vcs`` flag was passed. Common case (autodetect succeeds) skips this.
    """
    result = questionary.select(
        _PROMPT_VCS,
        choices=_VCS_CHOICES,
        default=_VCS_CHOICES[0],
    ).ask()
    if result is None:
        return "github"
    return result


def _ask_surfaces(detected_surfaces: list[str] | None = None) -> list[str]:
    """Prompt the single Surface question. Aborts on Ctrl+C.

    Pre-check only Surfaces autodetected on disk; nothing is selected by
    default in a greenfield install (spec-133 D-133-17 user feedback).
    """
    result = questionary.checkbox(
        _PROMPT_SURFACES,
        choices=_build_surface_choices(detected_surfaces=detected_surfaces or []),
        validate=_checkbox_validate,
        instruction="(spacebar to select, Enter to confirm)",
    ).ask()
    if result is None:
        return []
    return result


def run_wizard(
    detected: DetectionResult,
    resolved: dict[str, Any] | None = None,
) -> WizardResult:
    """Present the single-question wizard and return the user's selections.

    Stack + VCS are auto-detected silently. CLI flags ``--surface``,
    ``--stack``, and ``--vcs`` skip the wizard entirely when provided.
    """
    if resolved is None:
        resolved = {}

    # Stacks: silent auto-detect (no prompt) unless overridden.
    # spec-133 D-133-25 / B16 Gap 1+2: do NOT default to ["python"] in
    # greenfield mode; preserve empty list when autodetect found nothing.
    stacks = resolved["stacks"] if "stacks" in resolved else list(detected.stacks)

    # VCS: silent when autodetect succeeded; prompt when ambiguous.
    # D-133-17 amendment (option 3): preserve KISS for the common case;
    # fall back to interactive selection only when no remote is configured.
    if "vcs" in resolved:
        vcs = resolved["vcs"]
    elif detected.vcs:
        vcs = detected.vcs
    else:
        vcs = _ask_vcs()

    # Surfaces: single user-facing question (or CLI override).
    if "surfaces" in resolved:
        surfaces = resolved["surfaces"]
    else:
        surfaces = _ask_surfaces(detected_surfaces=list(detected.surfaces))

    return WizardResult(
        stacks=stacks,
        surfaces=surfaces,
        vcs=vcs,
    )
