"""Interactive install wizard — spec-133 D-133-17 collapsed to 1 question.

The single Surface question replaces the four legacy prompts
(``Select technology stacks`` / ``Select AI providers`` /
``Select IDE integrations`` / ``Select VCS provider``). Stack and VCS
auto-detect silently; CLI flags ``--stack`` and ``--vcs`` override
without prompting.
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

    Note: legacy fields ``providers``/``ides`` are preserved during the
    spec-133 in-flight migration; their values are derived from the
    canonical ``surfaces`` field. Future PRs will drop them.
    """

    stacks: list[str]
    surfaces: list[str]
    providers: list[str]
    ides: list[str]
    vcs: str


_VCS_CHOICES: list[str] = _order_by_popularity(
    ["github", "azure_devops"],
    _VCS_POPULARITY,
)

_PROMPT_SURFACES = "Which Surface(s) do you use?"


def _build_surface_choices(detected_ides: list[str]) -> list[questionary.Choice]:
    """One ``Choice`` per Surface, preselected only when autodetect marker matched."""
    detected_set: set[str] = {sid for sid in SURFACE_IDS if sid in detected_ides}
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


def _ask_surfaces(detected_ides: list[str] | None = None) -> list[str]:
    """Prompt the single Surface question. Aborts on Ctrl+C.

    Pre-check only Surfaces autodetected on disk; nothing is selected by
    default in a greenfield install (spec-133 D-133-17 user feedback).
    """
    result = questionary.checkbox(
        _PROMPT_SURFACES,
        choices=_build_surface_choices(detected_ides=detected_ides or []),
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

    # VCS: silent default to github (or detected). No prompt.
    vcs = resolved.get("vcs", detected.vcs or "github")

    # Surfaces: single user-facing question (or CLI override).
    if "surfaces" in resolved:
        surfaces = resolved["surfaces"]
    elif "providers" in resolved or "ides" in resolved:
        # Back-compat path: legacy --provider/--ide derives surfaces.
        legacy = list(resolved.get("providers", [])) + list(resolved.get("ides", []))
        surfaces = [s for s in legacy if s in SURFACE_IDS] or ["claude-code"]
    else:
        surfaces = _ask_surfaces(detected_ides=list(detected.ides))

    # Derive legacy ``providers`` and ``ides`` for in-flight downstream code.
    providers = [s for s in surfaces if s in SURFACE_IDS]
    ides = list(surfaces)

    return WizardResult(
        stacks=stacks,
        surfaces=surfaces,
        providers=providers,
        ides=ides,
        vcs=vcs,
    )
