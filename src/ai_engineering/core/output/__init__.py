"""Centralised output module (spec-132 D-132-12).

Single source of truth for command output. See ``renderer.py`` for the
public ``Renderer`` contract; the four legacy output modules
(``cli_envelope``, ``cli_ui``, ``cli_progress``, ``cli_output``) are
wrapped, not replaced. Direct imports of those four modules from
``cli_commands/`` are banned by the conformance gate introduced in
sub-002 and tightened to zero in sub-004.
"""

from ai_engineering.core.output.renderer import (
    ChangeKind,
    NextAction,
    Renderer,
    Verb,
)

__all__ = ["ChangeKind", "NextAction", "Renderer", "Verb"]
