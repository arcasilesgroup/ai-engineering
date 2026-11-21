// A probe, not a contract: on Windows, uninstall sometimes refuses ~/.copilot/hooks/ai-eng.json
// as "changed while ai-eng was removing its entries". Every guard on that path compares a
// path lstat with a descriptor fstat field by field. This measures which field disagrees on
// NTFS for a file just written, and how often the real install-then-strip cycle refuses.

import { expect, test } from "bun:test";
import { closeSync, fstatSync, lstatSync, mkdirSync, mkdtempSync, openSync, readFileSync, rmSync, writeFileSync, type Stats } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { installMachineCarriers, removeMachineCarriers } from "../src/surfaces/carriers-install.ts";

const FIELDS = ["dev", "ino", "size", "mtimeMs", "ctimeMs", "mode", "nlink"] as const;

function differing(left: Stats, right: Stats): string[] {
  return FIELDS.filter((field) => left[field] !== right[field]).map((field) => `${field} ${String(left[field])}≠${String(right[field])}`);
}

test.skipIf(process.platform !== "win32")("probe: lstat and fstat of a file just written agree on every field", () => {
  const dir = mkdtempSync(join(tmpdir(), "ai-eng-stat-probe-"));
  const counts: Record<string, number> = {};
  const examples: string[] = [];
  try {
    for (let run = 0; run < 300; run += 1) {
      const path = join(dir, "settings.json");
      writeFileSync(path, `{"run": ${run}}\n`);
      const entry = lstatSync(path);
      const descriptor = openSync(path, "r");
      const opened = fstatSync(descriptor);
      readFileSync(descriptor);
      const afterRead = fstatSync(descriptor);
      closeSync(descriptor);
      const entryAfter = lstatSync(path);
      for (const [label, left, right] of [["lstat/fstat", entry, opened], ["fstat/fstat", opened, afterRead], ["fstat/lstat", afterRead, entryAfter]] as const) {
        for (const diff of differing(left, right)) {
          const key = `${label} ${diff.split(" ")[0]}`;
          counts[key] = (counts[key] ?? 0) + 1;
          if (examples.length < 6) examples.push(`${label} ${diff}`);
        }
      }
    }
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
  console.log(`stat probe: ${JSON.stringify({ counts, examples })}`);
  expect(counts).toEqual({});
});

test.skipIf(process.platform !== "win32")("probe: install then strip the Copilot carrier, 40 times, never refuses", () => {
  const home = mkdtempSync(join(tmpdir(), "ai-eng-strip-probe-"));
  const before = process.env["AI_ENG_HOME"];
  const refusals: string[] = [];
  try {
    process.env["AI_ENG_HOME"] = home;
    for (let run = 0; run < 40; run += 1) {
      rmSync(join(home, ".copilot"), { recursive: true, force: true });
      mkdirSync(join(home, ".copilot", "hooks"), { recursive: true });
      writeFileSync(join(home, ".copilot", "hooks", "ai-eng.json"), `${JSON.stringify({ user: "owned" }, null, 2)}\n`);
      const installed = installMachineCarriers(["copilot-cli"]);
      if (installed.refused.length > 0) refusals.push(`install ${run}: ${JSON.stringify(installed.refused)}`);
      const removed = removeMachineCarriers(["copilot-cli"]);
      if (removed.refused.length > 0) refusals.push(`strip ${run}: ${JSON.stringify(removed.refused)}`);
    }
  } finally {
    if (before === undefined) delete process.env["AI_ENG_HOME"];
    else process.env["AI_ENG_HOME"] = before;
    rmSync(home, { recursive: true, force: true });
  }
  console.log(`strip probe: ${refusals.length} refusals ${JSON.stringify(refusals.slice(0, 4))}`);
  expect(refusals).toEqual([]);
}, 60_000);
