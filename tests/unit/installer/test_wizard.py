"""Unit tests for the install wizard module.

Covers AC9, AC10, AC11, AC12, AC13, AC16b from spec-064.
Updated for spec-072: popularity ordering, VCS no-default, Ctrl+C abort.
All questionary interactions are mocked at module level.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ai_engineering.installer.autodetect import DetectionResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Popularity-ordered lists (matching Octoverse 2025 ranking)
_STACKS = [
    "typescript",
    "python",
    "javascript",
    "java",
    "csharp",
    "go",
    "php",
    "rust",
    "ruby",
    "kotlin",
    "swift",
    "dart",
    "elixir",
    "sql",
    "bash",
    "universal",
]

_PROVIDERS = ["github-copilot", "claude-code", "gemini-cli", "codex"]

_IDES = ["vscode", "jetbrains", "cursor", "terminal"]

_VCS_CHOICES = ["github", "azure_devops"]


def _detected(
    *,
    stacks: list[str] | None = None,
    providers: list[str] | None = None,
    ides: list[str] | None = None,
    vcs: str = "github",
) -> DetectionResult:
    return DetectionResult(
        stacks=stacks or [],
        providers=providers or [],
        ides=ides or [],
        vcs=vcs,
    )


# ---------------------------------------------------------------------------
# AC9: Detected items preselected (checked=True)
# ---------------------------------------------------------------------------


class TestDetectedPreselection:
    """AC9: Wizard shows checkboxes with detected items preselected."""

    def test_detected_stacks_are_checked(self) -> None:
        from ai_engineering.installer.wizard import run_wizard

        detected = _detected(stacks=["python", "go"])

        mock_checkbox = MagicMock()
        mock_checkbox.return_value.ask.side_effect = [
            ["python", "go"],
            ["claude-code"],
            ["vscode"],
        ]
        mock_select = MagicMock()
        mock_select.return_value.ask.return_value = "github"

        with (
            patch("ai_engineering.installer.wizard.questionary.checkbox", mock_checkbox),
            patch("ai_engineering.installer.wizard.questionary.select", mock_select),
            patch("ai_engineering.installer.wizard.questionary.print"),
        ):
            run_wizard(detected)

            # First checkbox call is stacks
            stacks_call = mock_checkbox.call_args_list[0]
            choices = stacks_call.kwargs.get("choices", [])
            checked_names = {c.title for c in choices if c.checked}
            unchecked_names = {c.title for c in choices if not c.checked}
            assert "python" in checked_names
            assert "go" in checked_names
            assert "rust" in unchecked_names

    def test_detected_providers_are_checked(self) -> None:
        from ai_engineering.installer.wizard import run_wizard

        detected = _detected(providers=["claude-code", "github-copilot"])

        mock_checkbox = MagicMock()
        mock_checkbox.return_value.ask.side_effect = [
            ["python"],
            ["claude-code", "github-copilot"],
            ["terminal"],
        ]
        mock_select = MagicMock()
        mock_select.return_value.ask.return_value = "github"

        with (
            patch("ai_engineering.installer.wizard.questionary.checkbox", mock_checkbox),
            patch("ai_engineering.installer.wizard.questionary.select", mock_select),
            patch("ai_engineering.installer.wizard.questionary.print"),
        ):
            run_wizard(detected)

            # Second checkbox call is providers
            providers_call = mock_checkbox.call_args_list[1]
            choices = providers_call.kwargs.get("choices", [])
            checked_names = {c.title for c in choices if c.checked}
            assert "claude-code" in checked_names
            assert "github-copilot" in checked_names

    def test_detected_ides_are_checked(self) -> None:
        from ai_engineering.installer.wizard import run_wizard

        detected = _detected(ides=["vscode", "jetbrains"])

        mock_checkbox = MagicMock()
        mock_checkbox.return_value.ask.side_effect = [
            ["python"],
            ["claude-code"],
            ["vscode", "jetbrains"],
        ]
        mock_select = MagicMock()
        mock_select.return_value.ask.return_value = "github"

        with (
            patch("ai_engineering.installer.wizard.questionary.checkbox", mock_checkbox),
            patch("ai_engineering.installer.wizard.questionary.select", mock_select),
            patch("ai_engineering.installer.wizard.questionary.print"),
        ):
            run_wizard(detected)

            # Third checkbox call is ides
            ides_call = mock_checkbox.call_args_list[2]
            choices = ides_call.kwargs.get("choices", [])
            checked_names = {c.title for c in choices if c.checked}
            assert "vscode" in checked_names
            assert "jetbrains" in checked_names


# ---------------------------------------------------------------------------
# AC10: All valid options are shown (popularity ordered)
# ---------------------------------------------------------------------------


class TestAllOptionsShown:
    """AC10: Wizard shows all valid options in popularity order."""

    def test_all_stacks_shown_popularity_ordered(self) -> None:
        from ai_engineering.installer.wizard import run_wizard

        detected = _detected(stacks=["python"])

        mock_checkbox = MagicMock()
        mock_checkbox.return_value.ask.side_effect = [
            ["python"],
            ["claude-code"],
            ["terminal"],
        ]
        mock_select = MagicMock()
        mock_select.return_value.ask.return_value = "github"

        with (
            patch("ai_engineering.installer.wizard.questionary.checkbox", mock_checkbox),
            patch("ai_engineering.installer.wizard.questionary.select", mock_select),
            patch(
                "ai_engineering.installer.operations.get_available_stacks",
                return_value=_STACKS,
            ),
            patch("ai_engineering.installer.wizard.questionary.print"),
        ):
            run_wizard(detected)

            stacks_call = mock_checkbox.call_args_list[0]
            choices = stacks_call.kwargs.get("choices", [])
            choice_names = [c.title for c in choices]
            assert choice_names == _STACKS
            assert choice_names[0] == "typescript"
            assert choice_names[-1] == "universal"

    def test_all_providers_shown_popularity_ordered(self) -> None:
        from ai_engineering.installer.wizard import run_wizard

        detected = _detected(providers=["claude-code"])

        mock_checkbox = MagicMock()
        mock_checkbox.return_value.ask.side_effect = [
            ["python"],
            ["claude-code"],
            ["terminal"],
        ]
        mock_select = MagicMock()
        mock_select.return_value.ask.return_value = "github"

        with (
            patch("ai_engineering.installer.wizard.questionary.checkbox", mock_checkbox),
            patch("ai_engineering.installer.wizard.questionary.select", mock_select),
            patch("ai_engineering.installer.wizard.questionary.print"),
        ):
            run_wizard(detected)

            providers_call = mock_checkbox.call_args_list[1]
            choices = providers_call.kwargs.get("choices", [])
            choice_names = [c.title for c in choices]
            assert choice_names == _PROVIDERS
            assert choice_names[0] == "github-copilot"

    def test_all_ides_shown_popularity_ordered(self) -> None:
        from ai_engineering.installer.wizard import run_wizard

        detected = _detected(ides=["vscode"])

        mock_checkbox = MagicMock()
        mock_checkbox.return_value.ask.side_effect = [
            ["python"],
            ["claude-code"],
            ["vscode"],
        ]
        mock_select = MagicMock()
        mock_select.return_value.ask.return_value = "github"

        with (
            patch("ai_engineering.installer.wizard.questionary.checkbox", mock_checkbox),
            patch("ai_engineering.installer.wizard.questionary.select", mock_select),
            patch(
                "ai_engineering.installer.operations.get_available_ides",
                return_value=_IDES,
            ),
            patch("ai_engineering.installer.wizard.questionary.print"),
        ):
            run_wizard(detected)

            ides_call = mock_checkbox.call_args_list[2]
            choices = ides_call.kwargs.get("choices", [])
            choice_names = [c.title for c in choices]
            assert choice_names == _IDES
            assert choice_names[0] == "vscode"

    def test_all_vcs_shown_popularity_ordered(self) -> None:
        from ai_engineering.installer.wizard import run_wizard

        detected = _detected(vcs="github")

        with patch("ai_engineering.installer.wizard.questionary") as mock_q:
            mock_q.checkbox.return_value.ask.side_effect = [
                ["python"],
                ["claude-code"],
                ["terminal"],
            ]
            mock_q.select.return_value.ask.return_value = "github"

            run_wizard(detected)

            select_call = mock_q.select.call_args_list[0]
            choices = select_call.kwargs.get("choices", select_call[1].get("choices", []))
            assert choices == _VCS_CHOICES
            assert choices[0] == "github"


# ---------------------------------------------------------------------------
# AC11: Empty detection -> nothing preselected
# ---------------------------------------------------------------------------


class TestEmptyDetection:
    """AC11: Empty repo -> wizard shows all options with nothing preselected."""

    def test_no_stacks_detected_none_checked(self) -> None:
        from ai_engineering.installer.wizard import run_wizard

        detected = _detected()

        mock_checkbox = MagicMock()
        mock_checkbox.return_value.ask.side_effect = [
            ["python"],
            ["claude-code"],
            ["terminal"],
        ]
        mock_select = MagicMock()
        mock_select.return_value.ask.return_value = "github"

        with (
            patch("ai_engineering.installer.wizard.questionary.checkbox", mock_checkbox),
            patch("ai_engineering.installer.wizard.questionary.select", mock_select),
            patch("ai_engineering.installer.wizard.questionary.print"),
        ):
            run_wizard(detected)

            stacks_call = mock_checkbox.call_args_list[0]
            choices = stacks_call.kwargs.get("choices", [])
            checked = [c for c in choices if c.checked]
            assert checked == []

    def test_no_providers_detected_none_checked(self) -> None:
        from ai_engineering.installer.wizard import run_wizard

        detected = _detected()

        mock_checkbox = MagicMock()
        mock_checkbox.return_value.ask.side_effect = [
            [],
            ["claude-code"],
            ["terminal"],
        ]
        mock_select = MagicMock()
        mock_select.return_value.ask.return_value = "github"

        with (
            patch("ai_engineering.installer.wizard.questionary.checkbox", mock_checkbox),
            patch("ai_engineering.installer.wizard.questionary.select", mock_select),
            patch("ai_engineering.installer.wizard.questionary.print"),
        ):
            run_wizard(detected)

            providers_call = mock_checkbox.call_args_list[1]
            choices = providers_call.kwargs.get("choices", [])
            checked = [c for c in choices if c.checked]
            assert checked == []

    def test_no_ides_detected_none_checked(self) -> None:
        from ai_engineering.installer.wizard import run_wizard

        detected = _detected()

        mock_checkbox = MagicMock()
        mock_checkbox.return_value.ask.side_effect = [
            [],
            [],
            ["terminal"],
        ]
        mock_select = MagicMock()
        mock_select.return_value.ask.return_value = "github"

        with (
            patch("ai_engineering.installer.wizard.questionary.checkbox", mock_checkbox),
            patch("ai_engineering.installer.wizard.questionary.select", mock_select),
            patch("ai_engineering.installer.wizard.questionary.print"),
        ):
            run_wizard(detected)

            ides_call = mock_checkbox.call_args_list[2]
            choices = ides_call.kwargs.get("choices", [])
            checked = [c for c in choices if c.checked]
            assert checked == []


# ---------------------------------------------------------------------------
# AC12: VCS uses questionary.select() not checkbox()
# ---------------------------------------------------------------------------


class TestVCSUsesSelect:
    """AC12: VCS selection uses radio buttons (single select), not checkboxes."""

    def test_vcs_uses_select(self) -> None:
        from ai_engineering.installer.wizard import run_wizard

        detected = _detected(vcs="azure_devops")

        with patch("ai_engineering.installer.wizard.questionary") as mock_q:
            mock_q.checkbox.return_value.ask.side_effect = [
                ["python"],
                ["claude-code"],
                ["terminal"],
            ]
            mock_q.select.return_value.ask.return_value = "azure_devops"

            run_wizard(detected)

            # select() called exactly once for VCS
            assert mock_q.select.call_count == 1
            select_call = mock_q.select.call_args
            assert "Select VCS provider:" in select_call[0][0]

    def test_vcs_default_from_detection(self) -> None:
        from ai_engineering.installer.wizard import run_wizard

        detected = _detected(vcs="azure_devops")

        with patch("ai_engineering.installer.wizard.questionary") as mock_q:
            mock_q.checkbox.return_value.ask.side_effect = [
                [],
                [],
                [],
            ]
            mock_q.select.return_value.ask.return_value = "azure_devops"

            run_wizard(detected)

            select_call = mock_q.select.call_args
            assert select_call.kwargs.get("default") == "azure_devops"

    def test_vcs_empty_detection_no_default(self) -> None:
        """When VCS detection returns empty, no default is passed."""
        from ai_engineering.installer.wizard import run_wizard

        detected = _detected(vcs="")

        with patch("ai_engineering.installer.wizard.questionary") as mock_q:
            mock_q.checkbox.return_value.ask.side_effect = [
                [],
                [],
                [],
            ]
            mock_q.select.return_value.ask.return_value = "github"

            run_wizard(detected)

            select_call = mock_q.select.call_args
            assert "default" not in select_call.kwargs
            # "Detected: none" note should have been printed
            mock_q.print.assert_called_once()


# ---------------------------------------------------------------------------
# AC13: Returns WizardResult dataclass with correct fields
# ---------------------------------------------------------------------------


class TestWizardResult:
    """AC13: Wizard returns a WizardResult dataclass with all selections."""

    def test_returns_wizard_result(self) -> None:
        from ai_engineering.installer.wizard import WizardResult, run_wizard

        detected = _detected(stacks=["python"], providers=["claude-code"])

        with patch("ai_engineering.installer.wizard.questionary") as mock_q:
            mock_q.checkbox.return_value.ask.side_effect = [
                ["python", "go"],
                ["claude-code"],
                ["vscode", "terminal"],
            ]
            mock_q.select.return_value.ask.return_value = "github"

            result = run_wizard(detected)

            assert isinstance(result, WizardResult)
            assert result.stacks == ["python", "go"]
            assert result.providers == ["claude-code"]
            assert result.ides == ["vscode", "terminal"]
            assert result.vcs == "github"

    def test_result_has_all_fields(self) -> None:
        from ai_engineering.installer.wizard import WizardResult

        result = WizardResult(
            stacks=["python"],
            providers=["claude-code"],
            ides=["terminal"],
            vcs="github",
        )
        assert result.stacks == ["python"]
        assert result.providers == ["claude-code"]
        assert result.ides == ["terminal"]
        assert result.vcs == "github"


# ---------------------------------------------------------------------------
# AC16b: Partial resolution — resolved categories skip wizard
# ---------------------------------------------------------------------------


class TestPartialResolution:
    """AC16b: resolved dict categories skip wizard prompts."""

    def test_stacks_resolved_skips_stacks_prompt(self) -> None:
        from ai_engineering.installer.wizard import run_wizard

        detected = _detected()
        resolved = {"stacks": ["python", "typescript"]}

        with patch("ai_engineering.installer.wizard.questionary") as mock_q:
            # Only 2 checkbox calls: providers, ides (stacks skipped)
            mock_q.checkbox.return_value.ask.side_effect = [
                ["claude-code"],
                ["terminal"],
            ]
            mock_q.select.return_value.ask.return_value = "github"

            result = run_wizard(detected, resolved=resolved)

            assert result.stacks == ["python", "typescript"]
            assert mock_q.checkbox.call_count == 2

            # Verify the first checkbox is providers (not stacks)
            first_call_prompt = mock_q.checkbox.call_args_list[0][0][0]
            assert "provider" in first_call_prompt.lower()

    def test_all_categories_resolved_no_prompts(self) -> None:
        from ai_engineering.installer.wizard import run_wizard

        detected = _detected()
        resolved = {
            "stacks": ["python"],
            "providers": ["claude-code"],
            "ides": ["terminal"],
            "vcs": "github",
        }

        with patch("ai_engineering.installer.wizard.questionary") as mock_q:
            result = run_wizard(detected, resolved=resolved)

            mock_q.checkbox.assert_not_called()
            mock_q.select.assert_not_called()
            assert result.stacks == ["python"]
            assert result.providers == ["claude-code"]
            assert result.ides == ["terminal"]
            assert result.vcs == "github"

    def test_vcs_resolved_skips_select(self) -> None:
        from ai_engineering.installer.wizard import run_wizard

        detected = _detected()
        resolved = {"vcs": "azure_devops"}

        with patch("ai_engineering.installer.wizard.questionary") as mock_q:
            mock_q.checkbox.return_value.ask.side_effect = [
                ["python"],
                ["claude-code"],
                ["terminal"],
            ]

            result = run_wizard(detected, resolved=resolved)

            mock_q.select.assert_not_called()
            assert result.vcs == "azure_devops"

    def test_providers_and_ides_resolved(self) -> None:
        from ai_engineering.installer.wizard import run_wizard

        detected = _detected(stacks=["python"])
        resolved = {
            "providers": ["claude-code", "github-copilot"],
            "ides": ["vscode"],
        }

        with patch("ai_engineering.installer.wizard.questionary") as mock_q:
            # Only 1 checkbox call: stacks
            mock_q.checkbox.return_value.ask.side_effect = [
                ["python", "go"],
            ]
            mock_q.select.return_value.ask.return_value = "github"

            result = run_wizard(detected, resolved=resolved)

            assert result.stacks == ["python", "go"]
            assert result.providers == ["claude-code", "github-copilot"]
            assert result.ides == ["vscode"]
            assert mock_q.checkbox.call_count == 1


# ---------------------------------------------------------------------------
# Keyboard interrupt / None handling
# ---------------------------------------------------------------------------


class TestInterruptHandling:
    """User presses Ctrl+C or questionary returns None."""

    def test_checkbox_returns_none_yields_empty_list(self) -> None:
        from ai_engineering.installer.wizard import run_wizard

        detected = _detected()

        with patch("ai_engineering.installer.wizard.questionary") as mock_q:
            mock_q.checkbox.return_value.ask.side_effect = [
                None,  # stacks -> Ctrl+C
                None,  # providers
                None,  # ides
            ]
            mock_q.select.return_value.ask.return_value = "github"

            result = run_wizard(detected)

            assert result.stacks == []
            assert result.providers == []
            assert result.ides == []
            assert result.vcs == "github"

    def test_vcs_select_returns_none_aborts_install(self) -> None:
        """Ctrl+C during VCS select aborts install with SystemExit(1)."""
        from ai_engineering.installer.wizard import run_wizard

        detected = _detected(vcs="azure_devops")

        with patch("ai_engineering.installer.wizard.questionary") as mock_q:
            mock_q.checkbox.return_value.ask.side_effect = [
                ["python"],
                ["claude-code"],
                ["terminal"],
            ]
            mock_q.select.return_value.ask.return_value = None

            with pytest.raises(SystemExit) as exc_info:
                run_wizard(detected)

            assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# Empty user selection
# ---------------------------------------------------------------------------


class TestEmptySelection:
    """User selects nothing in checkboxes."""

    def test_empty_stacks_selection(self) -> None:
        from ai_engineering.installer.wizard import run_wizard

        detected = _detected(stacks=["python"])

        with patch("ai_engineering.installer.wizard.questionary") as mock_q:
            mock_q.checkbox.return_value.ask.side_effect = [
                [],  # user deselected everything
                ["claude-code"],
                ["terminal"],
            ]
            mock_q.select.return_value.ask.return_value = "github"

            result = run_wizard(detected)

            assert result.stacks == []

    def test_all_empty_selections(self) -> None:
        from ai_engineering.installer.wizard import run_wizard

        detected = _detected()

        with patch("ai_engineering.installer.wizard.questionary") as mock_q:
            mock_q.checkbox.return_value.ask.side_effect = [
                [],
                [],
                [],
            ]
            mock_q.select.return_value.ask.return_value = "github"

            result = run_wizard(detected)

            assert result.stacks == []
            assert result.providers == []
            assert result.ides == []
            assert result.vcs == "github"


# ---------------------------------------------------------------------------
# spec-098: Checkbox validation and instruction hint
# ---------------------------------------------------------------------------


class TestCheckboxValidation:
    """spec-098: _ask_checkbox must pass validate and instruction to questionary."""

    def test_checkbox_passes_validate_that_rejects_empty(self) -> None:
        """_ask_checkbox passes a validate callback that rejects empty lists."""
        from ai_engineering.installer.wizard import _ask_checkbox

        mock_checkbox = MagicMock()
        mock_checkbox.return_value.ask.return_value = ["python"]

        with patch("ai_engineering.installer.wizard.questionary.checkbox", mock_checkbox):
            choices = [MagicMock(name="python")]
            _ask_checkbox("Select stacks:", choices)

            call_kwargs = mock_checkbox.call_args.kwargs
            assert "validate" in call_kwargs, (
                "_ask_checkbox must pass a 'validate' kwarg to questionary.checkbox"
            )

            validator = call_kwargs["validate"]

            # Valid selection should pass (return True or truthy)
            valid_result = validator(["python"])
            assert valid_result is True, "validate should return True for non-empty selections"

            # Empty selection should fail (return a string message)
            invalid_result = validator([])
            assert isinstance(invalid_result, str), (
                "validate should return an error string for empty selections"
            )

    def test_checkbox_passes_instruction_with_spacebar(self) -> None:
        """_ask_checkbox passes an instruction string mentioning spacebar."""
        from ai_engineering.installer.wizard import _ask_checkbox

        mock_checkbox = MagicMock()
        mock_checkbox.return_value.ask.return_value = ["python"]

        with patch("ai_engineering.installer.wizard.questionary.checkbox", mock_checkbox):
            choices = [MagicMock(name="python")]
            _ask_checkbox("Select stacks:", choices)

            call_kwargs = mock_checkbox.call_args.kwargs
            assert "instruction" in call_kwargs, (
                "_ask_checkbox must pass an 'instruction' kwarg to questionary.checkbox"
            )
            assert "spacebar" in call_kwargs["instruction"].lower(), (
                "instruction must mention 'spacebar' to guide users"
            )

    def test_checkbox_ctrl_c_still_returns_empty_list(self) -> None:
        """When questionary returns None (Ctrl+C), _ask_checkbox returns []."""
        from ai_engineering.installer.wizard import _ask_checkbox

        mock_checkbox = MagicMock()
        mock_checkbox.return_value.ask.return_value = None

        with patch("ai_engineering.installer.wizard.questionary.checkbox", mock_checkbox):
            choices = [MagicMock(name="python")]
            result = _ask_checkbox("Select stacks:", choices)

            assert result == []
