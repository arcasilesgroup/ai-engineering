// tests/test-hygiene.spec.ts — a suite must leave the process and the tree as it found
// them. Two leaks made the serial suite non-deterministic: temp roots created under
// tests/ (left behind whenever a run is killed before afterAll), and a sandbox that
// deleted AI_ENG_HOME / PI_CODING_AGENT_DIR / GIT_CONFIG_GLOBAL instead of restoring
// them, so every suite after it ran against a different machine home.
//
// Both are observed from outside, in a child `bun test`: the tests/ directory is
// watched while the child runs, and a preloaded root afterAll records the env and cwd
// after every sandboxed suite.

import { afterEach, describe, expect, test } from "bun:test";
import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync, readdirSync, rmSync, watch, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, relative, sep } from "node:path";
import { SANDBOX_VARS } from "./fixtures/sandbox-env.ts";

const REPO = join(import.meta.dir, "..");
const TESTS = import.meta.dir;
const LEAK_PREFIXES = [".worktree-lifecycle-", ".dirfd-probe-"];
const roots: string[] = [];

afterEach(() => {
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

function tempDir(prefix: string): string {
  const dir = mkdtempSync(join(tmpdir(), prefix));
  roots.push(dir);
  return dir;
}

function childEnv(overrides: Record<string, string>): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = { ...process.env };
  for (const name of SANDBOX_VARS) delete env[name];
  return { ...env, ...overrides };
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

const isLeak = (name: string): boolean => LEAK_PREFIXES.some((prefix) => name.startsWith(prefix));

describe("test hygiene — no suite writes under tests/", () => {
  test(
    "running worktree-lifecycle.spec.ts leaves the tests/ listing unchanged and never creates a temp root there",
    async () => {
      const before = readdirSync(TESTS).sort();
      // Premise: the listing is clean before the child runs, or "unchanged" proves nothing.
      expect(before.filter(isLeak)).toEqual([]);

      // A temp root removed in afterAll still leaks whenever the run is killed first, so
      // its creation is the fault, not only what survives: watch every entry that appears.
      const seen: string[] = [];
      const watcher = watch(TESTS, (_event, name) => {
        if (typeof name === "string") seen.push(name);
      });
      let run: { status: number | null; output: string };
      try {
        run = await runBunTest(["tests/worktree-lifecycle.spec.ts"], childEnv({}));
      } finally {
        watcher.close();
      }

      expect(run.status, run.output).toBe(0);
      expect(seen.filter(isLeak)).toEqual([]);
      expect(readdirSync(TESTS).sort()).toEqual(before);
    },
    300_000,
  );
});

/** Every suite that assigns or deletes a sandbox variable — derived from the tree at run
 *  time, so a new sandboxed suite is checked the day it lands, not when someone adds it here. */
function sandboxedSuites(): string[] {
  const variable = `process\\.env(\\.|\\[["'])(${SANDBOX_VARS.join("|")})\\b(["']\\])?`;
  const assigns = new RegExp(`delete\\s+${variable}|${variable}\\s*=[^=]`);
  return readdirSync(TESTS, { recursive: true, encoding: "utf8" })
    .filter((path) => /\.(spec|test)\.ts$/.test(path) && !path.startsWith("fixtures"))
    .filter((path) => assigns.test(readFileSync(join(TESTS, path), "utf8")))
    .map((path) => `tests/${path.split(sep).join("/")}`)
    .sort();
}

describe("test hygiene — a sandboxed suite restores what it changed", () => {
  test(
    "after every suite that sets AI_ENG_HOME, PI_CODING_AGENT_DIR or GIT_CONFIG_GLOBAL, those variables and cwd hold their prior values",
    async () => {
      const suites = sandboxedSuites();
      // Premise: the derivation finds the suites this rule was written for.
      for (const known of ["tests/uninstall-command.spec.ts", "tests/doctor-command.spec.ts", "tests/config-command.spec.ts", "tests/init-command.spec.ts", "tests/update-command.spec.ts"]) {
        expect(suites).toContain(known);
      }
      const outer = tempDir("ai-eng-hygiene-");
      const report = join(outer, "report.jsonl");
      const priorHome = join(outer, "prior-home");
      const priorGitConfig = join(outer, "prior-gitconfig");
      writeFileSync(priorGitConfig, "");
      // PI_CODING_AGENT_DIR is left unset on purpose: unset must stay unset, never
      // become the string "undefined" or a leftover sandbox path.
      const env = childEnv({ AI_ENG_HOME: priorHome, GIT_CONFIG_GLOBAL: priorGitConfig, HYGIENE_REPORT: report });

      // One process, one suite after another — the serial run where a leak reaches the next suite.
      const run = await runBunTest(
        ["--parallel=1", "--preload", "./tests/preload.ts", "--preload", "./tests/fixtures/env-snapshot.preload.ts", ...suites],
        env,
      );
      expect(run.status, run.output).toBe(0);

      const lines = readFileSync(report, "utf8")
        .trim()
        .split("\n")
        .map((line) => JSON.parse(line) as { suite: string; phase: string; env: Record<string, string | null>; cwd: string })
        .map((line) => ({ ...line, suite: relative(REPO, line.suite).split(sep).join("/") }))
        // Stable sort: each suite's "before" stays ahead of its "after-suite".
        .sort((a, b) => a.suite.localeCompare(b.suite));
      // Every suite found the values this test handed the child — so none before it leaked —
      // and left them that way; one line pair per suite, so no probe can silently not fire.
      const handed = { env: { AI_ENG_HOME: priorHome, PI_CODING_AGENT_DIR: null, GIT_CONFIG_GLOBAL: priorGitConfig }, cwd: REPO };
      expect(lines).toEqual(suites.flatMap((suite) => [{ suite, phase: "before", ...handed }, { suite, phase: "after-suite", ...handed }]));
    },
    300_000,
  );
});
