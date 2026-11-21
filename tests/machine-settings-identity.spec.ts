// A settings file is refused when it is the machine record under a second name (a hard
// link): rewriting it would rewrite the record. The identity check compares file ids as
// bigints, because an NTFS id is 64 bits and a JS number rounds it once it passes 2^53;
// two files created a moment apart then shared an id, and uninstall refused the Copilot
// settings on Windows CI as "a hard link with a second name" about one run in three.

import { afterEach, describe, expect, test } from "bun:test";
import { linkSync, mkdirSync, mkdtempSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { installMachineCarriers, removeMachineCarriers } from "../src/surfaces/carriers-install.ts";
import { machineSettingsAliasMachineState, machineStateFile, readableMachineSettings } from "../src/surfaces/machine-state.ts";

const homeBefore = process.env["AI_ENG_HOME"];
const roots: string[] = [];

afterEach(() => {
  if (homeBefore === undefined) delete process.env["AI_ENG_HOME"];
  else process.env["AI_ENG_HOME"] = homeBefore;
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});

function machine(): string {
  const home = mkdtempSync(join(tmpdir(), "ai-eng-identity-"));
  roots.push(home);
  process.env["AI_ENG_HOME"] = home;
  writeFileSync(machineStateFile(), "{}\n");
  return home;
}

describe("a settings file and the machine record are one file only when they are", () => {
  test("a hard link to the machine record is an alias; a file of its own is not", () => {
    const home = machine();
    const own = join(home, "own.json");
    writeFileSync(own, "{}\n");
    const ownSnapshot = readableMachineSettings(own);
    expect(ownSnapshot).not.toBeNull();
    expect(machineSettingsAliasMachineState(ownSnapshot!)).toBe(false);

    const linked = join(home, "linked.json");
    linkSync(machineStateFile(), linked);
    const linkedSnapshot = readableMachineSettings(linked);
    expect(linkedSnapshot).not.toBeNull();
    expect(machineSettingsAliasMachineState(linkedSnapshot!)).toBe(true);
  });

  test("files created back to back never read as one, however large their ids", () => {
    const home = machine();
    let largeIds = 0;
    for (let run = 0; run < 200; run += 1) {
      const path = join(home, `settings-${run}.json`);
      writeFileSync(path, "{}\n");
      if (statSync(path, { bigint: true }).ino > BigInt(Number.MAX_SAFE_INTEGER)) largeIds += 1;
      const snapshot = readableMachineSettings(path);
      expect(machineSettingsAliasMachineState(snapshot!)).toBe(false);
    }
    // The evidence the bigint comparison is needed where it runs, not a requirement.
    console.log(`file ids past 2^53 on ${process.platform}: ${largeIds} of 200`);
  });

  test("installing then stripping the Copilot carrier never refuses, run after run", () => {
    const home = machine();
    const settings = join(home, ".copilot", "hooks", "ai-eng.json");
    const refusals: string[] = [];
    for (let run = 0; run < 30; run += 1) {
      rmSync(join(home, ".copilot"), { recursive: true, force: true });
      mkdirSync(join(home, ".copilot", "hooks"), { recursive: true });
      writeFileSync(settings, `${JSON.stringify({ user: "owned" }, null, 2)}\n`);
      refusals.push(...installMachineCarriers(["copilot-cli"]).refused.map((entry) => `install ${run}: ${entry.reason}`));
      refusals.push(...removeMachineCarriers(["copilot-cli"]).refused.map((entry) => `strip ${run}: ${entry.reason}`));
    }
    expect(refusals).toEqual([]);
  }, 60_000);
});
