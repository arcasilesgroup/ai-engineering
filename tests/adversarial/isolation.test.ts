// Adversarial: AI_ENG_HOME isolates the canon and mirrors from the real machine home.
import { test, expect, beforeAll, afterAll } from "bun:test";
import { mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import { join } from "node:path";
import { mirrorTargets } from "../../src/surfaces/canon-install.ts";
import { restoreSandboxEnv, snapshotSandboxEnv } from "../fixtures/sandbox-env.ts";

let override: string;
const envBefore = snapshotSandboxEnv();

beforeAll(() => {
  override = mkdtempSync(join(tmpdir(), "ai-eng-iso-"));
  // Mimic what init does: a canon dir with one skill so materialize can run.
  mkdirSync(join(override, "skills", "ai-demo"), { recursive: true });
});

test("mirrorTargets derives from home(), not the physical home", () => {
  process.env.AI_ENG_HOME = override;
  const targets = mirrorTargets();
  for (const t of targets) {
    // Every target must live under the override — never under the real ~.
    expect(t.dir.startsWith(override)).toBe(true);
    expect(t.dir.startsWith(homedir())).toBe(false);
  }
});

afterAll(() => {
  restoreSandboxEnv(envBefore);
  rmSync(override, { recursive: true, force: true });
});
