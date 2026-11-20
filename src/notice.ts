// src/notice.ts — two signals, decided in one place: a newer ai-eng on the
// registry, and a repo installed by an older binary than the one running. A person
// reads them as one line each at the end of a human verb; the agent reads them at
// session start. One registry read a day at most, and the answer is remembered
// whether it came back or not, so a bad network costs one 3 s wait a day, not one per
// command. Offline is silence, never a failure.
// Opt-out: [notices] enabled = false in config.toml, or AI_ENG_NO_UPDATE_NOTICES=1.

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { spawn } from "node:child_process";
import { join } from "node:path";
import { repoRoot, loadConfig, versionFile } from "./env.ts";
import { VERSION, compareVersions } from "./version.ts";

const TTL_MS = 24 * 60 * 60 * 1000;
const REGISTRY_TIMEOUT_MS = 3000;
const REGISTRY_URL = "https://registry.npmjs.org/ai-engineering/latest";

/** Set on the detached child a session start spawns to refresh a stale cache. */
export const REFRESH_ENV = "AI_ENG_REFRESH_VERSION_CACHE";

/** The registry's answer and when it was asked. `version: null` remembers a failure. */
export type VersionCache = { version: string | null; ts: number };

/** What the running binary, the registry and this repo's lock say, and what follows. */
export type Signal =
  | { kind: "newer"; latest: string; binary: string }
  | { kind: "repo-behind"; installed: string; binary: string };

export function readCache(): VersionCache | null {
  try {
    const doc = JSON.parse(readFileSync(versionFile(), "utf8")) as Partial<VersionCache>;
    const isVersion = typeof doc.version === "string" || doc.version === null;
    return isVersion && typeof doc.ts === "number" ? { version: doc.version ?? null, ts: doc.ts } : null;
  } catch {
    return null; // absent or corrupt: as if never asked
  }
}

export function writeCache(version: string | null): void {
  try {
    writeFileSync(versionFile(), JSON.stringify({ version, ts: Date.now() } satisfies VersionCache));
  } catch {
    /* unwritable cache: this run still has its answer */
  }
}

export function isFresh(cache: VersionCache, now: number = Date.now()): boolean {
  return now - cache.ts < TTL_MS;
}

/** One request, 3 s, no retry. AI_ENG_REGISTRY_URL points tests at a local server. */
export async function fetchLatest(): Promise<string | null> {
  try {
    const response = await fetch(process.env["AI_ENG_REGISTRY_URL"] ?? REGISTRY_URL, { signal: AbortSignal.timeout(REGISTRY_TIMEOUT_MS) });
    if (!response.ok) return null;
    const body = (await response.json()) as { version?: unknown };
    return typeof body.version === "string" && /^\d+\.\d+\.\d+/.test(body.version) ? body.version : null;
  } catch {
    return null;
  }
}


export function noticesOff(root: string | null = repoRoot()): boolean {
  if (process.env["AI_ENG_NO_UPDATE_NOTICES"]) return true;
  return root !== null && loadConfig(root)["notices"]?.["enabled"] === false;
}

/** The ai-eng version that last installed this repo's files, or null when there is no lock. */
export function lockVersion(root: string | null): string | null {
  if (root === null) return null;
  const path = join(root, ".ai-engineering", "ai-eng.lock");
  if (!existsSync(path)) return null;
  try {
    const version = (Bun.TOML.parse(readFileSync(path, "utf8")) as { version?: unknown }).version;
    return typeof version === "string" && version.length > 0 ? version : null;
  } catch {
    return null;
  }
}

/** Pure: what is worth saying, given the three versions. */
export function signals(input: { binary: string; latest: string | null; lockVersion: string | null }): Signal[] {
  const found: Signal[] = [];
  if (input.latest !== null && compareVersions(input.latest, input.binary) > 0) {
    found.push({ kind: "newer", latest: input.latest, binary: input.binary });
  }
  if (input.lockVersion !== null && compareVersions(input.lockVersion, input.binary) < 0) {
    found.push({ kind: "repo-behind", installed: input.lockVersion, binary: input.binary });
  }
  return found;
}

/** The person's lines: what changed, and the one command that answers it. */
export function noticeLines(found: Signal[]): string[] {
  return found.map((signal) =>
    signal.kind === "newer"
      ? `ai-eng ${signal.latest} available (you have ${signal.binary}) → ai-eng update`
      : `this repo was installed with ai-eng ${signal.installed}, the binary is ${signal.binary} → ai-eng update`,
  );
}

/** The agent's lines. Installing changes the machine for every repo, so the agent asks first. */
export function agentLines(found: Signal[]): string[] {
  return found.map((signal) =>
    signal.kind === "newer"
      ? `ai-eng ${signal.latest} available (you have ${signal.binary}) → ai-eng update · ask the person before installing: it changes the machine for every repo`
      : `this repo was installed with ai-eng ${signal.installed}, the binary is ${signal.binary} → ai-eng update`,
  );
}

export type NoticeLine = { readonly kind: Signal["kind"]; readonly line: string };

/** Cache and lock only. A stale or missing cache calls `onStale` and still answers
 *  from whatever the cache already holds, so the verb never waits on the registry. */
function cachedSignals(root: string | null, onStale: () => void): Signal[] {
  const cache = readCache();
  if (cache === null || !isFresh(cache)) onStale();
  return signals({ binary: VERSION, latest: cache?.version ?? null, lockVersion: lockVersion(root) });
}

/** The end-of-verb notice: at most one line per signal, none when all is current or
 *  the notices are off. The caller prints them: this module stays free of the UI, so
 *  the chain bundle that reads it at session start carries no prompt library.
 *  A stale cache refreshes in the background; this call does not wait. */
export function noticeNow(onStale: () => void = refreshInBackground): NoticeLine[] {
  const root = repoRoot();
  if (noticesOff(root)) return [];
  return cachedSignals(root, onStale).map((signal) => ({ kind: signal.kind, line: noticeLines([signal])[0] ?? "" }));
}

/** What the agent is told at session start — no network: the cache and the lock only.
 *  A stale cache calls `onStale`, which the CLI answers with a detached refresh for the
 *  next session. Null when there is nothing to say or the notices are off. */
export function sessionStartContext(root: string | null, onStale: () => void = () => {}): string | null {
  if (noticesOff(root)) return null;
  const lines = agentLines(cachedSignals(root, onStale));
  return lines.length === 0 ? null : lines.join("\n");
}

/** Re-runs the ai-eng CLI this process is with REFRESH_ENV set: cli.ts answers that
 *  before anything else, so the argument after the runtime (the script, or whatever a
 *  compiled binary carries there) only has to start it. Only the CLI may call this —
 *  under any other entry point argv[1] is someone else's program. Not waited on, no
 *  stdio inherited; a failure is fine. */
export function refreshInBackground(): void {
  try {
    const child = spawn(process.execPath, process.argv.slice(1, 2), {
      detached: true,
      stdio: "ignore",
      env: { ...process.env, [REFRESH_ENV]: "1" },
    });
    child.on("error", () => {});
    child.unref();
  } catch {
    /* the next session asks again */
  }
}

/** The detached child's whole job. */
export async function refreshVersionCache(): Promise<void> {
  writeCache(await fetchLatest());
}
