// `bun run bench` — the chain's hot-path latency (p95 over 100 calls) in a governed
// scratch repo. A measurement, never a gate: it prints the number and exits 0, because
// a wall-clock budget asserted inside the test suite failed whenever the machine was busy.

import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { runChain } from "../src/chain/mod.ts";

const SAMPLE_COUNT = 100;
const BUDGET_MS = 50;

const scratch = mkdtempSync(join(tmpdir(), "ai-eng-bench-"));
const homeBefore = process.env.AI_ENG_HOME;
const cwdBefore = process.cwd();
try {
  mkdirSync(join(scratch, ".ai-engineering"), { recursive: true });
  writeFileSync(join(scratch, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n');
  // The loop guard keeps session state in the machine home: never the real one.
  process.env.AI_ENG_HOME = join(scratch, "home");
  process.chdir(scratch);

  const samples: number[] = [];
  for (let i = 0; i < SAMPLE_COUNT; i++) {
    const t0 = performance.now();
    runChain({ tool_name: "Bash", tool_input: { command: `echo ${i}` }, tool_use_id: `lat-${i}`, session_id: "bench" }, "PreToolUse", { inProcess: true });
    samples.push(performance.now() - t0);
  }
  samples.sort((a, b) => a - b);
  // Nearest-rank p95: with 100 samples, a few scheduler pauses cannot move it.
  const p95 = samples[Math.ceil(samples.length * 0.95) - 1] ?? 0;
  const verdict = p95 < BUDGET_MS ? "within" : "OVER";
  console.log(`chain p95: ${p95.toFixed(2)} ms over ${SAMPLE_COUNT} calls (${verdict} the ${BUDGET_MS} ms budget)`);
} finally {
  process.chdir(cwdBefore);
  if (homeBefore === undefined) delete process.env.AI_ENG_HOME;
  else process.env.AI_ENG_HOME = homeBefore;
  rmSync(scratch, { recursive: true, force: true });
}
