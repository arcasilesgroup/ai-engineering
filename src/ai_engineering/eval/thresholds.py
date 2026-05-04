"""Manifest-driven evaluation thresholds (D-119-04)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ManifestEvaluationConfig:
    """Loaded shape of the manifest `evaluation:` section."""

    pass_at_k_k: int
    pass_at_k_threshold: float
    hallucination_rate_max: float
    regression_tolerance: float
    scenario_packs: tuple[str, ...]
    enforcement: str  # "blocking" | "advisory"

    @property
    def is_blocking(self) -> bool:
        return self.enforcement == "blocking"


def _coerce_int(value: object, name: str) -> int:
    if isinstance(value, bool):  # bool is a subclass of int — exclude it explicitly
        msg = f"{name} must be an integer, got bool"
        raise ValueError(msg)
    if not isinstance(value, int):
        msg = f"{name} must be an integer, got {type(value).__name__}"
        raise ValueError(msg)
    return value


def _coerce_unit(value: object, name: str) -> float:
    if isinstance(value, bool):
        msg = f"{name} must be numeric in [0, 1], got bool"
        raise ValueError(msg)
    if not isinstance(value, int | float):
        msg = f"{name} must be numeric in [0, 1], got {type(value).__name__}"
        raise ValueError(msg)
    f = float(value)
    if not (0 <= f <= 1):
        msg = f"{name} must be in [0, 1], got {f}"
        raise ValueError(msg)
    return f


def load_evaluation_config(manifest_path: Path) -> ManifestEvaluationConfig:
    if not manifest_path.exists():
        msg = f"manifest not found: {manifest_path}"
        raise FileNotFoundError(msg)
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or "evaluation" not in raw:
        msg = "manifest does not declare an `evaluation:` section (spec-119 D-119-04)"
        raise ValueError(msg)
    section = raw["evaluation"]
    pass_at_k = section["pass_at_k"]
    enforcement = section.get("enforcement", "blocking")
    if enforcement not in {"blocking", "advisory"}:
        msg = f"evaluation.enforcement must be one of 'blocking' | 'advisory'; got {enforcement!r}"
        raise ValueError(msg)
    packs = section.get("scenario_packs", [])
    if not isinstance(packs, list) or not all(isinstance(p, str) and p for p in packs):
        msg = "evaluation.scenario_packs must be a non-empty list of strings"
        raise ValueError(msg)
    return ManifestEvaluationConfig(
        pass_at_k_k=_coerce_int(pass_at_k["k"], "evaluation.pass_at_k.k"),
        pass_at_k_threshold=_coerce_unit(pass_at_k["threshold"], "evaluation.pass_at_k.threshold"),
        hallucination_rate_max=_coerce_unit(
            section["hallucination_rate"]["max"], "evaluation.hallucination_rate.max"
        ),
        regression_tolerance=_coerce_unit(
            section["regression_tolerance"], "evaluation.regression_tolerance"
        ),
        scenario_packs=tuple(packs),
        enforcement=enforcement,
    )
