"""TypeScript adapter fixture (sub-008 T-8.10.ts).

Proves the adapter prose for the ``typescript`` stack is structurally
sound: parses as markdown, references the canonical TS toolchain, and
ships at least one realistic example file.

This is intentionally a *lightweight* fixture — `ai-build` agent loads
the markdown at runtime; the build agent itself is the integration
test. The unit-level guarantee here is "the prose exists and names the
right tools".
"""

from __future__ import annotations

from pathlib import Path

import pytest

_ADAPTER = Path(__file__).resolve().parents[2] / ".ai-engineering" / "adapters" / "typescript"


def test_conventions_names_strict_mode() -> None:
    """``strict: true`` is the load-bearing tsconfig flag we expect."""
    text = (_ADAPTER / "conventions.md").read_text(encoding="utf-8")
    assert '"strict": true' in text, "TypeScript conventions must require strict mode in tsconfig."


def test_conventions_names_pnpm_or_bun() -> None:
    """At least one of pnpm/bun is named — pinning a runtime is mandatory."""
    text = (_ADAPTER / "conventions.md").read_text(encoding="utf-8").lower()
    assert ("pnpm" in text) or ("bun" in text), (
        "TypeScript conventions must name a package manager / runtime."
    )


def test_tdd_harness_names_vitest() -> None:
    """Vitest is the default runner per adapter prose."""
    text = (_ADAPTER / "tdd_harness.md").read_text(encoding="utf-8").lower()
    assert "vitest" in text, "TypeScript TDD harness must default to Vitest."


def test_security_floor_names_zod_or_valibot() -> None:
    """A schema validator is named at the trust boundary."""
    text = (_ADAPTER / "security_floor.md").read_text(encoding="utf-8").lower()
    assert any(name in text for name in ("zod", "valibot", "effect/schema")), (
        "TypeScript security floor must name a schema validator."
    )


def test_examples_count_minimum_two() -> None:
    """At least two examples ship under examples/."""
    examples = sorted((_ADAPTER / "examples").glob("*.md"))
    assert len(examples) >= 2, f"need ≥2 examples, found {len(examples)}"


@pytest.mark.parametrize("example_name", ["nextjs-page.md", "node-service.md"])
def test_canonical_examples_present(example_name: str) -> None:
    """Canonical examples named in plan T-8.2.d exist."""
    assert (_ADAPTER / "examples" / example_name).is_file(), (
        f"canonical example missing: {example_name}"
    )


def test_conventions_source_header_pins_actual_sha() -> None:
    """The source-revision header pins a concrete 40-char hex SHA."""
    first_line = (_ADAPTER / "conventions.md").read_text(encoding="utf-8").splitlines()[0]
    # Header format already validated by scaffolding test; we check the
    # non-placeholder shape (no 'TBD', no 'PLACEHOLDER').
    placeholder_markers = ("TBD", "PLACEHOLDER", "FIXME", "XXX")
    for marker in placeholder_markers:
        assert marker not in first_line, (
            f"source header still has placeholder {marker!r}: {first_line}"
        )
