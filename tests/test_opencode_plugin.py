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


def _drive(tmp_path: Path, python: str, chain: str) -> list[list[str]]:
    """Run the plugin the way OpenCode would, with its placeholders filled as the
    installer fills them, and report what it did with two tool calls."""

    tmp_path.mkdir(parents=True, exist_ok=True)
    materialised = tmp_path / "opencode.ts"
    materialised.write_text(
        PLUGIN.read_text(encoding="utf-8")
        .replace('"__PYTHON__"', json.dumps(python))
        .replace('"__CHAIN__"', json.dumps(chain)),
        encoding="utf-8",
    )
    driver = tmp_path / "drive.mts"
    driver.write_text(DRIVER.replace("PLUGIN_PATH", f"./{materialised.name}"), encoding="utf-8")
    # Its own home and its own session, because the loop guard counts repeats and this
    # test would otherwise deny its own ordinary call on the sixth run — and because a test
    # that writes into the operator's real `~/.ai-engineering` has already happened once in
    # this repository's history and is not going to happen twice.
    house = tmp_path / "house"
    house.mkdir(parents=True, exist_ok=True)
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
    return json.loads(done.stdout.strip().splitlines()[-1])


@pytest.mark.skipif(
    shutil.which("node") is None and not os.environ.get("AI_ENG_REQUIRE_NODE"),
    reason="no node here to run the plugin with",
)
def test_the_plugin_denies_when_it_cannot_run_its_own_guard(tmp_path):
    """Two calls, twice: once with a working dispatcher and once with none.

    The second is the whole point. Before this, a plugin that could not spawn its guard
    returned as if the guard had approved the call — and the person would have seen nothing
    at all, because that is what allowing looks like."""

    chain = str(ROOT / "hooks" / "chain.py")

    # A dispatcher that works: the denial is a policy denial and the ordinary call passes.
    working = _drive(tmp_path / "working", sys.executable, chain)
    named = {row[0]: row for row in working}
    assert named["policy"][1] == "denied"
    assert "no_verify_guard" in named["policy"][2]
    assert named["ordinary"][1] == "allowed"

    # A dispatcher that cannot be spawned at all. Both calls must be refused, and the
    # message must say it was the install and not the policy, because they need different
    # repairs and telling a person the wrong one costs them an afternoon.
    broken = _drive(tmp_path / "broken", "/definitely/not/an/interpreter", chain)
    for row in broken:
        assert row[1] == "denied", row
        assert "the guard could not run" in row[2], row
        assert "ai-eng doctor" in row[2], row
