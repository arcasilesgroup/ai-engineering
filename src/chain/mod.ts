// The dispatcher. One process per call (or one import in-process), the only way to
// run anything. A table event→guards, a verdict cache keyed on the fingerprint of
// one physical call, fail-closed on any guard crash — a guard that cannot decide
// denies, because denying everything on a surface is how you disable a whole
// product by installing it.

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, join } from "node:path";
import { repoRoot, isGoverned, adoptSession, sessionId, receiptsDir, loadLocalRules, loadCircuitBreakerConfig } from "../env.ts";
import { normalise, deduplicable, fingerprint, loopExact } from "./payload.ts";
import type { Payload } from "./payload.ts";
import { deny, allow, allowRewrite, readOverrides, overrideActive, type Dialect } from "./dialect.ts";
import { runNoVerify, type GuardResult } from "../guards/no-verify.ts";
import { runSelfProtect } from "../guards/self-protect.ts";
import { policyModeFor, runPolicy } from "../guards/policy.ts";
import { runInjection, type GuardResult as InjectionGuardResult } from "../guards/injection.ts";
import { runSpokenSecret } from "../guards/spoken-secret.ts";
import { runLoopGuard } from "../guards/loop.ts";
import { CircuitBreaker } from "../guards/circuit-breaker.ts";
import { isTestCommand, rewrite } from "../guards/wrap.ts";
import { writeReceipt, upsertDenyLedger } from "../receipts.ts";

export type GuardName = "self-protect" | "no-verify" | "policy" | "injection" | "loop" | "wrap" | "spoken-secret";

type GuardRow = { name: GuardName; matcher: RegExp };
type GuardOutcome = { deny: true; reason: string; rewriteTo?: string } | { deny: false; review: true; reason: string; rule: { id: string; name: string; risk: number } } | undefined;

export type ChainContext = {
  repoRoot: string | null;
  loopOverride: boolean;
  /** Circuit breaker for external service calls (Jev, MCP). Shared per process. */
  circuitBreaker: CircuitBreaker;
};

/** event -> [(guard, tool matcher)]. Adding an entry point means adding a row here,
 *  and this table is what emits: there is no way to add a hook without instrumentation. */
export const TABLE: Record<string, GuardRow[]> = {
  PreToolUse: [
    { name: "self-protect", matcher: /^(Edit|Write|MultiEdit|NotebookEdit|Bash|PowerShell|shell|command)$/ },
    { name: "no-verify", matcher: /^(Bash|PowerShell|shell|command|Edit|Write|MultiEdit|NotebookEdit)$/ },
    { name: "policy", matcher: /^(Bash|PowerShell|shell|command)$/ },
    { name: "injection", matcher: /^(Read|NotebookRead|ReadFile|Bash|PowerShell|shell|command)$/ },
    { name: "wrap", matcher: /^(Bash|PowerShell|shell|command)$/ },
    { name: "loop", matcher: /^.*$/ },
  ],
  PostToolUse: [
    { name: "injection", matcher: /^(WebFetch|Fetch|WebSearch|mcp__.*|tool_result)$/ },
    { name: "loop", matcher: /^.*$/ },
  ],
  // The prompt arm: fires before the user's text enters the transcript. A prompt
  // payload carries no tool at all, and normalise leaves tool_name as "" — the empty
  // name IS this event's signature. Anchored like every row (TABLE invariant test).
  UserPromptSubmit: [{ name: "spoken-secret", matcher: /^$/ }],
};

const HOT_PATH_BUDGET_MS = 200;

/** Shared circuit breaker instance per process. Created once, reused across runs. */
const sharedCircuitBreaker = new CircuitBreaker();

export type ChainOptions = {
  surface?: string;
  /** The host's denial vocabulary (§10.1). Absent = claude, the surface that has
   *  run since second zero. */
  dialect?: Dialect;
  /** In-process mode returns outcomes instead of exiting (OMP/OpenCode plugins). */
  inProcess?: boolean;
};

export type ChainOutcome =
  | { action: "allow"; guards: string[]; receiptId: string | null }
  | { action: "deny"; by: string; reason: string; guards: string[]; receiptId: string | null }
  | { action: "rewrite"; command: string; guards: string[]; receiptId: string | null }
  | { action: "review"; reason: string; rule: { id: string; name: string; risk: number }; guards: string[]; receiptId: string | null };

type EventName = keyof typeof TABLE;

function selected(event: string, tool: string): GuardRow[] {
  // The TABLE keys are fixed; the event arrives from the hook payload, not from
  // user-controlled text that could influence which regex runs.
  if (!(event in TABLE)) return [];
  const key: EventName = event;
  // snyk ignore reason: all matchers are hardcoded RegExp literals (TABLE above);
  // `tool` is the value being tested, not the pattern. The matchers are simple
  // alternations (^(A|B|C)$) that cannot cause catastrophic backtracking.
  return TABLE[key]!.filter((row) => row.matcher.test(tool));
}

type Verdict = { deny: boolean; by?: string; message?: string };

/** Verdict cache keyed on the fingerprint of one physical call: a second delivery of
 *  the same call gets the guard's own words instead of re-running every guard. */
function cachedVerdict(file: string, fp: string): Verdict | null {
  try {
    const book = JSON.parse(readFileSync(file, "utf8")) as Record<string, Verdict>;
    const entry = book[fp];
    if (!entry || typeof entry.deny !== "boolean") return null;
    if (entry.deny && !(typeof entry.by === "string" && typeof entry.message === "string")) return null;
    return entry;
  } catch {
    return null;
  }
}

function rememberVerdict(file: string, fp: string, verdict: Verdict): void {
  try {
    let book: Record<string, Verdict> = {};
    try {
      book = JSON.parse(readFileSync(file, "utf8")) as Record<string, Verdict>;
    } catch {
      /* first entry */
    }
    // The directory does not exist until the first verdict lands: without this the write
    // threw ENOENT into the catch below and the cache silently never worked at all.
    mkdirSync(dirname(file), { recursive: true });
    book[fp] = verdict;
    const trimmed: Record<string, Verdict> = {};
    for (const key of Object.keys(book).slice(-500)) trimmed[key] = book[key]!;
    writeFileSync(file, JSON.stringify(trimmed));
  } catch {
    /* state must never break the chain */
  }
}

/** The workspace directory the host says this call belongs to, when it says one. pi and
 *  OMP send `cwd` (measured on omp 18.1.17: ctx.cwd is the workspace root), and Claude
 *  Code sends it at the top level too. The gate resolves the repo from THIS when it is
 *  there: a host process that chdir'd is not the workspace, and the payload is what the
 *  host knows for sure. */
function hostCwd(raw: unknown): string | undefined {
  if (raw === null || typeof raw !== "object" || Array.isArray(raw)) return undefined;
  const record = raw as Record<string, unknown>;
  for (const key of ["cwd", "workspaceRoot", "workspacePath"]) {
    const value = record[key];
    if (typeof value === "string" && value.length > 0) return value;
  }
  return undefined;
}

/** Run the chain over a normalized payload. A crash inside a guard is a DENY, not a pass. */
export function runChain(rawPayload: Record<string, unknown>, event: string, options: ChainOptions = {}): ChainOutcome {
  const started = Date.now();
  // One resolution, used by the gate AND by everything below it: the repo the call
  // belongs to. A gate decided on one root while the receipt resolves from another is how
  // a foreign repo gets written to anyway.
  const root = repoRoot(hostCwd(rawPayload));
  // THE gate, first — before the payload is read and before anything is written.
  // A repo that never declared itself in config.toml gets allow and nothing else:
  // no guards, no receipt, no receipts/ directory invented in a stranger's clone.
  // This is the one fail-open in the system, and it is bounded to one question,
  // asked in one place (§A). Everything below assumes a repo that asked for policy.
  if (root === null || !isGoverned(root)) return { action: "allow", guards: [], receiptId: null };
  if (rawPayload === null || Array.isArray(rawPayload) || typeof rawPayload !== "object") {
    return denyOutcome("chain", "BLOCKED: the hook payload could not be read, so nothing here can say whether this action is safe.", [], event, options, started, root, "unknown");
  }
  // The payload boundary is fail-closed like every guard: an object that throws while
  // being read (an in-process host can hand us one) must deny, never escape as an
  // uncaught exception — a crashing hook is a hook that lets the call through.
  let payload: Payload;
  try {
    payload = normalise(rawPayload, options.surface);
  } catch {
    return denyOutcome("chain", "BLOCKED: the hook payload could not be read, so nothing here can say whether this action is safe.", [], event, options, started, root, "unknown");
  }
  adoptSession(payload.session_id);
  payload._event = event;
  // Phase 1: attach declarative local rules from config.toml to the payload.
  // The injection guard reads payload.localRules and evaluates them before
  // falling through to the built-in IOC catalogue.
  const localRules = loadLocalRules(root);
  if (localRules.length > 0) {
    (payload as Record<string, unknown>)["localRules"] = localRules;
  }
  const tool = payload.tool_name;
  const fp = fingerprint(payload);

  const overrides = readOverrides(root);
  // Configure the shared circuit breaker from config.toml (once per process;
  // subsequent reads update the thresholds without creating new instances).
  const cbConfig = loadCircuitBreakerConfig(root);
  if (cbConfig.failureThreshold !== undefined || cbConfig.resetMs !== undefined) {
    sharedCircuitBreaker.configure(cbConfig);
  }
  const ctx: ChainContext = { repoRoot: root, loopOverride: overrideActive(overrides, "loop") !== null, circuitBreaker: sharedCircuitBreaker };

  // Same call, same answer: no guard decides the same call twice. The cache lives inside
  // .ai-engineering/ — the directory the lock owns and uninstall sweeps — and not at the
  // repo root, where it would be an unowned directory our own `git add -A` commits, with
  // the guard's own messages (absolute paths included) in it. The filename is
  // DERIVED, never the raw session id: a host-supplied string with a slash or `..` in it
  // would put this write outside the cache directory (audit finding R3).
  const dedup = deduplicable(payload) && event === "PreToolUse";
  const cacheFile = join(root, ".ai-engineering", "cache", "verdicts", `${createHash("sha256").update(payload.session_id ?? "proc").digest("hex").slice(0, 32)}.json`);
  if (dedup) {
    const verdict = cachedVerdict(cacheFile, fp);
    if (verdict !== null) {
      if (verdict.deny) {
        return denyOutcome(verdict.by ?? "chain", verdict.message ?? "denied", [], event, options, started, root, tool);
      }
      return { action: "allow", guards: [], receiptId: null };
    }
  }

  const ran: string[] = [];
  let reviewResult: { reason: string; rule: { id: string; name: string; risk: number } } | undefined;
  for (const row of selected(event, tool)) {
    ran.push(row.name);
    const outcome = dispatchGuard(row.name, payload, ctx);
    if (outcome !== undefined && outcome.deny === true) {
      // A rewrite must never be cached as a hard denial: the verdict-cache shape only
      // knows deny/allow, and a replayed rewrite entry would flip the second delivery
      // of the same physical call from rewrite to deny (audit run-1). Uncached, the
      // redelivery simply re-runs the guards and rewrites again.
      if (dedup && outcome.rewriteTo === undefined) rememberVerdict(cacheFile, fp, { deny: true, by: row.name, message: outcome.reason });
      if (outcome.rewriteTo) {
        return rewriteOutcome(outcome.rewriteTo, ran, event, options, started, root);
      }
      return denyOutcome(row.name, outcome.reason, ran, event, options, started, root, tool, loopExact(payload));
    }
    // Phase 1: review outcomes are logged but do not block. The first review
    // match (highest risk, block-priority sorted) is recorded; subsequent
    // reviews within the same chain run are still collected but not surfaced.
    if (outcome !== undefined && outcome.deny === false && "review" in outcome && reviewResult === undefined) {
      reviewResult = { reason: outcome.reason, rule: outcome.rule };
    }
  }

  if (dedup) rememberVerdict(cacheFile, fp, { deny: false });
  const latency = Math.max(1, Date.now() - started);
  // Phase 1: if a local rule triggered review (not block), record it in the
  // receipt but still allow the call. The receipt carries the review metadata
  // for later analysis; the call itself proceeds.
  if (reviewResult !== undefined) {
    const receipt = writeReceipt({
      event,
      surface: options.surface ?? "unknown",
      tool,
      guards: { ran, denied_by: null },
      latency_ms: latency,
      outcome: "allow",
      session_id: sessionId(),
    }, root);
    return { action: "review", reason: reviewResult.reason, rule: reviewResult.rule, guards: ran, receiptId: receipt?.operation_id ?? null };
  }
  const receipt = writeReceipt({
    event,
    surface: options.surface ?? "unknown",
    tool,
    guards: { ran, denied_by: null },
    latency_ms: latency,
    outcome: "allow",
    session_id: sessionId(),
  }, root);
  return { action: "allow", guards: ran, receiptId: receipt?.operation_id ?? null };
}

function dispatchGuard(name: GuardName, payload: Payload, ctx: ChainContext): GuardOutcome {
  try {
    if (name === "wrap") {
      if (payload._event !== "PreToolUse") return undefined;
      const command = payload.tool_input["command"];
      if (typeof command !== "string") return undefined;
      const decision = isTestCommand(command);
      if (!decision.wrap) return undefined;
      return { deny: true, reason: `wrap: ${decision.runner}`, rewriteTo: rewrite(command) };
    }
    // self-protect, no-verify, injection and loop answer in one shape.
    // injection can also return { review: true, ... } — handled below.
    const result: GuardResult | InjectionGuardResult = (() => {
      switch (name) {
        case "self-protect":
          return runSelfProtect(payload, ctx.repoRoot);
        case "no-verify":
          return runNoVerify(payload, ctx.repoRoot);
        case "policy": {
          const command = payload.tool_input["command"];
          if (typeof command !== "string" || command.length === 0) return undefined;
          const cwd = typeof payload["cwd"] === "string" && payload["cwd"].length > 0 ? payload["cwd"] : process.cwd();
          return runPolicy(command, cwd, policyModeFor(ctx.repoRoot));
        }
        case "injection":
          return runInjection(payload);
        case "spoken-secret":
          return runSpokenSecret(payload);
        default:
          return runLoopGuard(payload, ctx.loopOverride);
      }
    })();
    if (result?.deny === true) return { deny: true, reason: result.reason };
    if (result && "review" in result && result.review && "reason" in result && "rule" in result) {
      const review = result as { reason: string; rule: { id: string; name: string; risk: number } };
      return { deny: false, review: true, reason: review.reason, rule: review.rule };
    }
    return undefined;
  } catch {
    // A guard that crashed is a guard that denies. The message says what a person
    // must do, never what the model could exploit.
    return {
      deny: true,
      reason: `BLOCKED: the ${name} guard could not decide (internal error), so nothing here can say whether the action is safe. Fix the guard.`,
    };
  }
}

function denyOutcome(
  by: string,
  reason: string,
  ran: string[],
  event: string,
  options: ChainOptions,
  started: number,
  root: string,
  tool: string,
  loopKey?: string,
): ChainOutcome {
  const latency = Math.max(1, Date.now() - started);
  // The cross-session ledger ticks once per real denial — here, never on a cached
  // replay of the same physical call, which would count one denial twice. The upsert
  // returns how many times this exact call was denied BEFORE this one; a repeat gets
  // one clause on the human-facing message. It never touches the verdict, and the
  // helper swallows every write failure for the same reason.
  if (loopKey !== undefined) {
    const repeats = upsertDenyLedger(receiptsDir(root), loopKey);
    if (repeats > 0) reason += ` · this exact call has been denied ${repeats} times before`;
  }
  const receipt = writeReceipt({
    event,
    surface: options.surface ?? "unknown",
    tool,
    guards: { ran, denied_by: by },
    latency_ms: latency,
    outcome: "deny",
    session_id: sessionId(),
  }, root);
  if (latency > HOT_PATH_BUDGET_MS) {
    process.stderr.write(`[ai-eng] chain: hot path over ${HOT_PATH_BUDGET_MS} ms (${latency} ms)\n`);
  }
  const outcome: ChainOutcome = { action: "deny", by, reason, guards: ran, receiptId: receipt?.operation_id ?? null };
  if (options.inProcess) return outcome;
  deny(by, reason, options.dialect ?? "claude", event);
}

function rewriteOutcome(
  command: string,
  ran: string[],
  event: string,
  options: ChainOptions,
  started: number,
  root: string,
): ChainOutcome {
  const latency = Math.max(1, Date.now() - started);
  const receipt = writeReceipt({
    event,
    surface: options.surface ?? "unknown",
    tool: "Bash",
    guards: { ran, denied_by: null },
    latency_ms: latency,
    outcome: "allow",
    session_id: sessionId(),
  }, root);
  const outcome: ChainOutcome = { action: "rewrite", command, guards: ran, receiptId: receipt?.operation_id ?? null };
  if (options.inProcess) return outcome;
  allowRewrite(command, options.dialect ?? "claude", event);
}

/** stdio entry used by `ai-eng chain <event>`: stdin payload → verdict on stdout. */
export function chainMain(event: string, raw: string, options: ChainOptions = {}): void {
  if (!raw.trim()) process.exit(0); // nothing was decided, so there is nothing to judge
  let body: Record<string, unknown>;
  try {
    body = JSON.parse(raw) as Record<string, unknown>;
    if (body === null || Array.isArray(body) || typeof body !== "object") throw new Error("not an object");
  } catch {
    deny("chain", "BLOCKED: the hook payload could not be read, so nothing here can say whether this action is safe.", options.dialect ?? "claude", event);
  }
  const outcome = runChain(body, event, options);
  // An allow is a verdict too, and one host reads an empty answer as a refusal.
  if (outcome.action === "allow") allow(options.dialect ?? "claude");
  process.exit(0);
}
