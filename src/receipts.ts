// The receipt — one JSON per execution, append-only. No envelope, no HMAC, no
// hash-chain: the real signature is the Receipt-Id trailer in the commit — git
// already is the chain.

import { writeFileSync, readFileSync, readdirSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { createHash, randomUUID } from "node:crypto";
import { printable, receiptsDir } from "./env.ts";

export type Receipt = {
  schema: "urn:ai-eng:receipt:2";
  operation_id: string;
  event: string;
  surface: string;
  tool: string;
  guards: { ran: string[]; denied_by: string | null };
  latency_ms: number;
  outcome: "allow" | "deny" | "error";
  ts: string;
  /** The session this receipt belongs to. Present when the surface sent a session
   *  id; absent in legacy receipts and git-floor writes. Groupable via
   *  summarizeBySession(). */
  session_id?: string;
};

export function writeReceipt(receipt: Omit<Receipt, "schema" | "operation_id" | "ts">, root?: string | null): Receipt | null {
  const dir = receiptsDir(root);
  if (!dir) return null; // a stray call with no governed repo writes nothing
  const full: Receipt = {
    schema: "urn:ai-eng:receipt:2",
    operation_id: randomUUID().slice(0, 8),
    ts: new Date().toISOString(),
    ...receipt,
  };
  try {
    mkdirSync(dir, { recursive: true });
    const stamp = full.ts.replace(/[:.]/g, "-");
    writeFileSync(join(dir, `${stamp}-${full.event}-${full.operation_id}.json`), JSON.stringify(full));
    return full;
  } catch {
    return null;
  }
}

export type DailyPoint = { runs: number; denies: number };

export type ReceiptSummary = {
  total: number;
  denies: number;
  p50: number;
  p95: number;
  /** deny counts by guards.denied_by, by tool, by surface — the "unknown" tool of the
   *  unreadable-payload deny is its own honest bucket, never merged into a real one. */
  per_guard: Record<string, number>;
  per_tool: Record<string, number>;
  per_surface: Record<string, number>;
  /** ISO-date → activity of that day, from the receipts' own ts. */
  daily: Record<string, DailyPoint>;
};

/** True for a receipt that ran the surface tool-use guard chain (the only runs the
 *  50ms ceiling in doctor measures). The git floor (gitleaks ~700ms) and the spec
 *  runner (the gate suite, seconds) write receipts too, but they have their own
 *  budgets — pulling them into the chain p95 makes the chain look slow when it
 *  isn't. */
export function isChainReceipt(event: string): boolean {
  return !/^(git-|commit-msg|spec-)/.test(event);
}

/** doctor's aggregate: without this you don't know whether the chain runs at all —
 *  nor who denies, on what tool, on which day (research/001 R1: the gc must stop
 *  throwing away the story the receipts already tell). */
export function summarizeReceipts(dir?: string): ReceiptSummary {
  const target = dir ?? receiptsDir();
  const latencies: number[] = [];
  let total = 0;
  let denies = 0;
  const per: Record<"per_guard" | "per_tool" | "per_surface", Record<string, number>> = {
    per_guard: {}, per_tool: {}, per_surface: {},
  };
  const daily: Record<string, DailyPoint> = {};
  if (target) {
    try {
      for (const name of readdirSync(target)) {
        if (!name.endsWith(".json")) continue;
        // gc writes its own summary into this folder; counting it as a receipt would
        // inflate the total by one on every collection (§21.3).
        if (name === "summary.json" || name === "denies.json") continue;
        try {
          const receipt = JSON.parse(readFileSync(join(target, name), "utf8")) as Receipt;
          total += 1;
          // Keys come from files an adversary inside the repo may write — they reach
          // doctor's HUMAN line as-is. printable() (env.ts) is the repo's own strip of
          // control/ANSI characters, applied here at the source so no consumer must
          // remember it (audit run-1 F3: a receipt's denied_by forged whole ✓ rows).
          if (receipt.outcome === "deny") {
            denies += 1;
            const guard = printable(receipt.guards?.denied_by ?? "chain");
            const tool = printable(receipt.tool);
            const surface = printable(receipt.surface);
            per.per_guard[guard] = (per.per_guard[guard] ?? 0) + 1;
            per.per_tool[tool] = (per.per_tool[tool] ?? 0) + 1;
            per.per_surface[surface] = (per.per_surface[surface] ?? 0) + 1;
          }
          const day = typeof receipt.ts === "string" ? printable(receipt.ts.slice(0, 10)) : "";
          if (day !== "") {
            const point = daily[day] ?? { runs: 0, denies: 0 };
            point.runs += 1;
            if (receipt.outcome === "deny") point.denies += 1;
            daily[day] = point;
          }
          if (typeof receipt.latency_ms === "number" && isChainReceipt(receipt.event)) latencies.push(receipt.latency_ms);
        } catch {
          /* a torn write is data, not a crash */
        }
      }
    } catch {
      /* no receipts yet */
    }
  }
  latencies.sort((a, b) => a - b);
  const pick = (q: number) => (latencies.length ? latencies[Math.min(latencies.length - 1, Math.floor(q * latencies.length))]! : 0);
  return { total, denies, p50: pick(0.5), p95: pick(0.95), ...per, daily };
}

export type SessionSummary = {
  session_id: string;
  runs: number;
  denies: number;
  first_ts: string;
  last_ts: string;
  tools: string[];
  guards_denied: string[];
};

/** Group receipts by session_id. Sessions without a session_id are grouped under
 *  "unknown". Returns sessions sorted by last_ts descending (most recent first). */
export function summarizeBySession(dir?: string): SessionSummary[] {
  const target = dir ?? receiptsDir();
  const sessions = new Map<string, { runs: number; denies: number; first_ts: string; last_ts: string; tools: Set<string>; guards_denied: Set<string> }>();
  if (target) {
    try {
      for (const name of readdirSync(target)) {
        if (!name.endsWith(".json")) continue;
        if (name === "summary.json" || name === "denies.json") continue;
        try {
          const receipt = JSON.parse(readFileSync(join(target, name), "utf8")) as Receipt;
          const sid = receipt.session_id ?? "unknown";
          const existing = sessions.get(sid);
          const tools = existing?.tools ?? new Set<string>();
          const guards_denied = existing?.guards_denied ?? new Set<string>();
          if (typeof receipt.tool === "string") tools.add(printable(receipt.tool));
          if (receipt.outcome === "deny" && typeof receipt.guards?.denied_by === "string") {
            guards_denied.add(printable(receipt.guards.denied_by));
          }
          sessions.set(sid, {
            runs: (existing?.runs ?? 0) + 1,
            denies: (existing?.denies ?? 0) + (receipt.outcome === "deny" ? 1 : 0),
            first_ts: existing?.first_ts ?? (typeof receipt.ts === "string" ? receipt.ts : ""),
            last_ts: typeof receipt.ts === "string" ? receipt.ts : (existing?.last_ts ?? ""),
            tools,
            guards_denied,
          });
        } catch {
          /* torn write */
        }
      }
    } catch {
      /* no receipts */
    }
  }
  return [...sessions.entries()]
    .map(([session_id, s]) => ({
      session_id,
      runs: s.runs,
      denies: s.denies,
      first_ts: s.first_ts,
      last_ts: s.last_ts,
      tools: [...s.tools],
      guards_denied: [...s.guards_denied],
    }))
    .sort((a, b) => b.last_ts.localeCompare(a.last_ts));
}

/** A summand from a file an adversary may have written: finite, non-negative, whole,
 *  or zero. Hostile shapes (string, NaN, boolean, object) never reach a human sum. */
const count = (v: unknown): number => (typeof v === "number" && Number.isFinite(v) && v >= 0 ? Math.floor(v) : 0);

/** The gc merge, kept beside the reader it serves: the live window wins per day-key
 *  (the raw receipts are always fresher than the summary they aggregate), days older
 *  than keepDays fall off the front, and a prior summary that is missing or torn is
 *  simply no prior — a torn write is data, not a crash, at this boundary too.
 *  Values from the prior file are coerced to non-negative finite integers (audit
 *  run-1 F2): a forged string/NaN/boolean must never flow into a human sum. */
export function mergeDaily(
  prior: Record<string, DailyPoint> | undefined,
  current: Record<string, DailyPoint>,
  keepDays = 90,
  now = Date.now(),
): Record<string, DailyPoint> {
  const merged: Record<string, DailyPoint> = { ...prior, ...current };
  const cutoff = new Date(now - keepDays * 86_400_000).toISOString().slice(0, 10);
  const out: Record<string, DailyPoint> = {};
  for (const [day, point] of Object.entries(merged)) {
    if (day >= cutoff) out[day] = { runs: count(point?.runs), denies: count(point?.denies) };
  }
  return out;
}

/** Stable short id for a Receipt-Id trailer. */
export function receiptId(receipt: Receipt): string {
  return createHash("sha256").update(`${receipt.ts}:${receipt.operation_id}`).digest("hex").slice(0, 8);
}

/** The cross-session deny ledger (research/001 R2): key → {times denied, last seen}.
 *  One small file in the receipts folder that the gc prunes instead of sweeping.
 *  todo: read-modify-write races between concurrent hook processes lose an
 *  increment; this is a bell, not enforcement, and a lost count changes a clause's
 *  number, never a verdict. */
export type DenyLedger = Record<string, { n: number; last_seen: string }>;

/** Cap shared by the hot-path upsert and the gc prune: a forged oversized ledger
 *  stops being oversized at the very next denial (audit run-1: the file is
 *  attacker-writable and read+rewritten on the deny hot path). */
export const LEDGER_CAP = 500;

/** Record one denial of an exact call; returns how many denials of that key were
 *  ALREADY there (0 = the first, so the caller knows whether to say "seen before").
 *  Every failure mode returns 0 and moves on: signal must never break the chain,
 *  and an unwritable or corrupt ledger must not change what the guard answers. */
export function upsertDenyLedger(dir: string | null, key: string): number {
  if (!dir) return 0;
  try {
    const file = join(dir, "denies.json");
    let ledger: DenyLedger = {};
    try {
      ledger = JSON.parse(readFileSync(file, "utf8")) as DenyLedger;
    } catch {
      /* first entry, or a torn file — both mean no prior */
    }
    const prior = typeof ledger[key]?.n === "number" && Number.isFinite(ledger[key]!.n) ? Math.max(0, Math.floor(ledger[key]!.n)) : 0;
    ledger[key] = { n: prior + 1, last_seen: new Date().toISOString() };
    mkdirSync(dir, { recursive: true });
    // Re-emit at most the newest LEDGER_CAP well-formed entries: attacker-planted
    // bulk and hostile shapes never survive the round-trip on the hot path.
    const fresh = Object.entries(ledger)
      .filter(([, entry]) => typeof entry?.last_seen === "string" && Number.isFinite(entry?.n))
      .sort((a, b) => (a[1].last_seen < b[1].last_seen ? 1 : -1))
      .slice(0, LEDGER_CAP);
    const kept: DenyLedger = {};
    for (const [k, entry] of fresh) kept[k] = { n: Math.max(1, Math.floor(entry.n)), last_seen: entry.last_seen };
    writeFileSync(file, JSON.stringify(kept));
    return prior;
  } catch {
    return 0;
  }
}

/** The gc's ledger pass: entries nobody has seen in ttlDays fall off, and the file
 *  is capped at the newest `cap` keys by last_seen. The ledger IS the aggregate —
 *  the sweep must never delete it by mtime, which is why it prunes by content. */
export function pruneDenyLedger(file: string, ttlDays = 90, cap = LEDGER_CAP, now = Date.now()): void {
  try {
    const ledger = JSON.parse(readFileSync(file, "utf8")) as DenyLedger;
    const cutoff = new Date(now - ttlDays * 86_400_000).toISOString();
    const fresh = Object.entries(ledger)
      .filter(([, entry]) => typeof entry?.last_seen === "string" && entry.last_seen >= cutoff)
      .sort((a, b) => (a[1].last_seen < b[1].last_seen ? 1 : -1))
      .slice(0, cap);
    const kept: DenyLedger = {};
    for (const [key, entry] of fresh) kept[key] = entry;
    writeFileSync(file, JSON.stringify(kept));
  } catch {
    /* a ledger that cannot be read cannot be pruned; the chain keeps writing it */
  }
}
