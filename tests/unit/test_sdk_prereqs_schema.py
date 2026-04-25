"""Failing tests for `prereqs.sdk_per_stack` schema (spec-101 T-0.9 — RED phase).

Covers (per plan T-0.9 + spec.md D-101-14):
- Valid `prereqs.sdk_per_stack` block (all 9 SDK-required stacks) parses.
- Missing `install_link` for a declared SDK fails Pydantic validation.
- Non-semver `min_version` value fails (e.g., "abc").
- `install_link` without a URL scheme fails (e.g., "not-a-url").
- The canonical `swift.install_link` is `https://www.swift.org/install/`.
- `load_sdk_prereqs(stacks)` filters to SDK-required stacks only.

The 9 SDK-required stacks are: java, kotlin, swift, dart, csharp, go, rust, php, cpp.
Python is NOT SDK-required (ships with the framework).

These tests MUST FAIL initially: `SdkPrereq` (state.models) and
`load_sdk_prereqs` (state.manifest) do not exist until T-0.10 lands.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

# These imports intentionally fail until T-0.10 lands. Pytest collection will
# raise ImportError, which is the RED-phase signal.
from ai_engineering.state.manifest import load_sdk_prereqs  # type: ignore[import-not-found]
from ai_engineering.state.models import SdkPrereq  # type: ignore[import-not-found]

# ---------------------------------------------------------------------------
# Constants — canonical 9 SDK-required stacks (matches spec.md L114-126).
# ---------------------------------------------------------------------------

SDK_REQUIRED_STACKS: tuple[str, ...] = (
    "java",
    "kotlin",
    "swift",
    "dart",
    "csharp",
    "go",
    "rust",
    "php",
    "cpp",
)

# Expected install_link patterns per stack (canonical values from spec.md).
EXPECTED_INSTALL_LINKS: dict[str, str] = {
    "java": "https://adoptium.net/",
    "kotlin": "https://adoptium.net/",
    "swift": "https://www.swift.org/install/",
    "dart": "https://dart.dev/get-dart",
    "csharp": "https://dotnet.microsoft.com/download",
    "go": "https://go.dev/dl/",
    "rust": "https://rustup.rs/",
    "php": "https://www.php.net/downloads",
    "cpp": "https://llvm.org/builds/",
}


@pytest.fixture()
def valid_sdk_per_stack_block() -> dict[str, dict[str, str]]:
    """Return a valid `prereqs.sdk_per_stack` mapping for all 9 SDK-required stacks."""
    return {
        "java": {
            "name": "JDK",
            "min_version": "21",
            "install_link": "https://adoptium.net/",
        },
        "kotlin": {
            "name": "JDK",
            "min_version": "21",
            "install_link": "https://adoptium.net/",
        },
        "swift": {
            "name": "Swift toolchain",
            "install_link": "https://www.swift.org/install/",
        },
        "dart": {
            "name": "Dart SDK",
            "install_link": "https://dart.dev/get-dart",
        },
        "csharp": {
            "name": ".NET SDK",
            "min_version": "9",
            "install_link": "https://dotnet.microsoft.com/download",
        },
        "go": {
            "name": "Go toolchain",
            "install_link": "https://go.dev/dl/",
        },
        "rust": {
            "name": "Rust toolchain",
            "install_link": "https://rustup.rs/",
        },
        "php": {
            "name": "PHP",
            "min_version": "8.2",
            "install_link": "https://www.php.net/downloads",
        },
        "cpp": {
            "name": "clang/LLVM",
            "install_link": "https://llvm.org/builds/",
        },
    }


# ---------------------------------------------------------------------------
# Schema validation — happy path
# ---------------------------------------------------------------------------


class TestSdkPrereqValid:
    """Valid `prereqs.sdk_per_stack` entries parse into SdkPrereq models."""

    def test_full_block_parses_all_9_stacks(
        self, valid_sdk_per_stack_block: dict[str, dict[str, str]]
    ) -> None:
        """Every entry of the canonical 9-stack block validates without error."""
        # Act
        models = {
            stack: SdkPrereq.model_validate(entry)
            for stack, entry in valid_sdk_per_stack_block.items()
        }

        # Assert
        assert len(models) == 9
        for stack in SDK_REQUIRED_STACKS:
            assert stack in models, f"missing model for {stack}"

    def test_swift_install_link_matches_canonical(
        self, valid_sdk_per_stack_block: dict[str, dict[str, str]]
    ) -> None:
        """`prereqs.sdk_per_stack.swift.install_link` MUST be the canonical URL."""
        # Act
        swift = SdkPrereq.model_validate(valid_sdk_per_stack_block["swift"])

        # Assert — exact value pinned in spec.md L120.
        assert str(swift.install_link).rstrip("/") + "/" == "https://www.swift.org/install/"
        assert swift.name == "Swift toolchain"

    def test_min_version_optional_for_some_stacks(
        self, valid_sdk_per_stack_block: dict[str, dict[str, str]]
    ) -> None:
        """Stacks like swift/dart/go/rust/cpp omit `min_version` per spec.md."""
        # Act
        swift = SdkPrereq.model_validate(valid_sdk_per_stack_block["swift"])
        dart = SdkPrereq.model_validate(valid_sdk_per_stack_block["dart"])

        # Assert
        assert swift.min_version is None
        assert dart.min_version is None

    def test_min_version_present_for_versioned_stacks(
        self, valid_sdk_per_stack_block: dict[str, dict[str, str]]
    ) -> None:
        """Stacks with explicit min versions (java, kotlin, csharp, php) carry them."""
        # Act
        java = SdkPrereq.model_validate(valid_sdk_per_stack_block["java"])
        php = SdkPrereq.model_validate(valid_sdk_per_stack_block["php"])
        csharp = SdkPrereq.model_validate(valid_sdk_per_stack_block["csharp"])

        # Assert
        assert java.min_version == "21"
        assert php.min_version == "8.2"
        assert csharp.min_version == "9"


# ---------------------------------------------------------------------------
# Schema validation — failure modes
# ---------------------------------------------------------------------------


class TestSdkPrereqInvalid:
    """Malformed `prereqs.sdk_per_stack` entries are rejected by Pydantic."""

    def test_missing_install_link_fails(self) -> None:
        """A declared SDK without an `install_link` MUST fail validation."""
        # Arrange
        bad_entry = {"name": "JDK", "min_version": "21"}

        # Act + Assert
        with pytest.raises(ValidationError):
            SdkPrereq.model_validate(bad_entry)

    def test_missing_name_fails(self) -> None:
        """A declared SDK without a `name` MUST fail validation."""
        # Arrange
        bad_entry = {
            "min_version": "21",
            "install_link": "https://adoptium.net/",
        }

        # Act + Assert
        with pytest.raises(ValidationError):
            SdkPrereq.model_validate(bad_entry)

    def test_non_semver_min_version_fails(self) -> None:
        """Non-semver `min_version` (e.g., "abc") MUST fail the regex check."""
        # Arrange
        bad_entry = {
            "name": "JDK",
            "min_version": "abc",
            "install_link": "https://adoptium.net/",
        }

        # Act + Assert
        with pytest.raises(ValidationError):
            SdkPrereq.model_validate(bad_entry)

    def test_install_link_without_scheme_fails(self) -> None:
        """`install_link` lacking a URL scheme (e.g., "not-a-url") MUST fail."""
        # Arrange
        bad_entry = {
            "name": "JDK",
            "min_version": "21",
            "install_link": "not-a-url",
        }

        # Act + Assert
        with pytest.raises(ValidationError):
            SdkPrereq.model_validate(bad_entry)

    def test_install_link_empty_string_fails(self) -> None:
        """An empty `install_link` MUST fail validation (R-defensive)."""
        # Arrange
        bad_entry = {
            "name": "JDK",
            "min_version": "21",
            "install_link": "",
        }

        # Act + Assert
        with pytest.raises(ValidationError):
            SdkPrereq.model_validate(bad_entry)


# ---------------------------------------------------------------------------
# Loader — load_sdk_prereqs(stacks)
# ---------------------------------------------------------------------------


class TestLoadSdkPrereqs:
    """`load_sdk_prereqs(stacks)` returns prereqs only for SDK-required stacks."""

    def test_two_sdk_stacks_returns_two_entries(self) -> None:
        """`load_sdk_prereqs(["java", "go"])` returns exactly 2 entries."""
        # Act
        result = load_sdk_prereqs(["java", "go"])

        # Assert
        assert len(result) == 2
        names = {prereq.name for prereq in result}
        assert "JDK" in names
        assert "Go toolchain" in names

    def test_empty_stacks_returns_empty_list(self) -> None:
        """`load_sdk_prereqs([])` returns an empty list."""
        # Act
        result = load_sdk_prereqs([])

        # Assert
        assert result == []

    def test_python_stack_returns_empty_list(self) -> None:
        """Python is NOT SDK-required; `load_sdk_prereqs(["python"])` is empty."""
        # Act
        result = load_sdk_prereqs(["python"])

        # Assert — python ships with the framework's `uv` toolchain (D-101-12).
        assert result == []

    def test_mixed_stacks_filters_to_sdk_required(self) -> None:
        """Mix of SDK-required and non-SDK stacks returns only SDK entries."""
        # Act
        result = load_sdk_prereqs(["python", "java", "typescript", "rust"])

        # Assert — python + typescript are NOT SDK-required; java + rust ARE.
        assert len(result) == 2
        names = {prereq.name for prereq in result}
        assert "JDK" in names
        assert "Rust toolchain" in names


# ---------------------------------------------------------------------------
# Parametric coverage — all 9 SDK-required stacks
# ---------------------------------------------------------------------------


# Sanity gate: prevents silent omission of a stack from the parametric set.
assert len(SDK_REQUIRED_STACKS) == 9, (
    f"expected exactly 9 SDK-required stacks, got {len(SDK_REQUIRED_STACKS)}"
)


class TestAllSdkRequiredStacksHaveProbes:
    """Parametric sweep asserts every SDK-required stack has a registered probe."""

    @pytest.mark.parametrize("stack", SDK_REQUIRED_STACKS)
    def test_stack_returns_single_prereq(self, stack: str) -> None:
        """`load_sdk_prereqs([<stack>])` returns exactly one prereq."""
        # Act
        result = load_sdk_prereqs([stack])

        # Assert
        assert len(result) == 1, f"stack {stack} returned {len(result)} prereqs"

    @pytest.mark.parametrize("stack", SDK_REQUIRED_STACKS)
    def test_stack_install_link_matches_expected(self, stack: str) -> None:
        """Each SDK-required stack carries the canonical `install_link`."""
        # Act
        result = load_sdk_prereqs([stack])

        # Assert
        assert len(result) == 1
        prereq = result[0]
        actual = str(prereq.install_link).rstrip("/")
        expected = EXPECTED_INSTALL_LINKS[stack].rstrip("/")
        assert actual == expected, (
            f"stack {stack}: expected install_link {expected!r}, got {actual!r}"
        )
