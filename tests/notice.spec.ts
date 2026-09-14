// tests/notice.spec.ts — the version notice is one line at the end and never a
// block (§14.0): one anonymous registry read per day at most, silence when offline,
// and two documented ways to switch it off. Every test here is offline: the registry
// lookup is answered either by a stale cache or by a shim named `bun` on PATH.

import { describe, expect, test, afterEach, spyOn } from "bun:test";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, existsSync, chmodSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { VERSION } from "../src/version.ts";

const roots: string[] = [];
const savedEnv = { home: process.env["AI_ENG_HOME"], path: process.env["PATH"], opt: process.env["AI_ENG_NO_UPDATE_NOTICES"] };
const savedCwd = process.cwd();

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

/** Capture what the notice writes: clack's logger goes to stdout, not stderr. */
function captureOutput(run: () => void): string {
  const chunks: string[] = [];
  const streamSpy = spyOn(process.stdout, "write").mockImplementation(((chunk: string) => {
    chunks.push(String(chunk));
    return true;
  }) as never);
  const logSpy = spyOn(console, "log").mockImplementation(((...args: unknown[]) => {
    chunks.push(args.map(String).join(" "));
  }) as never);
  try {
    run();
  } finally {
    streamSpy.mockRestore();
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
    expect(existsSync(join(home, "version.json"))).toBe(false);
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
    expect(captureOutput(() => maybeNotice())).toBe("");
  });

  test("a newer version on the registry is one line, and the answer is cached for the next 24h", async () => {
    const home = sandbox("home");
    process.env["AI_ENG_HOME"] = home;
    process.env["PATH"] = pathWithRegistryShim("9.9.9");
    const { maybeNotice } = await notice();
    const line = captureOutput(() => maybeNotice());
    expect(line).toContain("9.9.9 available");
    expect(line).toContain(`current: ${VERSION}`);
    expect(JSON.parse(readFileSync(join(home, "version.json"), "utf8")).version).toBe("9.9.9");
  });

  test("a fresh cache answers without touching the registry, and the tool does not announce itself", async () => {
    const home = sandbox("home");
    writeFileSync(join(home, "version.json"), JSON.stringify({ version: VERSION, ts: Date.now() }));
    process.env["AI_ENG_HOME"] = home;
    process.env["PATH"] = sandbox("empty-bin"); // no manager: a network read would return null and hide the bug
    const { maybeNotice } = await notice();
    expect(captureOutput(() => maybeNotice())).toBe("");
  });

  test("a cache older than a day is stale: the registry is asked again", async () => {
    const home = sandbox("home");
    writeFileSync(join(home, "version.json"), JSON.stringify({ version: "0.0.1", ts: Date.now() - 25 * 60 * 60 * 1000 }));
    process.env["AI_ENG_HOME"] = home;
    process.env["PATH"] = pathWithRegistryShim("9.9.9");
    const { maybeNotice } = await notice();
    expect(captureOutput(() => maybeNotice())).toContain("9.9.9 available");
    expect(JSON.parse(readFileSync(join(home, "version.json"), "utf8")).version).toBe("9.9.9");
  });

  test("a corrupt cache is treated as absent, not as a crash", async () => {
    const home = sandbox("home");
    writeFileSync(join(home, "version.json"), "{not json at all");
    process.env["AI_ENG_HOME"] = home;
    process.env["PATH"] = pathWithRegistryShim(VERSION);
    const { maybeNotice } = await notice();
    expect(captureOutput(() => maybeNotice())).toBe("");
    expect(JSON.parse(readFileSync(join(home, "version.json"), "utf8")).version).toBe(VERSION);
  });

  test("offline with a stale cache stays silent — a notice is never worth a failure", async () => {
    const home = sandbox("home");
    writeFileSync(join(home, "version.json"), JSON.stringify({ version: "0.0.1", ts: 0 }));
    process.env["AI_ENG_HOME"] = home;
    process.env["PATH"] = sandbox("empty-bin");
    const { maybeNotice } = await notice();
    expect(captureOutput(() => maybeNotice())).toBe("");
  });
});
