"""VCS abstraction layer for ai-engineering.

Provides a provider-agnostic interface for version control operations
(PR creation, auto-complete, status queries) supporting both GitHub (``gh``)
and Azure DevOps (``az repos``) backends.

Re-exports:
    get_provider, VcsProvider, VcsContext
"""

from __future__ import annotations
