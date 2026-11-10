// The receipt — one JSON per execution, append-only. No envelope, no HMAC, no
// hash-chain: the real signature is the Receipt-Id trailer in the commit — git
// already is the chain.

import { closeSync, constants, openSync, writeFileSync, readFileSync, readdirSync, mkdirSync, lstatSync, realpathSync, renameSync, rmSync, unlinkSync } from "node:fs";
import { dirname, join } from "node:path";
import { createHash, randomUUID } from "node:crypto";
import { loadConfig, printable, receiptsDir, type Config } from "./env.ts";
import { readProjectFileSnapshot, safeProjectPath, takeCheckedProjectFile, withCheckedProjectParent } from "./shared-project-fs.ts";

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
  /** The session this receipt belongs to when the surface supplied an id. */
  session_id?: string;
};

const AI_DIR = ".ai-engineering";
const RECEIPTS_REL = `${AI_DIR}/receipts`;

/** Where a repo's receipts folder stands. A cloned repo can commit `.ai-engineering` or
 *  `receipts` as a link into the user's home; every reader that writes or deletes there
 *  first needs it `checked`: both are real folders whose real path stays inside the repo. */
type ReceiptsFolder = { kind: "checked"; path: string } | { kind: "absent" } | { kind: "refused"; rel: string };

function receiptsFolder(root: string): ReceiptsFolder {
  for (const rel of [AI_DIR, RECEIPTS_REL]) {
    try {
      lstatSync(join(root, rel));
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === "ENOENT") return { kind: "absent" };
      return { kind: "refused", rel };
    }
    if (safeProjectPath(root, rel) === null) return { kind: "refused", rel };
  }
  const path = safeProjectPath(root, RECEIPTS_REL);
  return path === null ? { kind: "refused", rel: RECEIPTS_REL } : { kind: "checked", path };
}

/** The checked receipts folder, created when missing and checked again after the create
 *  (R38); null when it cannot be proven to be the repo's own folder. */
function ensureReceiptsFolder(root: string): string | null {
  const aiDir = safeProjectPath(root, AI_DIR);
  if (aiDir === null) return null;
  try {
    mkdirSync(join(aiDir, "receipts"));
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "EEXIST") return null;
  }
  return safeProjectPath(root, RECEIPTS_REL);
}

/** The event names its receipt file, and a caller- or surface-supplied `/` in it would
 *  send the write into a subfolder no reader, retention pass or summary ever lists —
 *  the receipt would vanish. Flattened to the filename's own alphabet (RECEIPT_NAME's
 *  [A-Za-z0-9_-]): anything else becomes "-", repeats collapse, and edge "-" is
 *  trimmed. One input, one name, always. */
export function receiptEventName(event: string): string {
  return event.replace(/[^A-Za-z0-9_-]/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "");
}

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
    const folder = ensureReceiptsFolder(dirname(dirname(dir)));
    if (folder === null) return null;
    const stamp = full.ts.replace(/[:.]/g, "-");
    // "wx": a fresh name only — never through a link or over a file already there.
    writeFileSync(join(folder, `${stamp}-${receiptEventName(full.event)}-${full.operation_id}.json`), JSON.stringify(full), { flag: "wx" });
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

export const RECEIPT_HEALTH_WINDOW_DAYS = 14;

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
      // The doctor needs only the 14-day deny window. Raw receipts remain on disk
      // for the configured retention period; this only bounds the health summary.
      // Skipping by filename avoids opening and parsing older records on each check.
      const cutoff = new Date(Date.now() - RECEIPT_HEALTH_WINDOW_DAYS * 86_400_000)
        .toISOString()
        .slice(0, 10)
        .replaceAll("-", "");
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
    const folder = ensureReceiptsFolder(dirname(dirname(dir)));
    if (folder === null) return 0;
    const file = join(folder, "denies.json");
    let ledger: DenyLedger = {};
    try {
      ledger = JSON.parse(readNoFollow(file)) as DenyLedger;
    } catch {
      /* first entry, or a torn file — both mean no prior */
    }
    const prior = typeof ledger[key]?.n === "number" && Number.isFinite(ledger[key]!.n) ? Math.max(0, Math.floor(ledger[key]!.n)) : 0;
    ledger[key] = { n: prior + 1, last_seen: new Date().toISOString() };
    // Re-emit at most the newest LEDGER_CAP well-formed entries: attacker-planted
    // bulk and hostile shapes never survive the round-trip on the hot path.
    const fresh = Object.entries(ledger)
      .filter(([, entry]) => typeof entry?.last_seen === "string" && Number.isFinite(entry?.n))
      .sort((a, b) => (a[1].last_seen < b[1].last_seen ? 1 : -1))
      .slice(0, LEDGER_CAP);
    const kept: DenyLedger = {};
    for (const [k, entry] of fresh) kept[k] = { n: Math.max(1, Math.floor(entry.n)), last_seen: entry.last_seen };
    writeNoFollow(file, JSON.stringify(kept));
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
    const ledger = JSON.parse(readNoFollow(file)) as DenyLedger;
    const cutoff = new Date(now - ttlDays * 86_400_000).toISOString();
    const fresh = Object.entries(ledger)
      .filter(([, entry]) => typeof entry?.last_seen === "string" && entry.last_seen >= cutoff)
      .sort((a, b) => (a[1].last_seen < b[1].last_seen ? 1 : -1))
      .slice(0, cap);
    const kept: DenyLedger = {};
    for (const [key, entry] of fresh) kept[key] = entry;
    writeNoFollow(file, JSON.stringify(kept));
  } catch {
    /* a ledger that cannot be read cannot be pruned; the chain keeps writing it */
  }
}

/** The ledger is read and rewritten in place; a link planted at its name (a file in the
 *  user's home) is refused (ELOOP), never read or truncated through. */
function readNoFollow(path: string): string {
  const descriptor = openSync(path, constants.O_RDONLY | constants.O_NOFOLLOW);
  try {
    return readFileSync(descriptor, "utf8");
  } finally {
    closeSync(descriptor);
  }
}

function writeNoFollow(path: string, text: string): void {
  const descriptor = openSync(path, constants.O_WRONLY | constants.O_CREAT | constants.O_TRUNC | constants.O_NOFOLLOW, 0o666);
  try {
    writeFileSync(descriptor, text);
  } finally {
    closeSync(descriptor);
  }
}

/** The most receipts one automatic retention pass deletes. A repo that never ran the
 *  gc may hold tens of thousands, and the chain call that triggers the pass must not
 *  pay for all of them at once: while a backlog remains, the next call takes the next
 *  batch. */
export const RECEIPTS_GC_BATCH = 500;

const DEFAULT_RECEIPTS_TTL_DAYS = 30;
/** The shortest retention a repo can ask for: `[gc].receipts_ttl` comes from a file a
 *  cloned repo controls, so "0d" must not mean "delete every receipt now". */
export const MIN_RECEIPTS_TTL_DAYS = 1;

/** `[gc].receipts_ttl` in days: "30d" when the key is absent or unreadable, never below
 *  MIN_RECEIPTS_TTL_DAYS. */
export function receiptsTtlDays(config: Config): number {
  const days = Number(String(config["gc"]?.["receipts_ttl"] ?? `${DEFAULT_RECEIPTS_TTL_DAYS}d`).replace("d", ""));
  if (!Number.isFinite(days)) return DEFAULT_RECEIPTS_TTL_DAYS;
  return Math.max(MIN_RECEIPTS_TTL_DAYS, days);
}

/** The names the receipt writers produce, and the only names retention deletes:
 *  writeReceipt's `<ISO stamp>-<event>-<8 hex>.json` (aged by that stamp) and wrap's
 *  `<8 hex>.log` full output (aged by its mtime). */
const RECEIPT_NAME = /^(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z)-[A-Za-z0-9_-]+-[0-9a-f]{8}\.json$/;
const WRAP_LOG_NAME = /^[0-9a-f]{8}\.log$/;
const stampOf = (ms: number): string => new Date(ms).toISOString().replace(/[:.]/g, "-");

/** Fold the receipts this pass collected into summary.json. The daily series is the
 *  gc's long-term memory and is additive — each receipt is tallied once, on the pass
 *  that deletes it, so a day split across batches sums instead of being overwritten.
 *  The other figures describe the receipts this pass collected; `total` is how many
 *  receipts the store held when the pass ran. Written via rename inside the checked
 *  folder so a reader never sees a torn file — a torn summary reads back as no prior and
 *  loses the series — and a link planted at the name is replaced, never written through. */
function mergeAndWriteSummary(root: string, folder: string, collected: ReceiptSummary, total: number, now: number): void {
  const summaryPath = join(folder, "summary.json");
  let prior: { daily?: Record<string, DailyPoint> } | null = null;
  const snapshot = readProjectFileSnapshot(root, summaryPath, withCheckedProjectParent);
  try {
    if (snapshot !== null) prior = JSON.parse(snapshot.content.toString("utf8")) as { daily?: Record<string, DailyPoint> };
  } catch {
    /* no prior summary, or a torn one: the collected batch starts the series */
  }
  const summed: Record<string, DailyPoint> = {};
  for (const [day, point] of Object.entries(collected.daily)) {
    const before = prior?.daily?.[day];
    summed[day] = { runs: count(before?.runs) + point.runs, denies: count(before?.denies) + point.denies };
  }
  const merged = { ...collected, total, daily: mergeDaily(prior?.daily, summed, 90, now), gc: new Date(now).toISOString() };
  withCheckedProjectParent(root, summaryPath, (path) => {
    // Not a .json name, and never a receipt stamp: no reader counts it, no sweep ages it as a receipt.
    const staging = join(dirname(path), `.summary-${randomUUID()}.tmp`);
    try {
      writeFileSync(staging, JSON.stringify(merged), { flag: "wx" });
      renameSync(staging, path);
    } finally {
      rmSync(staging, { force: true });
    }
    return true;
  });
}

/** One gc pass over the receipts folder: how many it deleted, and whether stale
 *  receipts were left for a later pass. */
type ReceiptsPass = { deleted: number; hasBacklog: boolean };
type StaleReceipt = { stamp: string; name: string };

/** The listing behind a pass, taken from the checked folder: the receipts older
 *  than `cutStamp` and how many receipts the store holds. Only names a receipt writer
 *  produces are candidates; anything else in the folder is never aged or deleted. */
function listStaleReceipts(root: string, folder: string, cutStamp: string): { stale: StaleReceipt[]; stored: number } | null {
  let listing: { stale: StaleReceipt[]; stored: number } | null = null;
  const isListed = withCheckedProjectParent(root, join(folder, "summary.json"), () => {
    const stale: StaleReceipt[] = [];
    let stored = 0;
    for (const name of readdirSync(folder)) {
      // The gc's own memory, not its trash: summary.json (the series) and denies.json
      // (the ledger) are pruned by their contents, never swept by age.
      if (name === "summary.json" || name === "denies.json") continue;
      if (name.endsWith(".json")) stored += 1;
      const named = RECEIPT_NAME.exec(name)?.[1];
      if (named !== undefined) {
        if (named < cutStamp) stale.push({ stamp: named, name });
        continue;
      }
      if (!WRAP_LOG_NAME.test(name)) continue;
      try {
        const aged = stampOf(lstatSync(join(folder, name)).mtimeMs);
        if (aged < cutStamp) stale.push({ stamp: aged, name });
      } catch {
        /* gone between the listing and the stat: nothing left to collect */
      }
    }
    listing = { stale, stored };
    return true;
  });
  return isListed ? listing : null;
}

/** The pass behind gcReceipts, over the checked folder. Its cost is bounded by the batch,
 *  not by the store: staleness comes from the timestamp writeReceipt put in the name, so
 *  the folder is listed once and only the receipts being deleted are stat-ed and opened
 *  (F7: 36k opens cost 5 s, and the automatic pass runs inside a tool-use hook). Null
 *  when the folder could not be entered as checked. */
function collectReceipts(root: string, folder: string, ttlDays: number, maxDeletes: number | undefined, now: number): ReceiptsPass | null {
  const listing = listStaleReceipts(root, folder, stampOf(now - ttlDays * 86_400_000));
  if (listing === null) return null;
  const { stale, stored } = listing;
  stale.sort((a, b) => (a.stamp < b.stamp ? -1 : a.stamp > b.stamp ? 1 : 0));
  const canonicalRoot = canonicalPath(root);
  if (canonicalRoot === null) return null;
  const limit = maxDeletes ?? stale.length;
  const tally = emptyTally();
  let deleted = 0;
  let consumed = 0;
  for (const entry of stale) {
    if (deleted >= limit) break;
    consumed += 1;
    // Regular files only, opened once, read and removed through the folder re-checked before
    // each step while still the exact file read: a link, a directory (audit run-1 F4) or a
    // file swapped after the listing is kept. The root is resolved once per pass, not per file.
    const content = takeCheckedProjectFile(canonicalRoot, join(folder, entry.name));
    if (content === null) continue;
    deleted += 1;
    // Tallied only once the unlink succeeded, so two passes never count one receipt twice.
    if (!entry.name.endsWith(".json")) continue;
    try {
      tallyReceipt(JSON.parse(content.toString("utf8")) as Receipt, tally);
    } catch {
      /* a torn write is data, not a crash */
    }
  }
  if (deleted > 0) mergeAndWriteSummary(root, folder, summaryOf(tally), stored, now);
  withCheckedProjectParent(root, join(folder, "denies.json"), (path) => {
    pruneDenyLedger(path, 90, LEDGER_CAP, now);
    return true;
  });
  return { deleted, hasBacklog: consumed < stale.length };
}

function canonicalPath(path: string): string | null {
  try {
    return realpathSync(path);
  } catch {
    return null;
  }
}

/** What the gc's receipts pass did: how many receipts it deleted, and the folder it
 *  refused to touch because it is a link or resolves outside the repo. */
export type ReceiptsGc = { deleted: number; refused: string | null };

/** The gc's receipts pass over `root`'s receipts folder. `maxDeletes` bounds one pass
 *  (oldest first) — `doctor --gc` leaves it unbounded. Receipts carry no citation to
 *  respect: their permanent half is the Receipt-Id trailer on the commit. */
export function gcReceipts(root: string, ttlDays: number, options: { maxDeletes?: number; now?: number } = {}): ReceiptsGc {
  const folder = receiptsFolder(root);
  if (folder.kind === "absent") return { deleted: 0, refused: null };
  if (folder.kind === "refused") return { deleted: 0, refused: folder.rel };
  const pass = collectReceipts(root, folder.path, ttlDays, options.maxDeletes, options.now ?? Date.now());
  return pass === null ? { deleted: 0, refused: RECEIPTS_REL } : { deleted: pass.deleted, refused: null };
}

/** Automatic retention, run by the chain after it writes its receipt: at most
 *  RECEIPTS_GC_BATCH deletions per pass, and once the backlog is clear, at most one
 *  pass per calendar day (UTC) per repo. A receipts folder that is not the repo's own is
 *  skipped. It runs inside the host's process, so it never changes the working directory,
 *  and it never throws — housekeeping must not change a verdict. */
export function retainReceipts(root: string, now = Date.now()): { ran: boolean; deleted: number } {
  try {
    return runRetention(root, now);
  } catch {
    return { ran: false, deleted: 0 };
  }
}

function runRetention(root: string, now: number): { ran: boolean; deleted: number } {
  const idle = { ran: false, deleted: 0 };
  const today = `receipts-retention-${new Date(now).toISOString().slice(0, 10)}`;
  // The claim lives in the gitignored cache, not the receipts folder, so no reader of
  // receipts ever sees it and the sweep can never delete it.
  const aiDir = safeProjectPath(root, AI_DIR);
  if (aiDir === null) return idle;
  try {
    mkdirSync(join(aiDir, "cache"));
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "EEXIST") return idle;
  }
  const cache = safeProjectPath(root, `${AI_DIR}/cache`);
  if (cache === null) return idle;
  const claim = join(cache, today);
  // Exclusive create: of the parallel tool calls that open a day, exactly one runs
  // the pass. Already claimed, or an unwritable cache — either way, skip.
  const isClaimed = withCheckedProjectParent(root, claim, (path) => {
    closeSync(openSync(path, "wx"));
    return true;
  });
  if (!isClaimed) return idle;
  let pass: ReceiptsPass = { deleted: 0, hasBacklog: false };
  try {
    const folder = receiptsFolder(root);
    if (folder.kind === "checked") {
      pass = collectReceipts(root, folder.path, receiptsTtlDays(loadConfig(root)), RECEIPTS_GC_BATCH, now) ?? pass;
    }
  } catch {
    /* the day stays claimed: a pass that throws is not retried on every call */
  }
  // A backlog bigger than one batch drains over the next calls; the day is only
  // done once a pass leaves nothing stale behind. A claim that cannot be released
  // only delays the next batch to tomorrow.
  let entries: string[] = [];
  try {
    entries = readdirSync(cache);
  } catch {
    /* an unreadable cache keeps its claims; the next day tries again */
  }
  for (const entry of entries) {
    const isOldClaim = entry.startsWith("receipts-retention-") && entry !== today;
    if (!isOldClaim && !(entry === today && pass.hasBacklog)) continue;
    // The cache is re-checked before each unlink: a folder swapped for a link meanwhile is left alone.
    withCheckedProjectParent(root, join(cache, entry), (path) => {
      unlinkSync(path);
      return true;
    });
  }
  return { ran: true, deleted: pass.deleted };
}
