// Machine- and repo-level paths, session identity, and config reads. Ported from
// v1's _emit.py — the same floor every module needs and none may guess at.

import { homedir, tmpdir } from "node:os";
import { join, resolve, sep } from "node:path";
import { existsSync, readFileSync, mkdirSync } from "node:fs";
import { parseToml } from "./toml.ts";

/** AI_ENG_HOME for tests; ~/.ai-engineering in the wild. */
export function home(): string {
  const override = process.env.AI_ENG_HOME;
  if (override) return override;
  return join(homedir(), ".ai-engineering");
}

/** The governed repo this call happens in: the nearest ancestor with .git or .ai-engineering. */
export function repoRoot(start?: string): string | null {
  let dir = resolve(start ?? process.cwd());
  for (;;) {
    if (existsSync(join(dir, ".git")) || existsSync(join(dir, ".ai-engineering", "config.toml"))) return dir;
    const parent = resolve(dir, "..");
    if (parent === dir) return null;
    dir = parent;
  }
}

/** Receipts live with the repo that governs the call; a stray call writes nothing. */
export function receiptsDir(): string | null {
  const root = repoRoot();
  return root ? join(root, ".ai-engineering", "receipts") : null;
}

const SESSION_STATE = new Map<string, string>();
/** The session the surface sent, minted per process when it did not. One session = one state file. */
export function sessionId(): string {
  const fromPayload = SESSION_STATE.get("session");
  if (fromPayload) return fromPayload;
  const env = process.env.AI_ENG_SESSION;
  if (env) return env;
  const minted = `proc-${process.pid}-${Date.now()}`;
  SESSION_STATE.set("session", minted);
  return minted;
}

/** Adopt the surface's session before any fingerprint or state file is opened (v1 chain.py). */
export function adoptSession(id: unknown): void {
  if (typeof id === "string" && id.trim()) SESSION_STATE.set("session", id.trim());
}

/** Where the installed version cache lives (24h update check, §14.0). */
export function versionFile(): string {
  return join(home(), "version.json");
}

type TomlValue = string | number | boolean;
export type Config = Record<string, Record<string, TomlValue>>;

export function loadConfig(): Config {
  const root = repoRoot();
  if (!root) return {};
  const path = join(root, ".ai-engineering", "config.toml");
  if (!existsSync(path)) return {};
  try {
    return parseToml(readFileSync(path, "utf8")) as Config;
  } catch {
    return {};
  }
}

export function guardLimits(): { window: number; repeats: number; failures: number } {
  const g = loadConfig().guards ?? {};
  return {
    window: intOr(g["loop_window"], 6),
    repeats: intOr(g["loop_repeats"], 3),
    failures: intOr(g["loop_failures"], 5),
  };
}

function intOr(value: TomlValue | undefined, fallback: number): number {
  const n = typeof value === "number" ? value : Number.parseInt(String(value ?? ""), 10);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

/** Print control characters out of a denial: a path that ends in a newline must not eat the message. */
export function printable(text: string): string {
  return text.replace(/[\p{C}]/gu, "").slice(0, 200);
}

/** Smoke-testable temp root for adversarial suites. */
export function scratchRoot(prefix: string): string {
  const dir = join(tmpdir(), `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`);
  mkdirSync(dir, { recursive: true });
  return dir;
}

export const PATH_SEP = sep;
