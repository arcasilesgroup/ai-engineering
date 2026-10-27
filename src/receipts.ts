// The receipt — one JSON per execution, append-only. No envelope, no HMAC, no
// hash-chain: the real signature is the Receipt-Id trailer in the commit — git
// already is the chain.

import { closeSync, openSync, writeFileSync, readFileSync, readdirSync, mkdirSync, existsSync, lstatSync, renameSync, rmSync, unlinkSync } from "node:fs";
import { join } from "node:path";
import { createHash, randomUUID } from "node:crypto";
import { loadConfig, printable, receiptsDir, type Config } from "./env.ts";

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

/** The running aggregate one receipt folds into. Kept as a plain record so the fold
 *  is a small function of its own: `summarizeReceipts` keeps the scan (which files,
 *  which window) and `tallyReceipt` keeps the arithmetic, and neither carries the
 *  other's nesting. */
interface ReceiptTally {
  total: number;
  denies: number;
  latencies: number[];
  per: Record<"per_guard" | "per_tool" | "per_surface", Record<string, number>>;
  daily: Record<string, DailyPoint>;
}

/** Fold one receipt into the tally. The deny buckets and the daily series are
 *  independent of each other, and the latency is independent of both: a receipt
 *  with no `ts` still counts its latency. */
function tallyReceipt(receipt: Receipt, tally: ReceiptTally): void {
  tally.total += 1;
  if (receipt.outcome === "deny") {
    tally.denies += 1;
    // Keys come from files an adversary inside the repo may write — they reach
    // doctor's HUMAN line as-is. printable() (env.ts) is the repo's own strip of
    // control/ANSI characters, applied here at the source so no consumer must
    // remember it (audit run-1 F3: a receipt's denied_by forged whole ✓ rows).
    const guard = printable(receipt.guards?.denied_by ?? "chain");
    const tool = printable(receipt.tool);
    const surface = printable(receipt.surface);
    tally.per.per_guard[guard] = (tally.per.per_guard[guard] ?? 0) + 1;
    tally.per.per_tool[tool] = (tally.per.per_tool[tool] ?? 0) + 1;
    tally.per.per_surface[surface] = (tally.per.per_surface[surface] ?? 0) + 1;
  }
  const day = typeof receipt.ts === "string" ? printable(receipt.ts.slice(0, 10)) : "";
  if (day !== "") {
    const point = tally.daily[day] ?? { runs: 0, denies: 0 };
    point.runs += 1;
    if (receipt.outcome === "deny") point.denies += 1;
    tally.daily[day] = point;
  }
  if (typeof receipt.latency_ms === "number" && isChainReceipt(receipt.event)) tally.latencies.push(receipt.latency_ms);
}

/** doctor's aggregate: without this you don't know whether the chain runs at all —
 *  nor who denies, on what tool, on which day (research/001 R1: the gc must stop
 *  throwing away the story the receipts already tell). */
export function summarizeReceipts(dir?: string | null): ReceiptSummary {
  // `dir` is tri-state: `undefined` = resolve the caller's repo, `null` = no store
  // at all (the caller already knows this root has none), a string = that store.
  const target = dir === undefined ? receiptsDir() : dir;
  const tally = emptyTally();
  if (target) {
    try {
      // The filename carries the ISO timestamp the receipt was written with, so the
      // window is cut by name before any file is opened: a repo that runs the chain
      // all day accumulates tens of thousands of receipts, and every reader pays this
      // scan — opening each file for 36k receipts cost 5 s on the dev machine. Files that predate the window are either past
      // the gc's TTL (config.toml `[gc].receipts_ttl`, default 30d — the gc
      // aggregates and deletes them) or a fixture with a crafted name, and the
      // doctor's deviation rule reads a 14-day window, so a 40-day stamp covers
      // both. Only a timestamped name is skipped unopened; every other file —
      // fixtures, future shapes — is parsed exactly as before.
      const cutoff = new Date(Date.now() - 40 * 86_400_000).toISOString().slice(0, 10).replaceAll("-", "");
      for (const name of readdirSync(target)) {
        if (!name.endsWith(".json")) continue;
        // gc writes its own summary into this folder; counting it as a receipt would
        // inflate the total by one on every collection (§21.3).
        if (name === "summary.json" || name === "denies.json") continue;
        if (/^\d{4}-\d{2}-\d{2}T/.test(name) && name.slice(0, 10).replaceAll("-", "") < cutoff) continue;
        try {
          tallyReceipt(JSON.parse(readFileSync(join(target, name), "utf8")) as Receipt, tally);
        } catch {
          /* a torn write is data, not a crash */
        }
      }
    } catch {
      /* no receipts yet */
    }
  }
  return summaryOf(tally);
}

function emptyTally(): ReceiptTally {
  return { total: 0, denies: 0, latencies: [], per: { per_guard: {}, per_tool: {}, per_surface: {} }, daily: {} };
}

function summaryOf(tally: ReceiptTally): ReceiptSummary {
  const { latencies } = tally;
  latencies.sort((a, b) => a - b);
  const pick = (q: number) => (latencies.length ? latencies[Math.min(latencies.length - 1, Math.floor(q * latencies.length))]! : 0);
  return { total: tally.total, denies: tally.denies, p50: pick(0.5), p95: pick(0.95), ...tally.per, daily: tally.daily };
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
            first_ts: existing === undefined || (typeof receipt.ts === "string" && receipt.ts < existing.first_ts)
              ? (typeof receipt.ts === "string" ? receipt.ts : (existing?.first_ts ?? ""))
              : existing.first_ts,
            last_ts: existing === undefined || (typeof receipt.ts === "string" && receipt.ts > existing.last_ts)
              ? (typeof receipt.ts === "string" ? receipt.ts : (existing?.last_ts ?? ""))
              : existing.last_ts,
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

/** The most receipts one automatic retention pass deletes. A repo that never ran the
 *  gc may hold tens of thousands, and the chain call that triggers the pass must not
 *  pay for all of them at once: while a backlog remains, the next call takes the next
 *  batch. */
export const RECEIPTS_GC_BATCH = 500;

/** `[gc].receipts_ttl` in days ("30d" when the key is absent). */
export function receiptsTtlDays(config: Config): number {
  return Number(String(config["gc"]?.["receipts_ttl"] ?? "30d").replace("d", ""));
}

/** The ISO timestamp writeReceipt puts at the front of every receipt name. */
const RECEIPT_STAMP = /^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z/;
const stampOf = (ms: number): string => new Date(ms).toISOString().replace(/[:.]/g, "-");

/** Fold the receipts this pass collected into summary.json. The daily series is the
 *  gc's long-term memory and is additive — each receipt is tallied once, on the pass
 *  that deletes it, so a day split across batches sums instead of being overwritten.
 *  The other figures describe the receipts this pass collected; `total` is how many
 *  receipts the store held when the pass ran. Written via rename so a reader never
 *  sees a torn file — a torn summary reads back as no prior and loses the series. */
function mergeAndWriteSummary(receipts: string, collected: ReceiptSummary, total: number, now: number): void {
  let prior: { daily?: Record<string, DailyPoint> } | null = null;
  try {
    prior = JSON.parse(readFileSync(join(receipts, "summary.json"), "utf8")) as { daily?: Record<string, DailyPoint> };
  } catch {
    /* no prior summary, or a torn one: the collected batch starts the series */
  }
  const summed: Record<string, DailyPoint> = {};
  for (const [day, point] of Object.entries(collected.daily)) {
    const before = prior?.daily?.[day];
    summed[day] = { runs: count(before?.runs) + point.runs, denies: count(before?.denies) + point.denies };
  }
  const merged = { ...collected, total, daily: mergeDaily(prior?.daily, summed, 90, now), gc: new Date(now).toISOString() };
  // Not a .json name, and never a receipt stamp: no reader counts it, no sweep ages it as a receipt.
  const staging = join(receipts, `.summary-${randomUUID()}.tmp`);
  try {
    writeFileSync(staging, JSON.stringify(merged));
    renameSync(staging, join(receipts, "summary.json"));
  } finally {
    rmSync(staging, { force: true });
  }
}

/** One gc pass over the receipts folder: how many it deleted, and whether stale
 *  receipts were left for a later pass. */
type ReceiptsPass = { deleted: number; hasBacklog: boolean };

/** The pass behind gcReceipts. Its cost is bounded by the batch, not by the store:
 *  staleness comes from the timestamp writeReceipt put in the name, so the folder is
 *  listed once and only the receipts being deleted are stat-ed and opened (F7: 36k
 *  opens cost 5 s, and the automatic pass runs inside a tool-use hook). A name
 *  without that stamp (a fixture, a future shape) is aged by its mtime instead. */
function collectReceipts(receipts: string, ttlDays: number, maxDeletes: number | undefined, now: number): ReceiptsPass {
  const cutStamp = stampOf(now - ttlDays * 86_400_000);
  const stale: { stamp: string; name: string }[] = [];
  let stored = 0;
  for (const name of readdirSync(receipts)) {
    // The gc's own memory, not its trash: summary.json (the series) and denies.json
    // (the ledger) are pruned by their contents, never swept by age.
    if (name === "summary.json" || name === "denies.json") continue;
    if (name.endsWith(".json")) stored += 1;
    const named = RECEIPT_STAMP.exec(name)?.[0];
    if (named !== undefined) {
      if (named < cutStamp) stale.push({ stamp: named, name });
      continue;
    }
    try {
      const { mtimeMs } = lstatSync(join(receipts, name));
      const aged = stampOf(mtimeMs);
      if (aged < cutStamp) stale.push({ stamp: aged, name });
    } catch {
      /* gone between the listing and the stat: nothing left to collect */
    }
  }
  stale.sort((a, b) => (a.stamp < b.stamp ? -1 : a.stamp > b.stamp ? 1 : 0));
  const limit = maxDeletes ?? stale.length;
  const tally = emptyTally();
  let deleted = 0;
  let consumed = 0;
  for (const entry of stale) {
    if (deleted >= limit) break;
    consumed += 1;
    const path = join(receipts, entry.name);
    try {
      // Files only: a planted DIRECTORY named like a receipt (`mkdir bomb.json`) made
      // unlinkSync throw before the summary write, bricking the gc on every future
      // run (audit run-1 F4). A directory in the receipts folder is not a receipt.
      if (!lstatSync(path).isFile()) continue;
      const text = readFileSync(path, "utf8");
      unlinkSync(path);
      deleted += 1;
      // Tallied only once the unlink succeeded, so two passes never count one receipt twice.
      try {
        tallyReceipt(JSON.parse(text) as Receipt, tally);
      } catch {
        /* a torn write is data, not a crash */
      }
    } catch {
      /* a concurrent pass took it first */
    }
  }
  if (deleted > 0) mergeAndWriteSummary(receipts, summaryOf(tally), stored, now);
  const ledger = join(receipts, "denies.json");
  if (existsSync(ledger)) pruneDenyLedger(ledger, 90, LEDGER_CAP, now);
  return { deleted, hasBacklog: consumed < stale.length };
}

/** The gc's receipts pass; returns how many receipts it deleted. `maxDeletes` bounds
 *  one pass (oldest first) — `doctor --gc` leaves it unbounded. Receipts carry no
 *  citation to respect: their permanent half is the Receipt-Id trailer on the commit. */
export function gcReceipts(receipts: string, ttlDays: number, options: { maxDeletes?: number; now?: number } = {}): number {
  if (!existsSync(receipts)) return 0;
  return collectReceipts(receipts, ttlDays, options.maxDeletes, options.now ?? Date.now()).deleted;
}

/** Automatic retention, run by the chain after it writes its receipt: at most
 *  RECEIPTS_GC_BATCH deletions per pass, and once the backlog is clear, at most one
 *  pass per calendar day (UTC) per repo. Never throws — housekeeping must not change
 *  a verdict. */
export function retainReceipts(root: string, now = Date.now()): { ran: boolean; deleted: number } {
  const idle = { ran: false, deleted: 0 };
  const today = new Date(now).toISOString().slice(0, 10);
  // The claim lives in the gitignored cache, not the receipts folder, so no reader of
  // receipts ever sees it and the sweep can never delete it.
  const cache = join(root, ".ai-engineering", "cache");
  const claim = join(cache, `receipts-retention-${today}`);
  try {
    mkdirSync(cache, { recursive: true });
    // Exclusive create: of the parallel tool calls that open a day, exactly one runs
    // the pass. Already claimed, or an unwritable cache — either way, skip.
    closeSync(openSync(claim, "wx"));
  } catch {
    return idle;
  }
  let pass: ReceiptsPass = { deleted: 0, hasBacklog: false };
  try {
    const receipts = join(root, ".ai-engineering", "receipts");
    if (existsSync(receipts)) pass = collectReceipts(receipts, receiptsTtlDays(loadConfig(root)), RECEIPTS_GC_BATCH, now);
  } catch {
    /* the day stays claimed: a pass that throws is not retried on every call */
  }
  try {
    // A backlog bigger than one batch drains over the next calls; the day is only
    // done once a pass leaves nothing stale behind.
    if (pass.hasBacklog) rmSync(claim, { force: true });
    for (const name of readdirSync(cache)) {
      if (name.startsWith("receipts-retention-") && name !== `receipts-retention-${today}`) rmSync(join(cache, name), { force: true });
    }
  } catch {
    /* a claim that cannot be released only delays the next batch to tomorrow */
  }
  return { ran: true, deleted: pass.deleted };
}
