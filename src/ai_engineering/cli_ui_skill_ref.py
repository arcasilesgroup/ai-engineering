"""Skill-reference rendering helper — spec-133 D-133-22.

Every place the CLI prints a ``/ai-<name>`` to a shell user, route it
through ``skill_ref()`` or ``skill_ref_tight()``. Both helpers make it
unambiguous that the slash command is a chat command for the AI
surface, NOT a shell command. Avoids the recurring B17 incident where
operators paste ``/ai-start`` into a terminal.

Companion lint check: ``tools/skill_lint/checks/cli_output_skill_refs.py``
AST-walks the CLI tree and fails on naked ``/ai-<name>`` literals
inside ``print``/``typer.echo``/``OutputPort.emit`` calls.
"""

from __future__ import annotations


def _normalise(name: str) -> str:
    """Strip optional leading ``/`` and ``ai-`` prefix, return canonical slug."""
    if not name or not name.strip():
        raise ValueError("skill name must not be empty")
    slug = name.strip()
    if slug.startswith("/"):
        slug = slug[1:]
    if slug.startswith("ai-"):
        slug = slug[3:]
    if not slug:
        raise ValueError("skill name reduced to empty after prefix strip")
    return slug


def skill_ref(name: str) -> str:
    """Canonical long-form skill reference.

    Example:
        >>> skill_ref("start")
        'the /ai-start skill (run in your AI surface chat, not shell)'
    """
    slug = _normalise(name)
    return f"the /ai-{slug} skill (run in your AI surface chat, not shell)"


def skill_ref_tight(name: str) -> str:
    """Tight inline reference for compact contexts.

    Example:
        >>> skill_ref_tight("commit")
        '/ai-commit (in your AI surface)'
    """
    slug = _normalise(name)
    return f"/ai-{slug} (in your AI surface)"
