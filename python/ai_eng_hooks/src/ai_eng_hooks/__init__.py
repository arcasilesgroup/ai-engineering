"""ai-engineering hooks package.

Hooks live as standalone executables under this package. The framework
discovers them by name and invokes them at the IDE host's lifecycle
points (PreToolUse, PostToolUse, SessionStart, Stop, UserPromptSubmit).

See ADR-0004 for why hooks stay in Python while the CLI is TypeScript.
"""

from ai_eng_hooks._meta import __version__

__all__ = ["__version__"]
