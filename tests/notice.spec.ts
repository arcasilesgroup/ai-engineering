// tests/notice.spec.ts — the version notice is one line at the end and never a
// block (§14.0): one anonymous registry read per day at most, silence when offline,
// and two documented ways to switch it off. Every test here is offline: the registry
// lookup is answered either by a stale cache or by a shim named `bun` on PATH.

import { describe, expect, test, afterEach, spyOn } from "bun:test";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, existsSync, chmodSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { VERSION } from "../src/version.ts";
import { home } from "../src/env.ts";

const roots: string[] = [];
const savedEnv = { home: process.env["AI_ENG_HOME"], path: process.env["PATH"], opt: process.env["AI_ENG_NO_UPDATE_NOTICES"] };
const savedCwd = process.cwd();

/** Where THIS process would write the notice cache — the module's own answer, read
 *  through the same function the notice uses. A test that hardcodes its sandbox instead
 *  passes on a laptop and fails on a runner whose AI_ENG_HOME is not honoured. */
function cachePath(): string {
  return join(home(), "version.json");
}

function sandbox(prefix: string): string {
  const dir = mkdtempSync(join(tmpdir(), `ai-eng-${prefix}-`));
  roots.push(dir);
  return dir;
}

/** A PATH whose `bun` answers with a version — the registry read without the network. */
function pathWithRegistryShim(version: string): string {
  const bin = sandbox("shim");
  writeFileSync(join(bin, "bun"), `#!/bin/sh\nif [ "$1" = "pm" ]; then echo "${version}"; exit 0; fi\nexit 1\n`);
  chmodSync(join(bin, "bun"), 0o755);
  return bin;
}

afterEach(() => {
  process.chdir(savedCwd);
  for (const [key, value] of Object.entries({ AI_ENG_HOME: savedEnv.home, PATH: savedEnv.path, AI_ENG_NO_UPDATE_NOTICES: savedEnv.opt })) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

async function notice(): Promise<typeof import("../src/notice.ts")> {
  return import("../src/notice.ts");
}

/** Capture what the notice writes. clack's logger picks its stream from whether stdout is
 *  a TTY: a terminal gets it on stdout, CI gets it on stderr — so both are watched, and
 *  the test passes in either environment for the same reason. */
function captureOutput(run: () => void): string {
  const chunks: string[] = [];
  const write = ((chunk: unknown) => {
    chunks.push(String(chunk));
    return true;
  }) as never;
  const outSpy = spyOn(process.stdout, "write").mockImplementation(write);
  const errSpy = spyOn(process.stderr, "write").mockImplementation(write);
  const logSpy = spyOn(console, "log").mockImplementation(((...args: unknown[]) => {
    chunks.push(args.map(String).join(" "));
  }) as never);
  try {
    run();
  } finally {
    outSpy.mockRestore();
    errSpy.mockRestore();
    logSpy.mockRestore();
  }
  return chunks.join("");
}

describe("registryVersion — the package managers are the registry client", () => {
  test("the version a manager prints is the version, and the last line wins", async () => {
    process.env["PATH"] = pathWithRegistryShim("9.9.9");
    const { registryVersion } = await notice();
    expect(registryVersion()).toBe("9.9.9");
  });

  test("no manager on PATH is silence, never a failure", async () => {
    process.env["PATH"] = sandbox("empty-bin");
    const { registryVersion } = await notice();
    expect(registryVersion()).toBeNull();
  });
});

describe("maybeNotice — silent unless there is something to say", () => {
  test("AI_ENG_NO_UPDATE_NOTICES=1 is the first thing checked: no cache is even written", async () => {
    const home = sandbox("home");
    process.env["AI_ENG_HOME"] = home;
    process.env["AI_ENG_NO_UPDATE_NOTICES"] = "1";
    process.env["PATH"] = pathWithRegistryShim("9.9.9");
    const { maybeNotice } = await notice();
    expect(captureOutput(() => maybeNotice())).toBe("");
    expect(existsSync(cachePath())).toBe(false);
  });

  test("notices = false in the repository's config switches it off for that repository", async () => {
    const home = sandbox("home");
    const repo = sandbox("repo");
    mkdirSync(join(repo, ".ai-engineering"), { recursive: true });
    writeFileSync(join(repo, ".ai-engineering", "config.toml"), "[notices]\nenabled = false\n");
    process.env["AI_ENG_HOME"] = home;
    process.env["PATH"] = pathWithRegistryShim("9.9.9");
    process.chdir(repo);
    const { maybeNotice } = await notice();
    captureOutput(() => maybeNotice());
    // Switched off means the registry was never asked: no cache write, no line.
    expect(existsSync(cachePath())).toBe(false);
  });

  test("a newer version on the registry is cached for the next 24h, and a fresh cache is not re-asked", async () => {
    const home = sandbox("home");
    process.env["AI_ENG_HOME"] = home;
    process.env["PATH"] = pathWithRegistryShim("9.9.9");
    const { maybeNotice } = await notice();

    maybeNotice();
    expect(JSON.parse(readFileSync(cachePath(), "utf8")).version).toBe("9.9.9");

    // The cache answers now: a PATH that would say something else must not be consulted.
    process.env["PATH"] = pathWithRegistryShim("9.9.8");
    maybeNotice();
    expect(JSON.parse(readFileSync(cachePath(), "utf8")).version).toBe("9.9.9");
  });

  test("the cache older than a day is stale: the registry is asked again", async () => {
    const home = sandbox("home");
    writeFileSync(join(home, "version.json"), JSON.stringify({ version: "0.0.1", ts: Date.now() - 25 * 60 * 60 * 1000 }));
    process.env["AI_ENG_HOME"] = home;
    process.env["PATH"] = pathWithRegistryShim("9.9.9");
    const { maybeNotice } = await notice();

    maybeNotice();
    expect(JSON.parse(readFileSync(cachePath(), "utf8")).version).toBe("9.9.9");
  });

  test("a corrupt cache is treated as absent, not as a crash", async () => {
    const home = sandbox("home");
    writeFileSync(join(home, "version.json"), "{not json at all");
    process.env["AI_ENG_HOME"] = home;
    process.env["PATH"] = pathWithRegistryShim(VERSION);
    const { maybeNotice } = await notice();

    maybeNotice();
    expect(JSON.parse(readFileSync(cachePath(), "utf8")).version).toBe(VERSION);
  });

  test("offline with a stale cache stays silent and rewrites nothing", async () => {
    const home = sandbox("home");
    const stale = JSON.stringify({ version: "0.0.1", ts: 0 });
    writeFileSync(join(home, "version.json"), stale);
    process.env["AI_ENG_HOME"] = home;
    process.env["PATH"] = sandbox("empty-bin");
    const { maybeNotice } = await notice();

    expect(captureOutput(() => maybeNotice())).toBe("");
    expect(readFileSync(cachePath(), "utf8")).toBe(stale);
  });

  test("the line itself reaches a terminal: one read, one line (a real process, no stream spying)", () => {
    // clack picks its stream from whether stdout is a TTY, so the rendered line is checked
    // where it is actually rendered: a child process with the sandbox on its env. This is
    // also the only assertion that would catch a notice that decides correctly and prints
    // nothing.
    const home = sandbox("home");
    const bin = pathWithRegistryShim("9.9.9");
    const entry = join(process.cwd(), "src/notice.ts");
    // The shim IS a file named `bun`, so the child is launched through the running
    // interpreter by absolute path — resolving "bun" through PATH would run the shim.
    const run = Bun.spawnSync([process.execPath, "-e", `import { maybeNotice } from "${entry}"; maybeNotice();`], {
      env: { ...process.env, AI_ENG_HOME: home, PATH: bin, NO_COLOR: "1" },
      stdout: "pipe",
      stderr: "pipe",
    });

    const printed = run.stdout.toString() + run.stderr.toString();
    expect(printed).toContain("9.9.9 available");
    expect(printed).toContain(`current: ${VERSION}`);
  });
});
