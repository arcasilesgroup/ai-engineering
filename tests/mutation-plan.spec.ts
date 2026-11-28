// The campaign is planned before it starts. A ceiling that is lower than the work
// does not report a failure: it cancels the job and reads green in the checks list.
// These tests pin the decision — an estimate from measurement, and a refusal that
// names both numbers instead of a silent kill.
import { afterEach, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { planCampaign, refusalMessage } from "../scripts/mutation-plan.ts";

const REPO = join(import.meta.dir, "..");
const SCRIPT = join(REPO, "scripts", "mutation-plan.ts");

const scratchRoots: string[] = [];

afterEach(() => {
  for (const root of scratchRoots.splice(0)) rmSync(root, { recursive: true, force: true });
});

function scratch(): string {
  const root = mkdtempSync(join(tmpdir(), "mutation-plan-"));
  scratchRoots.push(root);
  return root;
}

/** A source file of exactly `lines` lines, so an estimate is arithmetic and not a guess. */
function sourceFile(root: string, path: string, lines: number): void {
  const full = join(root, path);
  mkdirSync(join(full, ".."), { recursive: true });
  writeFileSync(full, `${Array.from({ length: lines }, () => "const x = 1;").join("\n")}\n`);
}

/** An incremental report whose measured density for `path` is exactly `mutantsPerLine`. */
function report(root: string, entries: Array<{ path: string; sourceLines: number; live: number }>): string {
  const files: Record<string, unknown> = {};
  for (const entry of entries) {
    const mutants: Record<string, { status: string }> = {};
    for (let index = 0; index < entry.live; index += 1) mutants[String(index)] = { status: "Killed" };
    files[entry.path] = { language: "typescript", mutants, source: `${"x\n".repeat(entry.sourceLines - 1)}x` };
  }
  const path = join(root, "stryker-incremental.json");
  writeFileSync(path, JSON.stringify({ schemaVersion: "1", files }));
  return path;
}

describe("mutation-plan — the estimate comes from measurement, not from hope", () => {
  test("the campaign measured on 2026-11-28 does not fit the ceiling it was cancelled under, and does fit the nightly's", () => {
    const root = scratch();
    // 12,000 mutants over 6,000 measured lines: the size of the set that hit 40 minutes.
    const incremental = report(root, [{ path: "src/guards/big.ts", sourceLines: 6000, live: 12000 }]);
    sourceFile(root, "src/guards/big.ts", 6000);

    const under = planCampaign({ root, files: ["src/guards/big.ts"], ceiling: 40, reportPath: incremental });
    const nightly = planCampaign({ root, files: ["src/guards/big.ts"], ceiling: 90, reportPath: incremental });

    expect(under.mutants).toBe(12000);
    expect(under.fits).toBe(false);
    expect(nightly.mutants).toBe(12000);
    expect(nightly.fits).toBe(true);
    expect(nightly.minutes).toBeLessThan(90);
  });

  test("a set twice that size no longer fits the nightly ceiling", () => {
    const root = scratch();
    const incremental = report(root, [{ path: "src/guards/big.ts", sourceLines: 13000, live: 26000 }]);
    sourceFile(root, "src/guards/big.ts", 13000);

    const plan = planCampaign({ root, files: ["src/guards/big.ts"], ceiling: 90, reportPath: incremental });

    expect(plan.mutants).toBe(26000);
    expect(plan.fits).toBe(false);
  });

  test("a file that grew keeps its measured density, so a stale report does not under-estimate it", () => {
    const root = scratch();
    // The report saw 1,000 lines and 1 mutant a line; the file has since doubled.
    const incremental = report(root, [{ path: "src/guards/grown.ts", sourceLines: 1000, live: 1000 }]);
    sourceFile(root, "src/guards/grown.ts", 2000);

    const plan = planCampaign({ root, files: ["src/guards/grown.ts"], ceiling: 90, reportPath: incremental });

    expect(plan.mutants).toBeGreaterThanOrEqual(1998);
    expect(plan.mutants).toBeLessThanOrEqual(2002);
  });

  test("a file the report has never seen is estimated from the measured mutants per line", () => {
    const root = scratch();
    const incremental = report(root, []);
    sourceFile(root, "src/guards/fresh.ts", 500);

    const plan = planCampaign({ root, files: ["src/guards/fresh.ts"], ceiling: 90, reportPath: incremental });

    expect(plan.mutants).toBeGreaterThan(0);
    expect(plan.fits).toBe(true);
    expect(plan.files).toEqual(["src/guards/fresh.ts"]);
  });

  test("an empty surface is no campaign at all: nothing to refuse", () => {
    const root = scratch();

    const plan = planCampaign({ root, files: [], ceiling: 30 });

    expect(plan).toMatchObject({ files: [], mutants: 0, minutes: 0, fits: true });
  });

  test("the refusal names the estimate, the ceiling and the way out", () => {
    const root = scratch();
    sourceFile(root, "src/guards/big.ts", 6000);
    const plan = planCampaign({ root, files: ["src/guards/big.ts"], ceiling: 5 });

    const message = refusalMessage(plan);

    expect(message).toContain("::error::");
    expect(message).toContain(String(plan.minutes));
    expect(message).toContain("5");
    expect(message).toContain("timeout-minutes");
  });
});

describe("mutation-plan — the command CI runs", () => {
  test("a campaign that fits exits 0 and a campaign that does not exits 1 with ::error::", () => {
    const root = scratch();
    sourceFile(root, "src/guards/big.ts", 6000);
    const run = (ceiling: string) =>
      spawnSync(process.execPath, [SCRIPT, "--ceiling", ceiling, "src/guards/big.ts"], { cwd: root, encoding: "utf8" });

    const fitting = run("90");
    const refused = run("5");

    expect(fitting.status).toBe(0);
    expect(fitting.stdout).not.toContain("::error::");
    expect(refused.status).toBe(1);
    expect(refused.stdout).toContain("::error::");
  });

  test("a ceiling is required, and a surface may arrive as one comma-separated argument", () => {
    const root = scratch();
    sourceFile(root, "src/guards/one.ts", 100);
    sourceFile(root, "src/guards/two.ts", 100);
    const run = (args: string[]) => spawnSync(process.execPath, [SCRIPT, ...args], { cwd: root, encoding: "utf8" });

    expect(run(["src/guards/one.ts"]).status).toBe(2);
    const joined = run(["--ceiling", "30", "src/guards/one.ts,src/guards/two.ts"]);
    expect(joined.status).toBe(0);
    expect(joined.stdout).toContain("src/guards/two.ts");
  });
});
