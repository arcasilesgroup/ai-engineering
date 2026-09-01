// Entry for `ai-eng git <hook>` — the floor the 3-line shims exec into (§13.2).
// commit-msg needs the receipt for its trailer; pre-commit/pre-push stay dry and fast.

import { repoRoot } from "../env.ts";
import { preCommit, commitMsg, prePush } from "./index.ts";
import { writeReceipt, receiptId, summarizeReceipts } from "../receipts.ts";
import { readOverrides, overrideActive } from "../chain/dialect.ts";

export async function floor(hook: string, msgFile?: string): Promise<number> {
  const root = repoRoot();
  if (!root) {
    process.stderr.write("ai-eng git: no governed repo from here.\n");
    return 2;
  }
  if (hook === "pre-commit") {
    const t0 = Date.now();
    const result = preCommit(root);
    const receipt = writeReceipt({
      event: "git-pre-commit",
      surface: "git",
      tool: "pre-commit",
      guards: { ran: ["floor"], denied_by: result.ok ? null : "floor" },
      latency_ms: Date.now() - t0,
      outcome: result.ok ? "allow" : "deny",
    });
    for (const line of result.lines) process.stderr.write(`${line}\n`);
    if (!result.ok) {
      process.stderr.write("[git floor] pre-commit: BLOCKED — what the hooks would say is what needs fixing.\n");
      return 1;
    }
    if (receipt) process.stderr.write(`[git floor] pre-commit ✓ (${Date.now() - t0}ms · ${summarizeReceipts().total} receipts)\n`);
    return 0;
  }
  if (hook === "commit-msg") {
    if (!msgFile) {
      process.stderr.write("usage: ai-eng git commit-msg <msgfile>\n");
      return 2;
    }
    const overrides = readOverrides(root);
    const active = overrides.find((o) => overrideActive(overrides, o.name) !== null) ?? null;
    const id = receiptId({
      schema: "urn:ai-eng:receipt:2",
      operation_id: "floor",
      event: "commit-msg",
      surface: "git",
      tool: "commit-msg",
      guards: { ran: ["floor"], denied_by: null },
      latency_ms: 0,
      outcome: "allow",
      ts: new Date().toISOString(),
    });
    const result = commitMsg(msgFile, id, active?.reason ?? null);
    for (const line of result.lines) process.stderr.write(`${line}\n`);
    return result.ok ? 0 : 1;
  }
  if (hook === "pre-push") {
    const result = prePush(root);
    for (const line of result.lines) process.stderr.write(`${line}\n`);
    return result.ok ? 0 : 1;
  }
  process.stderr.write("usage: ai-eng git pre-commit|commit-msg|pre-push\n");
  return 2;
}
