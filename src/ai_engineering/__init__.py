"""
ai-engineering: Context-first AI governance framework

Provides enforceable standards, session management, and gate controls
for AI-assisted development.
"""

try:
    from importlib.metadata import version

    __version__ = version("ai-engineering")
except Exception:
    __version__ = "0.0.0"

__all__ = ["__version__"]
