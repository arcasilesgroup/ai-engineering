// Entry for `ai-eng git <hook>` — the floor the 3-line shims exec into.
// commit-msg needs the receipt for its trailer; pre-commit/pre-push stay dry and fast.

import { repoRoot, isGoverned } from "../env.ts";
import { preCommit, commitMsg, prePush } from "./index.ts";
import { createHash } from "node:crypto";
import { receiptId, writeReceipt } from "../receipts.ts";

function writeHookOutput(result: { ok: boolean; lines: string[] }): void {
  if (result.ok || result.lines.length === 0) return;
  const output = result.lines.join("\n").replace(/\r\n?/g, "\n").replace(/\n+$/, "");
  const outputLines = output.split("\n");
  const limitedLines = outputLines.length <= 3
    ? outputLines
    : [...outputLines.slice(0, 2), outputLines.slice(2).join(" | ")];
  for (const line of limitedLines) process.stderr.write(`${line}\n`);
}

export async function floor(hook: string, msgFile?: string): Promise<number> {
  const root = repoRoot();
  // The same gate as the chain, for the same reason: a repo that never declared
  // itself is not ours to judge, and the shims run in every clone now — a foreign
  // repo's commit must pass in silence, not pay for policy nobody asked for (G5).
  if (root === null || !isGoverned(root)) return 0;
  if (hook === "pre-commit") {
    const t0 = Date.now();
    const result = preCommit(root);
    writeReceipt({
      event: "git-pre-commit",
      surface: "git",
      tool: "pre-commit",
      guards: { ran: ["floor"], denied_by: result.ok ? null : "floor" },
      latency_ms: Date.now() - t0,
      outcome: result.ok ? "allow" : "deny",
    });
    if (!result.ok) {
      writeHookOutput({
        ...result,
        lines: [...result.lines, "[git floor] pre-commit: BLOCKED — what the hooks would say is what needs fixing."],
      });
      return 1;
    }
    writeHookOutput(result);
    return 0;
  }
  if (hook === "commit-msg") {
    if (!msgFile) {
      process.stderr.write("usage: ai-eng git commit-msg <msgfile>\n");
      return 2;
    }
    // No override lookup here: the floor has no guard an override can excuse, so
    // stamping a reason would write false exceptions into git history (T19).
    const started = Date.now();
    // Write the receipt only once the message passes validation, so the trailer names
    // a real on-disk receipt and rejected commit messages never log a false allow.
    const mintReceiptId = (): string => {
      const receipt = writeReceipt({
        event: "git-commit-msg",
        surface: "git",
        tool: "commit-msg",
        guards: { ran: ["floor"], denied_by: null },
        latency_ms: Math.max(1, Date.now() - started),
        outcome: "allow",
      }, root);
      return receipt === null
        ? createHash("sha256").update(`${new Date().toISOString()}:floor`).digest("hex").slice(0, 8)
        : receiptId(receipt);
    };
    const result = commitMsg(msgFile, mintReceiptId);
    writeHookOutput(result);
    return result.ok ? 0 : 1;
  }
  if (hook === "pre-push") {
    const result = prePush(root);
    writeHookOutput(result);
    return result.ok ? 0 : 1;
  }
  process.stderr.write("usage: ai-eng git pre-commit|commit-msg|pre-push\n");
  return 2;
}
