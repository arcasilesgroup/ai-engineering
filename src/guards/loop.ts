// The same call repeated, or the same tool failing over and over with the arguments
// tweaked each time. Window 6 / repeats 3 / failures 5, thresholds in config.toml.
// The only bypass is a written override — never a recipe printed to the model that
// may be obeying injected text.

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { createHash } from "node:crypto";
import { join } from "node:path";
import type { Payload } from "../payload.ts";
import { isReadOrControl, loopExact, loopSignature } from "../payload.ts";
import { guardLimits, home, printable, sessionId } from "../env.ts";

const SIGNATURES_KEPT = 20; // distinct failing signatures remembered per session

// ponytail: a host that registers the chain more than once (Copilot runs the repo carrier
// and the machine carriers for one call) delivers the same call within one hook round,
// with no tool_use_id to tell it apart, but with the call's own timestamp. A genuine repeat
// needs a model turn in between, so the same call stamped inside this window is the same
// call. Ceiling: two identical calls in one parallel batch count once; that is not a loop.
const SAME_CALL_MS = 3_000;

type LoopState = {
  recent: string[];
  failures: Record<string, number>;
  denials: Record<string, number>;
  /** When each call was last counted, and the denial it got, so a re-delivery replays it. */
  delivered: Record<string, { at: number; reason?: string }>;
};

function stateFile(): string {
  // The session id is host-supplied (or the AI_ENG_SESSION environment), so the filename
  // is DERIVED, never the raw value: a session id of `../../../.claude/settings` would
  // otherwise make the first guarded call of the session overwrite a file in the user's
  // home — their editor settings, or the machine carrier itself.
  return join(home(), "cache", "loop", `${createHash("sha256").update(sessionId()).digest("hex").slice(0, 32)}.json`);
}

function loadState(): LoopState {
  try {
    const parsed = JSON.parse(readFileSync(stateFile(), "utf8")) as Partial<LoopState>;
    return {
      recent: Array.isArray(parsed.recent) ? parsed.recent : [],
      failures: parsed.failures ?? {},
      denials: parsed.denials ?? {},
      delivered: parsed.delivered ?? {},
    };
  } catch {
    return { recent: [], failures: {}, denials: {}, delivered: {} };
  }
}

/** When the host says the call happened (Copilot sends epoch ms, its VS Code shape an ISO
 *  string), or null: a host that stamps nothing never re-delivers, so it is never deduped. */
function callTime(payload: Payload): number | null {
  const stamp = payload["timestamp"];
  if (typeof stamp === "number" && Number.isFinite(stamp)) return stamp;
  if (typeof stamp === "string" && Number.isFinite(Date.parse(stamp))) return Date.parse(stamp);
  return null;
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
  // Reading the same file or reporting progress twice is not a stuck loop; acting twice is.
  if (isReadOrControl(payload.tool_name)) return undefined;
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
  const at = callTime(payload);
  const previous = state.delivered[call];
  // The same call delivered again by another registration: it was already counted, so it
  // gets the answer the first delivery got instead of counting as a second attempt.
  if (at !== null && previous !== undefined && Math.abs(at - previous.at) <= SAME_CALL_MS) {
    return previous.reason === undefined ? undefined : { deny: true, reason: previous.reason };
  }
  const verdict = judgeCall(state, call, payload, sig, limits);
  if (at !== null) {
    state.delivered[call] = { at, ...(verdict?.deny === true ? { reason: verdict.reason } : {}) };
    state.delivered = Object.fromEntries(Object.entries(state.delivered).slice(-SIGNATURES_KEPT));
  }
  saveState(state);
  return verdict;
}

function judgeCall(state: LoopState, call: string, payload: Payload, sig: string, limits: ReturnType<typeof guardLimits>): GuardResult {
  state.recent = [...state.recent, call].slice(-limits.window);
  const seen = state.recent.filter((c) => c === call).length;
  if (seen >= limits.repeats) {
    // A repetition count per window, carried in the state so the third identical
    // denial escalates (rule 12: the same judgement resolved the same way three
    // times) instead of restating the verdict. Capped at the window.
    const denials = Math.min((state.denials[call] ?? 0) + 1, limits.window);
    state.denials[call] = denials;
    const denialEntries = Object.entries(state.denials);
    state.denials = Object.fromEntries(denialEntries.slice(-limits.window));
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
