// tests/receipts-retention.spec.ts — receipts stay bounded without anybody running
// `doctor --gc`.
//
// The chain writes one receipt per tool call; a busy repo accumulated tens of thousands
// and every reader paid for them. Retention is the gc's receipts pass, run on its own:
// at most RECEIPTS_GC_BATCH deletions per pass, at most once per day once no backlog is
// left (a per-day claim), and only from the chain after its receipt is written — never
// from the git floor (tests/floor-hooks.spec.ts F7 pins that side).
//
// The contract under test, exported from src/receipts.ts:
//   RECEIPTS_GC_BATCH: number                      — the most one pass deletes
//   retainReceipts(root: string, now?: number): { ran: boolean; deleted: number }
//     reads [gc].receipts_ttl from root's config.toml (default 30d), returns
//     { ran: false, deleted: 0 } without touching the folder when `now`'s day is already
//     claimed, otherwise claims the day and runs the bounded gcReceipts pass; a pass
//     that leaves stale receipts behind releases the claim so the next call drains on.
// `now` is injected so no case here depends on the wall clock; mtimes are set relative
// to it with utimesSync.

import { afterAll, afterEach, beforeAll, describe, expect, spyOn, test } from "bun:test";
import { spawn } from "node:child_process";
import * as fs from "node:fs";
import { mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, utimesSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";
import * as receiptsModule from "../src/receipts.ts";
import { runChain } from "../src/chain/mod.ts";

type Retention = { ran: boolean; deleted: number };
const retention = receiptsModule as unknown as {
  RECEIPTS_GC_BATCH?: number;
  retainReceipts?: (root: string, now?: number) => Retention;
};

const DAY = 86_400_000;
// Midday UTC: one minute later is the same calendar day in every timezone.
const NOW = Date.UTC(2030, 0, 15, 12, 0, 0);
const roots: string[] = [];
const HOME_BEFORE = process.env.AI_ENG_HOME;
const CWD_BEFORE = process.cwd();

beforeAll(() => {
  // The loop guard keeps session state in the machine home; never the real one.
  process.env.AI_ENG_HOME = mkdtempSync(join(tmpdir(), "ai-eng-retention-home-"));
  roots.push(process.env.AI_ENG_HOME);
});
afterEach(() => {
  process.chdir(CWD_BEFORE);
});
afterAll(() => {
  process.chdir(CWD_BEFORE);
  if (HOME_BEFORE === undefined) delete process.env.AI_ENG_HOME;
  else process.env.AI_ENG_HOME = HOME_BEFORE;
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

function retainReceipts(root: string, now?: number): Retention {
  expect(typeof retention.retainReceipts).toBe("function");
  return retention.retainReceipts!(root, now);
}

function batchSize(): number {
  const batch = retention.RECEIPTS_GC_BATCH;
  expect(typeof batch).toBe("number");
  // Premise for the fixtures below: a positive whole batch this suite can outnumber.
  expect(Number.isInteger(batch) && batch! >= 1 && batch! <= 5000).toBe(true);
  return batch!;
}

/** A governed repo; `ttl` lands as `[gc].receipts_ttl` when given. */
function governedRepo(ttl?: string): string {
  const root = mkdtempSync(join(tmpdir(), "ai-eng-retention-"));
  roots.push(root);
  mkdirSync(join(root, ".ai-engineering", "receipts"), { recursive: true });
  const gc = ttl === undefined ? "" : `\n[gc]\nreceipts_ttl = "${ttl}"\n`;
  writeFileSync(join(root, ".ai-engineering", "config.toml"), `[surfaces]\nenabled = ["claude-code"]\n${gc}`);
  return root;
}

const receiptsOf = (root: string): string => join(root, ".ai-engineering", "receipts");

const isReceiptName = (name: string): boolean => /^\d{4}-\d{2}-\d{2}T.*\.json$/.test(name);

function receiptNames(root: string): string[] {
  return readdirSync(receiptsOf(root)).filter(isReceiptName).sort();
}

let serial = 0;
/** One receipt on disk exactly as writeReceipt names and shapes it, aged to `mtime`. */
function seedReceipt(root: string, mtime: number): string {
  serial += 1;
  const id = serial.toString(16).padStart(8, "0");
  const ts = new Date(mtime).toISOString();
  const name = `${ts.replace(/[:.]/g, "-")}-PreToolUse-${id}.json`;
  const path = join(receiptsOf(root), name);
  writeFileSync(
    path,
    JSON.stringify({
      schema: "urn:ai-eng:receipt:2",
      operation_id: id,
      event: "PreToolUse",
      surface: "claude-code",
      tool: "Bash",
      guards: { ran: ["policy"], denied_by: null },
      latency_ms: 2,
      outcome: "allow",
      ts,
    }),
  );
  utimesSync(path, new Date(mtime), new Date(mtime));
  return name;
}

function seedMany(root: string, count: number, mtime: number): string[] {
  return Array.from({ length: count }, () => seedReceipt(root, mtime));
}

describe("retainReceipts — bounded by [gc].receipts_ttl", () => {
  test("after N stale writes only the receipts younger than the configured ttl remain", () => {
    const root = governedRepo("7d");
    // 10 days old: past a 7d ttl, yet inside the 30d default — so only a retention
    // that reads [gc].receipts_ttl deletes them.
    const stale = seedMany(root, 30, NOW - 10 * DAY);
    const young = seedMany(root, 10, NOW - 2 * DAY);
    // Premise: all N receipts are on disk before the pass.
    expect(receiptNames(root)).toEqual([...stale, ...young].sort());

    const result = retainReceipts(root, NOW);

    expect(result).toEqual({ ran: true, deleted: stale.length });
    expect(receiptNames(root)).toEqual([...young].sort());
  });

  test("a receipt younger than the ttl is never deleted, even when it is the only one", () => {
    const root = governedRepo("30d");
    const young = seedMany(root, 3, NOW - 29 * DAY);

    expect(retainReceipts(root, NOW)).toEqual({ ran: true, deleted: 0 });
    expect(receiptNames(root)).toEqual([...young].sort());
  });
});

describe("retainReceipts — at most once per day", () => {
  test("a second trigger the same day does no scan; the next day it runs again", () => {
    const root = governedRepo("7d");
    seedMany(root, 5, NOW - 10 * DAY);
    expect(retainReceipts(root, NOW)).toEqual({ ran: true, deleted: 5 });
    // Premise: the first pass left no stale receipt behind.
    expect(receiptNames(root)).toEqual([]);

    const lateArrivals = seedMany(root, 4, NOW - 10 * DAY);
    expect(retainReceipts(root, NOW + 60_000)).toEqual({ ran: false, deleted: 0 });
    expect(receiptNames(root)).toEqual([...lateArrivals].sort());

    expect(retainReceipts(root, NOW + DAY)).toEqual({ ran: true, deleted: 4 });
    expect(receiptNames(root)).toEqual([]);
  });
});

describe("retainReceipts — bounded batches; the gc's own memory survives", () => {
  test("one pass deletes at most RECEIPTS_GC_BATCH; summary.json and denies.json survive every pass", () => {
    const batch = batchSize();
    const root = governedRepo("7d");
    const dir = receiptsOf(root);
    const stale = seedMany(root, batch + 25, NOW - 10 * DAY);
    const ledger = JSON.stringify({ "Bash:rm -rf /": { n: 3, last_seen: "2099-01-01T00:00:00.000Z" } });
    writeFileSync(join(dir, "denies.json"), ledger);
    writeFileSync(join(dir, "summary.json"), JSON.stringify({ total: 7, daily: { "2099-01-01": { runs: 7, denies: 2 } } }));
    // Older than any ttl by mtime: only the pass's own exemption keeps them.
    for (const name of ["denies.json", "summary.json"]) utimesSync(join(dir, name), new Date(NOW - 400 * DAY), new Date(NOW - 400 * DAY));
    // Premise: more stale receipts than one pass may delete.
    expect(receiptNames(root)).toHaveLength(stale.length);
    expect(stale.length).toBeGreaterThan(batch);

    expect(retainReceipts(root, NOW)).toEqual({ ran: true, deleted: batch });
    expect(receiptNames(root)).toHaveLength(25);
    expect(readFileSync(join(dir, "denies.json"), "utf8")).toBe(ledger);
    const summary = JSON.parse(readFileSync(join(dir, "summary.json"), "utf8")) as { daily: Record<string, unknown> };
    expect(summary.daily["2099-01-01"]).toEqual({ runs: 7, denies: 2 });

    expect(retainReceipts(root, NOW + DAY)).toEqual({ ran: true, deleted: 25 });
    expect(receiptNames(root)).toEqual([]);
    expect(readFileSync(join(dir, "denies.json"), "utf8")).toBe(ledger);
    const after = JSON.parse(readFileSync(join(dir, "summary.json"), "utf8")) as { daily: Record<string, unknown> };
    expect(after.daily["2099-01-01"]).toEqual({ runs: 7, denies: 2 });
  });
});

describe("retention is triggered by the chain after its receipt is written", () => {
  // The chain has no injected clock, so staleness is anchored far in the past: an
  // mtime in 2000 is past any ttl on whatever day this runs.
  const ANCIENT = Date.UTC(2000, 0, 1);
  const harmlessRead = (root: string, id: string): Record<string, unknown> => ({
    tool_name: "Read",
    tool_input: { file_path: join(root, "README.md") },
    tool_use_id: id,
    session_id: "retention",
    cwd: root,
  });

  test("the first chain run of the day collects stale receipts; a second run the same day leaves new stale ones alone", () => {
    const root = governedRepo();
    writeFileSync(join(root, "README.md"), "hello\n");
    process.chdir(root);
    const stale = seedMany(root, 20, ANCIENT);
    expect(receiptNames(root)).toEqual([...stale].sort());

    const first = runChain(harmlessRead(root, "u-first"), "PreToolUse", { inProcess: true });
    // Premise: the chain allowed the call and wrote its receipt.
    expect(first.action).toBe("allow");
    expect(first.receiptId).not.toBeNull();
    const afterFirst = receiptNames(root);
    expect(afterFirst.filter((name) => stale.includes(name))).toEqual([]);
    expect(afterFirst.some((name) => name.endsWith(`-${first.receiptId}.json`))).toBe(true);

    const lateArrivals = seedMany(root, 20, ANCIENT);
    const second = runChain(harmlessRead(root, "u-second"), "PreToolUse", { inProcess: true });
    expect(second.action).toBe("allow");
    expect(second.receiptId).not.toBeNull();
    const afterSecond = receiptNames(root);
    expect(lateArrivals.filter((name) => !afterSecond.includes(name))).toEqual([]);
  });
});

describe("retainReceipts — bounded in work, not only in deletions", () => {
  test("with thousands of receipts inside the ttl, the pass opens and stats only the stale ones it deletes", () => {
    const root = governedRepo("7d");
    const dir = receiptsOf(root);
    const young = seedMany(root, 3000, NOW - 2 * DAY);
    const stale = seedMany(root, 5, NOW - 10 * DAY);
    // Premise: the store really holds the thousands the pass must not open.
    expect(receiptNames(root)).toHaveLength(young.length + stale.length);

    const spies = [spyOn(fs, "readFileSync"), spyOn(fs, "lstatSync"), spyOn(fs, "statSync"), spyOn(fs, "openSync")];
    let result: Retention;
    let touched: string[];
    try {
      result = retainReceipts(root, NOW);
    } finally {
      // Read the calls before restoring: mockRestore() clears them.
      touched = spies.flatMap((spy) => spy.mock.calls.map((call) => String((call as unknown[])[0])));
      for (const spy of spies) spy.mockRestore();
    }
    const receiptsTouched = [...new Set(touched.filter((path) => path.startsWith(dir) && isReceiptName(basename(path))).map((path) => basename(path)))];

    expect(result).toEqual({ ran: true, deleted: stale.length });
    // Positive control: the spies see the pass's own reads, so an empty list below is not vacuous.
    expect(receiptsTouched.length).toBeGreaterThan(0);
    expect(receiptsTouched.sort()).toEqual([...stale].sort());
    expect(receiptNames(root)).toEqual([...young].sort());
  });
});

describe("retainReceipts — a backlog bigger than one batch drains the same day", () => {
  test("3×batch stale receipts clear over three same-day calls, the fourth does no scan, and the series counts each once", () => {
    const batch = batchSize();
    const root = governedRepo("7d");
    const staleDay = new Date(NOW - 10 * DAY).toISOString().slice(0, 10);
    seedMany(root, 3 * batch, NOW - 10 * DAY);
    const young = seedMany(root, 3, NOW - DAY);

    expect(retainReceipts(root, NOW)).toEqual({ ran: true, deleted: batch });
    expect(retainReceipts(root, NOW + 60_000)).toEqual({ ran: true, deleted: batch });
    expect(retainReceipts(root, NOW + 120_000)).toEqual({ ran: true, deleted: batch });
    expect(receiptNames(root)).toEqual([...young].sort());

    const lateArrival = seedMany(root, 1, NOW - 10 * DAY);
    expect(retainReceipts(root, NOW + 180_000)).toEqual({ ran: false, deleted: 0 });
    expect(receiptNames(root)).toEqual([...lateArrival, ...young].sort());

    // A day split across three batches is summed, never overwritten by the last batch.
    const summary = JSON.parse(readFileSync(join(receiptsOf(root), "summary.json"), "utf8")) as { daily: Record<string, unknown> };
    expect(summary.daily[staleDay]).toEqual({ runs: 3 * batch, denies: 0 });
  });
});

describe("retainReceipts — parallel calls that open a day", () => {
  test("of six processes racing on the first call of the day exactly one runs the pass, and the series counts each receipt once", async () => {
    const root = governedRepo("7d");
    const staleDay = new Date(NOW - 10 * DAY).toISOString().slice(0, 10);
    const stale = seedMany(root, 40, NOW - 10 * DAY);
    const script = `const { retainReceipts } = await import(${JSON.stringify(join(import.meta.dir, "..", "src", "receipts.ts"))}); console.log(JSON.stringify(retainReceipts(${JSON.stringify(root)}, ${NOW})));`;
    const racer = (): Promise<Retention> =>
      new Promise((resolve, reject) => {
        const child = spawn(process.execPath, ["-e", script], { stdio: ["ignore", "pipe", "inherit"] });
        let out = "";
        child.stdout.on("data", (chunk: Buffer) => (out += chunk.toString()));
        child.on("close", (status) => (status === 0 ? resolve(JSON.parse(out) as Retention) : reject(new Error(`racer exited ${status}`))));
      });

    const results = await Promise.all(Array.from({ length: 6 }, racer));

    expect(results.filter((r) => r.ran)).toEqual([{ ran: true, deleted: stale.length }]);
    expect(receiptNames(root)).toEqual([]);
    const summary = JSON.parse(readFileSync(join(receiptsOf(root), "summary.json"), "utf8")) as { daily: Record<string, unknown> };
    expect(summary.daily[staleDay]).toEqual({ runs: stale.length, denies: 0 });
  }, 60_000);
});
