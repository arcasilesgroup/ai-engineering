// tests/test-hygiene.spec.ts — the default preload guards every suite's sandbox state
// and watches the lifecycle suite's temp roots without rerunning that suite here.

import { describe, expect, test } from "bun:test";
import { spawn } from "node:child_process";
import { mkdirSync, readdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { SANDBOX_VARS } from "./fixtures/sandbox-env.ts";

const REPO = join(import.meta.dir, "..");
const TESTS = import.meta.dir;
const LEAK_PREFIXES = [".worktree-lifecycle-", ".dirfd-probe-"];

function childEnv(overrides: Record<string, string>): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = { ...process.env };
  for (const name of SANDBOX_VARS) delete env[name];
  return { ...env, ...overrides };
}

if (process.env["HYGIENE_LEAK_PROBE"] === "1") {
  test("intentional hygiene leak probe", () => {
    process.env["AI_ENG_HOME"] = "leaked";
    process.chdir(TESTS);
    mkdirSync(join(TESTS, ".worktree-lifecycle-probe"));
  });
}

function runBunTest(args: string[], env: NodeJS.ProcessEnv): Promise<{ status: number | null; output: string }> {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, ["test", ...args], { cwd: REPO, env, stdio: ["ignore", "pipe", "pipe"] });
    let output = "";
    child.stdout.on("data", (chunk: Buffer) => (output += chunk.toString()));
    child.stderr.on("data", (chunk: Buffer) => (output += chunk.toString()));
    child.on("close", (status) => resolve({ status, output }));
  });
}

describe("test hygiene — the default preload guards suite state", () => {
  test(
    "the preload rejects environment, cwd and temp-root leaks",
    async () => {
      const before = readdirSync(TESTS).sort();
      expect(before.filter((name) => LEAK_PREFIXES.some((prefix) => name.startsWith(prefix)))).toEqual([]);
      const leakedRoot = join(TESTS, ".worktree-lifecycle-probe");
      let run: { status: number | null; output: string };
      try {
        run = await runBunTest(
          ["--test-name-pattern", "intentional hygiene leak probe", "tests/test-hygiene.spec.ts"],
          childEnv({ AI_ENG_HOME: REPO, HYGIENE_LEAK_PROBE: "1" }),
        );
        expect(run.status).not.toBe(0);
        expect(run.output).toContain(
          "test suite leaked sandbox state: AI_ENG_HOME, cwd, temporary paths under tests/",
        );
      } finally {
        rmSync(leakedRoot, { recursive: true, force: true });
      }
      expect(readdirSync(TESTS).sort()).toEqual(before);
    },
  );
});
