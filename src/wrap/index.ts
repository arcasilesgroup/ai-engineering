// `ai-eng wrap test --base64 <cmd>` — the deterministic filter the guard rewrites to.
// Runs the REAL command (vitest gets its JSON reporter), prints only failures
// grouped by file (§15): 14 tests → 3 blocks, ~85% less context. Always prints its
// line with the receipt id — the trace must not lie about which command ran.

import { spawnSync } from "node:child_process";
import { lstatSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { receiptsDir, repoRoot } from "../env.ts";
import { judgeWrappedCommand } from "../chain/mod.ts";
import { isTestCommand } from "../guards/wrap.ts";
import { writeReceipt, receiptId, type Receipt } from "../receipts.ts";
import { detectRunner, paint, paintVitestJson, countSummary } from "./paint.ts";

/** A hung runner must not hang the agent's context forever. */
const TIMEOUT_MS = 10 * 60 * 1000;
/** The wrapped command is the agent's shell text. Windows has no /bin/sh: the POSIX
 *  shell the agent's Bash tool runs there (Git for Windows) is found on PATH. */
const SHELL = process.platform === "win32" ? "sh" : "/bin/sh";

function decodeCommand(args: string[]): string | null {
  if (args.length !== 3 || args[0] !== "test" || args[1] !== "--base64") return null;
  const encoded = args[2]!;
  if (!/^[A-Za-z0-9_-]+$/.test(encoded)) return null;
  const bytes = Buffer.from(encoded, "base64url");
  if (bytes.toString("base64url") !== encoded) return null;
  const command = bytes.toString("utf8");
  return Buffer.from(command, "utf8").equals(bytes) ? command : null;
}

function saveFullOutput(receipt: Receipt | null, output: string): string | null {
  const root = repoRoot();
  const directory = root === null ? null : receiptsDir(root);
  if (receipt === null || root === null || directory === null) return null;
  try {
    for (const path of [join(root, ".ai-engineering"), directory]) {
      const stat = lstatSync(path);
      if (!stat.isDirectory() || stat.isSymbolicLink()) return null;
    }
    const id = receiptId(receipt);
    writeFileSync(join(directory, `${id}.log`), output, { flag: "wx", mode: 0o600 });
    return `.ai-engineering/receipts/${id}.log`;
  } catch {
    return null;
  }
}

export function wrapMain(args: string[]): number {
  const command = decodeCommand(args);
  if (command === null || command.trim().length === 0) {
    process.stderr.write("usage: ai-eng wrap test --base64 <encoded test command>\n");
    return 2;
  }
  // The wrapper is not a second way to run code: only a test command, and only one the
  // guards allow from here — the same answer the agent would get running it directly.
  const refusal = isTestCommand(command).wrap
    ? judgeWrappedCommand(command, process.cwd())
    : "only a test-runner command can be wrapped";
  if (refusal !== null) {
    process.stderr.write(`ai-eng wrap: refused. ${refusal}\n`);
    return 2;
  }
  const runner = detectRunner(command);
  // vitest is the one runner whose JSON reporter is free to consume; the others
  // are painted from their own text, which the guard's SKIPS already protects.
  const useJson = runner === "vitest" && !/--reporter/.test(command);
  const t0 = Date.now();
  const done = spawnSync(SHELL, ["-c", useJson ? `${command} --reporter=json` : command], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
    timeout: TIMEOUT_MS,
  });
  const timedOut = done.error != null && (done.error as NodeJS.ErrnoException).code === "ETIMEDOUT";
  // A command that never started has no counts to paint: "? passed · 0 failed" with a
  // receipt would report a run that did not happen. Only a spawn with no pid never
  // started: ENOBUFS (output over maxBuffer) stops a running child, and what it printed
  // before the cut is still the run's evidence.
  const neverStarted = !timedOut && !(done.pid > 0);
  if (done.error != null && neverStarted) {
    process.stderr.write(`ai-eng wrap: could not start ${SHELL}: ${done.error.message}\n`);
    return 127;
  }
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
  const logPath = saveFullOutput(receipt, `${stdout}${done.stderr ?? ""}`);
  if (logPath !== null) process.stdout.write(`full output: ${logPath}\n`);
  return status;
}
