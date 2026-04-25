"""RED tests for spec-101 T-0.3 — `required_tools` schema validation.

These tests assert the shape and governance rules of the 15-key
`required_tools` block declared in `.ai-engineering/manifest.yml` per
D-101-01 + D-101-03 + D-101-13.

Models under test (created in T-0.4):
    - ``ai_engineering.state.models.ToolSpec`` — single tool entry.
    - ``ai_engineering.state.models.StackSpec`` — stack-level wrapper that
      may carry ``platform_unsupported_stack`` + ``unsupported_reason``.

Both are Pydantic ``BaseModel`` subclasses with
``model_config = {"frozen": True}`` (per phase-0-notes.md §1, the codebase
convention is Pydantic, not ``@dataclass``). The plan T-0.4 phrasing of
"frozen dataclass" is informal -- match the existing **Pydantic**
convention.

Governance covered:
    - 15 stack keys recognised (baseline + 14 stacks per G-1).
    - Missing the ``baseline`` key fails (baseline is mandatory).
    - Tool-level ``platform_unsupported`` rejects unknown OS values.
    - Tool-level ``platform_unsupported`` listing all 3 OSes fails
      (D-101-03 abuse-prevention cap of 2-of-3).
    - ``platform_unsupported`` set without ``unsupported_reason`` fails
      (D-101-03).
    - Stack-level ``platform_unsupported_stack`` is recognised when a
      reason is supplied (D-101-13 escalation path for swift).
    - Stack-level ``platform_unsupported_stack`` without
      ``unsupported_reason`` fails.

This file is RED until T-0.4 lands ``ToolSpec`` / ``StackSpec``.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_engineering.state.models import StackSpec, ToolSpec

# ---------------------------------------------------------------------------
# Constants -- the 15 keys per D-101-01
# ---------------------------------------------------------------------------

_BASELINE_KEY = "baseline"

_STACK_KEYS: tuple[str, ...] = (
    "python",
    "typescript",
    "javascript",
    "java",
    "csharp",
    "go",
    "php",
    "rust",
    "kotlin",
    "swift",
    "dart",
    "sql",
    "bash",
    "cpp",
)

_ALL_KEYS: tuple[str, ...] = (_BASELINE_KEY, *_STACK_KEYS)


def _minimal_block() -> dict[str, object]:
    """Return a fresh, valid 15-key ``required_tools`` block.

    Each stack carries one trivial tool so the block is structurally
    complete; the swift stack uses the D-101-13 nested ``tools`` shape
    with ``platform_unsupported_stack`` + ``unsupported_reason``.
    """
    return {
        "baseline": [{"name": "gitleaks"}, {"name": "jq"}],
        "python": [{"name": "ruff"}],
        "typescript": [{"name": "tsc", "scope": "project_local"}],
        "javascript": [{"name": "eslint", "scope": "project_local"}],
        "java": [{"name": "checkstyle"}],
        "csharp": [{"name": "dotnet-format"}],
        "go": [{"name": "staticcheck"}],
        "php": [{"name": "phpstan"}],
        "rust": [{"name": "cargo-audit"}],
        "kotlin": [{"name": "ktlint"}],
        "swift": {
            "platform_unsupported_stack": ["linux", "windows"],
            "unsupported_reason": ("swiftlint and swift-format have no Linux/Windows binaries"),
            "tools": [{"name": "swiftlint"}, {"name": "swift-format"}],
        },
        "dart": [{"name": "dart-stack-marker"}],
        "sql": [{"name": "sqlfluff"}],
        "bash": [{"name": "shellcheck"}],
        "cpp": [{"name": "clang-tidy"}],
    }


# ---------------------------------------------------------------------------
# Happy-path: 15-key block parses without error
# ---------------------------------------------------------------------------


class TestRequiredToolsBlock:
    """The full 15-key block is recognised by ``StackSpec``-driven loading."""

    def test_full_15_key_block_parses(self) -> None:
        """All 15 keys (baseline + 14 stacks) coerce into typed specs."""
        block = _minimal_block()

        # Each stack key must be coercible into a StackSpec; the baseline
        # uses the bare-list shape and the swift stack uses the nested
        # dict shape -- StackSpec must accept both per D-101-13.
        for key in _ALL_KEYS:
            spec = StackSpec.model_validate({"name": key, "raw": block[key]})
            assert spec.name == key

    @pytest.mark.parametrize("stack_key", _STACK_KEYS)
    def test_each_stack_key_recognised(self, stack_key: str) -> None:
        """Each of the 14 declared stacks produces a valid StackSpec."""
        block = _minimal_block()
        spec = StackSpec.model_validate({"name": stack_key, "raw": block[stack_key]})
        assert spec.name == stack_key


# ---------------------------------------------------------------------------
# Negative case: missing the mandatory baseline key
# ---------------------------------------------------------------------------


class TestBaselineKeyMandatory:
    """The ``baseline`` key is mandatory across the whole block (D-101-01)."""

    def test_missing_baseline_key_fails(self) -> None:
        """A required_tools block lacking ``baseline`` is rejected."""
        block = _minimal_block()
        del block[_BASELINE_KEY]

        # The validator surface (T-0.6/T-0.8) must reject this. We verify
        # the smaller invariant here: the StackSpec for a missing key
        # cannot be constructed -- the absence is detected during
        # block-level validation. We model it as a Pydantic validation
        # failure on a top-level "RequiredToolsBlock" (T-0.6).
        from ai_engineering.state.models import RequiredToolsBlock

        with pytest.raises(ValidationError):
            RequiredToolsBlock.model_validate(block)


# ---------------------------------------------------------------------------
# Negative case: invalid OS values in platform_unsupported
# ---------------------------------------------------------------------------


class TestPlatformUnsupportedOsEnum:
    """Tool-level ``platform_unsupported`` only accepts darwin/linux/windows."""

    @pytest.mark.parametrize(
        "bad_os_value",
        [
            "mars",
            "OSX",  # case-sensitive: only 'darwin' is allowed
            "ubuntu",
            "macos",
            "win32",
        ],
    )
    def test_invalid_os_values_rejected(self, bad_os_value: str) -> None:
        """Any non-{darwin,linux,windows} OS string fails validation."""
        with pytest.raises(ValidationError):
            ToolSpec.model_validate(
                {
                    "name": "semgrep",
                    "platform_unsupported": ["windows", bad_os_value],
                    "unsupported_reason": "fixture",
                }
            )

    def test_full_invalid_os_pair_rejected(self) -> None:
        """``[windows, mars]`` fails: ``mars`` is not in the OS enum."""
        with pytest.raises(ValidationError):
            ToolSpec.model_validate(
                {
                    "name": "semgrep",
                    "platform_unsupported": ["windows", "mars"],
                    "unsupported_reason": "fixture",
                }
            )


# ---------------------------------------------------------------------------
# Negative case: tool-level all-3-OSes (D-101-03 abuse cap)
# ---------------------------------------------------------------------------


class TestToolLevelMaxTwoOfThree:
    """Tool-level ``platform_unsupported`` may list AT MOST 2 of the 3 OSes."""

    def test_all_three_oses_at_tool_level_fails(self) -> None:
        """Listing all 3 OSes at tool-level defeats the install invariant.

        Per D-101-03, a tool that is unavailable on all 3 OSes is in
        practice optional; this is prohibited at tool-level. Stack-level
        ``platform_unsupported_stack`` is the legitimate escape hatch
        (D-101-13).
        """
        with pytest.raises(ValidationError):
            ToolSpec.model_validate(
                {
                    "name": "ghost-tool",
                    "platform_unsupported": ["darwin", "linux", "windows"],
                    "unsupported_reason": "abuse-prevention fixture",
                }
            )

    @pytest.mark.parametrize(
        "two_of_three",
        [
            ["darwin", "linux"],
            ["darwin", "windows"],
            ["linux", "windows"],
        ],
    )
    def test_two_of_three_at_tool_level_allowed(self, two_of_three: list[str]) -> None:
        """Two-of-three is the maximum tool-level allowance."""
        spec = ToolSpec.model_validate(
            {
                "name": "semgrep",
                "platform_unsupported": two_of_three,
                "unsupported_reason": "fixture",
            }
        )
        assert sorted(spec.platform_unsupported) == sorted(two_of_three)


# ---------------------------------------------------------------------------
# Negative case: platform_unsupported without unsupported_reason
# ---------------------------------------------------------------------------


class TestUnsupportedReasonMandatoryAtToolLevel:
    """``platform_unsupported`` requires a sibling ``unsupported_reason``."""

    def test_tool_level_missing_reason_fails(self) -> None:
        """A tool with ``platform_unsupported`` but no reason is rejected."""
        with pytest.raises(ValidationError):
            ToolSpec.model_validate(
                {
                    "name": "semgrep",
                    "platform_unsupported": ["windows"],
                    # unsupported_reason intentionally omitted
                }
            )

    def test_tool_level_blank_reason_fails(self) -> None:
        """An empty-string reason is treated as missing per D-101-03."""
        with pytest.raises(ValidationError):
            ToolSpec.model_validate(
                {
                    "name": "semgrep",
                    "platform_unsupported": ["windows"],
                    "unsupported_reason": "",
                }
            )


# ---------------------------------------------------------------------------
# Stack-level platform_unsupported_stack (D-101-13)
# ---------------------------------------------------------------------------


class TestStackLevelPlatformUnsupportedStack:
    """Stack-level escalation path per D-101-13."""

    def test_swift_stack_with_two_oses_unsupported_recognised(self) -> None:
        """``platform_unsupported_stack: [linux, windows]`` parses for swift."""
        spec = StackSpec.model_validate(
            {
                "name": "swift",
                "raw": {
                    "platform_unsupported_stack": ["linux", "windows"],
                    "unsupported_reason": (
                        "swiftlint and swift-format have no Linux/Windows binaries"
                    ),
                    "tools": [{"name": "swiftlint"}, {"name": "swift-format"}],
                },
            }
        )
        assert spec.name == "swift"
        assert sorted(spec.platform_unsupported_stack) == ["linux", "windows"]
        assert spec.unsupported_reason
        assert len(spec.tools) == 2

    def test_stack_level_missing_reason_fails(self) -> None:
        """``platform_unsupported_stack`` without reason is rejected."""
        with pytest.raises(ValidationError):
            StackSpec.model_validate(
                {
                    "name": "swift",
                    "raw": {
                        "platform_unsupported_stack": ["linux", "windows"],
                        # unsupported_reason intentionally omitted
                        "tools": [{"name": "swiftlint"}],
                    },
                }
            )

    @pytest.mark.parametrize(
        "stack_oses",
        [
            ["linux"],
            ["windows"],
            ["linux", "windows"],
            # All three is permitted at stack-level per D-101-13 -- the
            # 2-of-3 cap applies only at tool-level. T-0.7/T-0.8 handle
            # the lint surface; here we only assert recognition.
            ["darwin", "linux", "windows"],
        ],
    )
    def test_stack_level_combinations_recognised(self, stack_oses: list[str]) -> None:
        """Stack-level may list 1-3 OSes when ``unsupported_reason`` is set."""
        spec = StackSpec.model_validate(
            {
                "name": "swift",
                "raw": {
                    "platform_unsupported_stack": stack_oses,
                    "unsupported_reason": "fixture rationale",
                    "tools": [{"name": "swiftlint"}],
                },
            }
        )
        assert sorted(spec.platform_unsupported_stack) == sorted(stack_oses)

    def test_stack_level_invalid_os_rejected(self) -> None:
        """Stack-level OS values are constrained to the same enum."""
        with pytest.raises(ValidationError):
            StackSpec.model_validate(
                {
                    "name": "swift",
                    "raw": {
                        "platform_unsupported_stack": ["linux", "mars"],
                        "unsupported_reason": "fixture",
                        "tools": [{"name": "swiftlint"}],
                    },
                }
            )
