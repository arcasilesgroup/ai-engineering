"""spec-105 Phase 6 -- live hook + template hook byte-equivalence.

Asserts that the live PostToolUse auto-format hook in
``.ai-engineering/scripts/hooks/auto-format.py`` and the install template
in ``src/ai_engineering/templates/.ai-engineering/scripts/hooks/auto-format.py``
are byte-equivalent. Drift between the two means a fresh ``ai-eng install``
ships a different hook than what the framework dogfoods, breaking the
spec-105 D-105-09 cross-layer guarantee that orchestrator + hook share
the SAME auto-stage primitive.

NOT marked spec_105_red -- this lands GREEN on the same commit as the
hook update so we never have a window where the two hooks could drift
silently.
"""

from __future__ import annotations

from pathlib import Path

import ai_engineering

_LIVE_HOOK_REL = Path(".ai-engineering/scripts/hooks/auto-format.py")
_TEMPLATE_HOOK_REL = Path("templates/.ai-engineering/scripts/hooks/auto-format.py")


def _repo_root() -> Path:
    """Return the repository root by walking up from the package install."""
    return Path(ai_engineering.__file__).resolve().parent.parent.parent


def _package_root() -> Path:
    """Return the ``src/ai_engineering`` package root for template lookup."""
    return Path(ai_engineering.__file__).resolve().parent


def test_live_hook_and_template_are_byte_equivalent() -> None:
    """The live hook and the template hook MUST be byte-for-byte equal."""
    live_path = _repo_root() / _LIVE_HOOK_REL
    template_path = _package_root() / _TEMPLATE_HOOK_REL

    assert live_path.exists(), f"missing live hook: {live_path}"
    assert template_path.exists(), f"missing template hook: {template_path}"

    live_bytes = live_path.read_bytes()
    template_bytes = template_path.read_bytes()

    # Equality assertion produces a clear diff in pytest output when the
    # two diverge -- the operator immediately sees what byte changed.
    assert live_bytes == template_bytes, (
        f"hook drift detected:\n"
        f"  live:     {live_path} ({len(live_bytes)} bytes)\n"
        f"  template: {template_path} ({len(template_bytes)} bytes)\n"
        f"Run scripts/sync-hook-template.sh or copy the live hook over the template."
    )


def test_both_hook_copies_carry_scripts_exclusion_guard() -> None:
    """spec-179 D-179-04: both the live hook and its template twin MUST carry the
    ``.ai-engineering/scripts/`` exclusion guard.

    Byte-equivalence alone would pass if a refactor deleted the guard from BOTH
    copies in lockstep. This guard-TEXT assertion fails loudly if the exclusion
    is dropped, independent of byte parity.
    """
    live_path = _repo_root() / _LIVE_HOOK_REL
    template_path = _package_root() / _TEMPLATE_HOOK_REL

    needle = ".ai-engineering/scripts/"
    for label, path in (("live", live_path), ("template", template_path)):
        text = path.read_text(encoding="utf-8")
        assert needle in text and "_is_under_pinned_scripts" in text, (
            f"{label} auto-format.py is missing the spec-179 pinned-scripts "
            f"exclusion guard ({path})"
        )
