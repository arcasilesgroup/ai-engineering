// tests/update-binary.spec.ts — the first half of `ai-eng update`: install a newer ai-eng
// through the package manager that installed this one, then hand over to it. Every
// part that touches the world (the registry, the manager, PATH, the terminal) is a
// stand-in here: no network, and nothing is ever installed.

import { afterEach, describe, expect, spyOn, test } from "bun:test";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { installCommand, managerFor, RELAUNCHED_ENV, updateBinary, type BinaryDeps } from "../src/commands/update-binary.ts";
import { readCache } from "../src/notice.ts";
import { VERSION } from "../src/version.ts";

const [major, minor, patch] = VERSION.split(".").map((part) => Number.parseInt(part, 10));
const NEXT = `${major}.${minor}.${(patch ?? 0) + 1}`;

const roots: string[] = [];
const saved = { home: process.env["AI_ENG_HOME"], optOut: process.env["AI_ENG_NO_UPDATE_NOTICES"], relaunched: process.env[RELAUNCHED_ENV] };

afterEach(() => {
  for (const [key, value] of Object.entries({ AI_ENG_HOME: saved.home, AI_ENG_NO_UPDATE_NOTICES: saved.optOut, [RELAUNCHED_ENV]: saved.relaunched })) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

type Call = { command: string; args: string[]; env?: NodeJS.ProcessEnv };

/** A world where the registry answers `latest`, the install exits `installStatus`, and
 *  the ai-eng on PATH reports `onPath`. Every command run is recorded. */
function world(opts: {
  latest: string | null;
  installStatus?: number;
  onPath?: string | null;
  interactive?: boolean;
  confirm?: boolean;
  execPath?: string;
  relaunchStatus?: number;
}): { deps: BinaryDeps; calls: Call[]; fetches: () => number } {
  const home = mkdtempSync(join(tmpdir(), "ai-eng-update-binary-"));
  roots.push(home);
  process.env["AI_ENG_HOME"] = home;
  delete process.env["AI_ENG_NO_UPDATE_NOTICES"];
  delete process.env[RELAUNCHED_ENV];
  const calls: Call[] = [];
  let fetches = 0;
  const deps: BinaryDeps = {
    fetchLatest: () => {
      fetches += 1;
      return Promise.resolve(opts.latest);
    },
    run: (command, args, options) => {
      calls.push({ command, args, ...(options.env === undefined ? {} : { env: options.env }) });
      if (args[0] === "--version") return { status: 0, stdout: `ai-eng ${opts.onPath ?? ""}\n` };
      if (args[0] === "update") return { status: opts.relaunchStatus ?? 0, stdout: "" };
      return { status: opts.installStatus ?? 0, stdout: "" };
    },
    which: () => (opts.onPath === null ? null : "/home/person/.bun/bin/ai-eng"),
    isInteractive: () => opts.interactive ?? false,
    confirm: () => Promise.resolve(opts.confirm ?? false),
    execPath: opts.execPath ?? "/home/person/.bun/bin/bun",
  };
  return { deps, calls, fetches: () => fetches };
}

/** What the step prints, from wherever the UI layer sends it. */
async function printed<T>(run: () => Promise<T>): Promise<{ value: T; out: string }> {
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

describe("the package manager is the one that installed ai-eng", () => {
  test("a binary under ~/.bun is bun's; anything else is npm's, on every OS", () => {
    expect(managerFor("/home/person/.bun/bin/bun")).toBe("bun");
    expect(managerFor("C:\\Users\\person\\.bun\\bin\\bun.exe")).toBe("bun");
    expect(managerFor("/usr/local/bin/node")).toBe("npm");
    expect(installCommand("bun", "3.0.9")).toEqual(["bun", "add", "-g", "ai-engineering@3.0.9"]);
    expect(installCommand("npm", "3.0.9")).toEqual(["npm", "install", "-g", "ai-engineering@3.0.9"]);
  });
});

describe("updateBinary — install, check the PATH, hand over", () => {
  test("offline is silence: the sync goes on, and the failure is remembered", async () => {
    const { deps, calls } = world({ latest: null });
    const { value, out } = await printed(() => updateBinary({ yes: true }, deps));
    expect(value).toBeNull();
    expect(calls).toEqual([]);
    expect(out).toBe("");
    expect(readCache()).toMatchObject({ version: null });
  });

  test("nothing newer: no install, the sync goes on", async () => {
    const { deps, calls } = world({ latest: VERSION });
    expect((await printed(() => updateBinary({ yes: true }, deps))).value).toBeNull();
    expect(calls).toEqual([]);
  });

  test("with no terminal and no --yes, nothing is installed: the command is shown and the sync goes on", async () => {
    const { deps, calls } = world({ latest: NEXT, interactive: false });
    const { value, out } = await printed(() => updateBinary({ yes: false }, deps));
    expect(value).toBeNull();
    expect(calls).toEqual([]);
    expect(out).toContain(`bun add -g ai-engineering@${NEXT}`);
    expect(out).toContain(`releases/tag/v${NEXT}`);
  });

  test("a person who says no keeps this binary", async () => {
    const { deps, calls } = world({ latest: NEXT, interactive: true, confirm: false });
    expect((await printed(() => updateBinary({ yes: false }, deps))).value).toBeNull();
    expect(calls).toEqual([]);
  });

  test("--yes installs with the manager, checks the PATH, and hands over to the new binary once", async () => {
    const { deps, calls } = world({ latest: NEXT, onPath: NEXT, relaunchStatus: 0 });
    const { value } = await printed(() => updateBinary({ yes: true }, deps));
    expect(value).toBe(0);
    expect(calls.map((call) => [call.command, ...call.args])).toEqual([
      ["bun", "add", "-g", `ai-engineering@${NEXT}`],
      ["/home/person/.bun/bin/ai-eng", "--version"],
      ["/home/person/.bun/bin/ai-eng", "update", "--yes"],
    ]);
    // The handed-over run carries the mark that stops it from asking again.
    expect(calls[2]!.env?.[RELAUNCHED_ENV]).toBe("1");
  });

  test("the relaunched run's exit code is update's exit code", async () => {
    const { deps } = world({ latest: NEXT, onPath: NEXT, relaunchStatus: 3 });
    expect((await printed(() => updateBinary({ yes: true }, deps))).value).toBe(3);
  });

  test("an npm-installed ai-eng is updated with npm", async () => {
    const { deps, calls } = world({ latest: NEXT, onPath: NEXT, execPath: "/usr/local/bin/node" });
    await printed(() => updateBinary({ yes: true }, deps));
    expect([calls[0]!.command, ...calls[0]!.args]).toEqual(["npm", "install", "-g", `ai-engineering@${NEXT}`]);
  });

  test("an older ai-eng first on PATH stops everything: named, with its path, and nothing is synced", async () => {
    const { deps, calls } = world({ latest: NEXT, onPath: VERSION });
    const { value, out } = await printed(() => updateBinary({ yes: true }, deps));
    expect(value).toBe(1);
    expect(out).toContain("/home/person/.bun/bin/ai-eng");
    expect(out).toContain(`reports ${VERSION}`);
    expect(calls.some((call) => call.args[0] === "update")).toBe(false);
  });

  test("a failed install keeps this binary and lets the sync go on", async () => {
    const { deps, calls } = world({ latest: NEXT, installStatus: 1 });
    expect((await printed(() => updateBinary({ yes: true }, deps))).value).toBeNull();
    expect(calls).toHaveLength(1);
  });

  test("the relaunched run never asks the registry again: no loop", async () => {
    const { deps, fetches } = world({ latest: NEXT, onPath: NEXT });
    process.env[RELAUNCHED_ENV] = "1";
    expect(await updateBinary({ yes: true }, deps)).toBeNull();
    expect(fetches()).toBe(0);
  });

  test("AI_ENG_NO_UPDATE_NOTICES=1 skips the registry; update still syncs", async () => {
    const { deps, fetches } = world({ latest: NEXT, onPath: NEXT });
    process.env["AI_ENG_NO_UPDATE_NOTICES"] = "1";
    expect(await updateBinary({ yes: true }, deps)).toBeNull();
    expect(fetches()).toBe(0);
  });
});
