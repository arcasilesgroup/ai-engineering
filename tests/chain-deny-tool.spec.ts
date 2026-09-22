// tests/chain-deny-tool.spec.ts — G1: a deny receipt names the tool that was denied.
//
// Before this, denyOutcome hardcoded tool: "unknown" for every deny while runChain
// held the real one — per-tool analysis of the historical denies was a lie. The two
// fail-closed payload-illegible calls keep "unknown" as their own honest bucket.

import { describe, expect, test, afterAll, beforeEach } from "bun:test";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync, readdirSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { runChain } from "../src/chain/mod.ts";

let scratch: string;
let cwdBefore: string;
beforeEach(() => {
  if (!scratch) {
    scratch = mkdtempSync(join(tmpdir(), "ai-eng-denytool-"));
    cwdBefore = process.cwd();
    process.chdir(scratch);
  }
  rmSync(join(scratch, ".ai-engineering"), { recursive: true, force: true });
  mkdirSync(join(scratch, ".ai-engineering"), { recursive: true });
  writeFileSync(join(scratch, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n');
});
afterAll(() => {
  if (cwdBefore) process.chdir(cwdBefore);
  if (scratch) rmSync(scratch, { recursive: true, force: true });
});

const receipts = (): Record<string, unknown>[] => {
  const dir = join(scratch, ".ai-engineering", "receipts");
  try {
    return readdirSync(dir)
      .filter((n) => n.endsWith(".json") && n !== "summary.json" && n !== "denies.json")
      .map((n) => JSON.parse(readFileSync(join(dir, n), "utf8")) as Record<string, unknown>);
  } catch {
    return [];
  }
};

describe("G1 — deny receipts carry the real tool", () => {
  test("a guard-deny records the tool that was denied, not unknown", () => {
    const outcome = runChain(
      { tool_name: "Bash", tool_input: { command: "git commit --no-verify -m x" }, tool_use_id: "d1", session_id: "denytool" },
      "PreToolUse",
      { inProcess: true },
    );
    expect(outcome.action).toBe("deny");
    const rs = receipts();
    expect(rs.length).toBe(1);
    expect(rs[0]!.tool).toBe("Bash");
    expect((rs[0]!.guards as Record<string, unknown>).denied_by).toBe("no-verify");
  });

  test("the unreadable-payload fail-closed keeps its own honest bucket: tool unknown", () => {
    const outcome = runChain(null as unknown as Record<string, unknown>, "PreToolUse", { inProcess: true });
    expect(outcome.action).toBe("deny");
    const rs = receipts();
    expect(rs.length).toBe(1);
    expect(rs[0]!.tool).toBe("unknown");
    expect(outcome.action === "deny" && outcome.by).toBe("chain");
  });
});
