// The mutation gate's thresholds are the contract CI enforces. break used to sit
// at 85 while the measured incremental score was 58.51, so every governance pull
// request was red and the red meant nothing.
import { spawnSync } from "node:child_process";
import { describe, expect, test } from "bun:test";

function mutationThresholds(): { high: number; low: number; break: number } {
  const run = spawnSync(
    process.execPath,
    ["-e", "const config = await import('./stryker.conf.mjs'); console.log(JSON.stringify(config.default.thresholds));"],
    { cwd: new URL("..", import.meta.url).pathname, encoding: "utf8" },
  );
  if (run.status !== 0) throw new Error(run.stderr || "could not load stryker.conf.mjs");
  return JSON.parse(run.stdout) as { high: number; low: number; break: number };
}

describe("mutation thresholds", () => {
  test("break is the measured incremental floor, under the clean score and under the old unreachable 85", () => {
    expect(mutationThresholds()).toEqual({ high: 90, low: 58, break: 58 });
  });
});
