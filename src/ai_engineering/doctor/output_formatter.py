"""Doctor output formatter for spec-113 G-11 / D-113-09 (VCS consolidation).

The doctor runs three independent checks that all surface the same
underlying reality when ``gh`` is missing in a freshly-installed repo:

* ``tools-vcs`` -- VCS-tool probe (gh / az).
* ``vcs-auth`` -- runtime auth probe (gh auth status).
* ``detection-current`` -- VCS provider mismatch / no-remote check.

When all three roots back to the same gh-missing fact, three near-identical
WARN lines render to the operator. The pre-spec-113 surface was redundant
noise. spec-113 D-113-09 keeps the three checks distinct in telemetry
(internal name unchanged) but consolidates the human-rendered surface to
a single agreed line:

    VCS '<provider>' tooling: gh missing -- install with <distro_command>;
    auth not verifiable until installed

The aggregator inspects the report and, when consolidation conditions
are met, returns a tuple of (consolidated_message, set of suppressed
check names). Callers render the consolidated message in place of the
suppressed warnings.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ai_engineering.doctor.models import CheckResult, CheckStatus

__all__ = (
    "VCSConsolidation",
    "consolidate_vcs_warnings",
)


# Names of checks that participate in the gh-missing consolidation.
_VCS_CHECK_NAMES: frozenset[str] = frozenset(
    {
        "tools-vcs",
        "vcs-auth",
        "detection-current",
    }
)


@dataclass(frozen=True)
class VCSConsolidation:
    """Outcome of attempting to consolidate VCS-related warnings.

    Attributes:
        consolidated: True when consolidation criteria were met.
        message: The single human-rendered line that should replace the
            suppressed warnings; empty string when ``consolidated`` is False.
        suppressed_names: Names of the original checks whose human output
            should be skipped in favour of the consolidated message.
    """

    consolidated: bool
    message: str
    suppressed_names: frozenset[str]


def consolidate_vcs_warnings(
    checks: Iterable[CheckResult],
    *,
    vcs_provider: str | None,
    install_hint: str | None = None,
) -> VCSConsolidation:
    """Return a single consolidated message when all three VCS checks warn together.

    spec-113 G-11: the consolidation key is "all three VCS checks WARN
    AND the underlying reason is the same gh-missing fact". When the
    conditions do NOT hold, returns ``VCSConsolidation(consolidated=False)``
    so callers fall back to the existing per-check rendering.

    Args:
        checks: All check results emitted by the doctor (phase + runtime).
        vcs_provider: The vcs_provider value from install state (used to
            label the consolidated message).
        install_hint: Distro-aware install hint for ``gh`` (e.g.
            ``"sudo apt-get install -y gh"``). May be ``None`` when the
            caller could not compute it; the generic surface is used in
            that case.

    Returns:
        :class:`VCSConsolidation` either describing the merged message
        or signalling that no consolidation should happen.
    """
    relevant: dict[str, CheckResult] = {}
    for cr in checks:
        if cr.name in _VCS_CHECK_NAMES:
            relevant[cr.name] = cr

    # Need ALL three checks present.
    if set(relevant.keys()) != _VCS_CHECK_NAMES:
        return VCSConsolidation(consolidated=False, message="", suppressed_names=frozenset())

    # All three must currently surface as WARN -- if any is OK, the
    # underlying reality is no longer "gh missing" and the per-check
    # rendering is more informative.
    if any(cr.status != CheckStatus.WARN for cr in relevant.values()):
        return VCSConsolidation(consolidated=False, message="", suppressed_names=frozenset())

    tools_vcs = relevant["tools-vcs"]
    # The tools-vcs message names the missing tool ("VCS tool 'gh' not
    # found ..."). When the consolidation root is something other than
    # gh missing, we keep per-check rendering.
    missing_tool = _extract_missing_tool(tools_vcs.message)
    if missing_tool is None:
        return VCSConsolidation(consolidated=False, message="", suppressed_names=frozenset())

    label = vcs_provider or "github"
    hint_clause = f" -- install with {install_hint}" if install_hint else ""
    consolidated_message = (
        f"VCS '{label}' tooling: {missing_tool} missing{hint_clause}; "
        "auth not verifiable until installed"
    )
    return VCSConsolidation(
        consolidated=True,
        message=consolidated_message,
        suppressed_names=frozenset(_VCS_CHECK_NAMES),
    )


def _extract_missing_tool(message: str) -> str | None:
    """Return the missing-tool name parsed from a ``tools-vcs`` WARN message.

    The current message shape is::

        VCS tool 'gh' not found (provider: github)

    On unrecognised shapes, returns ``None`` so the caller falls back to
    per-check rendering.
    """
    if "VCS tool" not in message or "not found" not in message:
        return None
    # Quote-extract: take whatever is between the first single-quote pair.
    open_idx = message.find("'")
    if open_idx == -1:
        return None
    close_idx = message.find("'", open_idx + 1)
    if close_idx == -1:
        return None
    candidate = message[open_idx + 1 : close_idx].strip()
    return candidate or None
