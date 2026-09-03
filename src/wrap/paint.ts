// Pure painters for `ai-eng wrap test` (§15): text in, failure blocks out.
// One shape per runner, grouped by file. No I/O here — the entry point spawns,
// the painters parse. vitest gets a real JSON reporter; the rest are regex over
// the runner's own output, which is stable enough and costs the agent nothing.

export type Block = { file: string; lines: string[] };

// Runners colorize even when piped; strip before matching. Built from the code
// point so the pattern itself carries no control character.
const ANSI = new RegExp(`${String.fromCharCode(27)}\\[[0-9;]*m`, "g");
const plain = (line: string): string => line.replace(ANSI, "");

export function detectRunner(command: string): string {
  if (/\bvitest\b/.test(command)) return "vitest";
  if (/\bjest\b/.test(command)) return "jest";
  if (/\bplaywright\b/.test(command)) return "playwright";
  if (/\bbun\s+test\b/.test(command)) return "bun";
  return "generic";
}

/** vitest/jest text: `❯ file (N failed)` header, `× <name>` cases, `→ detail` and `file:line:col`. */
function paintVitestText(output: string): Block[] {
  const blocks: Block[] = [];
  let current: Block | null = null;
  for (const raw of output.split("\n")) {
    const line = plain(raw);
    // `FAIL  src/payment.test.tsx > payment form validates`
    const fail = line.match(/^FAIL\s+\S*\|?\s*(\S+\.[tj]sx?)/);
    if (fail) {
      current = { file: fail[1]!, lines: [] };
      blocks.push(current);
      continue;
    }
    // Default reporter: `❯ src/cart.test.tsx (6 tests | 2 failed) 120ms`
    const header = line.match(/^❯\s+(\S+\.[tj]sx?)\s+\(\d+ tests? \| \d+ failed/);
    if (header) {
      current = { file: header[1]!, lines: [] };
      blocks.push(current);
      continue;
    }
    const test = line.match(/^\s*[×✕✗]\s+(.+)/);
    if (test && current) {
      current.lines.push(`× ${test[1]!.trim()}`);
      continue;
    }
    const detail = line.match(/^\s*→\s+(.+)/);
    if (detail && current) {
      current.lines.push(`  ${detail[1]!.trim()}`);
      continue;
    }
    const loc = line.match(/^\s*(\S+\.[tj]sx?:\d+:\d+)\s*(.*)$/);
    if (loc && current) {
      current.lines.push(`  ${loc[1]}${loc[2] ? ` → ${loc[2].trim()}` : ""}`);
    }
  }
  return blocks;
}

/** bun test: `file:` header scopes `(fail)` lines; `at <anonymous> (file:line:col)` locates.
 *  bun's output: the `at` line appears BEFORE the `(fail)` line, not after. */
export function paintBun(output: string): Block[] {
  const blocks: Block[] = [];
  let current: Block | null = null;
  // bun prints the error block (expect diff + `at` locator) BEFORE the
  // `(fail) <name>` line that names the test — so `(fail)` flushes the buffer.
  let loc: string | null = null;
  let errs: string[] = [];
  for (const raw of output.split("\n")) {
    const line = plain(raw);
    const file = line.match(/^(\S+\.[tj]sx?):\s*$/);
    if (file) {
      current = { file: file[1]!, lines: [] };
      blocks.push(current);
      continue;
    }
    const at = line.match(/^\s*at\s.*?\((\S+?:\d+:\d+)\)\s*$/);
    if (at) {
      if (!loc) loc = at[1]!;
      continue;
    }
    const err = line.match(/^(error|expect)\b/) ?? line.match(/^(Expected|Received):/);
    if (err) {
      errs.push(`  ${line.trim()}`);
      continue;
    }
    const fail = line.match(/^\(fail\)\s+(.+)/);
    if (fail) {
      if (current) {
        current.lines.push(`× ${fail[1]!.replace(/\s*\[\d+(\.\d+)?ms\]\s*$/, "").trim()}`);
        if (loc) current.lines.push(`  ${loc}`);
        current.lines.push(...errs);
      }
      loc = null;
      errs = [];
    }
  }
  return blocks.filter((b) => b.lines.length > 0);
}

/** playwright: `✘ N [project] › file.spec.ts:line:col › test name` */
function paintPlaywright(output: string): Block[] {
  const byFile = new Map<string, Block>();
  for (const raw of output.split("\n")) {
    const line = plain(raw);
    const m = line.match(/^✘\s+\d+\s+\[([^\]]+)\]\s+›\s+(\S+?):\d+:\d+\s+›\s+(.+)/);
    if (!m) continue;
    const block = byFile.get(m[2]!) ?? { file: m[2]!, lines: [] };
    block.lines.push(`× [${m[1]}] › ${m[3]!.trim()}`);
    byFile.set(m[2]!, block);
  }
  return [...byFile.values()];
}

/** Last-resort filter: failing lines only, capped so a crash dump cannot flood the context. */
export function paintGeneric(output: string): Block[] {
  const hits = output
    .split("\n")
    .map((l) => plain(l).trim())
    .filter((l) => /(fail|error)/i.test(l) && !/^\d+\s+(passed?|failing?|failed)/i.test(l));
  if (hits.length === 0) return [];
  return [{ file: "output", lines: hits.slice(0, 10) }];
}

export function paint(runner: string, output: string): Block[] {
  switch (runner) {
    case "bun":
      return paintBun(output);
    case "playwright":
      return paintPlaywright(output);
    case "vitest":
    case "jest":
      return paintVitestText(output);
    default:
      return paintGeneric(output);
  }
}

/** vitest JSON reporter → blocks + counts. Null when stdout is not the JSON report. */
export function paintVitestJson(stdout: string): { blocks: Block[]; passed: string; failed: string } | null {
  const start = stdout.indexOf("{");
  if (start === -1) return null;
  let report: {
    numTotalTestSuites?: number;
    numPassedTests?: number;
    numFailedTests?: number;
    testResults?: Array<{ name?: string; assertionResults?: Array<{ fullName?: string; title?: string; status?: string; failureMessages?: string[] }> }>;
  };
  try {
    report = JSON.parse(stdout.slice(start));
  } catch {
    return null;
  }
  if (!Array.isArray(report.testResults)) return null;
  const passed = typeof report.numPassedTests === "number" ? String(report.numPassedTests) : "?";
  const failed = typeof report.numFailedTests === "number" ? String(report.numFailedTests) : "?";
  const blocks: Block[] = [];
  for (const file of report.testResults) {
    const lines: string[] = [];
    for (const t of file.assertionResults ?? []) {
      if (t.status !== "failed") continue;
      lines.push(`× ${(t.fullName || t.title || "test").trim()}`);
      const msg = (t.failureMessages ?? []).join("\n").split("\n").find((l) => l.trim());
      if (msg) lines.push(`  ${msg.trim().slice(0, 160)}`);
    }
    if (lines.length) blocks.push({ file: file.name ?? "unknown", lines });
  }
  return { blocks, passed, failed };
}

/** Count lines from the runners' own summaries. bun says `2 pass`; node says `2 pass`. */
export function countSummary(output: string): { passed: string; failed: string } {
  const passed =
    output.match(/(\d+)\s+(?:tests?\s+)?passed?/i)?.[1] ??
    output.match(/(\d+)\s+passing/i)?.[1] ??
    output.match(/(\d+)\s+pass\b/i)?.[1] ??
    "?";
  const failed =
    output.match(/(\d+)\s+(?:tests?\s+)?failed/i)?.[1] ??
    output.match(/(\d+)\s+fail\b/i)?.[1] ??
    output.match(/(\d+)\s+failing/i)?.[1] ??
    "?";
  return { passed, failed };
}