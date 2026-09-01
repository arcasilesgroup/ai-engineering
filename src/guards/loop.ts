// The same call repeated, or the same tool failing over and over with the arguments
// tweaked each time. Window 6 / repeats 3 / failures 5, thresholds in config.toml.
// Ported from v1's loop_guard.py (149 LOC). The only bypass is a written override —
// never a recipe printed to the model that may be obeying injected text.

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import type { Payload } from "../chain/payload.ts";
import { loopExact, loopSignature } from "../chain/payload.ts";
import { guardLimits, home, printable, sessionId } from "../env.ts";

const SIGNATURES_KEPT = 20; // distinct failing signatures remembered per session

type LoopState = {
  recent: string[];
  failures: Record<string, number>;
  denials: Record<string, number>;
};

function stateFile(): string {
  return join(home(), "cache", "loop", `${sessionId()}.json`);
}

function loadState(): LoopState {
  try {
    const parsed = JSON.parse(readFileSync(stateFile(), "utf8")) as Partial<LoopState>;
    return {
      recent: Array.isArray(parsed.recent) ? parsed.recent : [],
      failures: parsed.failures ?? {},
      denials: parsed.denials ?? {},
    };
  } catch {
    return { recent: [], failures: {}, denials: {} };
  }
}

function saveState(state: LoopState): void {
  try {
    const file = stateFile();
    mkdirSync(join(file, ".."), { recursive: true });
    writeFileSync(file, JSON.stringify(state));
  } catch {
    /* state must never break the chain */
  }
}

/** Authoritative failure fields only. Scanning output for the word "error" makes a
 *  guard fire on a passing test suite that prints one. */
function failed(payload: Payload): boolean {
  const response = payload.tool_response;
  if (response !== null && typeof response === "object") {
    const record = response as Record<string, unknown>;
    return Boolean(record["is_error"] || record["isError"]);
  }
  return false;
}

type GuardResult = { deny: true; reason: string } | { deny: false } | undefined;

export function runLoopGuard(payload: Payload, overridesActiveLoop: boolean): GuardResult {
  if (overridesActiveLoop) return undefined; // written exception: reason already visible in commit+receipt
  const limits = guardLimits();
  const state = loadState();
  const sig = loopSignature(payload);

  if (payload._event !== "PreToolUse") {
    if (failed(payload)) {
      // Reinserted so a still-failing signature moves to the end and the trim drops
      // the ones nothing has touched. Bounded by the call window instead, five
      // failures inside six calls would be a threshold the failure arm can never
      // reach once anything else happens.
      state.failures[sig] = (state.failures[sig] ?? 0) + 1;
      const entries = Object.entries(state.failures);
      state.failures = Object.fromEntries(entries.slice(-SIGNATURES_KEPT));
    } else {
      delete state.failures[sig];
    }
    saveState(state);
    return undefined;
  }

  const call = loopExact(payload);
  state.recent = [...state.recent, call].slice(-limits.window);
  saveState(state);
  const seen = state.recent.filter((c) => c === call).length;
  if (seen >= limits.repeats) {
    // A repetition count per window, carried in the state so the third identical
    // denial escalates (rule 12: the same judgement resolved the same way three
    // times) instead of restating the verdict. Capped at the window.
    const denials = Math.min((state.denials[call] ?? 0) + 1, limits.window);
    state.denials[call] = denials;
    const denialEntries = Object.entries(state.denials);
    state.denials = Object.fromEntries(denialEntries.slice(-limits.window));
    saveState(state);
    if (denials >= 3) {
      const who = printable(loopSignature(payload));
      return {
        deny: true,
        reason: `${who} — this exact call has been denied ${denials} times in the last ${limits.window}. The loop is bounded; retrying returns what it returned before. Hand it to a person: an override in .ai-engineering/overrides.toml is the only way through, with reason + until.`,
      };
    }
    return {
      deny: true,
      reason: `this exact call has been made ${seen} times in the last ${limits.window}. Repeating it will return what it returned before. Say what you expected and what you got, and change the approach — or ask.`,
    };
  }
  const failureCount = state.failures[sig] ?? 0;
  if (failureCount >= limits.failures) {
    return {
      deny: true,
      reason: `${printable(sig)} has failed ${failureCount} times in a row with the arguments tweaked each time. Stop and say what is failing; retrying past this point is guessing, and it is being paid for by the person waiting.`,
    };
  }
  return undefined;
}
