"""spec-142 B-1 -- live session_bootstrap + template byte-equivalence.

Asserts that the live script at
``.ai-engineering/scripts/session_bootstrap.py`` and the install template at
``src/ai_engineering/templates/.ai-engineering/scripts/session_bootstrap.py``
are byte-equivalent. Drift means a fresh ``ai-eng install`` ships the
pre-spec-142 script instead of the updated one, silently breaking every
surface-aware dashboard feature introduced by spec-142.

Fix command when this test fails:

    cp .ai-engineering/scripts/session_bootstrap.py \\
       src/ai_engineering/templates/.ai-engineering/scripts/session_bootstrap.py

Reference: spec-142 B-1 (template parity gap blocker).
"""

from __future__ import annotations

from pathlib import Path

import ai_engineering

_LIVE_REL = Path(".ai-engineering/scripts/session_bootstrap.py")
_TEMPLATE_REL = Path("templates/.ai-engineering/scripts/session_bootstrap.py")


def _repo_root() -> Path:
    """Return the repository root by walking up from the package install."""
    return Path(ai_engineering.__file__).resolve().parent.parent.parent


def _package_root() -> Path:
    """Return the ``src/ai_engineering`` package root for template lookup."""
    return Path(ai_engineering.__file__).resolve().parent


def test_live_script_and_template_are_byte_equivalent() -> None:
    """Live session_bootstrap and template MUST be byte-for-byte equal.

    A divergence means fresh installs ship a stale script that lacks the
    spec-142 surface-aware dashboard changes.  Fix:

        cp .ai-engineering/scripts/session_bootstrap.py \\
           src/ai_engineering/templates/.ai-engineering/scripts/session_bootstrap.py

    (spec-142 B-1)
    """
    live_path = _repo_root() / _LIVE_REL
    template_path = _package_root() / _TEMPLATE_REL

    assert live_path.exists(), f"missing live script: {live_path}"
    assert template_path.exists(), f"missing template script: {template_path}"

    # Normalise CRLF → LF for cross-platform checkout safety (mirrors the
    # same normalisation used in test_hook_template_parity.py).
    live_bytes = live_path.read_bytes().replace(b"\r\n", b"\n")
    template_bytes = template_path.read_bytes().replace(b"\r\n", b"\n")

    assert live_bytes == template_bytes, (
        f"spec-142 B-1 template parity drift detected:\n"
        f"  live:     {live_path} ({len(live_bytes)} bytes)\n"
        f"  template: {template_path} ({len(template_bytes)} bytes)\n"
        f"Fix:\n"
        f"  cp .ai-engineering/scripts/session_bootstrap.py \\\n"
        f"     src/ai_engineering/templates/.ai-engineering/scripts/session_bootstrap.py"
    )
