"""Drive the OpenCode plugin through a real denial and write the receipt that proves it.

`EP-210` asks for a per-surface pinned version and an executed denial on one surface, and its
note says the thing worth acting on: *buildable rather than blocked, because this surface is
not one of the ones that needs a live editor*. OpenCode's adapter is a plugin this repository
ships, so nothing here waits on somebody else's software launching.

Until now the only executed denial receipt in the tree came out of `install-matrix.yml`,
which means the one surface that could be proved was the one CI happened to prove, and
`report surfaces` read every other row as unproven whether or not it was provable.

This is a runner rather than a pytest case on purpose, and the adversarial suite is the
precedent. A receipt is evidence about a machine, produced by something that ran on it; a
test writing one as a side effect would be a test mutating the tree, and worse, a receipt
whose provenance is "the suite happened to pass" rather than "this denial happened".

`tests/test_opencode_plugin.py` proves the plugin's behaviour across five dispatcher states
and is the deeper check. This proves one thing that file cannot: that a denial happened on
*this* machine, recently, and left a record another command can read.

It refuses rather than writes when node is absent, when the plugin does not deny, or when the
denial does not name the guard that made it. A receipt over a run that did not deny is the
exact artefact this product exists to prevent.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

ADAPTER = ROOT / "policy" / "adapters" / "opencode.adapter.json"
RECEIPTS = ROOT / ".ai" / "receipts" / "surface"
SCHEMA = "urn:ai-engineering:check-evidence:1"

# A day. The same bound `install-matrix.yml` writes for claude-code, and for the same reason:
# a denial that executed a week ago says nothing about the plugin as it is now.
MAX_AGE = 86_400

# The call the guard must refuse. `--no-verify` is what `no_verify_guard` exists for and what
# rule 3 names, so a surface that lets it through has failed at the thing it is for.
DENIED = "git commit --no-verify -m x"

# One run, three answers. `EP-199` asks that load and invoke be executed states in CI and not
# only install, deny and doctor — and this driver already did all three and reported one. The
# module resolving and exporting is discovery; the registration contract handing back the hook
# the surface would call is invocation; the hook refusing is enforcement. Reporting only the
# last made two states that had genuinely executed read as unproven, which is the same false
# reading as claiming them, with the sign reversed.
HOOK = "tool.execute.before"

DRIVER = """
import { AiEngineering } from "PLUGIN_PATH";

const hooks = await AiEngineering();
const invoked = typeof hooks?.["tool.execute.before"] === "function";
try {
  await hooks["tool.execute.before"](
    { tool: "Bash", sessionID: process.env.AI_ENG_ONCE },
    { args: { command: process.env.AI_ENG_COMMAND } },
  );
  console.log(JSON.stringify({ loaded: true, invoked, denied: false, said: "" }));
} catch (why) {
  console.log(JSON.stringify({ loaded: true, invoked, denied: true, said: String(why.message) }));
}
"""


def stamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def digest(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def drive(area: Path) -> tuple[dict, str]:
    """Run the plugin the way OpenCode runs it, in a home this run owns.

    The plugin is materialised by the installer rather than by a copy of it: the shipped
    file carries three placeholders, and a runner that filled them itself would be proving
    its own substitution rather than the one a person gets. Its own home and its own session
    id, because the heartbeat and the repeat counter are both real side effects and neither
    belongs in the operator's live installation.
    """

    from ai_engineering import wiring

    house = area / "house"
    house.mkdir(parents=True, exist_ok=True)
    environment = {
        **os.environ,
        "HOME": str(house),
        "USERPROFILE": str(house),
        "AI_ENGINEERING_HOME": str(house / ".ai-engineering"),
        "AI_ENG_ONCE": f"receipt-{uuid4().hex}",
        "AI_ENG_COMMAND": DENIED,
    }
    previous = {key: os.environ.get(key) for key in ("HOME", "USERPROFILE", "AI_ENGINEERING_HOME")}
    os.environ.update({key: environment[key] for key in previous})
    try:
        plugin = area / "opencode.ts"
        wiring.ts_opencode(plugin)
        body = plugin.read_text(encoding="utf-8")
        if str(house) not in body:
            return {}, "the plugin was written pointing at a home this run does not own"
        # The bytes that resolved, taken here because the area is removed before the receipts
        # are written and a digest of a file that no longer exists is a digest of nothing.
        resolved = digest(body.encode())
        driver = area / "drive.mts"
        driver.write_text(DRIVER.replace("PLUGIN_PATH", f"./{plugin.name}"), encoding="utf-8")
        done = subprocess.run(  # the driver is written above, from a literal in this file
            [shutil.which("node") or "node", "--experimental-strip-types", str(driver)],
            capture_output=True,
            text=True,
            cwd=str(area),
            timeout=180,
            env=environment,
            check=False,
        )
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    if done.returncode != 0:
        return {}, f"this node cannot run the plugin as OpenCode does: {done.stderr[-200:]}"
    try:
        answer = json.loads(done.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError):
        return {}, f"the driver printed nothing readable: {done.stdout.strip()[:200]}"
    answer["plugin_digest"] = resolved
    return answer, str(answer.get("said", ""))


def main(argv: list[str]) -> int:
    if shutil.which("node") is None:
        # Not a failure and not a receipt. A machine without node has proved nothing about
        # this surface, and saying so is what the three states are for.
        print("  SKIPPED: no node here, so the OpenCode plugin cannot be executed.")
        return 0

    declared = json.loads(ADAPTER.read_text(encoding="utf-8"))
    required, version = declared["proof"]["receipt_id"], declared["adapter_version"]

    started = stamp()
    with tempfile.TemporaryDirectory() as area:
        answered, said = drive(Path(area))
    finished = stamp()

    if not answered.get("denied"):
        print(f"  FAIL: the OpenCode plugin did not deny `{DENIED}`. It said: {said[:160]}")
        print("  No receipt written. A receipt over a run that did not deny is the artefact")
        print("  this product exists to prevent.")
        return 1
    if "no_verify_guard" not in said:
        print(f"  INCOMPLETE: it denied and did not name the guard that decided: {said[:160]}")
        print("  No receipt written. A denial nobody can attribute is not evidence about a")
        print("  control; it is evidence that something said no.")
        return 1

    RECEIPTS.mkdir(parents=True, exist_ok=True)

    # Three receipts from one run, because one run answered three questions. Each carries the
    # digest of the thing that actually proved it, so they are not three copies of one fact:
    # discovery is the plugin bytes that resolved, invocation is the hook name the surface's
    # own registration contract handed back, enforcement is what the guard said.
    proved = {
        "discovery": (answered["plugin_digest"], "the shipped plugin resolved and exported"),
        "invocation": (digest(HOOK.encode()), f"the contract returned {HOOK}"),
        "enforcement": (digest(said.encode()), "the guard denied and named itself"),
    }
    written = []
    for state, (artifact, why) in proved.items():
        where = RECEIPTS / f"opencode.{state}.json"
        where.write_text(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "schema_version": "1",
                    "kind": "automated",
                    # Read from the adapter rather than written here, which is what makes this
                    # evidence rather than a self-report: the id is a requirement the receipt
                    # did not get to choose, and `surface.adapter_proof` compares the two.
                    # Only enforcement has one; the other two keep this module's convention,
                    # and `surface.py` says which claim each of them is making.
                    "id": required if state == "enforcement" else f"opencode.{state}",
                    "applicability": "applicable",
                    "command": "python tests/surface_receipt.py opencode",
                    "tool_version": f"opencode-adapter {version}",
                    "input_digest": digest(DENIED.encode()),
                    "artifact_digest": artifact,
                    "started_at": started,
                    "finished_at": finished,
                    "max_age_seconds": MAX_AGE,
                    "outcome": "PASS",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        written.append((state, why, where))

    print(f"  RAN surfaces=1  opencode denied `{DENIED}`")
    print(f"  it named: {said.strip()[:100]}")
    for state, why, where in written:
        print(f"    {state:12} {why} — {where.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":  # pragma: no cover — the entry point, exercised by the gate
    sys.exit(main(sys.argv[1:]))
