// tests/wrap.test.ts — §15: the filter itself. The adversarial suite proves the
// guard rewrites; this proves the rewrite is worth making: failures survive,
// noise dies, counts are true, and the receipt id rides the trace line.

import { beforeAll, describe, expect, test } from "bun:test";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { detectRunner, paint, paintVitestJson, countSummary } from "../src/wrap/paint.ts";
import { wrapMain } from "../src/wrap/index.ts";

describe("wrap · detectRunner", () => {
  test("names the runner from the command", () => {
    expect(detectRunner("bun test")).toBe("bun");
    expect(detectRunner("npx vitest run")).toBe("vitest");
    expect(detectRunner("jest --ci")).toBe("jest");
    expect(detectRunner("playwright test")).toBe("playwright");
    expect(detectRunner("npm test")).toBe("generic");
  });
});

describe("wrap · paint bun", () => {
  const BUN = [
    "bun test v1.4.0 (34cbb9a40)",
    "",
    "t.test.ts:",
    '1 | test("checkout page loads", () => { expect("x").toBe("Total") });',
    "error: expect(received).toBe(expected)",
    "",
    'Expected: "Total"',
    'Received: "x"',
    "",
    "      at <anonymous> (/private/tmp/wrap-smoke/t.test.ts:4:49)",
    "(fail) checkout page loads [0.22ms]",
    "",
    " 2 pass",
    " 1 fail",
    "Ran 3 tests across 1 file. [6.00ms]",
  ].join("\n");
  test("groups failures by file with name + locator", () => {
    const blocks = paint("bun", BUN);
    expect(blocks).toHaveLength(1);
    expect(blocks[0]!.file).toBe("t.test.ts");
    expect(blocks[0]!.lines[0]).toBe("× checkout page loads");
    expect(blocks[0]!.lines.join("\n")).toContain("/private/tmp/wrap-smoke/t.test.ts:4:49");
  });
  test("passes counts through bun's own summary", () => {
    expect(countSummary(BUN)).toEqual({ passed: "2", failed: "1" });
  });
});

describe("wrap · paint vitest text", () => {
  const VITEST = [
    "❯ cart.test.ts (6 tests | 2 failed) 120ms",
    "   × checkout page loads",
    '     → expected "" to have text content "Total"',
    "       cart.test.ts:88:14",
    "FAIL  src/payment.test.tsx > payment form validates",
    "   × payment form validates",
    "Timeout 5000ms",
  ].join("\n");
  test("only failing cases make it into blocks", () => {
    const blocks = paint("vitest", VITEST);
    const text = JSON.stringify(blocks);
    expect(text).toContain("checkout page loads");
    expect(text).toContain("payment form validates");
    expect(text).not.toContain("homepage loads");
  });
});

describe("wrap · paint vitest JSON", () => {
  const REPORT = JSON.stringify({
    numTotalTestSuites: 2,
    numPassedTests: 12,
    numFailedTests: 2,
    testResults: [
      {
        name: "/repo/cart.test.tsx",
        assertionResults: [
          { fullName: "homepage loads", status: "passed" },
          { fullName: "checkout page loads", status: "failed", failureMessages: ['expected "" to have text content "Total"'] },
        ],
      },
      {
        name: "/repo/payment.test.tsx",
        assertionResults: [{ fullName: "payment form validates", status: "failed", failureMessages: ["Timeout 5000ms"] }],
      },
    ],
  });
  test("parses counts + failed-only blocks", () => {
    const r = paintVitestJson(REPORT);
    expect(r).not.toBeNull();
    expect(r!.passed).toBe("12");
    expect(r!.failed).toBe("2");
    expect(r!.blocks.map((b) => b.file)).toEqual(["/repo/cart.test.tsx", "/repo/payment.test.tsx"]);
    expect(r!.blocks[0]!.lines).toEqual(["× checkout page loads", '  expected "" to have text content "Total"']);
  });
  test("returns null on non-JSON stdout", () => {
    expect(paintVitestJson("plain text run")).toBeNull();
  });
});

describe("wrap · paint playwright", () => {
  const PW = [
    "✘  1 [chromium] › cart.spec.tsx:88:1 › checkout page loads (1.2s)",
    "✓  2 [chromium] › cart.spec.tsx:10:1 › adds an item (0.4s)",
    "✘  3 [firefox] › payment.spec.tsx:31:1 › payment form validates (5.0s)",
  ].join("\n");
  test("groups by spec file, failures only", () => {
    const blocks = paint("playwright", PW);
    expect(blocks).toHaveLength(2);
    expect(blocks[0]!.lines).toEqual(["× [chromium] › checkout page loads (1.2s)"]);
  });
});

describe("wrap · paint generic", () => {
  test("keeps failing lines, drops the passing ones", () => {
    const blocks = paint("generic", "ok line\nFAIL something\nError: boom\nall good");
    expect(blocks).toHaveLength(1);
    expect(blocks[0]!.lines).toEqual(["FAIL something", "Error: boom"]);
  });
  test("clean run paints nothing", () => {
    expect(paint("generic", "12 passed\nAll tests passed")).toEqual([]);
  });
});

describe("wrap · wrapMain end-to-end", () => {
  let dir: string;
  let home: string;
  beforeAll(() => {
    dir = mkdtempSync(join(tmpdir(), "wrap-e2e-"));
    home = mkdtempSync(join(tmpdir(), "wrap-home-"));
    mkdirSync(join(dir, ".git")); // a governed root, so the receipt has somewhere to live
    writeFileSync(
      join(dir, "a.test.ts"),
      `import { test, expect } from "bun:test";
test("a passes", () => { expect(1).toBe(1) });
test("b passes", () => { expect(2).toBe(2) });
test("checkout page loads", () => { expect("x").toBe("Total") });
`,
    );
  });
  test("filters a real bun run: noise gone, counts true, receipt line present", () => {
    const prevCwd = process.cwd();
    const prevHome = process.env.AI_ENG_HOME;
    process.chdir(dir);
    process.env.AI_ENG_HOME = home;
    const lines: string[] = [];
    const write = process.stdout.write.bind(process.stdout);
    process.stdout.write = ((chunk: string | Uint8Array) => {
      lines.push(String(chunk));
      return true;
    }) as typeof process.stdout.write;
    let status: number;
    try {
      status = wrapMain(["test", "--", "bun test"]);
    } finally {
      process.stdout.write = write;
      process.chdir(prevCwd);
      if (prevHome === undefined) delete process.env.AI_ENG_HOME;
      else process.env.AI_ENG_HOME = prevHome;
    }
    const out = lines.join("");
    expect(status).toBe(1); // the failing run keeps its exit code
    expect(out).toContain("× checkout page loads");
    expect(out).not.toContain("a passes");
    expect(out).toContain("2 passed · 1 failed");
    expect(out).toMatch(/\[ai-eng\] wrap: bun · salida filtrada · receipt [0-9a-f]{8}\n/);
  });
  test("usage error without a command", () => {
    const err = process.stderr.write.bind(process.stderr);
    process.stderr.write = (() => true) as typeof process.stderr.write;
    try {
      expect(wrapMain([])).toBe(2);
    } finally {
      process.stderr.write = err;
    }
  });
});
