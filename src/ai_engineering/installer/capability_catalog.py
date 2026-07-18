"""In-package bridge to the standalone capability-catalog generator.

The generator itself lives at ``scripts/gen_capability_catalog.py`` (stdlib-only,
runnable from a clean checkout). This module is the single integration point the
installer and ``ai-eng dev sync`` call so that the regeneration and drift-check
behavior — including the **fail-open-when-no-markers** contract — is defined
once (spec-153 D-153-12 / D-153-15, §10.4 DRY).

Fail-open contract: Wave 6 adds the ``<!-- catalog:start/end -->`` markers to the
README surfaces. Until then (and for any consumer project whose README has not
been marker-enabled), regeneration is skipped with a benign result rather than
raising — the absence of markers is an expected, non-blocking state.
"""

from __future__ import annotations

import importlib.util
import logging
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import ModuleType

logger = logging.getLogger(__name__)

# Target relative to the project root: the post-install client manual.
CATALOG_TARGET_REL = (".ai-engineering", "README.md")


class CatalogStatus(StrEnum):
    """Outcome of a catalog apply/check operation."""

    APPLIED = "applied"
    IN_SYNC = "in_sync"
    DRIFT = "drift"
    SKIPPED_NO_MARKERS = "skipped_no_markers"
    SKIPPED_NO_TARGET = "skipped_no_target"
    SKIPPED_NO_GENERATOR = "skipped_no_generator"


@dataclass(frozen=True)
class CatalogResult:
    """Structured result of a catalog operation."""

    status: CatalogStatus
    target: Path
    message: str

    @property
    def ok(self) -> bool:
        """True unless drift was detected (the only failing state)."""
        return self.status is not CatalogStatus.DRIFT


def _generator_path(project_root: Path) -> Path:
    return project_root / "scripts" / "gen_capability_catalog.py"


def _load_generator(project_root: Path) -> ModuleType | None:
    """Import the standalone generator by path; None when absent.

    The script is absent in consumer projects (it is a source-repo dev tool),
    so a missing generator is a benign skip, not an error.
    """
    path = _generator_path(project_root)
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("gen_capability_catalog", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _resolve_target(project_root: Path, target: Path | None) -> Path:
    if target is not None:
        return target
    return project_root.joinpath(*CATALOG_TARGET_REL)


def apply_capability_catalog(project_root: Path, target: Path | None = None) -> CatalogResult:
    """Regenerate the catalog block in *target*, failing open on missing markers.

    Returns a :class:`CatalogResult`; never raises for the expected
    no-generator / no-target / no-markers states.
    """
    resolved = _resolve_target(project_root, target)
    generator = _load_generator(project_root)
    if generator is None:
        return CatalogResult(
            CatalogStatus.SKIPPED_NO_GENERATOR,
            resolved,
            "capability-catalog generator not present; skipping (consumer project).",
        )
    if not resolved.is_file():
        return CatalogResult(
            CatalogStatus.SKIPPED_NO_TARGET,
            resolved,
            f"catalog target not found: {resolved}; skipping.",
        )
    try:
        generator.apply_to(resolved, project_root)
    except generator.MarkersNotFoundError:
        msg = (
            f"no catalog markers in {resolved}; skipping regeneration "
            "(markers are added by spec-153 Wave 6)."
        )
        logger.info(msg)
        return CatalogResult(CatalogStatus.SKIPPED_NO_MARKERS, resolved, msg)
    # Default-target runs also regenerate the source-repo install-template twin
    # so it never drifts from the live manual (spec-187 W4; fail-open when the
    # twin is absent, i.e. every consumer project).
    if target is None:
        generator.apply_template_twin(project_root)
    return CatalogResult(
        CatalogStatus.APPLIED, resolved, f"capability catalog regenerated in {resolved}."
    )


def check_capability_catalog(project_root: Path, target: Path | None = None) -> CatalogResult:
    """Check the catalog block in *target* for drift, failing open on no markers.

    Returns :class:`CatalogResult` with ``status == DRIFT`` (``ok`` False) only
    when a marker block exists and diverges from a fresh render.
    """
    resolved = _resolve_target(project_root, target)
    generator = _load_generator(project_root)
    if generator is None:
        return CatalogResult(
            CatalogStatus.SKIPPED_NO_GENERATOR,
            resolved,
            "capability-catalog generator not present; skipping check.",
        )
    if not resolved.is_file():
        return CatalogResult(
            CatalogStatus.SKIPPED_NO_TARGET,
            resolved,
            f"catalog target not found: {resolved}; skipping check.",
        )
    try:
        in_sync = generator.check(resolved, project_root)
    except generator.MarkersNotFoundError:
        msg = (
            f"no catalog markers in {resolved}; skipping drift check "
            "(markers are added by spec-153 Wave 6)."
        )
        logger.info(msg)
        return CatalogResult(CatalogStatus.SKIPPED_NO_MARKERS, resolved, msg)
    # Default-target checks also cover the source-repo install-template twin so
    # `dev sync --check` fails on a manually-drifted twin (spec-187 W4;
    # fail-open when the twin is absent).
    twin_in_sync = generator.check_template_twin(project_root) if target is None else True
    if in_sync and twin_in_sync:
        return CatalogResult(
            CatalogStatus.IN_SYNC, resolved, f"capability catalog in sync: {resolved}."
        )
    drift_target = resolved if not in_sync else generator.template_twin_path(project_root)
    return CatalogResult(
        CatalogStatus.DRIFT,
        drift_target,
        f"capability catalog drift detected in {drift_target}; run 'ai-eng dev sync'.",
    )
