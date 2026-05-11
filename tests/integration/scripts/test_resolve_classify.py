"""RED-phase tests for ``skill_scripts.resolve_classify`` (spec-129 T-11).

Contract under test (T-12 will implement):

* ``classify_conflict(path: Path | str, content: str | None = None) ->
  Classification`` — pure classifier. Reads ``content`` from ``path``
  when not supplied. Never writes resolutions; never auto-resolves
  unless the signal is unambiguous.
* ``ConflictType`` — string enum / Literal with members at minimum:
  ``"lock"``, ``"generated"``, ``"migration"``, ``"code"``,
  ``"config"``, ``"unknown"``.
* ``Classification`` — dataclass with fields ``type: ConflictType``,
  ``action: Literal["auto-resolve", "ambiguous", "manual"]``,
  ``confidence: Literal["low", "medium", "high"]``.

Conservative-default contract (spec-129 §Risks): when in doubt, return
``action="ambiguous"`` (or ``"manual"`` for unmistakable code). NEVER
return ``action="auto-resolve"`` on a low-confidence signal. Filename
heuristics alone (e.g. ``*_pb2.py``) MUST NOT trigger auto-resolve —
require an in-file sentinel.

Adversarial fixtures live under
``tests/integration/scripts/fixtures/conflicts/``:

* ``package-lock-edited.json`` — lock file body annotated with a
  manual-edit comment. Expected: ``lock`` + ``ambiguous`` + ``low``.
* ``looks_generated_no_sentinel_pb2.py`` — filename mimics a generated
  module, body has no sentinel. Expected: ``unknown`` + ``ambiguous``
  + ``low``.
* ``migrations/0001_initial.py`` — migration path. Expected:
  ``migration`` + ``ambiguous`` + ``high`` (certain it's a migration;
  ambiguous means *ask the user*, not *auto-resolve*).

Perf floor: classifying 100 paths completes under 500 ms wall-clock
(p95 proxy for the spec's hot-path budget).

These tests intentionally fail with ``ModuleNotFoundError`` until T-12
lands ``.ai-engineering/scripts/skills/skill_scripts/resolve_classify.py``
and exposes it on ``sys.path`` as ``skill_scripts``.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from skill_scripts.resolve_classify import (
    Classification,
    ConflictType,
    classify_conflict,
)

FIXTURES = Path(__file__).parent / "fixtures" / "conflicts"


# ---------------------------------------------------------------------------
# Lock-file family (5 fixtures) — auto-resolve, high confidence.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename",
    [
        "package-lock.json",
        "uv.lock",
        "poetry.lock",
        "Cargo.lock",
        "vendor.lock",
    ],
)
def test_lock_files_auto_resolve_with_high_confidence(
    tmp_path: Path,
    filename: str,
) -> None:
    """All five canonical lock-file shapes must auto-resolve."""
    target = tmp_path / filename
    target.write_text("{}\n", encoding="utf-8")
    result = classify_conflict(target)
    assert isinstance(result, Classification)
    assert result.type == ConflictType.LOCK
    assert result.action == "auto-resolve"
    assert result.confidence == "high"


# ---------------------------------------------------------------------------
# ADVERSARIAL #1 — lock file carrying manual edits must NOT auto-resolve.
# ---------------------------------------------------------------------------


def test_lock_file_with_manual_edit_marker_returns_ambiguous_low_confidence() -> None:
    """A lock file the user has hand-edited must surface to a human.

    Spec-129 §Risks calls out this exact adversarial case: lockfiles are
    normally regenerable, but once a human has pinned a version inline
    the regeneration would silently undo their fix. Conservative default
    wins: classify as lock (we know the file family), but refuse to
    auto-resolve.
    """
    target = FIXTURES / "package-lock-edited.json"
    assert target.exists(), "fixture must be checked in for the RED phase"
    result = classify_conflict(target)
    assert result.type == ConflictType.LOCK
    assert result.action == "ambiguous"
    assert result.confidence == "low"


# ---------------------------------------------------------------------------
# Generated WITH sentinel — auto-resolve.
# ---------------------------------------------------------------------------


def test_generated_file_with_sentinel_header_auto_resolves() -> None:
    """An in-file ``AUTO-GENERATED — DO NOT EDIT`` banner is the signal."""
    target = FIXTURES / "auto_generated_with_sentinel.py"
    assert target.exists()
    result = classify_conflict(target)
    assert result.type == ConflictType.GENERATED
    assert result.action == "auto-resolve"
    assert result.confidence == "high"


@pytest.mark.parametrize(
    "sentinel",
    [
        "// AUTO-GENERATED — DO NOT EDIT",
        "# AUTO-GENERATED",
        "/* AUTO-GENERATED FILE — DO NOT EDIT BY HAND */",
    ],
)
def test_generated_sentinel_variants_auto_resolve(
    tmp_path: Path,
    sentinel: str,
) -> None:
    """Sentinel detection must tolerate the three common comment shapes."""
    target = tmp_path / "synthetic.txt"
    target.write_text(f"{sentinel}\nbody\n", encoding="utf-8")
    result = classify_conflict(target)
    assert result.type == ConflictType.GENERATED
    assert result.action == "auto-resolve"
    assert result.confidence == "high"


# ---------------------------------------------------------------------------
# ADVERSARIAL #2 — looks generated by filename but no sentinel.
# ---------------------------------------------------------------------------


def test_filename_looks_generated_without_sentinel_returns_unknown_ambiguous() -> None:
    """``*_pb2.py`` naming alone must NOT trigger auto-resolve.

    Filename heuristics are too easy for a human to defeat (and for a
    typo to trigger). Without an in-file sentinel we treat the file as
    unknown and ambiguous so the operator gets the choice.
    """
    target = FIXTURES / "looks_generated_no_sentinel_pb2.py"
    assert target.exists()
    result = classify_conflict(target)
    assert result.type == ConflictType.UNKNOWN
    assert result.action == "ambiguous"
    assert result.confidence == "low"


@pytest.mark.parametrize(
    "filename",
    [
        "service.gen.ts",
        "schema.generated.go",
        "wire_gen.go",
    ],
)
def test_other_generated_naming_without_sentinel_stays_ambiguous(
    tmp_path: Path,
    filename: str,
) -> None:
    """Generated-looking names across stacks must still require a sentinel."""
    target = tmp_path / filename
    target.write_text("body without sentinel\n", encoding="utf-8")
    result = classify_conflict(target)
    assert result.type == ConflictType.UNKNOWN
    assert result.action == "ambiguous"
    assert result.confidence == "low"


# ---------------------------------------------------------------------------
# ADVERSARIAL #3 — migration paths NEVER auto-resolve.
# ---------------------------------------------------------------------------


def test_migration_path_returns_ambiguous_with_high_confidence() -> None:
    """A migration path is *certainly* a migration, but never auto-safe."""
    target = FIXTURES / "migrations" / "0001_initial.py"
    assert target.exists()
    result = classify_conflict(target)
    assert result.type == ConflictType.MIGRATION
    assert result.action == "ambiguous"
    assert result.confidence == "high"


@pytest.mark.parametrize(
    "rel_path",
    [
        "db/migrate/20260101_add_users.rb",
        "src/db/migrations/0007_addresses.sql",
        "infra/sql/0042_migration.sql",
        "alembic/versions/abc123_init.py",
    ],
)
def test_migration_path_variants_never_auto_resolve(
    tmp_path: Path,
    rel_path: str,
) -> None:
    """Common migration path shapes must all classify identically."""
    target = tmp_path / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("-- migration body\n", encoding="utf-8")
    result = classify_conflict(target)
    assert result.type == ConflictType.MIGRATION
    assert result.action == "ambiguous"
    assert result.confidence == "high"


# ---------------------------------------------------------------------------
# Plain code conflict — manual review required.
# ---------------------------------------------------------------------------


def test_plain_python_file_returns_code_manual_high() -> None:
    """A regular code file must route to human/LLM review."""
    target = FIXTURES / "regular_code.py"
    assert target.exists()
    result = classify_conflict(target)
    assert result.type == ConflictType.CODE
    assert result.action == "manual"
    assert result.confidence == "high"


@pytest.mark.parametrize(
    "filename",
    [
        "service.ts",
        "handler.go",
        "main.rs",
        "Program.cs",
    ],
)
def test_plain_code_file_across_stacks_returns_manual(
    tmp_path: Path,
    filename: str,
) -> None:
    """Plain code in any supported stack stays manual."""
    target = tmp_path / filename
    target.write_text("// trivial body\n", encoding="utf-8")
    result = classify_conflict(target)
    assert result.type == ConflictType.CODE
    assert result.action == "manual"
    assert result.confidence == "high"


# ---------------------------------------------------------------------------
# Config family — three-way merge possible, caller decides.
# ---------------------------------------------------------------------------


def test_pyproject_toml_returns_config_ambiguous_medium() -> None:
    """``pyproject.toml`` is mergeable but the caller owns the decision."""
    target = FIXTURES / "pyproject.toml"
    assert target.exists()
    result = classify_conflict(target)
    assert result.type == ConflictType.CONFIG
    assert result.action == "ambiguous"
    assert result.confidence == "medium"


@pytest.mark.parametrize(
    "filename",
    [
        ".env",
        "package.json",
        "Cargo.toml",
        "tsconfig.json",
    ],
)
def test_config_file_family_returns_ambiguous_medium(
    tmp_path: Path,
    filename: str,
) -> None:
    """Config files outside the lock family return config + ambiguous."""
    target = tmp_path / filename
    target.write_text("{}\n", encoding="utf-8")
    result = classify_conflict(target)
    assert result.type == ConflictType.CONFIG
    assert result.action == "ambiguous"
    assert result.confidence == "medium"


# ---------------------------------------------------------------------------
# Conservative default for paths with no signal.
# ---------------------------------------------------------------------------


def test_unknown_binary_path_returns_unknown_ambiguous_low() -> None:
    """A file with no recognizable signal must fall through conservatively."""
    target = FIXTURES / "unknown.bin"
    assert target.exists()
    result = classify_conflict(target)
    assert result.type == ConflictType.UNKNOWN
    assert result.action == "ambiguous"
    assert result.confidence == "low"


def test_random_path_with_no_signal_returns_unknown_ambiguous_low(
    tmp_path: Path,
) -> None:
    """Arbitrary nested paths with opaque names default to unknown."""
    target = tmp_path / "random" / "path" / "data.bin"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"\x00\x01\x02opaque")
    result = classify_conflict(target)
    assert result.type == ConflictType.UNKNOWN
    assert result.action == "ambiguous"
    assert result.confidence == "low"


# ---------------------------------------------------------------------------
# Performance smoke — 100 paths under 500 ms wall-clock.
# ---------------------------------------------------------------------------


def test_classify_conflict_perf_smoke_100_paths_under_500ms(tmp_path: Path) -> None:
    """Hot-path budget: 100 classifications must finish in < 500 ms."""
    paths: list[Path] = []
    for index in range(100):
        target = tmp_path / f"sample_{index}.py"
        target.write_text("body\n", encoding="utf-8")
        paths.append(target)

    start = time.monotonic()
    for target in paths:
        classify_conflict(target)
    elapsed_ms = (time.monotonic() - start) * 1000.0

    assert elapsed_ms < 500.0, (
        f"classify_conflict perf budget exceeded: {elapsed_ms:.1f}ms for 100 paths"
    )
