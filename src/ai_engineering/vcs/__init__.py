"""VCS abstraction layer for ai-engineering.

Provides a provider-agnostic interface for version control operations
(PR creation, auto-complete, status queries) supporting both GitHub (``gh``)
and Azure DevOps (``az repos``) backends.

Re-exports:
    get_provider, VcsProvider, VcsContext, VcsResult
"""

from __future__ import annotations

from ai_engineering.vcs.factory import get_provider
from ai_engineering.vcs.protocol import VcsContext, VcsProvider, VcsResult

__all__ = ["VcsContext", "VcsProvider", "VcsResult", "get_provider"]
