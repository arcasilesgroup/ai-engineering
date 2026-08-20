"""The OpenCode plugin's deny path, executed rather than compiled.

`just typecheck` proves this file compiles. Nothing proved it denies, and spec 010 wrote
the consequence down twice and left it for this wave: the plugin checked `status === 2`, so
every way the dispatcher could fail to run at all — a missing interpreter, a deleted
worktree, a five-second timeout — produced `status === null` and the call went through as
if a guard had considered it and approved it.

A guard that allows because it could not run is the root pattern this product exists to
cure, and it was sitting in the one surface file no Python test could reach.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "surfaces" / "opencode.ts"

DRIVER = """
import { AiEngineering } from "PLUGIN_PATH";

const hooks = await AiEngineering();
const before = hooks["tool.execute.before"];
const answers = [];
for (const [name, args] of [
  ["policy", { command: "git commit --no-verify -m x" }],
  ["ordinary", { command: `echo ${process.env.AI_ENG_ONCE}` }],
]) {
  try {
    await before({ tool: "Bash", sessionID: process.env.AI_ENG_ONCE }, { args });
    answers.push([name, "allowed", ""]);
  } catch (why) {
    answers.push([name, "denied", String(why.message)]);
  }
}
console.log(JSON.stringify(answers));
"""


def _drive(tmp_path: Path, python: str, chain: str, monkeypatch) -> list[list[str]]:
    """Run the plugin the way OpenCode would, with its placeholders filled as the
    installer fills them, and report what it did with two tool calls."""

    tmp_path.mkdir(parents=True, exist_ok=True)
    # Written by the installer, not by a copy of it. The test used to substitute the
    # placeholders itself, correctly escaped, while the installer dropped raw paths inside
    # the quotes — identical on this machine and mangled on Windows, which is exactly the
    # platform the test could never see. Calling the real writer makes parity structural
    # instead of remembered.
    from ai_engineering import wiring

    # The home is redirected BEFORE the plugin is written, not only for the child. The
    # first version set it afterwards and only in the subprocess environment, so
    # `__BEAT__` baked an absolute path to the operator's real home and every run wrote
    # their live OpenCode heartbeat — the signal `doctor` reads to decide the plugin is
    # loaded. A suite that forges the evidence a diagnostic trusts is worse than one that
    # tests nothing, and this file's own docstring promised it did not.
    house = tmp_path / "house"
    house.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AI_ENGINEERING_HOME", str(house / ".ai-engineering"))
    monkeypatch.setenv("HOME", str(house))
    monkeypatch.setenv("USERPROFILE", str(house))
    # `paths.load` inserts the hooks directory at the front of `sys.path` and never removes
    # it, and monkeypatch does not restore `sys.path` — two stub `chain.py` files were being
    # left there, ahead of the real one, for every test that ran afterwards.
    monkeypatch.setattr(sys, "path", list(sys.path))

    materialised = tmp_path / "opencode.ts"
    monkeypatch.setattr(wiring.sys, "executable", python)
    monkeypatch.setattr(wiring.paths, "hooks", lambda: Path(chain).parent)
    wiring.ts_opencode(materialised)
    assert str(house) in materialised.read_text(encoding="utf-8"), (
        "the plugin was written pointing at a home this test does not own"
    )
    driver = tmp_path / "drive.mts"
    driver.write_text(DRIVER.replace("PLUGIN_PATH", f"./{materialised.name}"), encoding="utf-8")
    # Its own home and its own session, because the loop guard counts repeats and this
    # test would otherwise deny its own ordinary call on the sixth run — and because a test
    # that writes into the operator's real `~/.ai-engineering` has already happened once in
    # this repository's history and is not going to happen twice.
    once = f"probe-{uuid4().hex}"
    done = subprocess.run(
        ["node", "--experimental-strip-types", str(driver)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=120,
        env={
            **os.environ,
            "HOME": str(house),
            "USERPROFILE": str(house),
            "AI_ENGINEERING_HOME": str(house / ".ai-engineering"),
            "AI_ENG_ONCE": once,
        },
    )
    if done.returncode != 0:
        # A skip is the honest answer on a machine whose node cannot strip types — and it
        # is the wrong answer in CI, where a silent skip means this proof quietly stopped
        # running and nothing said so. The job that owns the TypeScript surface sets the
        # marker, and there a skip is a failure.
        excuse = f"this node cannot run the plugin as OpenCode does: {done.stderr[-200:]}"
        if os.environ.get("AI_ENG_REQUIRE_NODE"):
            raise AssertionError(excuse)
        pytest.skip(excuse)
    # The heartbeat, checked on every leg. OpenCode's loader swallows a shape mismatch with
    # no error, no warning and no log, so this file is the only evidence the plugin was ever
    # loaded — and `ai-eng doctor` reads it to decide whether this surface can enforce at
    # all. Nothing asserted it existed, so a mutant that stopped writing it, or wrote it
    # somewhere nobody reads, survived: the guard would keep denying while the diagnostic
    # reported the surface as never loaded.
    beat = house / ".ai-engineering" / "cache" / "opencode-heartbeat"
    assert beat.is_file(), "the plugin loaded and left no evidence that it had"
    assert beat.read_text(encoding="utf-8").startswith("20"), beat.read_text(encoding="utf-8")
    return json.loads(done.stdout.strip().splitlines()[-1])


@pytest.mark.skipif(
    shutil.which("node") is None and not os.environ.get("AI_ENG_REQUIRE_NODE"),
    reason="no node here to run the plugin with",
)
def test_the_plugin_denies_when_it_cannot_run_its_own_guard(tmp_path, monkeypatch):
    """Two calls, twice: once with a working dispatcher and once with none.

    The second is the whole point. Before this, a plugin that could not spawn its guard
    returned as if the guard had approved the call — and the person would have seen nothing
    at all, because that is what allowing looks like."""

    chain = str(ROOT / "hooks" / "chain.py")
    # Held before anything is patched. `wiring.sys` IS `sys`, so setting
    # `wiring.sys.executable` sets it globally — the third leg below was silently reusing
    # the broken interpreter the second leg installed, and would have passed for the wrong
    # reason if its message had happened to match.
    real = sys.executable

    # A dispatcher that works: the denial is a policy denial and the ordinary call passes.
    working = _drive(tmp_path / "working", real, chain, monkeypatch)
    named = {row[0]: row for row in working}
    assert named["policy"][1] == "denied"
    assert "no_verify_guard" in named["policy"][2]
    assert named["ordinary"][1] == "allowed"

    # A dispatcher that cannot be spawned at all. Both calls must be refused, and the
    # message must say it was the install and not the policy, because they need different
    # repairs and telling a person the wrong one costs them an afternoon.
    broken = _drive(tmp_path / "broken", "/definitely/not/an/interpreter", chain, monkeypatch)
    for row in broken:
        assert row[1] == "denied", row
        assert "the guard could not run" in row[2], row
        assert "ai-eng doctor" in row[2], row
        # And it says which failure, not just that there was one. "could not run (exit
        # null)" sends a person looking for an exit code that does not exist; ENOENT sends
        # them to the path.
        assert "ENOENT" in row[2], row

    # And a dispatcher that starts and then dies. This is the case the shipped logic was
    # narrowed away from and the plan never was: exit 1 is CPython's uncaught-exception
    # status, so it means no guard decided, and allowing there let `--no-verify` through
    # whenever the interpreter could start and the dispatcher could not run. Nothing in the
    # suite exercised a status outside {0, 2}, so the width was untested in both directions.
    died = tmp_path / "died"
    died.mkdir(parents=True, exist_ok=True)
    (died / "chain.py").write_text("import sys\nsys.exit(1)\n", encoding="utf-8")
    for row in _drive(died, real, str(died / "chain.py"), monkeypatch):
        assert row[1] == "denied", row
        assert "the guard could not run" in row[2], row
        assert "exit 1" in row[2], row

    # Exit 2 without a spoken decision. CPython exits 2 when it cannot open the script at
    # all, which is what a moved or rebuilt install looks like — so the number alone cannot
    # tell a policy denial from a broken one, and telling a person the wrong one sends them
    # to argue with a rule instead of repairing their install.
    mute = tmp_path / "mute"
    mute.mkdir(parents=True, exist_ok=True)
    (mute / "chain.py").write_text("import sys\nsys.exit(2)\n", encoding="utf-8")
    for row in _drive(mute, real, str(mute / "chain.py"), monkeypatch):
        assert row[1] == "denied", row
        assert "the guard could not run" in row[2], f"an exit 2 that decided nothing: {row}"

    # What the guard is actually told, and which stream the person is shown. Both were
    # unmeasured: the real dispatcher writes the guard's name to *both* streams, so the one
    # assertion above passed whichever one the plugin read, and nothing at all looked at the
    # payload — a plugin that sent an empty tool name or dropped the session the loop guard
    # counts repeats by would have gone on denying the one call this test makes and stopped
    # protecting every call after it.
    echo = tmp_path / "echo"
    echo.mkdir(parents=True, exist_ok=True)
    (echo / "chain.py").write_text(
        'import sys\nprint(\'{"hookSpecificOutput": {"permission": "deny"}}\')\n'
        'sys.stderr.write("PAYLOAD " + sys.stdin.read())\nsys.exit(2)\n',
        encoding="utf-8",
    )
    for row in _drive(echo, real, str(echo / "chain.py"), monkeypatch):
        assert row[1] == "denied", row
        # The message is the guard's, from stderr. Reading stdout instead would show the
        # person the machine-readable decision the *other* surfaces consume.
        assert row[2].startswith("PAYLOAD "), f"this came from the wrong stream: {row}"
        assert "hookSpecificOutput" not in row[2], row
        sent = json.loads(row[2].removeprefix("PAYLOAD "))
        assert sent["hook_event_name"] == "PreToolUse", sent
        assert sent["tool_name"] == "Bash", sent
        assert sent["session_id"].startswith("probe-"), sent
        assert sent["tool_input"], f"the guard was asked about a call with no arguments: {sent}"


def test_the_receipt_runner_refuses_rather_than_writing_when_nothing_denied(tmp_path, monkeypatch):
    """`EP-210`'s runner, and the only property that makes its output evidence.

    `tests/surface_receipt.py` writes `.ai/receipts/surface/opencode.enforcement.json`, which
    `report surfaces` then reads as a proven surface. So the interesting cases are the ones
    where it must write nothing: a plugin that allowed the call, and a plugin that denied
    without saying which guard decided.

    The second is not pedantry. A denial nobody can attribute is evidence that something said
    no, and the receipt claims something narrower — that *this framework's* control ran. A
    runner that accepted any refusal would turn a crash into a proof.
    """

    import surface_receipt

    # Three receipts since `EP-199`, and the refusal has to cover all three: a run that wrote
    # discovery and invocation and then declined to write enforcement would leave two thirds
    # of a proven surface behind, which reads better than the nothing it earned.
    states = ("discovery", "invocation", "enforcement")
    receipts = {one: surface_receipt.RECEIPTS / f"opencode.{one}.json" for one in states}
    before = {one: (path.read_bytes() if path.exists() else None) for one, path in receipts.items()}
    monkeypatch.setattr(surface_receipt.shutil, "which", lambda name: "/usr/bin/node")

    def answered(said: str, denied: bool) -> dict:
        return {"loaded": True, "invoked": True, "denied": denied, "plugin_digest": "sha256:x"}

    try:
        for said, denied, expected, why in (
            ("it went through", False, 1, "allowed"),
            ("something refused and said nothing about itself", True, 1, "unattributed"),
            ("[no_verify_guard] BLOCKED: ...", True, 0, "attributed"),
        ):
            monkeypatch.setattr(
                surface_receipt,
                "drive",
                lambda area, _s=said, _d=denied: (answered(_s, _d), _s),
            )
            for path in receipts.values():
                path.unlink(missing_ok=True)
            assert surface_receipt.main(["opencode"]) == expected, why
            for one, path in receipts.items():
                assert path.exists() is (expected == 0), f"{why}: {one}"
    finally:
        for one, path in receipts.items():
            if before[one] is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(before[one])


def test_a_machine_without_node_says_so_and_does_not_write_a_receipt(monkeypatch):
    """Absence is not a pass, and it is not a failure either. A machine with no node has
    proved nothing about this surface — the run says so, exits zero because nothing is
    broken, and leaves `report surfaces` reading the row as unproven, which it is."""

    import surface_receipt

    receipt = surface_receipt.RECEIPTS / "opencode.enforcement.json"
    before = receipt.read_bytes() if receipt.exists() else None
    receipt.unlink(missing_ok=True)
    monkeypatch.setattr(surface_receipt.shutil, "which", lambda name: None)

    try:
        assert surface_receipt.main(["opencode"]) == 0
        assert not receipt.exists(), "a machine with no node wrote a receipt anyway"
    finally:
        if before is not None:
            receipt.write_bytes(before)
