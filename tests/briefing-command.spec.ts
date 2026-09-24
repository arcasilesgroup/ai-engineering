// Session handoff briefing — the first pending gate, a sorted deny list, and
// the ungoverned path. Exercises the parse helpers Sonar flagged (single-match
// instead of a one-iteration loop; localeCompare sort).
import { afterEach, expect, test } from "bun:test";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { formatBriefing, generateBriefing } from "../src/commands/briefing.ts";

const roots: string[] = [];

afterEach(() => {
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

function tempRepo(): string {
  const root = mkdtempSync(join(tmpdir(), "ai-eng-briefing-"));
  roots.push(root);
  mkdirSync(join(root, ".ai-engineering", "receipts"), { recursive: true });
  writeFileSync(join(root, ".ai-engineering", "config.toml"), '[surfaces]\nenabled = ["claude-code"]\n');
  return root;
}

test("generateBriefing names the first pending gate and ignores later ones", () => {
  const root = tempRepo();
  writeFileSync(
    join(root, ".ai-engineering", "spec.html"),
    `<pre id="gates">
- [ ] G3: the third thing
  CHECK: true
  EVIDENCE: pending
- [ ] G9: later
  CHECK: true
  EVIDENCE: pending
</pre>`,
  );
  writeFileSync(
    join(root, ".ai-engineering", "plan.html"),
    `<pre>
- [ ] ship the floor isolation
- [ ] then the windows package
</pre>`,
  );
  const briefing = generateBriefing(root);
  expect(briefing.governed).toBe(true);
  expect(briefing.spec.gates).toBe("G3: the third thing");
  expect(briefing.plan.current_step).toBe("ship the floor isolation");
  expect(formatBriefing(briefing)).toContain("Next gate: G3: the third thing");
});

test("generateBriefing lists recent denies newest-first by receipt name", () => {
  const root = tempRepo();
  const dir = join(root, ".ai-engineering", "receipts");
  for (const [name, tool] of [
    ["2020-01-01T00-00-00Z-old.json", "Bash"],
    ["2026-01-01T00-00-00Z-new.json", "Write"],
  ] as const) {
    writeFileSync(
      join(dir, name),
      JSON.stringify({
        outcome: "deny",
        ts: name.slice(0, 20),
        tool,
        guards: { denied_by: "self-protect" },
      }),
    );
  }
  const briefing = generateBriefing(root);
  expect(briefing.recent_denies[0]?.tool).toBe("Write");
  expect(briefing.recent_denies[1]?.tool).toBe("Bash");
});

test("generateBriefing on an ungoverned root says so", () => {
  const root = mkdtempSync(join(tmpdir(), "ai-eng-briefing-bare-"));
  roots.push(root);
  const briefing = generateBriefing(root);
  expect(briefing.governed).toBe(false);
  expect(formatBriefing(briefing)).toContain("not governed");
});
