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

from ai_engineering.installer.autodetect import DetectionResult


@dataclass
class WizardResult:
    """Holds the user's final selections from the install wizard."""

    stacks: list[str]
    providers: list[str]
    ides: list[str]
    vcs: str


# Valid AI provider identifiers (sorted for consistent display).
_VALID_AI_PROVIDERS: list[str] = sorted(["claude_code", "github_copilot", "gemini", "codex"])

# Valid VCS choices (sorted for consistent display).
_VCS_CHOICES: list[str] = sorted(["github", "azure_devops"])

# Default VCS when detection or user input fails.
_DEFAULT_VCS: str = "github"


def _build_choices(
    all_options: list[str],
    detected: list[str],
) -> list[questionary.Choice]:
    """Build a list of ``questionary.Choice`` with detected items pre-checked."""
    return [questionary.Choice(name, checked=(name in detected)) for name in all_options]


def _ask_checkbox(prompt: str, choices: list[questionary.Choice]) -> list[str]:
    """Run a checkbox prompt and handle None (Ctrl+C) gracefully."""
    result = questionary.checkbox(prompt, choices=choices).ask()
    if result is None:
        return []
    return result


def _ask_select(prompt: str, choices: list[str], default: str) -> str:
    """Run a select prompt and handle None (Ctrl+C) gracefully."""
    result = questionary.select(prompt, choices=choices, default=default).ask()
    if result is None:
        return _DEFAULT_VCS
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
        stacks_choices = _build_choices(get_available_stacks(), detected.stacks)
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
        ide_choices = _build_choices(get_available_ides(), detected.ides)
        ides = _ask_checkbox("Select IDE integrations:", ide_choices)

    # -- VCS ------------------------------------------------------------------
    if "vcs" in resolved:
        vcs = resolved["vcs"]
    else:
        vcs = _ask_select("Select VCS provider:", _VCS_CHOICES, detected.vcs)

    return WizardResult(stacks=stacks, providers=providers, ides=ides, vcs=vcs)
