// tests/notice.spec.ts — the two version signals (§14.0): a newer ai-eng on the
// registry, and a repo installed by an older binary. One registry read a day at most,
// remembered whether it answered or failed; silence when offline; two ways to switch it
// off. No test reaches the real registry: each one serves its own answer on a local
// port, and counts the requests that arrive.

import { afterEach, describe, expect, test } from "bun:test";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { VERSION } from "../src/version.ts";
import { versionFile } from "../src/env.ts";
import {
  agentLines,
  fetchLatest,
  isFresh,
  lockVersion,
  noticeLines,
  noticeNow,
  readCache,
  refreshVersionCache,
  sessionStartContext,
  signals,
} from "../src/notice.ts";

const [major, minor, patch] = VERSION.split(".").map((part) => Number.parseInt(part, 10));
const NEXT = `${major}.${minor}.${(patch ?? 0) + 1}`;
const PREVIOUS = `${major}.${minor}.${Math.max((patch ?? 1) - 1, 0)}`;
const HOUR = 60 * 60 * 1000;

const roots: string[] = [];
const servers: Array<{ stop: (force?: boolean) => void }> = [];
const saved = {
  home: process.env["AI_ENG_HOME"],
  url: process.env["AI_ENG_REGISTRY_URL"],
  optOut: process.env["AI_ENG_NO_UPDATE_NOTICES"],
};
const savedCwd = process.cwd();

afterEach(() => {
  process.chdir(savedCwd);
  for (const [key, value] of Object.entries({ AI_ENG_HOME: saved.home, AI_ENG_REGISTRY_URL: saved.url, AI_ENG_NO_UPDATE_NOTICES: saved.optOut })) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
  for (const server of servers.splice(0)) server.stop(true);
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

function sandbox(prefix: string): string {
  const dir = mkdtempSync(join(tmpdir(), `ai-eng-${prefix}-`));
  roots.push(dir);
  return dir;
}

/** A private machine home, so every cache read and write lands in the sandbox. */
function freshHome(): string {
  const home = sandbox("home");
  process.env["AI_ENG_HOME"] = home;
  delete process.env["AI_ENG_NO_UPDATE_NOTICES"];
  return home;
}

/** A registry on a local port: answers `body` with `status`, and counts what it is asked. */
function registry(body: unknown, status = 200): { requests: () => number } {
  let count = 0;
  const server = Bun.serve({
    port: 0,
    fetch: () => {
      count += 1;
      return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
    },
  });
  servers.push(server);
  process.env["AI_ENG_REGISTRY_URL"] = `http://127.0.0.1:${server.port}/ai-engineering/latest`;
  return { requests: () => count };
}

function cacheWith(version: string | null, ageMs: number): void {
  writeFileSync(versionFile(), JSON.stringify({ version, ts: Date.now() - ageMs }));
}

/** A governed repo whose lock says which ai-eng installed it. */
function repoInstalledWith(version: string | null, config = '[surfaces]\nenabled = ["claude-code"]\n'): string {
  const repo = sandbox("repo");
  mkdirSync(join(repo, ".git"));
  mkdirSync(join(repo, ".ai-engineering"));
  writeFileSync(join(repo, ".ai-engineering", "config.toml"), config);
  if (version !== null) writeFileSync(join(repo, ".ai-engineering", "ai-eng.lock"), `version = "${version}"\n\n[assets]\n`);
  return repo;
}

describe("signals — what is worth saying, from three versions (pure)", () => {
  test("a newer registry version is one signal; an equal or older one is none", () => {
    expect(signals({ binary: "3.0.8", latest: "3.0.9", lockVersion: null })).toEqual([{ kind: "newer", latest: "3.0.9", binary: "3.0.8" }]);
    expect(signals({ binary: "3.0.8", latest: "3.0.8", lockVersion: null })).toEqual([]);
    expect(signals({ binary: "3.0.8", latest: "3.0.7", lockVersion: null })).toEqual([]);
    expect(signals({ binary: "3.0.10", latest: "3.0.9", lockVersion: null })).toEqual([]);
  });

  test("a repo installed by an older binary is one signal; the same or a newer one is none", () => {
    expect(signals({ binary: "3.0.8", latest: null, lockVersion: "3.0.7" })).toEqual([{ kind: "repo-behind", installed: "3.0.7", binary: "3.0.8" }]);
    expect(signals({ binary: "3.0.8", latest: null, lockVersion: "3.0.8" })).toEqual([]);
    expect(signals({ binary: "3.0.8", latest: null, lockVersion: "3.0.9" })).toEqual([]);
  });

  test("the person's lines and the agent's lines name the same command; only the agent is told to ask", () => {
    const found = signals({ binary: "3.0.8", latest: "3.0.9", lockVersion: "3.0.7" });
    expect(noticeLines(found)).toEqual([
      "ai-eng 3.0.9 available (you have 3.0.8) → ai-eng update",
      "this repo was installed with ai-eng 3.0.7, the binary is 3.0.8 → ai-eng update",
    ]);
    const agent = agentLines(found);
    expect(agent[0]).toBe("ai-eng 3.0.9 available (you have 3.0.8) → ai-eng update · ask the person before installing: it changes the machine for every repo");
    expect(agent[1]).toBe(noticeLines(found)[1]!);
  });
});

/** The notice from a folder that is no repo, so only the registry signal can speak. */
function noticeOutside(onStale: () => void): ReturnType<typeof noticeNow> {
  process.chdir(sandbox("outside"));
  return noticeNow(onStale);
}

describe("the registry read — one request, remembered for 24 h whatever it answered", () => {
  test("a fresh answer in the cache is final: no refresh, no request", () => {
    freshHome();
    const server = registry({ version: NEXT });
    cacheWith(NEXT, HOUR);
    let stale = 0;
    expect(noticeOutside(() => (stale += 1)).map((notice) => notice.kind)).toEqual(["newer"]);
    expect(stale).toBe(0);
    expect(server.requests()).toBe(0);
  });

  test("a failure an hour old is remembered too: no refresh, and no version", () => {
    freshHome();
    cacheWith(null, HOUR);
    let stale = 0;
    expect(noticeOutside(() => (stale += 1))).toEqual([]);
    expect(stale).toBe(0);
  });

  test("a stale cache answers at once and is refreshed: one request, the answer stored", async () => {
    freshHome();
    const server = registry({ version: NEXT });
    cacheWith(VERSION, 25 * HOUR);
    let stale = 0;
    expect(noticeOutside(() => (stale += 1))).toEqual([]);
    expect(stale).toBe(1);
    await refreshVersionCache();
    expect(server.requests()).toBe(1);
    expect(readCache()?.version).toBe(NEXT);
  });

  test("a failed refresh is stored as a failure, so the next run does not ask", async () => {
    freshHome();
    const server = registry({ error: "down" }, 503);
    await refreshVersionCache();
    expect(readCache()).toMatchObject({ version: null });
    let stale = 0;
    noticeOutside(() => (stale += 1));
    expect(stale).toBe(0);
    expect(server.requests()).toBe(1);
  });

  test("nothing listening is a failure, not an error", async () => {
    freshHome();
    process.env["AI_ENG_REGISTRY_URL"] = "http://127.0.0.1:9/ai-engineering/latest";
    expect(await fetchLatest()).toBeNull();
  });

  test("an answer that is not a version is a failure", async () => {
    freshHome();
    registry({ version: "latest; rm -rf /" });
    expect(await fetchLatest()).toBeNull();
  });

  test("a corrupt cache reads as no cache, asks for a refresh, and is replaced", async () => {
    freshHome();
    const server = registry({ version: NEXT });
    writeFileSync(versionFile(), "{not json");
    expect(readCache()).toBeNull();
    let stale = 0;
    noticeOutside(() => (stale += 1));
    expect(stale).toBe(1);
    await refreshVersionCache();
    expect(readCache()?.version).toBe(NEXT);
    expect(server.requests()).toBe(1);
  });

  test("24 hours is the line between fresh and stale", () => {
    const now = Date.now();
    expect(isFresh({ version: null, ts: now - 23 * HOUR }, now)).toBe(true);
    expect(isFresh({ version: null, ts: now - 24 * HOUR }, now)).toBe(false);
  });
});

describe("noticeNow — the end-of-verb lines", () => {
  test("a fresh cache with a newer version is the line, with no request", async () => {
    freshHome();
    const server = registry({ version: NEXT });
    cacheWith(NEXT, HOUR);
    process.chdir(sandbox("outside"));
    expect(noticeNow(() => {})).toEqual([{ kind: "newer", line: `ai-eng ${NEXT} available (you have ${VERSION}) → ai-eng update` }]);
    expect(server.requests()).toBe(0);
  });

  test("a repo installed by an older ai-eng says so, and the command that fixes it", async () => {
    freshHome();
    cacheWith(VERSION, HOUR);
    process.chdir(repoInstalledWith(PREVIOUS));
    expect(noticeNow(() => {})).toEqual([{ kind: "repo-behind", line: `this repo was installed with ai-eng ${PREVIOUS}, the binary is ${VERSION} → ai-eng update` }]);
  });

  test("AI_ENG_NO_UPDATE_NOTICES=1 says nothing and asks nothing", async () => {
    const home = freshHome();
    const server = registry({ version: NEXT });
    process.env["AI_ENG_NO_UPDATE_NOTICES"] = "1";
    process.chdir(repoInstalledWith(PREVIOUS));
    expect(noticeNow(() => {})).toEqual([]);
    expect(server.requests()).toBe(0);
    expect(existsSync(join(home, "version.json"))).toBe(false);
  });

  test("[notices] enabled = false in the repo's config switches it off there", async () => {
    freshHome();
    cacheWith(NEXT, HOUR);
    process.chdir(repoInstalledWith(PREVIOUS, '[surfaces]\nenabled = ["claude-code"]\n\n[notices]\nenabled = false\n'));
    expect(noticeNow(() => {})).toEqual([]);
  });

  test("a stale cache asks for a refresh and does not wait on the registry", () => {
    freshHome();
    const server = registry({ version: NEXT });
    cacheWith(VERSION, 25 * HOUR);
    process.chdir(sandbox("outside"));
    let asked = 0;
    expect(noticeNow(() => (asked += 1))).toEqual([]);
    expect(asked).toBe(1);
    expect(server.requests()).toBe(0);
  });
});

describe("sessionStartContext — what the agent is told, with no network", () => {
  test("a repo behind its binary and a newer release are two lines, inside the hook budget", () => {
    freshHome();
    cacheWith(NEXT, HOUR);
    const repo = repoInstalledWith(PREVIOUS);
    const started = performance.now();
    const context = sessionStartContext(repo);
    expect(performance.now() - started).toBeLessThan(200);
    expect(context).toBe(
      [
        `ai-eng ${NEXT} available (you have ${VERSION}) → ai-eng update · ask the person before installing: it changes the machine for every repo`,
        `this repo was installed with ai-eng ${PREVIOUS}, the binary is ${VERSION} → ai-eng update`,
      ].join("\n"),
    );
  });

  test("everything current is no context at all", () => {
    freshHome();
    cacheWith(VERSION, HOUR);
    expect(sessionStartContext(repoInstalledWith(VERSION))).toBeNull();
  });

  test("the notices switched off is no context", () => {
    freshHome();
    cacheWith(NEXT, HOUR);
    process.env["AI_ENG_NO_UPDATE_NOTICES"] = "1";
    expect(sessionStartContext(repoInstalledWith(PREVIOUS))).toBeNull();
  });

  test("the lock is read for its version only, and a repo without one says nothing about it", () => {
    expect(lockVersion(repoInstalledWith(PREVIOUS))).toBe(PREVIOUS);
    expect(lockVersion(repoInstalledWith(null))).toBeNull();
    expect(lockVersion(null)).toBeNull();
  });

  test("only a stale or missing cache asks for a refresh", () => {
    freshHome();
    const repo = repoInstalledWith(VERSION);
    let asked = 0;
    cacheWith(VERSION, HOUR);
    sessionStartContext(repo, () => (asked += 1));
    expect(asked).toBe(0);
    cacheWith(VERSION, 25 * HOUR);
    sessionStartContext(repo, () => (asked += 1));
    expect(asked).toBe(1);
  });
});

describe("ai-eng chain SessionStart — the hook a host runs", () => {
  const cli = join(import.meta.dir, "..", "src", "cli.ts");

  function hook(repo: string, extraEnv: Record<string, string> = {}): { status: number | null; stdout: string } {
    const run = Bun.spawnSync([process.execPath, cli, "chain", "SessionStart"], {
      cwd: repo,
      stdin: Buffer.from(JSON.stringify({ hook_event_name: "SessionStart", source: "startup", cwd: repo })),
      env: { ...process.env, NO_COLOR: "1", ...extraEnv },
    });
    return { status: run.exitCode, stdout: run.stdout.toString() };
  }

  test("answers with the version lines as additionalContext, and exits 0", () => {
    freshHome();
    cacheWith(NEXT, HOUR);
    const repo = repoInstalledWith(PREVIOUS);
    const run = hook(repo);
    expect(run.status).toBe(0);
    const answer = JSON.parse(run.stdout) as { hookSpecificOutput: { hookEventName: string; additionalContext: string } };
    expect(answer.hookSpecificOutput.hookEventName).toBe("SessionStart");
    expect(answer.hookSpecificOutput.additionalContext).toContain(`this repo was installed with ai-eng ${PREVIOUS}`);
  });

  test("a human verb that succeeds ends with the notice line; a machine verb never prints it", () => {
    freshHome();
    cacheWith(NEXT, HOUR);
    const repo = repoInstalledWith(VERSION);
    const human = Bun.spawnSync([process.execPath, cli, "config", "--ci", "github-actions"], { cwd: repo, env: { ...process.env, NO_COLOR: "1" } });
    expect(human.exitCode).toBe(0);
    const lines = `${human.stdout.toString()}${human.stderr.toString()}`.trim().split("\n");
    expect(lines.at(-1)).toContain(`ai-eng ${NEXT} available (you have ${VERSION}) → ai-eng update`);
    const machine = Bun.spawnSync([process.execPath, cli, "chain", "PreToolUse"], {
      cwd: repo,
      stdin: Buffer.from(JSON.stringify({ tool_name: "Read", tool_input: { file_path: join(repo, "README.md") }, cwd: repo })),
      env: { ...process.env, NO_COLOR: "1" },
    });
    expect(machine.exitCode).toBe(0);
    expect(`${machine.stdout.toString()}${machine.stderr.toString()}`).not.toContain("available");
  });

  test("a repo that never declared itself gets nothing, and still exits 0", () => {
    freshHome();
    cacheWith(NEXT, HOUR);
    const repo = sandbox("foreign");
    expect(hook(repo)).toEqual({ status: 0, stdout: "" });
  });

  test("a stale cache is refreshed by a detached ai-eng, for the next session", async () => {
    freshHome();
    const server = registry({ version: NEXT });
    cacheWith(VERSION, 25 * HOUR);
    // The hook answers at once from what it has: everything current.
    expect(hook(repoInstalledWith(VERSION)).stdout).toBe("");
    const deadline = Date.now() + 10_000;
    while (readCache()?.version !== NEXT && Date.now() < deadline) await Bun.sleep(50);
    expect(JSON.parse(readFileSync(versionFile(), "utf8")).version).toBe(NEXT);
    expect(server.requests()).toBe(1);
  }, 15_000);
});
