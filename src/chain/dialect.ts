// One denial protocol per surface family: a denial travels as JSON on stdout, plus a
// status where the host reads one. A denial whose text never arrives reads as
// permission — so the envelope is written and flushed deliberately before exit.
//
// MEASURED per host (2026-09-10, docs of the installed versions):
// - claude: exit 2 + stderr blocks. The JSON blob below is what v2 has always
//   emitted and what runs today; it is kept byte-for-byte — an unmeasured wire
//   change on the surface that works is the one change nobody can justify.
// - codex: stdout {"hookSpecificOutput":{...,"permissionDecision":"deny"}}, exit 0.
//   A non-zero exit is NOT the contract, and `continue: false` is on Codex's
//   unsupported list — "hook fails, tool proceeds". The wrong envelope fail-opens.
// - cursor: stdout {"permission":"deny",...}, exit 0. A non-zero exit is a hook
//   ERROR to Cursor, not a denial (3.12+ validators, cursor.com/docs/hooks).
// - copilot: stdout {"permissionDecision":"deny","permissionDecisionReason"}, exit 0;
//   exit 2 also denies, but the JSON is the contract that carries the reason.
// - throw (OpenCode/Oh My Pi) is not here: those two hosts run the chain in-process
//   and their templates turn the outcome into throw/block themselves.

import { readFileSync } from "node:fs";
import { join } from "node:path";

export type Dialect = "claude" | "codex" | "cursor" | "copilot";

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

export function deny(guard: string, message: string, dialect: Dialect = "claude", event = "PreToolUse"): never {
  const text = `[ai-eng] ${guard}: ${message}`;
  process.stderr.write(`${text}\n`);
  if (guard === "loop") {
    process.stderr.write(
      "[ai-eng] loop: a person — not you — can grant an exception: .ai-engineering/overrides.toml [[guard.off]] with reason + until.\n",
    );
  }
  if (dialect === "codex") {
    writeJsonAndExit({ hookSpecificOutput: { hookEventName: event, permissionDecision: "deny", permissionDecisionReason: text } }, 0);
  }
  if (dialect === "cursor") {
    writeJsonAndExit({ permission: "deny", user_message: text, agent_message: text }, 0);
  }
  if (dialect === "copilot") {
    writeJsonAndExit({ permissionDecision: "deny", permissionDecisionReason: text }, 0);
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

/** The allowed-rewrite envelope (wrap): same per-host split as deny — Cursor reads
 *  `updated_input`, Copilot `modifiedArgs`, Codex a nested `updatedInput`. */
export function allowRewrite(command: string, dialect: Dialect = "claude", event = "PreToolUse"): never {
  if (dialect === "codex") {
    writeJsonAndExit({ hookSpecificOutput: { hookEventName: event, permissionDecision: "allow", updatedInput: { command } } }, 0);
  }
  if (dialect === "cursor") {
    writeJsonAndExit({ permission: "allow", updated_input: { command } }, 0);
  }
  if (dialect === "copilot") {
    writeJsonAndExit({ permissionDecision: "allow", modifiedArgs: { command } }, 0);
  }
  writeJsonAndExit({ permission: "allow", updatedInput: { command } }, 0);
}

export type Override = { name: string; reason: string; until?: string };

/** Read active overrides — the ONLY mechanism that turns a guard off (§09.1).
 *  `[[guard.off]]` parses to `{ guard: { off: [...] } }`: a TOML dotted key nests,
 *  it never survives as the literal `"guard.off"`. Reading the literal meant every
 *  file yielded `[]` and the switch was dead (measured 2026-09-10). */
export function readOverrides(repoRoot: string | null): Override[] {
  if (!repoRoot) return [];
  try {
    const path = join(repoRoot, ".ai-engineering", "overrides.toml");
    const doc = Bun.TOML.parse(readFileSync(path, "utf8")) as Record<string, unknown>;
    const guard = doc["guard"];
    const offs = guard && typeof guard === "object" && !Array.isArray(guard)
      ? (guard as Record<string, unknown>)["off"]
      : undefined;
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

/** Whole days until an override expires. `null` means it carries no usable `until`
 *  — which is itself a finding, not a neutral value: §12.1 asks for reason + date,
 *  and a missing date never expires, so the guard stays off forever. `0` = today.
 *  Negative ⇒ already expired: the guard is live again and the entry is dead
 *  config the human still has to delete. */
export function overrideDaysLeft(entry: Override, now: number = Date.now()): number | null {
  if (!entry.until || entry.until.length < 10) return null;
  const deadline = Date.parse(`${entry.until.slice(0, 10)}T23:59:59Z`);
  if (!Number.isFinite(deadline)) return null;
  const ms = deadline - now;
  if (ms >= 86_400_000) return Math.ceil(ms / 86_400_000);
  if (ms >= 0) return 0;
  return -Math.ceil(-ms / 86_400_000);
}

export function overrideActive(overrides: Override[], guard: string): Override | null {
  for (const entry of overrides) {
    if (entry.name !== guard) continue;
    const days = overrideDaysLeft(entry);
    if (days !== null && days < 0) continue; // expired: guard is live again
    return entry;
  }
  return null;
}
