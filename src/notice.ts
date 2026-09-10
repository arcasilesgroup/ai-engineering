// src/notice.ts — the version notice (§14.0): one line, at the end, never a
// block. The check is cached 24h in ~/.ai-engineering/version.json (one anonymous
// registry read per day at most); offline or error → silence, never a failure.
// Opt-out: notices = false in config.toml or AI_ENG_NO_UPDATE_NOTICES=1.

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { home, repoRoot, loadConfig } from "./env.ts";
import { VERSION } from "./version.ts";
import * as ui from "./ui.ts";

const TTL_MS = 24 * 60 * 60 * 1000;

function cachedVersion(cachePath: string): { version: string; fresh: boolean } {
  if (existsSync(cachePath)) {
    try {
      const doc = JSON.parse(readFileSync(cachePath, "utf8")) as { version?: string; ts?: number };
      if (typeof doc.version === "string" && typeof doc.ts === "number" && Date.now() - doc.ts < TTL_MS) {
        return { version: doc.version, fresh: true };
      }
    } catch {
      /* corrupt cache: treat as absent */
    }
  }
  return { version: "", fresh: false };
}

/** Latest registry version via the package managers; null when offline. */
export function registryVersion(): string | null {
  const bun = spawnSync("bun", ["pm", "view", "ai-engineering", "version"], { encoding: "utf8" });
  if (bun.status === 0 && bun.stdout) return bun.stdout.trim().split("\n").pop() ?? null;
  const npm = spawnSync("npm", ["view", "ai-engineering", "version"], { encoding: "utf8" });
  if (npm.status === 0 && npm.stdout) return npm.stdout.trim().split("\n").pop() ?? null;
  return null;
}

/** The notice line for init/doctor/update tails. Silent unless a newer version
 *  exists, the cache is stale (one network read/day max), and opt-out is off. */
export function maybeNotice(): void {
  if (process.env["AI_ENG_NO_UPDATE_NOTICES"]) return;
  const root = repoRoot();
  if (root) {
    const config = loadConfig();
    if (config["notices"]?.["enabled"] === false) return;
  }
  const cachePath = join(home(), "version.json");
  const cached = cachedVersion(cachePath);
  const latest = cached.fresh ? cached.version : registryVersion();
  if (!latest) return; // offline: silence, never a failure
  if (!cached.fresh) {
    try {
      writeFileSync(cachePath, JSON.stringify({ version: latest, ts: Date.now() }));
    } catch {
      /* unwritable cache: notice still works this run */
    }
  }
  if (latest === VERSION) return;
  ui.warn(`${latest} available → ai-eng upgrade · changelog: CHANGELOG.md (current: ${VERSION})`);
}
