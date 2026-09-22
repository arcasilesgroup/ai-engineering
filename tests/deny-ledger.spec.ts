// tests/deny-ledger.spec.ts — G8..G12: the cross-session deny ledger.
//
// One small file (.ai-engineering/receipts/denies.json) keyed by loopExact — the
// same tool + same input, whoever sends it, whichever session. A second denial of
// the same exact call gains one clause on the human message; the verdict itself is
// never changed by the ledger, and a broken ledger never changes anything either.
//
// Test names are load-bearing: spec.html's -t filters name them exactly
// ("clause", "never touch", "broken ledger"; "sweep" and "prunes the ledger" are
// added with the doctor gc wiring in step 4).

import { describe, expect, test, afterAll, beforeEach } from "bun:test";
import { chmodSync, existsSync, mkdirSync, readFileSync, rmSync, utimesSync, writeFileSync } from "node:fs";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { runChain } from "../src/chain/mod.ts";
import { pruneDenyLedger, type DenyLedger } from "../src/receipts.ts";
import { doctorMain } from "../src/commands/doctor.ts";

let scratch: string;
let cwdBefore: string;
let homeBefore: string | undefined;
beforeEach(() => {
  if (!scratch) {
    scratch = mkdtempSync(join(tmpdir(), "ai-eng-ledger-"));
    cwdBefore = process.cwd();
    homeBefore = process.env.AI_ENG_HOME;
    // The loop guard's session state lives in the machine home: unisolated, a
    // repeated test call turns "harmless" into a loop-deny for the NEXT run of the
    // suite (and pollutes the developer's real home). Same sandbox discipline as
    // tests/doctor-command.spec.ts.
    process.env.AI_ENG_HOME = mkdtempSync(join(tmpdir(), "ai-eng-ledger-home-"));
    process.chdir(scratch);
  }
  rmSync(join(scratch, ".ai-engineering"), { recursive: true, force: true });
  mkdirSync(join(scratch, ".ai-engineering"), { recursive: true });
  writeFileSync(join(scratch, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n');
});
afterAll(() => {
  if (cwdBefore) process.chdir(cwdBefore);
  if (homeBefore === undefined) delete process.env.AI_ENG_HOME;
  else process.env.AI_ENG_HOME = homeBefore;
  if (scratch) rmSync(scratch, { recursive: true, force: true });
});

const LEDGER = (): string => join(scratch!, ".ai-engineering", "receipts", "denies.json");
const readLedger = (): DenyLedger => JSON.parse(readFileSync(LEDGER(), "utf8")) as DenyLedger;

/** A call self-protect denies on sight, in any session: an Edit onto the config the fence owns. */
const guardedEdit = (sessionId: string) => ({
  tool_name: "Edit",
  tool_input: { file_path: join(scratch, ".ai-engineering", "config.toml"), old_string: "a", new_string: "b" },
  tool_use_id: `u-${sessionId}`,
  session_id: sessionId,
});
const RUN = (payload: Record<string, unknown>) => runChain(payload, "PreToolUse", { inProcess: true });

describe("deny ledger — the repeat clause (G8)", () => {
  test("the clause appears only on the second denial of the exact call, with the count before it", () => {
    const first = RUN(guardedEdit("ledger-s1"));
    expect(first.action).toBe("deny");
    if (first.action === "deny") expect(first.reason).not.toContain("denied");
    expect(existsSync(LEDGER())).toBe(true);
    expect(Object.values(readLedger())[0]).toMatchObject({ n: 1 });

    // Same tool + same input, a different session: loopExact matches where
    // fingerprint (session-keyed) would not.
    const second = RUN(guardedEdit("ledger-s2"));
    expect(second.action).toBe("deny");
    if (second.action === "deny") {
      expect(second.reason.endsWith(" · this exact call has been denied 1 times before")).toBe(true);
    }
    expect(Object.values(readLedger())[0]!.n).toBe(2);
  });
});

describe("deny ledger — signal, never verdict (G9-G10)", () => {
  test("allows, rewrites and the unreadable-payload fail-closed never touch the ledger", () => {
    RUN({ tool_name: "Read", tool_input: { file_path: "harmless.md" }, tool_use_id: "a1", session_id: "ledger-a" });
    RUN({ tool_name: "Bash", tool_input: { command: "bun test" }, tool_use_id: "w1", session_id: "ledger-w" }); // wrap rewrites
    const denied = RUN(null as unknown as Record<string, unknown>); // fail-closed: no payload to key
    expect(denied.action).toBe("deny");
    expect(existsSync(LEDGER())).toBe(false);
  });

  test("a broken ledger — torn content or an unwritable file — changes no verdict and no reason byte", () => {
    mkdirSync(join(scratch, ".ai-engineering", "receipts"), { recursive: true });
    writeFileSync(LEDGER(), "{ not json");
    const first = RUN(guardedEdit("ledger-x1"));
    expect(first.action).toBe("deny");
    if (first.action === "deny") {
      expect(first.by).toBe("self-protect"); // the torn file read as no prior: guard's own words stand
      expect(first.reason).not.toContain("times before");
    }

    chmodSync(LEDGER(), 0o444); // the chain cannot write its state at all
    const second = RUN(guardedEdit("ledger-x2"));
    expect(second.action).toBe("deny");
    if (second.action === "deny") expect(second.reason).not.toContain("times before");
    chmodSync(LEDGER(), 0o644);
  });
});

describe("deny ledger — the gc that owns its life (G11-G12)", () => {
  test("prunes the ledger: last_seen past 90 days falls off and the file caps at the newest 500", () => {
    mkdirSync(join(scratch, ".ai-engineering", "receipts"), { recursive: true });
    const fresh = new Date().toISOString();
    const old = new Date(Date.now() - 95 * 86_400_000).toISOString();
    const ledger: DenyLedger = { dead: { n: 7, last_seen: old } };
    for (let i = 0; i < 520; i++) ledger[`k${i}`] = { n: 1, last_seen: new Date(Date.parse(fresh) - i * 1000).toISOString() };
    writeFileSync(LEDGER(), JSON.stringify(ledger));
    pruneDenyLedger(LEDGER());
    const kept = readLedger();
    expect(kept.dead).toBeUndefined();
    expect(Object.keys(kept).length).toBe(500);
    expect(kept.k0).toBeDefined(); // newest survives the cap
    expect(kept.k519).toBeUndefined(); // oldest of the fresh ones does not
  });

  test("a forged oversized ledger is trimmed by the very next denial — no unbounded read+rewrite", () => {
    // Audit run-1 F1: the file is attacker-writable and read+rewritten on the deny
    // hot path; without a hot-path cap a 16 MB plant made every deny cost ~50-80 ms.
    mkdirSync(join(scratch, ".ai-engineering", "receipts"), { recursive: true });
    const plant: DenyLedger = {};
    for (let i = 0; i < 600; i++) plant[`pad-${i}-${"x".repeat(60)}`] = { n: 1, last_seen: new Date().toISOString() };
    writeFileSync(LEDGER(), JSON.stringify(plant));
    const out = RUN(guardedEdit("ledger-cap"));
    expect(out.action).toBe("deny");
    expect(Object.keys(readLedger()).length).toBeLessThanOrEqual(500);
  });

  test("the mtime sweep never deletes denies.json however stale it looks", async () => {
    // One stale receipt forces the gc to actually run its deletion pass.
    const receipts = join(scratch, ".ai-engineering", "receipts");
    mkdirSync(receipts, { recursive: true });
    writeFileSync(join(receipts, "2026-01-01T00-00-00-000Z-PreToolUse-abcdef12.json"), "{}");
    writeFileSync(LEDGER(), JSON.stringify({ k: { n: 1, last_seen: new Date().toISOString() } }));
    const old = new Date(Date.now() - 365 * 86_400_000);
    const stale = join(receipts, "2026-01-01T00-00-00-000Z-PreToolUse-abcdef12.json");
    utimesSync(stale, old, old); // force the deletion pass to actually run
    utimesSync(LEDGER(), old, old); // a year old by every clock the sweep reads
    const chunks: string[] = [];
    const stdout = process.stdout.write.bind(process.stdout);
    process.stdout.write = ((c: unknown) => { chunks.push(String(c)); return true; }) as typeof process.stdout.write;
    try {
      await doctorMain({ gc: true });
    } finally {
      process.stdout.write = stdout;
    }
    expect(chunks.join("")).toContain("aggregated into summary.json"); // the sweep really ran
    expect(existsSync(LEDGER())).toBe(true);
    expect(existsSync(join(receipts, "2026-01-01T00-00-00-000Z-PreToolUse-abcdef12.json"))).toBe(false);
  });

  test("the mtime sweep survives a planted directory named like a receipt", async () => {
    // Audit run-1 F4: bomb.json as a DIRECTORY made unlinkSync throw EPERM before
    // the summary write — every gc run died and the spike baseline froze.
    const receipts = join(scratch, ".ai-engineering", "receipts");
    mkdirSync(join(receipts, "bomb.json"), { recursive: true });
    const old = new Date(Date.now() - 365 * 86_400_000);
    utimesSync(join(receipts, "bomb.json"), old, old);
    const stale = join(receipts, "2026-01-01T00-00-00-000Z-PreToolUse-abcdef13.json");
    writeFileSync(stale, "{}");
    utimesSync(stale, old, old);
    const chunks: string[] = [];
    const stdout = process.stdout.write.bind(process.stdout);
    process.stdout.write = ((c: unknown) => { chunks.push(String(c)); return true; }) as typeof process.stdout.write;
    let threw = "";
    try {
      await doctorMain({ gc: true });
    } catch (e) {
      threw = String(e);
    } finally {
      process.stdout.write = stdout;
    }
    expect(threw).toBe(""); // the sweep does not die on the planted directory
    expect(chunks.join("")).toContain("aggregated into summary.json"); // it finishes
    expect(existsSync(join(receipts, "bomb.json"))).toBe(true); // dirs are left for a human
    expect(existsSync(stale)).toBe(false); // real stale receipts still sweep
  });
});
