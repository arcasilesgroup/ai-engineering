// Machine- and repo-level paths, session identity, and config reads. The same
// floor every module needs and none may guess at.

import { homedir } from "node:os";
import { join, resolve } from "node:path";
import { existsSync, readFileSync } from "node:fs";

/** AI_ENG_HOME for tests; ~/.ai-engineering in the wild. An override that resolves
 *  inside the governed repository is refused: Bun loads a committed `.env` into the
 *  process environment, so honouring one would let a repository point the gate
 *  executor at its own `gate-check.mjs` and report ALL MET — arbitrary code as the
 *  governor, in a client's CI (audit LOGIC-003). */
export function home(): string {
  const override = process.env.AI_ENG_HOME;
  if (override) {
    const root = repoRoot();
    const resolved = resolve(override);
    if (root === null || !(resolved === root || resolved.startsWith(root + "/"))) return override;
  }
  return join(homedir(), ".ai-engineering");
}

/** The repo this call happens in: the nearest ancestor with .git or .ai-engineering.
 *  NOT the gate — a repo having a root says nothing about it having asked for policy. */
export function repoRoot(start?: string): string | null {
  let dir = resolve(start ?? process.cwd());
  for (;;) {
    if (existsSync(join(dir, ".git")) || existsSync(join(dir, ".ai-engineering", "config.toml"))) return dir;
    const parent = resolve(dir, "..");
    if (parent === dir) return null;
    dir = parent;
  }
}

const configPath = (root: string) => join(root, ".ai-engineering", "config.toml");

/** Why a repo is not governed, or null when it is. */
type GovernanceGap = "no-repo" | "no-config" | "corrupt-config" | "no-surfaces";

/** What a repo declared, or why it declared nothing. THE order the gate is decided
 *  in — and the only read of the declaration, so `enabledSurfaces()` and the gate
 *  can never disagree about what was said.
 *
 *  Governed means config.toml exists, parses, AND names its surfaces. Existence
 *  alone is not enough: `loadConfig()` answers `{}` for a TOML it cannot read and
 *  `enabledSurfaces()` then falls back to ["claude-code"], so a zero-byte file
 *  would be a governed repo running the strictest policy off the emptiest file
 *  (F2). Nothing else in the codebase may answer this question (§A). */
export function declaration(root: string | null = repoRoot()): { surfaces: string[] } | { gap: GovernanceGap } {
  if (root === null) return { gap: "no-repo" };
  const path = configPath(root);
  if (!existsSync(path)) return { gap: "no-config" };
  let doc: Record<string, unknown>;
  try {
    doc = Bun.TOML.parse(readFileSync(path, "utf8")) as Record<string, unknown>;
  } catch {
    return { gap: "corrupt-config" };
  }
  const surfaces = doc["surfaces"];
  if (surfaces === null || typeof surfaces !== "object" || Array.isArray(surfaces)) return { gap: "no-surfaces" };
  const enabled = (surfaces as Record<string, unknown>)["enabled"];
  if (!Array.isArray(enabled)) return { gap: "no-surfaces" };
  return { surfaces: enabled.filter((item): item is string => typeof item === "string") };
}

/** The gate: null when this repo participates, otherwise the reason it does not. */
export function governanceGap(root: string | null = repoRoot()): GovernanceGap | null {
  const declared = declaration(root);
  return "gap" in declared ? declared.gap : null;
}

export function isGoverned(root: string | null = repoRoot()): boolean {
  return "surfaces" in declaration(root);
}

/** The base every machine-side path hangs off — the canon mirrors, the carriers, the git
 *  template: AI_ENG_HOME when a test set it, otherwise the real physical home. A test
 *  install must never rewrite the REAL ~/.claude, ~/.omp, ~/.pi or ~/.config. */
export function machineBase(): string {
  return process.env.AI_ENG_HOME !== undefined ? home() : homedir();
}

/** Receipts live with the repo that governs the call. A repo that never declared
 *  itself is not governed, so a stray hook there writes nothing: no receipts dir,
 *  no .ai-engineering/ invented behind the user's back.
 *
 *  `root` is the repo the CALL belongs to when the caller already resolved it (a host
 *  that reports its own workspace directory), so the receipt cannot land in a different
 *  checkout than the one the verdict was decided for. */
export function receiptsDir(root?: string | null): string | null {
  const resolved = root === undefined ? repoRoot() : root;
  return resolved !== null && isGoverned(resolved) ? join(resolved, ".ai-engineering", "receipts") : null;
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

/** Adopt the surface's session before any fingerprint or state file is opened. */
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
  const path = configPath(root);
  if (!existsSync(path)) return {};
  try {
    return Bun.TOML.parse(readFileSync(path, "utf8")) as Config;
  } catch {
    return {};
  }
}

/** Which surfaces this repo runs: the surfaces key of config.toml, read with
 *  type guards — no assertions. Default: the one surface init installs when
 *  config.toml is silent. Both update and uninstall ask this question. */
export function enabledSurfaces(): string[] {
  const declared = declaration();
  return "surfaces" in declared ? declared.surfaces : ["claude-code"];
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

// Phase 1: Local rules — declarative injection rules from config.toml.
// TOML array of tables: [[guards.local_rules]] → parsed as an array of objects.

export interface LocalRuleConfig {
  id: string;
  name: string;
  description?: string;
  enabled: boolean;
  scope: "all_text" | "tool_name" | "raw_json";
  match: "contains" | "equals";
  pattern: string;
  case_sensitive?: boolean;
  action: "block" | "review";
  risk: number;
}

/** Circuit breaker settings from config.toml. */
export interface CircuitBreakerConfig {
  failureThreshold?: number;
  resetMs?: number;
}

/** Load circuit breaker settings from config.toml. Returns defaults when absent. */
export function loadCircuitBreakerConfig(root?: string | null): CircuitBreakerConfig {
  const resolved = root === undefined ? repoRoot() : root;
  if (!resolved) return {};
  const path = configPath(resolved);
  if (!existsSync(path)) return {};
  try {
    const doc = Bun.TOML.parse(readFileSync(path, "utf8")) as Record<string, unknown>;
    const guards = doc["guards"];
    if (!guards || typeof guards !== "object" || Array.isArray(guards)) return {};
    const cb = (guards as Record<string, unknown>)["circuit_breaker"];
    if (!cb || typeof cb !== "object" || Array.isArray(cb)) return {};
    const cfg = cb as Record<string, unknown>;
    const result: CircuitBreakerConfig = {};
    if (typeof cfg["failure_threshold"] === "number") result.failureThreshold = cfg["failure_threshold"];
    if (typeof cfg["reset_ms"] === "number") result.resetMs = cfg["reset_ms"];
    return result;
  } catch {
    return {};
  }
}

/** Load local rules from the repo's config.toml. Returns [] when absent or unparseable. */
export function loadLocalRules(root?: string | null): LocalRuleConfig[] {
  const resolved = root === undefined ? repoRoot() : root;
  if (!resolved) return [];
  const path = configPath(resolved);
  if (!existsSync(path)) return [];
  try {
    const doc = Bun.TOML.parse(readFileSync(path, "utf8")) as Record<string, unknown>;
    const guards = doc["guards"];
    if (!guards || typeof guards !== "object" || Array.isArray(guards)) return [];
    const localRules = (guards as Record<string, unknown>)["local_rules"];
    if (!Array.isArray(localRules)) return [];
    return localRules.filter((r): r is LocalRuleConfig =>
      r !== null && typeof r === "object" && !Array.isArray(r)
      && typeof (r as Record<string, unknown>)["id"] === "string"
      && typeof (r as Record<string, unknown>)["pattern"] === "string"
    );
  } catch {
    return [];
  }
}
