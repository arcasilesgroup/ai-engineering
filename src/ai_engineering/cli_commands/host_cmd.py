"""``ai-eng host probe`` CLI (spec-139 M2, D-139-02).

Thin operator-facing wrapper over
:func:`ai_engineering.adapters.host.probe` that prints the current
:class:`HostProbe` as JSON plus the cap that
:func:`ai_engineering.config.resolve_wave_cap` would recommend given
the same probe. The default output is a one-liner suitable for piping
into ``jq``; ``--json`` pretty-prints the same payload for human
inspection.

The CLI invocation deliberately does NOT emit a ``host_capacity``
framework event -- the caller is the operator, not a skill dispatch.
Skill-side callers (``/ai-autopilot`` Phase 0, ``/ai-build`` step 0)
import ``adapters.host.probe`` directly and emit the event themselves
with the ``caller`` field set to the dispatching skill.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Annotated

import typer

from ai_engineering.adapters.host import probe as host_probe
from ai_engineering.config.concurrency import resolve_wave_cap


def host_probe_cmd(
    json_pretty: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Pretty-print the JSON payload for human inspection.",
        ),
    ] = False,
) -> None:
    """Print the current :class:`HostProbe` plus the recommended wave cap.

    Output schema (sorted keys for grep-friendliness)::

        {
          "cores": int,
          "free_ram_gb": int,
          "ok_to_dispatch": bool,
          "platform": "darwin" | "linux" | "win32" | "unknown",
          "pressure_pct": int,
          "recommended_cap": int,
          "swap_used_pct": int
        }
    """
    snapshot = host_probe()
    env_var = os.environ.get("AIENG_MAX_WAVE_AGENTS")
    cap = resolve_wave_cap(env_var=env_var, manifest_value=None, host_probe=snapshot)

    payload: dict[str, object] = asdict(snapshot)
    payload["ok_to_dispatch"] = snapshot.ok_to_dispatch
    payload["recommended_cap"] = cap

    if json_pretty:
        typer.echo(json.dumps(payload, sort_keys=True, indent=2))
    else:
        typer.echo(json.dumps(payload, sort_keys=True))


__all__ = ["host_probe_cmd"]
