// tests/check-workflow.spec.ts — the repository's own gate, as GitHub runs it. check.yml
// puts this checkout's dist on PATH on purpose (the floor shims look `ai-eng` up there),
// so a registry install in the update step lands behind that dist: the launcher installs
// the release, PATH keeps answering with the tree's binary, and the step refuses to sync
// — the red step every branch carried once 3.4.2 was published. The proof is the
// launcher's behaviour under the environment that file declares, not a grep of its text.

import { afterEach, describe, expect, spyOn, test } from "bun:test";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { RELAUNCHED_ENV, updateBinary, type BinaryDeps } from "../src/commands/update-binary.ts";

const ROOT = resolve(import.meta.dir, "..");
const WORKFLOW = resolve(ROOT, ".github/workflows/check.yml");
const DIST = join(ROOT, "dist", "ai-eng");

// The incident's shape: a branch head one release behind the registry.
const { version: TREE } = JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8")) as { version: string };
const [major, minor, patch] = TREE.split(".").map((part) => Number.parseInt(part, 10));
const REGISTRY = `${major}.${minor}.${(patch ?? 0) + 1}`;

type Step = { name?: string; run?: string; env?: Record<string, string | undefined> };
type Job = { env?: Record<string, string | undefined>; steps?: Step[] };
type CheckWorkflow = { env?: Record<string, string | undefined>; jobs: Record<string, Job> };

const workflow = Bun.YAML.parse(readFileSync(WORKFLOW, "utf8")) as CheckWorkflow;

const saved = {
  home: process.env["AI_ENG_HOME"],
  optOut: process.env["AI_ENG_NO_UPDATE_NOTICES"],
  relaunched: process.env[RELAUNCHED_ENV],
};
const roots: string[] = [];

afterEach(() => {
  for (const [key, value] of Object.entries({ AI_ENG_HOME: saved.home, AI_ENG_NO_UPDATE_NOTICES: saved.optOut, [RELAUNCHED_ENV]: saved.relaunched })) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

/** Every step of the gate that runs the update verb — the only place where a registry
 *  lookup can reach the tree's binary — with the environment the runner would give it:
 *  the workflow, job and step `env:` blocks on top of a runner that carries neither this
 *  suite's opt-outs nor the relaunch mark. */
function updateSteps(): Array<{ name: string; runnerEnv: NodeJS.ProcessEnv }> {
  const runnerEnv: NodeJS.ProcessEnv = { ...process.env };
  delete runnerEnv[RELAUNCHED_ENV];
  delete runnerEnv["AI_ENG_NO_UPDATE_NOTICES"];
  return Object.values(workflow.jobs).flatMap((job) =>
    (job.steps ?? [])
      .filter((step) => (step.run ?? "").includes("ai-eng update"))
      .map((step) => ({
        name: step.name ?? "(unnamed step)",
        runnerEnv: { ...runnerEnv, ...workflow.env, ...job.env, ...step.env },
      })),
  );
}

/** Hand the process the runner's environment, so the launcher — which reads process.env,
 *  not the step model — runs under exactly what check.yml declares. */
function enterRunner(runnerEnv: NodeJS.ProcessEnv): void {
  for (const key of Object.keys(process.env)) if (!(key in runnerEnv)) delete process.env[key];
  for (const [key, value] of Object.entries(runnerEnv)) if (value !== undefined) process.env[key] = value;
}

/** The gate's world: the registry has the release this branch does not carry yet, the
 *  tree's dist answers the version in its own package.json, and installing anything
 *  cannot change what PATH resolves — GitHub puts $GITHUB_PATH entries in front. */
function gateWorld(): { deps: BinaryDeps; calls: string[][] } {
  const calls: string[][] = [];
  return {
    calls,
    deps: {
      fetchLatest: () => Promise.resolve(REGISTRY),
      run: (command, args) => {
        calls.push([command, ...args]);
        return { status: 0, stdout: args[0] === "--version" ? `ai-eng ${TREE}\n` : "" };
      },
      which: () => DIST,
      isInteractive: () => false,
      confirm: () => Promise.resolve(false),
      execPath: DIST,
    },
  };
}

async function capture<T>(run: () => Promise<T>): Promise<{ value: T; out: string }> {
  const chunks: string[] = [];
  const write = ((chunk: unknown) => {
    chunks.push(String(chunk));
    return true;
  }) as never;
  const out = spyOn(process.stdout, "write").mockImplementation(write);
  const err = spyOn(process.stderr, "write").mockImplementation(write);
  try {
    return { value: await run(), out: chunks.join("") };
  } finally {
    out.mockRestore();
    err.mockRestore();
  }
}

describe("the check gate's update step", () => {
  test("runs the update verb, so the proof below cannot go vacuous", () => {
    expect(updateSteps().map((step) => step.name)).toEqual(["Make this checkout match the binary (canon + floor + lock)"]);
  });

  test("syncs with this checkout's binary instead of installing a release behind it", async () => {
    const home = mkdtempSync(join(tmpdir(), "ai-eng-check-workflow-"));
    roots.push(home);
    process.env["AI_ENG_HOME"] = home;
    const installs: string[] = [];
    const refusals: string[] = [];
    for (const step of updateSteps()) {
      enterRunner(step.runnerEnv);
      const { deps, calls } = gateWorld();
      const { value, out } = await capture(() => updateBinary({ yes: true }, deps));
      for (const call of calls.filter(([command]) => command === "npm" || command === "bun")) installs.push(`${step.name} → ${call.join(" ")}`);
      if (value !== null || out.includes("shadows it")) refusals.push(`${step.name} → exit ${String(value)}: ${out.trim()}`);
    }
    expect(installs).toEqual([]);
    expect(refusals).toEqual([]);
  });
});
