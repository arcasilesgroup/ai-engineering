"""spec-154 — hermetic sandbox bin for hook interpreter-resolution tests.

The hook resolver/launcher tests fabricate fake Python interpreters and
assert which one the resolver selects. Earlier versions built the
subprocess ``PATH`` as ``[fake_bindir, "/usr/bin", "/bin"]``. That is
environment-fragile: on CI ubuntu ``/usr/bin`` carries a real
``python3.12`` (and a >=3.11 ``python3``), and the resolver trusts named
interpreters (``python3.13/3.12/3.11``) *by name* — so the negative /
fail-open cases would find an ambient modern python they never
fabricated and fail.

The cure is hermeticity: the subprocess ``PATH`` must contain *only* a
sandbox bin dir that the test fully controls. No ``/usr/bin``, no
``/bin``. The resolver + launcher + the fake-python shebangs still need a
handful of real coreutils, so we symlink those into the sandbox.

``#!/usr/bin/env bash`` shebangs resolve ``/usr/bin/env`` via the
absolute kernel path (independent of ``PATH``); ``env`` then looks up
``bash`` on ``PATH`` — which is why ``bash`` (and friends) must live in
the sandbox.
"""

from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path

# The only non-builtin binaries the scripts + fake-python shebangs invoke.
# ``command -v`` is a bash builtin; ``cd``/``pwd``/``printf``/``[``/``read``
# are builtins too, so they need no symlink.
_COREUTILS = ("bash", "env", "sh", "dirname", "mktemp", "mkdir", "mv", "rm", "cat")


def make_sandbox_bin(tmp_path: Path, *, name: str = "sandbox-bin") -> Path:
    """Create a hermetic bin dir seeded with the coreutils the scripts need.

    Returns the sandbox bin dir. Symlinks every resolvable coreutil from
    :data:`_COREUTILS` into it (names that resolve to ``None`` are
    skipped). Callers place their fabricated fake interpreters here too;
    because this dir is the *only* ``PATH`` entry, the resolver cannot see
    any ambient python.
    """
    sandbox = tmp_path / name
    sandbox.mkdir(parents=True, exist_ok=True)
    for tool in _COREUTILS:
        resolved = shutil.which(tool)
        if resolved is None:
            continue
        link = sandbox / tool
        if not link.exists():
            os.symlink(resolved, link)
    return sandbox


def hermetic_env(sandbox_bin: Path, **overrides: str) -> dict[str, str]:
    """Build a subprocess env whose ``PATH`` is the single sandbox bin dir.

    Inherits the parent environment, then forces ``PATH`` to exactly one
    entry — the sandbox — so no ambient ``/usr/bin`` python can leak.
    Extra keyword overrides (e.g. ``CLAUDE_PROJECT_DIR``) are applied last.
    """
    env = dict(os.environ)
    env["PATH"] = str(sandbox_bin)
    env.update(overrides)
    return env


def make_exe(path: Path, body: str) -> None:
    """Write ``body`` to ``path`` and mark it executable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
