// The OpenCode adapter. One file, and it calls the same dispatcher every other surface
// calls, so no rule has a second implementation in here.
//
// A throw inside tool.execute.before kills the tool call. It does not kill the turn: the
// model sees a per-tool error, keeps going, and will try to route around it — in the live
// test it asked the user to switch off "whatever is intercepting file access". Claude
// Code's deny behaves the same way, so parity holds, but it is not a turn-level stop.
// The message is therefore written as an instruction, because the model is shown it.
//
// The loader wraps each plugin so a shape mismatch produces no error, no warning and no
// log, and a v2 plugin API with an incompatible module shape already ships beside v1. So
// this writes a heartbeat on load and `ai-eng doctor` asserts it. Without that, the day
// the v1 shape is dropped, enforcement stops here and nothing says so.
//
// Not weightless on disk: the moment any local plugin file exists, OpenCode creates a
// package.json, a lockfile and a node_modules of about 61 MB, and the first run pays an
// install. Its own generated ignore file keeps that out of git, so the committed surface
// really is one file — but "leaves nothing behind" would be a lie.
//
// The three placeholders are absolute paths written by `ai-eng init`. No tilde is ever
// written into a config value: not one surface documents expanding it.

import { spawnSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";

const PYTHON = "__PYTHON__";
const CHAIN = "__CHAIN__";
const BEAT = "__BEAT__";

function heartbeat() {
  mkdirSync(dirname(BEAT), { recursive: true });
  writeFileSync(BEAT, new Date().toISOString());
}

export const AiEngineering = async ({ client, $ }) => {
  heartbeat();
  return {
    "tool.execute.before": async (input, output) => {
      const payload = JSON.stringify({
        hook_event_name: "PreToolUse",
        tool_name: input.tool,
        tool_input: output.args ?? {},
        session_id: input.sessionID ?? "",
      });
      const result = spawnSync(PYTHON, [CHAIN, "PreToolUse"], {
        input: payload,
        timeout: 5000,
      });
      if (result.status === 2) {
        throw new Error(
          result.stderr.toString().trim() || "denied by ai-engineering",
        );
      }
    },
  };
};
