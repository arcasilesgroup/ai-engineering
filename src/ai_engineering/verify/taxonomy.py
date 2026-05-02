"""Canonical verification taxonomy and eval reporting helpers for HX-11."""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from math import comb

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ai_engineering.policy.orchestrator import CI_EXTRA_CHECKERS, LOCAL_CHECKERS
from ai_engineering.standards import EngineeringStandard, standards_for_verify_mode
from ai_engineering.validator._shared import IntegrityCategory

_TESTS_PERF_PATH = "tests/perf"


class VerificationPlane(StrEnum):
    """Primary verification plane for one check family."""

    KERNEL = "kernel"
    REPO_GOVERNANCE = "repo-governance"
    VERIFY_REPORT = "verify-report"
    EVAL = "eval"
    SHELL_ADAPTER = "shell-adapter"
    PERF_STABILITY = "perf-stability"


class ReportingSurface(StrEnum):
    """Where a check family is normally reported."""

    LOCAL_GATE = "local-gate"
    VALIDATE = "validate"
    VERIFY = "verify"
    CI = "ci"
    PERF = "perf"
    EVAL = "eval"


class VerificationTestShape(StrEnum):
    """Canonical test-shape boundary for reporting."""

    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERF = "perf"
    PARITY = "parity"
    RESILIENCE = "resilience"
    STATIC = "static"
    SECURITY = "security"
    GOVERNANCE = "governance"
    SCENARIO = "scenario"


class VerificationCheckSpec(BaseModel):
    """Stable registry entry for one verification check family."""

    stable_id: str = Field(alias="stableId")
    primary_plane: VerificationPlane = Field(alias="primaryPlane")
    current_names: tuple[str, ...] = Field(alias="currentNames")
    owner: str
    reporting_surfaces: tuple[ReportingSurface, ...] = Field(alias="reportingSurfaces")
    test_shape: VerificationTestShape = Field(alias="testShape")
    blocking: bool = False
    derived: bool = False
    provenance_refs: tuple[str, ...] = Field(default_factory=tuple, alias="provenanceRefs")
    standards: tuple[EngineeringStandard, ...] = Field(default_factory=tuple)

    model_config = ConfigDict(populate_by_name=True, frozen=True)

    @field_validator("stable_id", "owner")
    @classmethod
    def _validate_non_empty_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Verification registry entries require non-empty stableId and owner"
            raise ValueError(msg)
        return stripped

    @field_validator("current_names", "reporting_surfaces")
    @classmethod
    def _validate_non_empty_tuple(cls, value: tuple[object, ...]) -> tuple[object, ...]:
        if not value:
            msg = "Verification registry entries require current names and reporting surfaces"
            raise ValueError(msg)
        return value


class EvalScenario(BaseModel):
    """One replayable scenario seed delegated to an existing runner."""

    scenario_id: str = Field(alias="scenarioId")
    runner: str
    command: tuple[str, ...]
    test_shape: VerificationTestShape = Field(alias="testShape")
    provenance_refs: tuple[str, ...] = Field(default_factory=tuple, alias="provenanceRefs")

    model_config = ConfigDict(populate_by_name=True, frozen=True)


class EvalScenarioPack(BaseModel):
    """Replayable eval pack metadata that does not execute checks itself."""

    pack_id: str = Field(alias="packId")
    scenarios: tuple[EvalScenario, ...]
    baseline_ref: str | None = Field(default=None, alias="baselineRef")
    reporting_only: bool = Field(default=True, alias="reportingOnly")

    model_config = ConfigDict(populate_by_name=True, frozen=True)

    @field_validator("scenarios")
    @classmethod
    def _validate_scenarios(cls, value: tuple[EvalScenario, ...]) -> tuple[EvalScenario, ...]:
        if not value:
            msg = "Eval scenario packs require at least one scenario"
            raise ValueError(msg)
        return value


class EvalReplayOutcome(BaseModel):
    """Derived replay metrics for one eval/scenario pack."""

    pack_id: str = Field(alias="packId")
    attempts: int
    successes: int
    k: int = 1
    regressions: tuple[str, ...] = Field(default_factory=tuple)
    pass_at_k: float = Field(alias="passAtK")
    pass_power_k: float = Field(alias="passPowerK")
    derived: bool = True
    provenance_refs: tuple[str, ...] = Field(default_factory=tuple, alias="provenanceRefs")

    model_config = ConfigDict(populate_by_name=True, frozen=True)


class ReliabilityScorecard(BaseModel):
    """Derived reliability and performance scorecard."""

    scorecard_id: str = Field(alias="scorecardId")
    blocking: bool = False
    derived: bool = True
    pass_rate: float = Field(alias="passRate")
    pass_power_k: float = Field(alias="passPowerK")
    regression_count: int = Field(alias="regressionCount")
    latency_p95_ms: float | None = Field(default=None, alias="latencyP95Ms")
    retry_count: int = Field(default=0, alias="retryCount")
    provenance_refs: tuple[str, ...] = Field(alias="provenanceRefs")

    model_config = ConfigDict(populate_by_name=True, frozen=True)


def build_verification_registry() -> tuple[VerificationCheckSpec, ...]:
    """Build the canonical HX-11 verification registry."""
    entries: list[VerificationCheckSpec] = []
    entries.extend(_kernel_entries())
    entries.extend(_validator_entries())
    entries.extend(_verify_entries())
    entries.extend(_ci_entries())
    entries.extend(_perf_entries())
    validate_verification_registry(entries)
    return tuple(entries)


def validate_verification_registry(entries: Iterable[VerificationCheckSpec]) -> None:
    """Validate stable IDs, current-name coverage, and derived-metric provenance."""
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    for entry in entries:
        if entry.stable_id in seen_ids:
            msg = f"Duplicate verification stable id: {entry.stable_id}"
            raise ValueError(msg)
        seen_ids.add(entry.stable_id)
        for name in entry.current_names:
            if name in seen_names:
                msg = f"Duplicate verification current name: {name}"
                raise ValueError(msg)
            seen_names.add(name)
        if entry.derived and not entry.provenance_refs:
            msg = f"Derived verification metric lacks provenance: {entry.stable_id}"
            raise ValueError(msg)
        if not entry.standards:
            msg = f"Verification registry entry lacks standards binding: {entry.stable_id}"
            raise ValueError(msg)


def classify_check_name(name: str) -> VerificationCheckSpec | None:
    """Return the registry entry matching a current check name or stable ID."""
    normalized = name.strip()
    for entry in build_verification_registry():
        if normalized == entry.stable_id or normalized in entry.current_names:
            return entry
    return None


def build_seed_eval_pack() -> EvalScenarioPack:
    """Return the seed scenario pack over existing test runners."""
    return EvalScenarioPack(
        packId="eval.scenario.seed",
        baselineRef=".ai-engineering/evals/baselines/seed.json",
        scenarios=(
            EvalScenario(
                scenarioId="scenario.integration.research-tier0",
                runner="pytest",
                command=("pytest", "tests/integration/test_ai_research_tier0.py"),
                testShape=VerificationTestShape.SCENARIO,
                provenanceRefs=("tests/integration/test_ai_research_tier0.py",),
            ),
            EvalScenario(
                scenarioId="scenario.e2e.clean-install",
                runner="pytest",
                command=("pytest", "tests/e2e/test_install_clean.py"),
                testShape=VerificationTestShape.E2E,
                provenanceRefs=("tests/e2e/test_install_clean.py",),
            ),
            EvalScenario(
                scenarioId="scenario.perf.install-budget",
                runner="pytest",
                command=("pytest", _TESTS_PERF_PATH),
                testShape=VerificationTestShape.PERF,
                provenanceRefs=(_TESTS_PERF_PATH,),
            ),
        ),
    )


def build_replay_outcome(
    *,
    pack_id: str,
    attempts: int,
    successes: int,
    k: int = 1,
    regressions: tuple[str, ...] = (),
    provenance_refs: tuple[str, ...] = (),
) -> EvalReplayOutcome:
    """Build derived replay metrics for one scenario pack."""
    _validate_attempts(attempts, successes, k)
    rate = successes / attempts
    return EvalReplayOutcome(
        packId=pack_id,
        attempts=attempts,
        successes=successes,
        k=k,
        regressions=regressions,
        passAtK=_pass_at_k(attempts, successes, k),
        passPowerK=rate**k,
        provenanceRefs=provenance_refs,
    )


def build_reliability_scorecard(
    *,
    scorecard_id: str,
    outcomes: tuple[EvalReplayOutcome, ...],
    latency_samples_ms: tuple[float, ...] = (),
    retry_count: int = 0,
    blocking: bool = False,
    provenance_refs: tuple[str, ...] = (),
) -> ReliabilityScorecard:
    """Build a derived reliability/perf scorecard with explicit provenance."""
    if not outcomes:
        msg = "Reliability scorecards require at least one replay outcome"
        raise ValueError(msg)
    if not provenance_refs:
        msg = "Reliability scorecards require provenanceRefs"
        raise ValueError(msg)

    attempts = sum(outcome.attempts for outcome in outcomes)
    successes = sum(outcome.successes for outcome in outcomes)
    regressions = sum(len(outcome.regressions) for outcome in outcomes)
    pass_rate = successes / attempts if attempts else 0.0
    pass_power = min(outcome.pass_power_k for outcome in outcomes)
    return ReliabilityScorecard(
        scorecardId=scorecard_id,
        blocking=blocking,
        passRate=pass_rate,
        passPowerK=pass_power,
        regressionCount=regressions,
        latencyP95Ms=_percentile(latency_samples_ms, 95) if latency_samples_ms else None,
        retryCount=retry_count,
        provenanceRefs=provenance_refs,
    )


def summarize_replay_outcomes(outcomes: Iterable[EvalReplayOutcome]) -> dict[str, object]:
    """Build a derived per-pack regression summary for reports."""
    items = tuple(outcomes)
    return {
        "packs": len(items),
        "attempts": sum(item.attempts for item in items),
        "successes": sum(item.successes for item in items),
        "regressions": sorted({regression for item in items for regression in item.regressions}),
        "derived": True,
    }


def _kernel_entries() -> list[VerificationCheckSpec]:
    entries: list[VerificationCheckSpec] = []
    for name in (*LOCAL_CHECKERS, *CI_EXTRA_CHECKERS):
        entries.append(
            VerificationCheckSpec(
                stableId=f"check.kernel.{name.replace('-', '_')}",
                primaryPlane=VerificationPlane.KERNEL,
                currentNames=_current_names_for_kernel_check(name),
                owner="HX-04",
                reportingSurfaces=(ReportingSurface.LOCAL_GATE, ReportingSurface.CI),
                testShape=_shape_for_kernel_check(name),
                blocking=True,
                provenanceRefs=("src/ai_engineering/policy/orchestrator.py",),
                standards=_standards_for_kernel_check(name),
            )
        )
    return entries


def _validator_entries() -> list[VerificationCheckSpec]:
    return [
        VerificationCheckSpec(
            stableId=f"check.repo_governance.{category.value.replace('-', '_')}",
            primaryPlane=VerificationPlane.REPO_GOVERNANCE,
            currentNames=(category.value,),
            owner="validator",
            reportingSurfaces=(ReportingSurface.VALIDATE, ReportingSurface.CI),
            testShape=VerificationTestShape.GOVERNANCE,
            blocking=True,
            provenanceRefs=("src/ai_engineering/validator/_shared.py",),
            standards=(EngineeringStandard.SDD, EngineeringStandard.HARNESS_ENGINEERING),
        )
        for category in IntegrityCategory
    ]


def _verify_entries() -> list[VerificationCheckSpec]:
    return [
        VerificationCheckSpec(
            stableId=f"check.verify_report.{name}",
            primaryPlane=VerificationPlane.VERIFY_REPORT,
            currentNames=(f"verify:{name}", name),
            owner="verify",
            reportingSurfaces=(ReportingSurface.VERIFY,),
            testShape=(
                VerificationTestShape.GOVERNANCE
                if name == "governance"
                else VerificationTestShape.STATIC
            ),
            blocking=False,
            derived=True,
            provenanceRefs=("src/ai_engineering/verify/service.py",),
            standards=standards_for_verify_mode(name),
        )
        for name in ("governance", "security", "architecture", "quality", "feature")
    ]


def _ci_entries() -> list[VerificationCheckSpec]:
    return [
        VerificationCheckSpec(
            stableId="check.shell_adapter.test_hooks_matrix",
            primaryPlane=VerificationPlane.SHELL_ADAPTER,
            currentNames=("test-hooks-matrix", ".github/workflows/test-hooks-matrix.yml"),
            owner="shell-adapter",
            reportingSurfaces=(ReportingSurface.CI,),
            testShape=VerificationTestShape.PARITY,
            blocking=True,
            provenanceRefs=(".github/workflows/test-hooks-matrix.yml",),
            standards=(EngineeringStandard.SDD, EngineeringStandard.HARNESS_ENGINEERING),
        ),
        VerificationCheckSpec(
            stableId="check.perf_stability.install_time_budget",
            primaryPlane=VerificationPlane.PERF_STABILITY,
            currentNames=("install-time-budget", ".github/workflows/install-time-budget.yml"),
            owner="perf-stability",
            reportingSurfaces=(ReportingSurface.CI, ReportingSurface.PERF),
            testShape=VerificationTestShape.PERF,
            blocking=True,
            provenanceRefs=(".github/workflows/install-time-budget.yml",),
            standards=(EngineeringStandard.KISS, EngineeringStandard.HARNESS_ENGINEERING),
        ),
        VerificationCheckSpec(
            stableId="check.perf_stability.worktree_fast_second",
            primaryPlane=VerificationPlane.PERF_STABILITY,
            currentNames=("worktree-fast-second", ".github/workflows/worktree-fast-second.yml"),
            owner="perf-stability",
            reportingSurfaces=(ReportingSurface.CI, ReportingSurface.PERF),
            testShape=VerificationTestShape.PERF,
            blocking=False,
            provenanceRefs=(".github/workflows/worktree-fast-second.yml",),
            standards=(EngineeringStandard.KISS, EngineeringStandard.HARNESS_ENGINEERING),
        ),
    ]


def _perf_entries() -> list[VerificationCheckSpec]:
    return [
        VerificationCheckSpec(
            stableId="check.perf_stability.pytest_perf",
            primaryPlane=VerificationPlane.PERF_STABILITY,
            currentNames=(_TESTS_PERF_PATH, "pytest-perf"),
            owner="perf-stability",
            reportingSurfaces=(ReportingSurface.PERF,),
            testShape=VerificationTestShape.PERF,
            blocking=False,
            provenanceRefs=(_TESTS_PERF_PATH,),
            standards=(EngineeringStandard.KISS, EngineeringStandard.HARNESS_ENGINEERING),
        ),
        VerificationCheckSpec(
            stableId="check.eval.scenario_seed",
            primaryPlane=VerificationPlane.EVAL,
            currentNames=("eval.scenario.seed",),
            owner="eval",
            reportingSurfaces=(ReportingSurface.EVAL, ReportingSurface.VERIFY),
            testShape=VerificationTestShape.SCENARIO,
            blocking=False,
            derived=True,
            provenanceRefs=(".github/skills/ai-eval/SKILL.md",),
            standards=(EngineeringStandard.TDD, EngineeringStandard.HARNESS_ENGINEERING),
        ),
    ]


def _shape_for_kernel_check(name: str) -> VerificationTestShape:
    if name in {"gitleaks", "semgrep", "pip-audit"}:
        return VerificationTestShape.SECURITY
    if name in {"ruff", "ty"}:
        return VerificationTestShape.STATIC
    if name.startswith("pytest"):
        return VerificationTestShape.UNIT
    if name == "validate":
        return VerificationTestShape.GOVERNANCE
    return VerificationTestShape.STATIC


def _current_names_for_kernel_check(name: str) -> tuple[str, ...]:
    aliases = {
        "ruff": ("ruff", "ruff-check"),
        "validate": ("validate", "ai-eng-validate"),
        "pytest-smoke": ("pytest-smoke", "pytest"),
    }
    return aliases.get(name, (name,))


def _standards_for_kernel_check(name: str) -> tuple[EngineeringStandard, ...]:
    if name in {"gitleaks", "semgrep", "pip-audit"}:
        return (EngineeringStandard.SDD, EngineeringStandard.HARNESS_ENGINEERING)
    if name in {"ruff", "ty"}:
        return (EngineeringStandard.CLEAN_CODE, EngineeringStandard.KISS)
    if name.startswith("pytest"):
        return (EngineeringStandard.TDD, EngineeringStandard.HARNESS_ENGINEERING)
    if name == "validate":
        return (EngineeringStandard.SDD, EngineeringStandard.HARNESS_ENGINEERING)
    return (EngineeringStandard.KISS, EngineeringStandard.SDD)


def _validate_attempts(attempts: int, successes: int, k: int) -> None:
    if attempts <= 0:
        msg = "Replay attempts must be positive"
        raise ValueError(msg)
    if successes < 0 or successes > attempts:
        msg = "Replay successes must be between zero and attempts"
        raise ValueError(msg)
    if k <= 0 or k > attempts:
        msg = "Replay k must be between one and attempts"
        raise ValueError(msg)


def _pass_at_k(attempts: int, successes: int, k: int) -> float:
    failures = attempts - successes
    if failures < k:
        return 1.0
    return 1.0 - (comb(failures, k) / comb(attempts, k))


def _percentile(samples: tuple[float, ...], percentile: int) -> float:
    ordered = sorted(samples)
    if not ordered:
        msg = "Cannot compute percentile for empty samples"
        raise ValueError(msg)
    index = round((percentile / 100) * (len(ordered) - 1))
    return ordered[index]
