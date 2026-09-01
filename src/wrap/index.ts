// `ai-eng wrap test -- <cmd>` — the deterministic filter the wrap guard rewrites to.
// Runs the REAL runner with its JSON reporter, then prints only failures grouped by
// file (§15): 14 tests → 3 blocks, ~85% less context. Always prints its line — the
// trace must not lie about which command ran.

import { spawnSync } from "node:child_process";
import { writeReceipt } from "../receipts.ts";

type Painter = (output: string) => string[]; // parsed failures, grouped

const JEST_FAILURE = /(✕|✗|FAIL)\s+(.+)/g;

function paintGeneric(output: string): string[] {
  // Only failing lines, grouped by file when the reporter names one.
  const failures: string[] = [];
  for (const match of output.matchAll(JEST_FAILURE)) {
    failures.push(`${match[1]} ${match[2]?.trim()}`);
  }
  if (failures.length === 0 && /failed|error/i.test(output)) {
    failures.push(output.split("\n").filter((l) => /failed|error/i.test(l)).slice(0, 6).join("\n"));
  }
  return failures;
}

const PAINTERS: Record<string, Painter> = {
  vitest: paintGeneric,
  jest: paintGeneric,
  playwright: paintGeneric,
  bun: paintGeneric,
};

function detectRunner(command: string): string {
  if (/vitest/.test(command)) return "vitest";
  if (/jest/.test(command)) return "jest";
  if (/playwright/.test(command)) return "playwright";
  if (/bun\s+test/.test(command)) return "bun";
  return "generic";
}

export function wrapMain(args: string[]): number {
  if (args[0] === "test") args = args.slice(1);
  if (args[0] === "--") args = args.slice(1);
  const command = args.join(" ").trim();
  if (!command) {
    process.stderr.write("uso: ai-eng wrap test -- <comando de test>\n");
    return 2;
  }
  const runner = detectRunner(command);
  const t0 = Date.now();
  const done = spawnSync("/bin/sh", ["-c", command], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
  const output = `${done.stdout ?? ""}\n${done.stderr ?? ""}`;
  const painter = PAINTERS[runner] ?? paintGeneric;
  const failures = painter(output);
  for (const failure of failures) process.stdout.write(`${failure}\n`);
  const passedMatch = /(\d+)\s+(passed|passing)/.exec(output);
  const failedMatch = /(\d+)\s+failed/.exec(output) ?? (failures.length > 0 ? [null, String(failures.length)] : [null, "0"]);
  process.stdout.write(`${passedMatch?.[1] ?? "?"} passed · ${failedMatch?.[1] ?? failures.length} failed · ${((Date.now() - t0) / 1000).toFixed(1)}s\n`);
  process.stdout.write(`[ai-eng] wrap: ${runner} · salida filtrada\n`);
  writeReceipt({
    event: "PostToolUse",
    surface: "wrap",
    tool: runner,
    guards: { ran: ["wrap"], denied_by: null },
    latency_ms: Date.now() - t0,
    outcome: (done.status ?? 1) === 0 ? "allow" : "deny",
  });
  return done.status ?? 1;
}
