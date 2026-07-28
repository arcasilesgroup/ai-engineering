"""Codex IDE surface generators.

spec-201 D-201-04 / D-201-23: `.codex/skills` and `.codex/agents` were both
hard-deleted — Codex reads the shared `.agents/skills` tree, and its agent
namespace accepts TOML only — so the skill and agent generators went with
them. Only the provider-owned config/hooks surface generator remains.
"""

from __future__ import annotations

from scripts.sync_mirrors.core import generate_install_codex_surface

__all__ = ["generate_install_codex_surface"]
