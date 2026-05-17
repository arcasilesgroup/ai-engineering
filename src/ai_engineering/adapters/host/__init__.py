"""Host preflight adapter (spec-139 M2, D-139-09).

Public surface:

* :class:`HostProbe` -- the canonical dataclass re-exported from
  :mod:`ai_engineering.config.concurrency` so callers never have to
  reach across rings to import it. The single source of truth for the
  shape lives in the config module; this package contributes the
  platform-specific *measurement* logic.
* :func:`probe` -- dispatch entry point. Returns a populated
  :class:`HostProbe` for the current ``sys.platform`` or a degraded
  zero-valued snapshot on any failure (fail-open).
"""

from __future__ import annotations

from ai_engineering.adapters.host.probe import probe
from ai_engineering.config.concurrency import HostProbe

__all__ = ["HostProbe", "probe"]
