"""GEMINI.md placeholder tests — retired per spec-131 D-131-03.

The original module (spec-107 D-107-04 / spec-122 D-122-24) asserted
that ``templates/project/GEMINI.md`` used ``__SKILL_COUNT__`` /
``__AGENT_COUNT__`` placeholders that ``sync_command_mirrors.py``
materialised into ``<repo>/.gemini/GEMINI.md`` at sync time.

spec-131 D-131-03 deleted ``<repo>/.gemini/GEMINI.md`` outright (the
Gemini CLI does not read in-repo ``.gemini/`` — the canonical surface
is the root ``GEMINI.md`` mirror generated from CANONICAL.md). The
templates no longer use the placeholder substitution scheme either;
the byte-equivalent mirror contract handles count synchronisation via
the CANONICAL.md §12 Surface Index.

All four assertions in this module are retired by spec-131 closure
sweep C1. The skeleton remains as an anchor for the historical
contract so the rename is traceable; no live tests fire.
"""

from __future__ import annotations


def test_module_retired_per_spec_131() -> None:
    """Anchor for the retired ``__SKILL_COUNT__`` / ``__AGENT_COUNT__`` contract.

    spec-131 D-131-03 deleted ``.gemini/GEMINI.md`` and migrated the
    canonical Gemini payload to ``<repo>/GEMINI.md`` (byte-equivalent
    mirror of CANONICAL.md). The placeholder substitution path is no
    longer wired. See CHANGELOG.md "spec-131 S1 — Markdown Canon Reset"
    for the rationale.
    """
    # Intentionally empty — the module is preserved as an audit anchor.
    assert True
