// tests/security-findings.spec.ts — the security skill's ledger has two halves: `verdict`
// says a finding is real, `disposition` says whether it is still live. On `verdict` alone
// every finding stays `confirmed` forever, so a fixed vulnerability keeps reading as an
// unattributed advisory, the next run cannot tell live ground from closed ground, and the
// milestone CHECK "zero open HIGH findings" has nothing to evaluate. The coupling lives in
// report-schema.json; this runs it through the skill's own validator, which is the script
// the auditor runs before writing the report.
import { describe, expect, test, afterAll } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const ROOT = join(import.meta.dir, "..");
const VALIDATOR = join(ROOT, "skills", "ai-security", "references", "validate-findings.cjs");

/** A confirmed finding whose only interesting field is `disposition`: everything else is
 *  the shape the schema requires, so a failure below is about the state, not the shape. */
const CONFIRMED: Record<string, unknown> = {
  verdict: "confirmed",
  title: "a finding",
  description: "what it is",
  root_cause: "why it happens",
  intended_behavior: "what the code should do",
  trace: [
    { kind: "entrypoint", file: "src/a.ts", line: 1, scope: "f", description: "enters here" },
    { kind: "sink", file: "src/b.ts", line: 2, scope: "g", description: "lands here" },
  ],
  conditions: [{ kind: "system_configuration", description: "the host must be configured so" }],
  execution: {
    attacker_perspective: "what an attacker does",
    payloads: ["the bytes"],
    instructions: ["the step"],
    expected_result: "what it shows",
  },
  remediation: { strategy: "the fix" },
  severity: {
    likelihood: { score: "low", reason: "why" },
    impact: { score: "low", reason: "why" },
    overall_severity: "low",
  },
  confidence: { score: "low", reason: "why" },
};

const dir = mkdtempSync(join(tmpdir(), "ai-eng-findings-"));

afterAll(() => {
  rmSync(dir, { recursive: true, force: true });
});

function validate(finding: Record<string, unknown>): { code: number; output: string } {
  const file = join(dir, "findings.json");
  writeFileSync(file, JSON.stringify([finding]));
  const run = spawnSync("node", [VALIDATOR, file], { encoding: "utf8" });
  return { code: run.status ?? 1, output: `${run.stdout}${run.stderr}` };
}

describe("a finding must say where it stands", () => {
  test("one that says nothing is refused", () => {
    const { code, output } = validate(CONFIRMED);
    expect(code).not.toBe(0);
    expect(output).toContain('missing required field "disposition"');
  });

  test("`fixed` without the commit that carries it is refused", () => {
    const { code, output } = validate({ ...CONFIRMED, disposition: { status: "fixed" } });
    expect(code).not.toBe(0);
    expect(output).toContain('missing required field "landed_in"');
  });

  test("one that names its state, either way, validates", () => {
    expect(validate({ ...CONFIRMED, disposition: { status: "open" } }).code).toBe(0);
    const fixed = { status: "fixed", landed_in: "0".repeat(40) };
    expect(validate({ ...CONFIRMED, disposition: fixed }).code).toBe(0);
  });

  test("a state nobody defined is named, never accepted", () => {
    const { code, output } = validate({ ...CONFIRMED, disposition: { status: "patched" } });
    expect(code).not.toBe(0);
    expect(output).toContain('"status" must be one of "open", "fixed"');
  });
