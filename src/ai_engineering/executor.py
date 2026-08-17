"""The executor the capability manifest has been declaring at for fifteen capabilities.

`policy/capabilities.toml` declares read roots, write roots, an exec allowlist, network
hosts, secrets and a human gate for every mode of every capability. Until this file existed
none of it stopped anything: `capability.preflight` validated the declaration and then
returned `CAPABILITY_ENFORCEMENT_UNAVAILABLE`, and `doctor`'s assertion 23 said so out loud
because a declaration nobody enforces and nobody flags is the shape of a false green.

What was missing was never the check. It was somebody owning the operation. A decision that
is taken next to an operation rather than *by* it is advice, and advice is what every path
check in this repository would have been if the caller could still open the file itself.

So a `Sandbox` is the only way to perform the action. It names its own capability and mode
at construction, and every method re-decides at the moment of the operation against the real
resolved path or the real binary — not against the string it was handed. The two are
different whenever a symlink, a `..` or a race is involved, which is the entire attack.

What this does not close, and the honest edge of it: an action a *surface* performs is still
outside. Nothing here reads a running capability's identity out of somebody else's payload,
and no receipt has ever shown a surface sending one. This binds the framework's own actions.
That is a smaller claim than "capabilities are enforced" and it is the true one.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from ai_engineering import capability, imagery, intent

# Which action kinds a declared gate covers. `before_publish` is two kinds rather than one:
# publishing is a network call carrying a secret, and gating only the connection would let
# the token be read and stashed without anybody being asked.
GATES: dict[str, tuple[str, ...]] = {
    "never": (),
    "before_write": ("write",),
    "before_exec": ("exec",),
    "before_network": ("network",),
    "before_publish": ("network", "secret"),
}

HUMAN_GATE_UNCONFIRMED = (
    "CAPABILITY_HUMAN_GATE_UNCONFIRMED",
    "the declared human gate was not confirmed",
)
OUTSIDE_ROOT = ("CAPABILITY_PATH_OUTSIDE_ROOT", "the resolved path is outside the sandbox root")
NOT_A_REGULAR_FILE = ("CAPABILITY_PATH_NOT_REGULAR", "the path is not a regular file")
EXECUTABLE_UNRESOLVED = ("CAPABILITY_EXEC_UNRESOLVED", "the executable is not on this machine")
SECRET_ABSENT = ("CAPABILITY_SECRET_ABSENT", "the declared secret is not present in this process")

CORPUS = "capability-decisions.jsonl"


class Refused(Exception):
    """One refusal, carrying the machine result the caller would otherwise have to build.

    An exception rather than a returned pair because the alternative is a caller that
    forgets to look. `sandbox.write(...)` returning a `Validation` nobody reads is a write
    that silently did not happen, which is worse than the ungoverned write it replaced.
    """

    def __init__(self, result: intent.Validation) -> None:
        self.result = result
        super().__init__(result.reason)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


class Sandbox:
    """One capability, one mode, one root, and the only door to the operation.

    `confirm` is asked once per gated action and is asked *before* the operation, never
    after — a gate consulted afterwards records an opinion about something that already
    happened. `None` means no human is present, which is a refusal rather than a pass,
    because the manifest declaring a gate is the manifest saying somebody must be asked.
    """

    def __init__(
        self,
        capability_id: str,
        mode_id: str,
        root: Path,
        *,
        confirm: Callable[[capability.Action], bool] | None = None,
        corpus: Path | None = None,
    ) -> None:
        self.capability_id = capability_id
        self.mode_id = mode_id
        self.root = Path(root).resolve()
        self._confirm = confirm
        self._corpus = corpus
        self._mode: dict | None = None

    # -- what `capability.preflight` asks of an executor ---------------------------------

    def confirmed(self, action: capability.Action) -> bool:
        """Whether a human said yes to this exact action. Never cached: two writes are two
        decisions, and a remembered yes is a gate that opens once and stays open."""

        return bool(self._confirm and self._confirm(action))

    def owns(self, capability_id: str, mode_id: str, action: capability.Action) -> bool:
        """Whether *this* sandbox is about to perform *this* action under *this* identity.

        The identity comparison is not a formality. A sandbox built for `ai-note` must not
        be able to launder an `ai-ship` action through the same preflight call, and without
        this it could: preflight reads the declaration from the ids it is given.
        """

        if capability_id != self.capability_id or mode_id != self.mode_id:
            return False
        if action.kind in ("read", "write"):
            return self._resolved(action.path, writing=action.kind == "write") is not None
        if action.kind == "exec":
            return bool(action.argv) and shutil.which(action.argv[0]) is not None
        return action.kind in ("network", "secret")

    # -- the operations ------------------------------------------------------------------

    def read(self, relative: str) -> bytes:
        """Read one file, after proving the bytes come from inside the root."""

        where = self._decide(capability.Action.read(relative))
        try:
            with open(where, "rb", opener=self._opener(os.O_RDONLY)) as handle:
                return handle.read()
        except OSError as error:
            raise self._refuse(capability.Action.read(relative), NOT_A_REGULAR_FILE) from error

    def write(self, relative: str, payload: bytes) -> Path:
        """Write one file, never through a symlink, never outside the root, and — when the
        bytes are an image — without the metadata that travelled beside the picture.

        `EP-254` asks that imagery output lose its metadata and be sanitised when it is
        vector. Doing it here rather than in the caller is the difference between a control
        and an instruction: a skill file telling somebody to strip EXIF is a control that
        runs when they remember, and this one runs because there is no other way to write.

        `imagery.stripped` returns anything it cannot read unchanged, so a text file, a
        JSON payload or a format nobody taught it about passes through untouched.
        """

        action = capability.Action.write(relative)
        where = self._decide(action)
        payload = imagery.stripped(payload)
        try:
            where.parent.mkdir(parents=True, exist_ok=True)
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            with open(where, "wb", opener=self._opener(flags)) as handle:
                handle.write(payload)
        except OSError as error:
            raise self._refuse(action, NOT_A_REGULAR_FILE) from error
        return where

    def run(self, *argv: str, timeout: float = 60.0) -> subprocess.CompletedProcess[str]:
        """Run one allowed executable, with no shell and with the root as the directory.

        `shell=False` is what makes the allowlist mean anything: through a shell, `argv[0]`
        is a string somebody else parses and the entry that was checked is not the program
        that runs.
        """

        action = capability.Action.execute(*argv)
        self._decide(action)
        binary = shutil.which(argv[0])
        if binary is None:
            raise self._refuse(action, EXECUTABLE_UNRESOLVED)
        # Allowlisted argv, no shell, and a binary resolved to an absolute path before it
        # is run. Those three together are why the entry that was checked is the program
        # that starts.
        return subprocess.run(
            [binary, *argv[1:]],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    def connect(self, protocol: str, host: str, purpose: str) -> str:
        """Return the one origin this mode may talk to, having proved it is declared.

        No request is made here. This module owns the decision, not an HTTP client, and a
        fetch inside the sandbox would put a network stack behind the governance boundary
        for no gain: the caller still has to be handed something.
        """

        action = capability.Action.connect(protocol, host, purpose)
        self._decide(action)
        return f"{protocol}://{host}"

    def secret(self, name: str) -> str:
        """Hand back one declared secret from this process's environment, or refuse.

        The value never lands in the corpus, the receipt or an exception message — only its
        name does. A refusal that quoted the value would be a governance record that leaks
        exactly what it governs.
        """

        action = capability.Action.use_secret(name)
        self._decide(action)
        value = os.environ.get(name.replace(".", "_").replace("-", "_").upper(), "")
        if not value:
            raise self._refuse(action, SECRET_ABSENT)
        return value

    # -- the one decision every operation goes through -----------------------------------

    def _decide(self, action: capability.Action) -> Path:
        result = capability.preflight(self.capability_id, self.mode_id, action, executor=self)
        if result.outcome != "PASS":
            raise self._refuse(action, (result.code, result.reason))
        self._record(action, allowed=True, code="")
        if action.kind in ("read", "write"):
            resolved = self._resolved(action.path, writing=action.kind == "write")
            # `owns` already resolved this once and preflight would not have passed had it
            # failed. Kept because the two calls are separated by a `PASS` in another
            # module, and a path that stopped resolving in between is exactly the race
            # this class exists to lose safely.
            if resolved is None:
                raise self._refuse(action, OUTSIDE_ROOT)
            return resolved
        return self.root

    def _resolved(self, relative: str, *, writing: bool) -> Path | None:
        """The real path, or nothing at all.

        `resolve()` follows every link before the comparison, so a declared root containing
        a symlink out of the tree is refused here rather than at open time. Reading also
        requires a regular file that exists; writing does not, because the file is what the
        operation is about to create — but its parent must already resolve inside the root,
        or the write walks out through a linked directory.
        """

        try:
            candidate = (self.root / relative).resolve()
            reference = candidate if not writing else candidate.parent
            reference.relative_to(self.root)
        except (OSError, ValueError):
            return None
        if writing:
            return candidate if not candidate.is_symlink() else None
        try:
            details = candidate.lstat()
        except OSError:
            return None
        return candidate if stat.S_ISREG(details.st_mode) else None

    def _opener(self, flags: int) -> Callable[[str, int], int]:
        def opener(path: str, _flags: int) -> int:
            return os.open(path, flags | getattr(os, "O_NOFOLLOW", 0), 0o644)

        return opener

    # -- the corpus, which is what makes a declared proof id evidence ---------------------

    def _refuse(self, action: capability.Action, result: tuple[str, str]) -> Refused:
        self._record(action, allowed=False, code=result[0])
        return Refused(intent.Validation("INCOMPLETE", *result))

    def _record(self, action: capability.Action, *, allowed: bool, code: str) -> None:
        """Append one decision under the proof id the manifest declared for it.

        `proof_requirements.allow` and `.deny` were ids naming nothing. A captured decision
        under that id is what turns a declaration into evidence somebody can count, which is
        the whole difference between this file and the manifest that preceded it.

        Failing to write the corpus never blocks the operation and never turns a refusal
        into a pass: it is a record of a decision already taken. That is the one fail-open
        in this module and it is here on purpose, because a full disk must not become a way
        to make a governed action unavailable.
        """

        if self._corpus is None:
            return
        mode = self._declared_mode()
        proof = (mode or {}).get("proof_requirements", {})
        declared = proof.get("allow" if allowed else "deny") or [""]
        line = {
            "ts": _now(),
            "capability": self.capability_id,
            "mode": self.mode_id,
            "kind": action.kind,
            "allowed": allowed,
            "code": code,
            "proof_id": declared[0],
        }
        try:
            self._corpus.parent.mkdir(parents=True, exist_ok=True)
            with open(self._corpus, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(line, sort_keys=True) + "\n")
        except OSError:
            return

    def _declared_mode(self) -> dict | None:
        if self._mode is None:
            try:
                manifest = capability._validated(None)
            except Exception:
                return None
            for entry in manifest["capabilities"]:
                if entry["id"] != self.capability_id:
                    continue
                for mode in entry["modes"]:
                    if mode["id"] == self.mode_id:
                        self._mode = mode
        return self._mode
