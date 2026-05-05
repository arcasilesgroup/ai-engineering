"""Canonical engineering standards and legacy retirement contracts."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import TypeVar


class EngineeringStandard(StrEnum):
    """Canonical standards covered by the HX-12 closure layer."""

    CLEAN_CODE = "clean-code"
    CLEAN_ARCHITECTURE = "clean-architecture"
    SOLID = "solid"
    DRY = "dry"
    KISS = "kiss"
    YAGNI = "yagni"
    TDD = "tdd"
    SDD = "sdd"
    HARNESS_ENGINEERING = "harness-engineering"


class LegacyRetirementStatus(StrEnum):
    """Lifecycle state for one legacy surface family."""

    PRESERVED = "preserved"
    BLOCKED = "blocked"
    READY = "ready"
    RETIRED = "retired"


@dataclass(frozen=True)
class EngineeringStandardSpec:
    """Reusable standard entry with review and verify bindings."""

    standard: EngineeringStandard
    title: str
    summary: str
    canonical_refs: tuple[str, ...]
    review_lenses: tuple[str, ...]
    verify_modes: tuple[str, ...]


@dataclass(frozen=True)
class LegacyRetirementFamily:
    """Parity-first retirement contract for one legacy surface family."""

    family_id: str
    title: str
    sequence: int
    status: LegacyRetirementStatus
    replacement_owner: str
    current_surfaces: tuple[str, ...]
    replacement_refs: tuple[str, ...]
    parity_proofs: tuple[str, ...]
    rollback: str
    delete_allowed: bool = False


_REVIEW_LENSES = (
    "security",
    "backend",
    "performance",
    "correctness",
    "testing",
    "compatibility",
    "architecture",
    "maintainability",
    "frontend",
    "design",
)

_VERIFY_MODES = (
    "governance",
    "security",
    "architecture",
    "quality",
    "feature",
    "platform",
)

_OPERATIONAL_PRINCIPLES = ".ai-engineering/contexts/operational-principles.md"
_ENGINEERING_STANDARDS = ".ai-engineering/contexts/engineering-standards.md"
_HARNESS_ENGINEERING = ".ai-engineering/contexts/harness-engineering.md"
_CONSTITUTION = "CONSTITUTION.md"

_T = TypeVar("_T")


def build_engineering_standards_matrix() -> tuple[EngineeringStandardSpec, ...]:
    """Return the canonical standards matrix for review and verify consumers."""
    matrix = (
        EngineeringStandardSpec(
            standard=EngineeringStandard.CLEAN_CODE,
            title="Clean Code",
            summary="Readable, cohesive units with explicit names and direct control flow.",
            canonical_refs=(_OPERATIONAL_PRINCIPLES, _ENGINEERING_STANDARDS),
            review_lenses=(
                "correctness",
                "maintainability",
                "frontend",
                "design",
            ),
            verify_modes=("quality", "platform"),
        ),
        EngineeringStandardSpec(
            standard=EngineeringStandard.CLEAN_ARCHITECTURE,
            title="Clean Architecture",
            summary="Policy stays separated from framework, IO, and delivery concerns.",
            canonical_refs=(_OPERATIONAL_PRINCIPLES, _ENGINEERING_STANDARDS),
            review_lenses=("architecture", "backend", "compatibility"),
            verify_modes=("architecture", "platform"),
        ),
        EngineeringStandardSpec(
            standard=EngineeringStandard.SOLID,
            title="SOLID",
            summary="Responsibilities and abstractions stay proportionate to the change.",
            canonical_refs=(_OPERATIONAL_PRINCIPLES, _ENGINEERING_STANDARDS),
            review_lenses=("architecture", "maintainability", "backend"),
            verify_modes=("architecture", "quality"),
        ),
        EngineeringStandardSpec(
            standard=EngineeringStandard.DRY,
            title="DRY",
            summary="Shared knowledge is centralized only when drift would otherwise be real.",
            canonical_refs=(_OPERATIONAL_PRINCIPLES, _ENGINEERING_STANDARDS),
            review_lenses=("maintainability", "architecture", "performance"),
            verify_modes=("quality", "architecture"),
        ),
        EngineeringStandardSpec(
            standard=EngineeringStandard.KISS,
            title="KISS",
            summary="The simplest design that satisfies the approved spec wins.",
            canonical_refs=(_OPERATIONAL_PRINCIPLES, _ENGINEERING_STANDARDS),
            review_lenses=("architecture", "maintainability", "correctness"),
            verify_modes=("quality", "feature"),
        ),
        EngineeringStandardSpec(
            standard=EngineeringStandard.YAGNI,
            title="YAGNI",
            summary="Speculative extensions wait for real requirements and tests.",
            canonical_refs=(_OPERATIONAL_PRINCIPLES, _ENGINEERING_STANDARDS),
            review_lenses=("architecture", "compatibility", "maintainability"),
            verify_modes=("feature", "architecture"),
        ),
        EngineeringStandardSpec(
            standard=EngineeringStandard.TDD,
            title="TDD",
            summary="Domain behavior starts with failing tests and refactors stay green.",
            canonical_refs=(_CONSTITUTION, _ENGINEERING_STANDARDS),
            review_lenses=("testing", "correctness", "compatibility"),
            verify_modes=("quality", "feature", "platform"),
        ),
        EngineeringStandardSpec(
            standard=EngineeringStandard.SDD,
            title="SDD",
            summary="Implementation traces to approved specs, plans, evidence, and decisions.",
            canonical_refs=(_CONSTITUTION, _ENGINEERING_STANDARDS),
            review_lenses=("architecture", "compatibility", "testing"),
            verify_modes=("governance", "feature", "platform"),
        ),
        EngineeringStandardSpec(
            standard=EngineeringStandard.HARNESS_ENGINEERING,
            title="Harness Engineering",
            summary="Deterministic gates, work-plane state, mirrors, and evals remain governed.",
            canonical_refs=(_HARNESS_ENGINEERING, _ENGINEERING_STANDARDS),
            review_lenses=(
                "security",
                "architecture",
                "compatibility",
                "testing",
                "performance",
            ),
            verify_modes=("governance", "security", "architecture", "platform"),
        ),
    )
    validate_engineering_standards_matrix(matrix)
    return matrix


def validate_engineering_standards_matrix(entries: tuple[EngineeringStandardSpec, ...]) -> None:
    """Validate canonical standard coverage and consumer bindings."""
    standards = _unique(entry.standard for entry in entries)
    if set(standards) != set(EngineeringStandard):
        msg = "Engineering standards matrix must cover every required standard exactly once"
        raise ValueError(msg)
    for entry in entries:
        _require_text(entry.title, "standard title")
        _require_text(entry.summary, "standard summary")
        _require_items(entry.canonical_refs, "standard canonical refs")
        _require_known(entry.review_lenses, _REVIEW_LENSES, "review lens")
        _require_known(entry.verify_modes, _VERIFY_MODES, "verify mode")
    _require_consumer_coverage(entries)


def standards_for_review_lens(lens: str) -> tuple[EngineeringStandard, ...]:
    """Return standards bound to one review specialist lens."""
    normalized = lens.strip()
    return tuple(
        entry.standard
        for entry in build_engineering_standards_matrix()
        if normalized in entry.review_lenses
    )


def standards_for_verify_mode(mode: str) -> tuple[EngineeringStandard, ...]:
    """Return standards bound to one verify specialist or aggregate mode."""
    normalized = mode.strip()
    return tuple(
        entry.standard
        for entry in build_engineering_standards_matrix()
        if normalized in entry.verify_modes
    )


def build_legacy_retirement_manifest() -> tuple[LegacyRetirementFamily, ...]:
    """Return the family-by-family legacy retirement manifest."""
    manifest = (
        LegacyRetirementFamily(
            family_id="control-plane-compatibility-surfaces",
            title="Control-plane compatibility surfaces",
            sequence=10,
            status=LegacyRetirementStatus.PRESERVED,
            replacement_owner="HX-01",
            current_surfaces=("CONSTITUTION.md", ".ai-engineering/CONSTITUTION.md"),
            replacement_refs=(".ai-engineering/manifest.yml",),
            parity_proofs=(
                ".ai-engineering/state/archive/delivery-logs/spec-117/verify_hx01_t5_3_focused_end_to_end_proof.md",
            ),
            rollback="Restore compatibility readers and rerun cross-reference validation.",
        ),
        LegacyRetirementFamily(
            family_id="manual-instruction-families",
            title="Manual instruction families retained after mirror cutover",
            sequence=20,
            status=LegacyRetirementStatus.BLOCKED,
            replacement_owner="HX-03/HX-12",
            current_surfaces=(
                ".github/instructions/testing.instructions.md",
                ".github/instructions/markdown.instructions.md",
                ".github/instructions/sonarqube_mcp.instructions.md",
            ),
            replacement_refs=("scripts/sync_command_mirrors.py",),
            parity_proofs=(
                ".ai-engineering/state/archive/delivery-logs/spec-117/verify_hx03_t5_3_focused_end_to_end_proof.md",
            ),
            rollback="Re-enable manual family preservation and regenerate mirrors.",
        ),
        LegacyRetirementFamily(
            family_id="harness-gate-families",
            title="Legacy harness gate and eval affordances",
            sequence=30,
            status=LegacyRetirementStatus.BLOCKED,
            replacement_owner="HX-04/HX-11",
            current_surfaces=("src/ai_engineering/policy/orchestrator.py",),
            replacement_refs=("src/ai_engineering/verify/taxonomy.py",),
            parity_proofs=(
                ".ai-engineering/state/archive/delivery-logs/spec-117/verify_hx11_verification_eval_architecture.md",
            ),
            rollback="Restore prior gate routing and rerun verify taxonomy coverage.",
        ),
        LegacyRetirementFamily(
            family_id="state-report-residue",
            title="State and report residue surfaces",
            sequence=40,
            status=LegacyRetirementStatus.BLOCKED,
            replacement_owner="HX-05",
            current_surfaces=(".ai-engineering/state/",),
            replacement_refs=("src/ai_engineering/state/control_plane.py",),
            parity_proofs=(
                ".ai-engineering/state/archive/delivery-logs/spec-117/verify_hx05_t4_2_framework_events_snapshot_sequencing.md",
            ),
            rollback="Restore legacy state readers and rerun manifest-coherence validation.",
        ),
        LegacyRetirementFamily(
            family_id="template-runtime-duplication",
            title="Template/runtime duplication in packaged helpers",
            sequence=50,
            status=LegacyRetirementStatus.BLOCKED,
            replacement_owner="HX-08/HX-09/HX-10",
            current_surfaces=("src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/",),
            replacement_refs=("src/ai_engineering/hooks/asset_runtime.py",),
            parity_proofs=(
                ".ai-engineering/state/archive/delivery-logs/spec-117/verify_hx10_runtime_core_extraction_track_c.md",
            ),
            rollback="Restore stdlib-only helper mirrors and rerun hook asset runtime tests.",
        ),
        LegacyRetirementFamily(
            family_id="user-facing-rollout-docs",
            title="User-facing rollout docs for implemented runtime contracts",
            sequence=60,
            status=LegacyRetirementStatus.PRESERVED,
            replacement_owner="HX-12",
            current_surfaces=("README.md", "GETTING_STARTED.md"),
            replacement_refs=(".ai-engineering/contexts/harness-adoption.md",),
            parity_proofs=(
                ".ai-engineering/state/archive/delivery-logs/spec-117/verify_hx12_engineering_standards_and_legacy_retirement.md",
            ),
            rollback="Keep root docs trailing framework contexts until runtime commands are proven.",
        ),
    )
    validate_legacy_retirement_manifest(manifest)
    return manifest


def validate_legacy_retirement_manifest(entries: tuple[LegacyRetirementFamily, ...]) -> None:
    """Validate legacy retirement entries before any deletion is allowed."""
    _unique(entry.family_id for entry in entries)
    sequences = _unique(entry.sequence for entry in entries)
    if list(sequences) != sorted(sequences):
        msg = "Legacy retirement families must be serialized by ascending sequence"
        raise ValueError(msg)
    for entry in entries:
        _validate_retirement_family(entry)


def _validate_retirement_family(entry: LegacyRetirementFamily) -> None:
    _require_text(entry.family_id, "legacy family id")
    _require_text(entry.title, "legacy family title")
    _require_text(entry.replacement_owner, "replacement owner")
    _require_items(entry.current_surfaces, "current surfaces")
    _require_items(entry.replacement_refs, "replacement refs")
    _require_text(entry.rollback, "rollback")
    if not entry.parity_proofs:
        msg = f"Legacy family {entry.family_id} requires parity proof before deletion"
        raise ValueError(msg)
    if entry.delete_allowed and entry.status not in {
        LegacyRetirementStatus.READY,
        LegacyRetirementStatus.RETIRED,
    }:
        msg = f"Legacy family {entry.family_id} cannot delete before READY or RETIRED status"
        raise ValueError(msg)


def _require_consumer_coverage(entries: tuple[EngineeringStandardSpec, ...]) -> None:
    review_lenses = {lens for entry in entries for lens in entry.review_lenses}
    verify_modes = {mode for entry in entries for mode in entry.verify_modes}
    if review_lenses != set(_REVIEW_LENSES):
        msg = "Engineering standards matrix must cover every review lens"
        raise ValueError(msg)
    if verify_modes != set(_VERIFY_MODES):
        msg = "Engineering standards matrix must cover every verify mode"
        raise ValueError(msg)


def _require_text(value: str, label: str) -> None:
    if not value.strip():
        msg = f"Missing {label}"
        raise ValueError(msg)


def _require_items(values: tuple[object, ...], label: str) -> None:
    if not values:
        msg = f"Missing {label}"
        raise ValueError(msg)


def _require_known(values: tuple[str, ...], allowed: tuple[str, ...], label: str) -> None:
    _require_items(values, label)
    unknown = sorted(set(values) - set(allowed))
    if unknown:
        msg = f"Unknown {label}: {', '.join(unknown)}"
        raise ValueError(msg)


def _unique(values: Iterable[_T]) -> tuple[_T, ...]:
    seen: set[_T] = set()
    result: list[_T] = []
    for value in values:
        if value in seen:
            msg = f"Duplicate value: {value}"
            raise ValueError(msg)
        seen.add(value)
        result.append(value)
    return tuple(result)
