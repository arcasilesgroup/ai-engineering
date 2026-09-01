// The dispatcher. One process per call (or one import in-process), the only way to
// run anything. Ported from v1 chain.py (370 LOC): table event→guards, verdict cache
// keyed on the fingerprint of one physical call, fail-closed on any guard crash —
// a guard that cannot decide denies, because denying everything on a surface is how
// you disable a whole product by installing it.

import { repoRoot, adoptSession, receiptsDir } from "../env.ts";
import { normalise, deduplicable, fingerprint } from "./payload.ts";
import type { Payload, SurfaceAdapter } from "./payload.ts";
import { deny, VerdictCache, readOverrides, overrideActive } from "./dialect.ts";
import { runNoVerify } from "../guards/no-verify.ts";
import { runSelfProtect } from "../guards/self-protect.ts";
import { runInjection } from "../guards/injection.ts";
import { runLoopGuard } from "../guards/loop.ts";
import { isTestCommand, rewrite } from "../guards/wrap.ts";
import { writeReceipt } from "../receipts.ts";

export type GuardName = "self-protect" | "no-verify" | "injection" | "loop" | "wrap";

type GuardRow = { name: GuardName; matcher: RegExp };
type GuardOutcome = { deny: true; reason: string; rewriteTo?: string } | undefined;

export type ChainContext = {
  repoRoot: string | null;
  loopOverride: boolean;
};

/** event -> [(guard, tool matcher)]. Adding an entry point means adding a row here,
 *  and this table is what emits: there is no way to add a hook without instrumentation. */
export const TABLE: Record<string, GuardRow[]> = {
  PreToolUse: [
    { name: "self-protect", matcher: /^(Edit|Write|MultiEdit|NotebookEdit|Bash|PowerShell|shell|command)$/ },
    { name: "no-verify", matcher: /^(Bash|PowerShell|shell|command|Edit|Write|MultiEdit|NotebookEdit)$/ },
    { name: "injection", matcher: /^(Read|NotebookRead|ReadFile)$/ },
    { name: "wrap", matcher: /^(Bash|PowerShell|shell|command)$/ },
    { name: "loop", matcher: /^.*$/ },
  ],
  PostToolUse: [
    { name: "injection", matcher: /^(WebFetch|Fetch|WebSearch|mcp__.*|tool_result)$/ },
    { name: "loop", matcher: /^.*$/ },
  ],
};

const HOT_PATH_BUDGET_MS = 200;

export type ChainOptions = {
  /** How the verdict leaves: process exit (stdio) or interpreted by an in-process plugin. */
  dialect?: "claude-structured" | "exit2" | "throw" | "block-json";
  surface?: string;
  adapters?: SurfaceAdapter[];
  /** In-process mode returns outcomes instead of exiting (OMP/OpenCode plugins). */
  inProcess?: boolean;
  stateDir?: string;
  now?: () => number;
};

export type ChainOutcome =
  | { action: "allow"; guards: string[]; receiptId: string | null }
  | { action: "deny"; by: string; reason: string; guards: string[]; receiptId: string | null }
  | { action: "rewrite"; command: string; guards: string[]; receiptId: string | null };

function selected(event: string, tool: string): GuardRow[] {
  return (TABLE[event] ?? []).filter((row) => row.matcher.test(tool));
}

/** Run the chain over a normalized payload. A crash inside a guard is a DENY, not a pass. */
export function runChain(rawPayload: Record<string, unknown>, event: string, options: ChainOptions = {}): ChainOutcome {
  const started = (options.now ?? Date.now)();
  const root = repoRoot();
  if (rawPayload === null || Array.isArray(rawPayload) || typeof rawPayload !== "object") {
    return denyOutcome("chain", "BLOCKED: the hook payload could not be read, so nothing here can say whether this action is safe.", [], event, options, started, root, false);
  }
  const payload = normalise(rawPayload, options.adapters ?? []);
  adoptSession(payload.session_id);
  payload._event = event;
  payload._structured = options.dialect === "claude-structured" || Boolean(payload["transcript_path"]);
  const tool = payload.tool_name;
  const fp = fingerprint(payload);
  payload._fp = fp;
  payload._dedup = deduplicable(payload);

  const overrides = readOverrides(root);
  const ctx: ChainContext = { repoRoot: root, loopOverride: overrideActive(overrides, "loop") !== null };

  // Same call, same answer: no guard decides the same call twice. The cache lives
  // under the governed repo; a repo-less call skips it.
  const dedup = payload._dedup && event === "PreToolUse" && root !== null;
  const cache = new VerdictCache(root ?? options.stateDir ?? ".", payload.session_id ?? "proc");
  if (dedup) {
    const verdict = cache.read(fp);
    if (verdict !== null) {
      if (verdict.deny) {
        return denyOutcome(verdict.by ?? "chain", verdict.message ?? "denied", [], event, options, started, root, false);
      }
      return { action: "allow", guards: [], receiptId: null };
    }
  }

  const ran: string[] = [];
  for (const row of selected(event, tool)) {
    ran.push(row.name);
    const outcome = dispatchGuard(row.name, payload, ctx);
    if (outcome !== undefined && outcome.deny) {
      if (dedup) cache.remember(fp, { deny: true, by: row.name, message: outcome.reason });
      if (outcome.rewriteTo) {
        return rewriteOutcome(outcome.rewriteTo, ran, event, options, started);
      }
      return denyOutcome(row.name, outcome.reason, ran, event, options, started, root, dedup);
    }
  }

  if (dedup) cache.remember(fp, { deny: false });
  const latency = Math.max(1, (options.now ?? Date.now)() - started);
  const receipt = writeReceipt({
    event,
    surface: options.surface ?? "unknown",
    tool,
    guards: { ran, denied_by: null },
    latency_ms: latency,
    outcome: "allow",
  });
  return { action: "allow", guards: ran, receiptId: receipt?.operation_id ?? null };
}

function dispatchGuard(name: GuardName, payload: Payload, ctx: ChainContext): GuardOutcome {
  try {
    switch (name) {
      case "self-protect": {
        const result = runSelfProtect(payload, ctx.repoRoot);
        return result?.deny === true ? { deny: true, reason: result.reason } : undefined;
      }
      case "no-verify": {
        const result = runNoVerify(payload, ctx.repoRoot);
        return result?.deny === true ? { deny: true, reason: result.reason } : undefined;
      }
      case "injection": {
        const result = runInjection(payload);
        return result?.deny === true ? { deny: true, reason: result.reason } : undefined;
      }
      case "loop": {
        const result = runLoopGuard(payload, ctx.loopOverride);
        return result?.deny === true ? { deny: true, reason: result.reason } : undefined;
      }
      case "wrap": {
        if (payload._event !== "PreToolUse") return undefined;
        const command = payload.tool_input["command"];
        if (typeof command !== "string") return undefined;
        const decision = isTestCommand(command);
        if (!decision.wrap) return undefined;
        return { deny: true, reason: `wrap: ${decision.runner}`, rewriteTo: rewrite(command) };
      }
    }
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
  _root: string | null,
  _dedup: boolean,
): ChainOutcome {
  const latency = Math.max(1, (options.now ?? Date.now)() - started);
  const receipt = writeReceipt({
    event,
    surface: options.surface ?? "unknown",
    tool: "unknown",
    guards: { ran, denied_by: by },
    latency_ms: latency,
    outcome: "deny",
  });
  if (latency > HOT_PATH_BUDGET_MS) {
    process.stderr.write(`[ai-eng] chain: hot path over ${HOT_PATH_BUDGET_MS} ms (${latency} ms)\n`);
  }
  const outcome: ChainOutcome = { action: "deny", by, reason, guards: ran, receiptId: receipt?.operation_id ?? null };
  if (options.inProcess) return outcome;
  deny(by, reason, options.dialect ?? "exit2");
}

function rewriteOutcome(
  command: string,
  ran: string[],
  event: string,
  options: ChainOptions,
  started: number,
): ChainOutcome {
  const latency = Math.max(1, (options.now ?? Date.now)() - started);
  const receipt = writeReceipt({
    event,
    surface: options.surface ?? "unknown",
    tool: "Bash",
    guards: { ran, denied_by: null },
    latency_ms: latency,
    outcome: "allow",
  });
  const outcome: ChainOutcome = { action: "rewrite", command, guards: ran, receiptId: receipt?.operation_id ?? null };
  if (options.inProcess) return outcome;
  const dialect = options.dialect ?? "exit2";
  if (dialect === "claude-structured") {
    process.stdout.write(
      `${JSON.stringify({ hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "allow", updatedInput: { command } } })}\n`,
    );
    process.exit(0);
  }
  if (dialect === "block-json") {
    process.stdout.write(`${JSON.stringify({ decision: "allow", updated_input: { command } })}\n`);
    process.exit(0);
  }
  if (dialect === "throw") {
    throw Object.assign(new Error(`[ai-eng] wrap: rewritten to ${command}`), { rewrite: command });
  }
  process.stdout.write(`${JSON.stringify({ permission: "allow", updatedInput: { command } })}\n`);
  process.exit(0);
}

/** stdio entry used by `ai-eng chain <event>`: stdin payload → verdict on stdout. */
export function chainMain(event: string, raw: string, options: ChainOptions = {}): void {
  if (!raw.trim()) process.exit(0); // nothing was decided, so there is nothing to judge
  let body: Record<string, unknown>;
  try {
    body = JSON.parse(raw) as Record<string, unknown>;
    if (body === null || Array.isArray(body) || typeof body !== "object") throw new Error("not an object");
  } catch {
    deny("chain", "BLOCKED: the hook payload could not be read, so nothing here can say whether this action is safe.", options.dialect ?? "exit2");
  }
  runChain(body, event, options);
  process.exit(0);
}

export function receiptsLocation(): string | null {
  return receiptsDir();
}
