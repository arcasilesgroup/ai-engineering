// tests/receipts-summary.spec.ts — G2..G7: the gc summary keeps the story.
//
// summarizeReceipts used to answer four numbers and throw the rest of every receipt
// away when the 30-day sweep deleted it. These fixtures are written directly (no
// chain involved): the reader's job is to aggregate what is on disk, and the merge
// is the gc's own arithmetic, pinned here rather than through doctor's CLI.
//
// Test names are load-bearing: spec.html's -t filters name them exactly.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { mergeDaily, summarizeReceipts, type Receipt } from "../src/receipts.ts";

function dirWith(receipts: Receipt[]): string {
  const dir = mkdtempSync(join(tmpdir(), "ai-eng-summary-"));
  receipts.forEach((r, i) => writeFileSync(join(dir, `r${i}.json`), JSON.stringify(r)));
  return dir;
}

function receipt(over: Partial<Receipt>): Receipt {
  return {
    schema: "urn:ai-eng:receipt:2",
    operation_id: `op${Math.random().toString(36).slice(2, 6)}`,
    event: "PreToolUse",
    surface: "claude-code",
    tool: "Bash",
    guards: { ran: ["self-protect"], denied_by: null },
    latency_ms: 3,
    outcome: "allow",
    ts: new Date().toISOString(),
    ...over,
  };
}

const deny = (over: Partial<Receipt>): Receipt =>
  receipt({ outcome: "deny", guards: { ran: ["self-protect"], denied_by: "self-protect" }, ...over });

describe("summarizeReceipts — the aggregates the gc keeps (G2-G4, G7)", () => {
  test("per_guard counts denies by the guard that denied (3 self-protect + 1 loop)", () => {
    const dir = dirWith([
      deny({}),
      deny({}),
      deny({ guards: { ran: ["loop"], denied_by: "loop" } }),
      deny({ guards: { ran: ["self-protect"], denied_by: "self-protect" } }),
      receipt({}), // an allow never lands in a deny bucket
    ]);
    try {
      const s = summarizeReceipts(dir);
      expect(s.per_guard).toEqual({ "self-protect": 3, loop: 1 });
    } finally { rmSync(dir, { recursive: true, force: true }); }
  });

  test("denies count per_tool and per_surface, and the unknown tool is its own bucket", () => {
    const dir = dirWith([
      deny({ tool: "Bash" }),
      deny({ tool: "Bash", surface: "omp" }),
      deny({ tool: "unknown" }), // the unreadable-payload fail-closed
    ]);
    try {
      const s = summarizeReceipts(dir);
      expect(s.per_tool).toEqual({ Bash: 2, unknown: 1 });
      expect(s.per_surface).toEqual({ "claude-code": 2, omp: 1 });
    } finally { rmSync(dir, { recursive: true, force: true }); }
  });

  test("the daily series carries {runs, denies} per ISO date from the receipts' own ts", () => {
    const dir = dirWith([
      deny({ ts: "2026-09-18T10:00:00.000Z" }),
      receipt({ ts: "2026-09-18T11:00:00.000Z" }),
      receipt({ ts: "2026-09-19T09:00:00.000Z" }),
    ]);
    try {
      const s = summarizeReceipts(dir);
      expect(s.daily["2026-09-18"]).toEqual({ runs: 2, denies: 1 });
      expect(s.daily["2026-09-19"]).toEqual({ runs: 1, denies: 0 });
    } finally { rmSync(dir, { recursive: true, force: true }); }
  });

  test("denies.json is not counted as a receipt, exactly like summary.json", () => {
    const dir = dirWith([receipt({}), receipt({})]);
    try {
      writeFileSync(join(dir, "denies.json"), JSON.stringify({ somefp: { n: 4, last_seen: "2026-09-20T00:00:00.000Z" } }));
      writeFileSync(join(dir, "summary.json"), JSON.stringify({ total: 99 }));
      const s = summarizeReceipts(dir);
      expect(s.total).toBe(2);
      expect(s.denies).toBe(0);
    } finally { rmSync(dir, { recursive: true, force: true }); }
  });
});

describe("mergeDaily — the gc merge, not the gc overwrite (G5-G6)", () => {
  const day = (offset: number) => new Date(Date.UTC(2026, 8, 20) - offset * 86_400_000).toISOString().slice(0, 10);

  test("two gc passes merge the series: older days survive and the re-summarized day takes the fresh numbers", () => {
    const prior = { [day(10)]: { runs: 7, denies: 2 }, [day(3)]: { runs: 5, denies: 1 } };
    const current = { [day(3)]: { runs: 9, denies: 4 } };
    const merged = mergeDaily(prior, current, 90, Date.UTC(2026, 8, 20));
    expect(merged[day(10)]).toEqual({ runs: 7, denies: 2 }); // older day survived
    expect(merged[day(3)]).toEqual({ runs: 9, denies: 4 }); // fresh window wins the day-key
  });

  test("the merge prunes days older than keepDays from the front", () => {
    const prior = { [day(95)]: { runs: 1, denies: 0 }, [day(5)]: { runs: 2, denies: 1 } };
    const merged = mergeDaily(prior, {}, 90, Date.UTC(2026, 8, 20));
    expect(merged[day(95)]).toBeUndefined();
    expect(merged[day(5)]).toEqual({ runs: 2, denies: 1 });
  });

  test("a torn or missing prior summary merges as no prior", () => {
    const current = { [day(1)]: { runs: 3, denies: 1 } };
    expect(mergeDaily(undefined, current, 90, Date.UTC(2026, 8, 20))).toEqual(current);
    expect(mergeDaily({} as Record<string, never>, current, 90, Date.UTC(2026, 8, 20))).toEqual(current);
  });
});
