// `ai-eng wrap test -- <cmd>` — the deterministic filter the wrap guard rewrites to.
// Runs the REAL command (vitest gets its JSON reporter), prints only failures
// grouped by file (§15): 14 tests → 3 blocks, ~85% less context. Always prints its
// line with the receipt id — the trace must not lie about which command ran.

import { spawnSync } from "node:child_process";
import { writeReceipt, receiptId } from "../receipts.ts";
import { detectRunner, paint, paintVitestJson, countSummary } from "./paint.ts";

/** A hung runner must not hang the agent's context forever. */
const TIMEOUT_MS = 10 * 60 * 1000;

export function wrapMain(args: string[]): number {
  if (args[0] === "test") args = args.slice(1);
  if (args[0] === "--") args = args.slice(1);
  const command = args.join(" ").trim();
  if (!command) {
    process.stderr.write("usage: ai-eng wrap test -- <test command>\n");
    return 2;
  }
  const runner = detectRunner(command);
  // vitest is the one runner whose JSON reporter is free to consume; the others
  // are painted from their own text, which the guard's SKIPS already protects.
  const useJson = runner === "vitest" && !/--reporter/.test(command);
  const t0 = Date.now();
  const done = spawnSync("/bin/sh", ["-c", useJson ? `${command} --reporter=json` : command], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
    timeout: TIMEOUT_MS,
  });
  const timedOut = done.error != null && (done.error as NodeJS.ErrnoException).code === "ETIMEDOUT";
  const stdout = done.stdout ?? "";
  const output = `${stdout}\n${done.stderr ?? ""}`;

  const json = useJson ? paintVitestJson(stdout) : null;
  const blocks = json?.blocks ?? paint(runner, output);
  for (const block of blocks) {
    process.stdout.write(`${block.file}\n`);
    for (const line of block.lines) process.stdout.write(`${line}\n`);
  }
  const counts = json ? { passed: json.passed, failed: json.failed } : countSummary(output);
  const failed =
    counts.failed !== "?"
      ? counts.failed
      : String(blocks.reduce((n, b) => n + b.lines.filter((l) => l.startsWith("×")).length, 0));
  process.stdout.write(`${counts.passed} passed · ${failed} failed · ${((Date.now() - t0) / 1000).toFixed(1)}s\n`);

  const status = timedOut ? 124 : (done.status ?? 1);
  const receipt = writeReceipt({
    event: "PostToolUse",
    surface: "wrap",
    tool: runner,
    guards: { ran: ["wrap"], denied_by: null },
    latency_ms: Date.now() - t0,
    outcome: timedOut ? "error" : status === 0 ? "allow" : "deny",
  });
  process.stdout.write(
    `[ai-eng] wrap: ${runner} · salida filtrada${receipt ? ` · receipt ${receiptId(receipt)}` : ""}${timedOut ? " · TIMEOUT" : ""}\n`,
  );
  return status;
}
