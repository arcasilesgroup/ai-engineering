// One denial protocol per surface. A denial travels as text on stderr plus a status;
// Claude Code's structured answer carries the decision in JSON on exit 0. A denial
// whose text never arrives is a denial that reads as permission — both outputs are
// flushed deliberately before exit (v1 _wrap._verdict).

import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { parseToml } from "../toml.ts";

export type Dialect = "claude-structured" | "exit2" | "throw" | "block-json";

/** Security guards have no bypass; their denial never prints the recipe for one. */
export const SECURITY: Record<string, true> = { "no-verify": true, "self-protect": true, injection: true };
/** Flow guards allow an exception, but only through overrides.toml with reason+until. */
export const FLOW: Record<string, true> = { loop: true };

export type Verdict = { deny: boolean; by?: string; message?: string };

function writeJsonAndExit(decision: unknown, status: number): never {
  try {
    process.stdout.write(`${JSON.stringify(decision)}\n`);
  } catch {
    // The stdout write failing must not turn the denial into permission: v1 measured
    // a closed stdout rewriting exit status 2 into 120 at interpreter shutdown.
    process.exit(2);
  }
  process.exit(status);
}

export function deny(guard: string, message: string, dialect: Dialect = "exit2"): never {
  const text = `[ai-eng] ${guard}: ${message}`;
  process.stderr.write(`${text}\n`);
  if (guard === "loop") {
    process.stderr.write(
      "[ai-eng] loop: a person — not you — can grant an exception: .ai-engineering/overrides.toml [[guard.off]] with reason + until.\n",
    );
  }
  if (dialect === "claude-structured") {
    writeJsonAndExit(
      {
        hookSpecificOutput: {
          hookEventName: "PreToolUse",
          permissionDecision: "deny",
          permissionDecisionReason: text,
        },
      },
      0,
    );
  }
  if (dialect === "block-json") {
    writeJsonAndExit({ decision: "block", reason: text }, 2);
  }
  if (dialect === "throw") {
    throw new Error(text);
  }
  writeJsonAndExit(
    {
      permission: "deny",
      continue: false,
      user_message: text,
      userMessage: text,
      stop_reason: text,
      stopReason: text,
    },
    2,
  );
}

/** Verdict cache keyed on the fingerprint of one physical call: a second delivery of
 *  the same call gets the guard's own words instead of re-running every guard. */
export class VerdictCache {
  private readonly file: string;

  constructor(stateDir: string, sessionId: string) {
    this.file = join(stateDir, "cache", "verdicts", `${sessionId}.json`);
  }

  read(fp: string): Verdict | null {
    try {
      const book = JSON.parse(readFileSync(this.file, "utf8")) as Record<string, Verdict>;
      const entry = book[fp];
      if (!entry || typeof entry.deny !== "boolean") return null;
      if (entry.deny && !(typeof entry.by === "string" && typeof entry.message === "string")) return null;
      return entry;
    } catch {
      return null;
    }
  }

  remember(fp: string, verdict: Verdict): void {
    try {
      let book: Record<string, Verdict> = {};
      try {
        book = JSON.parse(readFileSync(this.file, "utf8")) as Record<string, Verdict>;
      } catch {
        /* first entry */
      }
      book[fp] = verdict;
      const trimmed: Record<string, Verdict> = {};
      for (const key of Object.keys(book).slice(-500)) trimmed[key] = book[key]!;
      writeFileSync(this.file, JSON.stringify(trimmed));
    } catch {
      /* state must never break the chain */
    }
  }
}

export type Override = { name: string; reason: string; until?: string };

/** Read active overrides — the ONLY mechanism that turns a guard off (§09.1). */
export function readOverrides(repoRoot: string | null): Override[] {
  if (!repoRoot) return [];
  try {
    const path = join(repoRoot, ".ai-engineering", "overrides.toml");
    const doc = parseToml(readFileSync(path, "utf8"));
    const offs = doc["guard.off"];
    if (!Array.isArray(offs)) return [];
    const out: Override[] = [];
    for (const entry of offs) {
      if (entry && typeof entry === "object" && typeof (entry as Record<string, unknown>)["name"] === "string") {
        const e = entry as Record<string, unknown>;
        const next: Override = { name: String(e["name"]), reason: typeof e["reason"] === "string" ? e["reason"] : "" };
        if (typeof e["until"] === "string") next.until = e["until"];
        out.push(next);
      }
    }
    return out;
  } catch {
    return [];
  }
}

export function overrideActive(overrides: Override[], guard: string): Override | null {
  for (const entry of overrides) {
    if (entry.name !== guard) continue;
    if (entry.until && entry.until.length >= 10) {
      const deadline = Date.parse(`${entry.until.slice(0, 10)}T23:59:59Z`);
      if (Number.isFinite(deadline) && deadline < Date.now()) continue; // expired: guard is live again
    }
    return entry;
  }
  return null;
}
