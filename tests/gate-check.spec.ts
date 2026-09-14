// The gate executor's own rule: a check that proves something says what it found.
//
// Reproduced from a real milestone: three gates were ticked with the recorded evidence
// `(no output)` — an `ls … >/dev/null`, a `test -f`, a `test … && grep -q` — so the box
// rested on an exit code and the ledger carried the silence as if it were proof. The
// shape is not an accident of that milestone: templates/spec.html.tpl taught it, with
// `CHECK: test -f README.md` as the single example a planner is handed.
//
// This file is the check that fails for that reason. It drives the real executor
// (skills/ai-proof/scripts/gate-check.mjs — the only executor, never reimplemented) against
// a fixture whose checks are deliberately silent and deliberately loud.

import { describe, test, expect, beforeAll, afterAll } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const executor = join(import.meta.dir, "..", "skills", "ai-proof", "scripts", "gate-check.mjs");
let dir: string;

/** One gate file, run through the executor: the file's text afterwards, and what the run said. */
function runGates(body: string): { text: string; said: string; code: number } {
  const file = join(dir, "GATES.md");
  writeFileSync(file, body);
  const out = spawnSync(process.execPath, [executor, file, "--recheck"], { encoding: "utf8" });
  const said = `${out.stdout ?? ""}${out.stderr ?? ""}`;
  // A crash is not a verdict: the first version of the silence rule threw a
  // ReferenceError and still "passed" the fixture, because a broken run and an unmet gate
  // both exit 1. The run has to name a verdict.
  expect(said).not.toInclude("Error");
  expect(out.status === 0 || out.status === 1).toBe(true);
  return { text: readFileSync(file, "utf8"), said, code: out.status ?? -1 };
}

const box = (text: string, id: string): string => (new RegExp(`^- \\[( |x)\\] ${id}:`, "m").exec(text)?.[1] ?? "?");
const evidence = (text: string, id: string): string => {
  const gate = new RegExp(`^- \\[.\] ${id}:.*$`, "m").exec(text);
  if (gate === null) return "";
  const rest = text.slice(gate.index);
  return (/^\s+EVIDENCE: (.*)$/m.exec(rest)?.[1] ?? "").trim();
};

beforeAll(() => {
  dir = mkdtempSync(join(tmpdir(), "ai-eng-gate-"));
});

afterAll(() => {
  rmSync(dir, { recursive: true, force: true });
});

describe("the gate executor records evidence, not silence", () => {
  test("a check that prints nothing is not evidence, and the box stays unticked", () => {
    const { text, said, code } = runGates(
      ["# Gates: fixture", "", "- [ ] G1: something that says nothing", "  CHECK: true", "  EVIDENCE: pending", ""].join("\n"),
    );
    expect(box(text, "G1")).toBe(" ");
    expect(evidence(text, "G1")).toInclude("no output");
    expect(evidence(text, "G1")).toInclude("says what it found");
    expect(said).toInclude("silence is not evidence");
    // And it is UNMET, not a tick that nobody counted: the run must say so and fail.
    expect(said).toInclude("UNMET: 1");
    expect(code).toBe(1);
  });

  test("a gate the author ticked loses its claim when its check turns out silent", () => {
    const { text, code } = runGates(
      ["# Gates: fixture", "", "- [x] G1: ticked on nothing", "  CHECK: true", "  EVIDENCE: author typed this", ""].join("\n"),
    );
    expect(code).toBe(1);
    // The box is the author's claim and this tool never unticks it — the same rule as a
    // check that fails: the evidence is withdrawn and the gate counts as unmet.
    expect(evidence(text, "G1")).toBe("pending");
  });

  test("a check that says what it found is evidence, and the box is ticked", () => {
    const { text, said, code } = runGates(
      ["# Gates: fixture", "", "- [ ] G1: something that reports", "  CHECK: echo 'checked 3 files'", "  EVIDENCE: pending", ""].join("\n"),
    );
    expect(box(text, "G1")).toBe("x");
    expect(evidence(text, "G1")).toInclude("checked 3 files");
    expect(said).toInclude("ALL MET");
    expect(code).toBe(0);
  });

  test("a check that fails is still a failure — silence is the new rule, not the only one", () => {
    const { text, said } = runGates(
      ["# Gates: fixture", "", "- [ ] G1: something broken", "  CHECK: sh -c 'echo boom >&2; exit 1'", "  EVIDENCE: pending", ""].join("\n"),
    );
    expect(box(text, "G1")).toBe(" ");
    expect(evidence(text, "G1")).toBe("pending"); // a failure has no evidence to record
    expect(said).toInclude("boom"); // the reason is what the run says
  });

  test("an EXPECT still decides, and a check that prints for it is met", () => {
    const { text } = runGates(
      ["# Gates: fixture", "", "- [ ] G1: a number", "  CHECK: echo 'total: 12'", "  EXPECT: /total: \\d+/", "  EVIDENCE: pending", ""].join("\n"),
    );
    expect(box(text, "G1")).toBe("x");
  });

  test("stderr counts as output: a check that reports there is heard", () => {
    const { text } = runGates(
      ["# Gates: fixture", "", "- [ ] G1: says it on stderr", "  CHECK: sh -c 'echo reported >&2'", "  EVIDENCE: pending", ""].join("\n"),
    );
    expect(box(text, "G1")).toBe("x");
    expect(evidence(text, "G1")).toInclude("reported");
  });
});
