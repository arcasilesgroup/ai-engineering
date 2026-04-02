"""Interactive install wizard using questionary.

Presents checkbox and select prompts for the user to confirm or modify
auto-detected project configuration.  Each category (stacks, providers,
IDEs, VCS) can be pre-resolved via CLI flags, in which case the wizard
skips that prompt entirely.

Functions:
    run_wizard -- present interactive prompts and return WizardResult
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import questionary

from ai_engineering.installer.autodetect import (
    _IDE_POPULARITY,
    _PROVIDER_POPULARITY,
    _STACK_POPULARITY,
    _VCS_POPULARITY,
    DetectionResult,
    _order_by_popularity,
)


@dataclass
class WizardResult:
    """Holds the user's final selections from the install wizard."""

    stacks: list[str]
    providers: list[str]
    ides: list[str]
    vcs: str


# Valid AI provider identifiers (popularity ordered).
_VALID_AI_PROVIDERS: list[str] = _order_by_popularity(
    ["claude_code", "github_copilot", "gemini", "codex"],
    _PROVIDER_POPULARITY,
)

# Valid VCS choices (popularity ordered).
_VCS_CHOICES: list[str] = _order_by_popularity(
    ["github", "azure_devops"],
    _VCS_POPULARITY,
)


def _build_choices(
    all_options: list[str],
    detected: list[str],
) -> list[questionary.Choice]:
    """Build a list of ``questionary.Choice`` with detected items pre-checked."""
    return [questionary.Choice(name, checked=(name in detected)) for name in all_options]


def _checkbox_validate(selection: list[str]) -> bool | str:
    """Return ``True`` if *selection* is non-empty, otherwise an error message."""
    if selection:
        return True
    return "Please select at least one option (use spacebar to toggle)"


def _ask_checkbox(prompt: str, choices: list[questionary.Choice]) -> list[str]:
    """Run a checkbox prompt and handle None (Ctrl+C) gracefully."""
    result = questionary.checkbox(
        prompt,
        choices=choices,
        validate=_checkbox_validate,
        instruction="(spacebar to select, Enter to confirm)",
    ).ask()
    if result is None:
        return []
    return result


def _ask_select(prompt: str, choices: list[str], default: str | None = None) -> str:
    """Run a select prompt. Abort install on Ctrl+C."""
    kwargs: dict[str, Any] = {"choices": choices}
    if default:
        kwargs["default"] = default
    result = questionary.select(prompt, **kwargs).ask()
    if result is None:
        raise SystemExit(1)
    return result


def run_wizard(
    detected: DetectionResult,
    resolved: dict[str, Any] | None = None,
) -> WizardResult:
    """Present the install wizard and return the user's selections.

    Args:
        detected: Auto-detection results.  Detected items are preselected
            in checkbox prompts.
        resolved: Dict of categories already resolved by CLI flags.  Keys
            can be ``"stacks"``, ``"providers"``, ``"ides"``, ``"vcs"``.
            Categories present in this dict are *not* prompted.

    Returns:
        A ``WizardResult`` with the final selections for all categories.
    """
    if resolved is None:
        resolved = {}

    # Lazy imports to avoid circular dependencies at module load time.
    from ai_engineering.installer.operations import get_available_ides, get_available_stacks

    # -- Stacks ---------------------------------------------------------------
    if "stacks" in resolved:
        stacks = resolved["stacks"]
    else:
        available = _order_by_popularity(get_available_stacks(), _STACK_POPULARITY)
        stacks_choices = _build_choices(available, detected.stacks)
        stacks = _ask_checkbox("Select technology stacks:", stacks_choices)

    # -- Providers ------------------------------------------------------------
    if "providers" in resolved:
        providers = resolved["providers"]
    else:
        provider_choices = _build_choices(_VALID_AI_PROVIDERS, detected.providers)
        providers = _ask_checkbox("Select AI providers:", provider_choices)

    # -- IDEs -----------------------------------------------------------------
    if "ides" in resolved:
        ides = resolved["ides"]
    else:
        available_ides = _order_by_popularity(get_available_ides(), _IDE_POPULARITY)
        ide_choices = _build_choices(available_ides, detected.ides)
        ides = _ask_checkbox("Select IDE integrations:", ide_choices)

    # -- VCS ------------------------------------------------------------------
    if "vcs" in resolved:
        vcs = resolved["vcs"]
    else:
        vcs_default = detected.vcs if detected.vcs else None
        if not vcs_default:
            questionary.print("  Detected: none", style="bold yellow")
        vcs = _ask_select("Select VCS provider:", _VCS_CHOICES, vcs_default)

    return WizardResult(stacks=stacks, providers=providers, ides=ides, vcs=vcs)
