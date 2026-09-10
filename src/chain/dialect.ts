// One denial protocol: the hook answer is JSON on stdout plus exit 2, with the
// human-readable reason on stderr. A denial whose text never arrives reads as
// permission — both outputs are flushed deliberately before exit (v1 _wrap._verdict).

import { readFileSync } from "node:fs";
import { join } from "node:path";

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

export function deny(guard: string, message: string): never {
  const text = `[ai-eng] ${guard}: ${message}`;
  process.stderr.write(`${text}\n`);
  if (guard === "loop") {
    process.stderr.write(
      "[ai-eng] loop: a person — not you — can grant an exception: .ai-engineering/overrides.toml [[guard.off]] with reason + until.\n",
    );
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

export type Override = { name: string; reason: string; until?: string };

/** Read active overrides — the ONLY mechanism that turns a guard off (§09.1). */
export function readOverrides(repoRoot: string | null): Override[] {
  if (!repoRoot) return [];
  try {
    const path = join(repoRoot, ".ai-engineering", "overrides.toml");
    const doc = Bun.TOML.parse(readFileSync(path, "utf8")) as Record<string, unknown>;
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
