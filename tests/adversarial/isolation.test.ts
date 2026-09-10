// Adversarial: AI_ENG_HOME must isolate EVERYTHING a test install touches. The
// canon already honors the override (env.home()); the mirrors did not — a test
// run rewired the REAL ~/.claude/skills to a /tmp canon (measured 2026-09-01,
// /tmp/aibrain-demo). Regression: with AI_ENG_HOME set, no symlink outside the
// override may appear or be rewritten.
import { test, expect, beforeAll, afterAll } from "bun:test";
import { mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import { join } from "node:path";
import { mirrorTargets } from "../../src/surfaces/adapters.ts";

let override: string;

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
  rmSync(override, { recursive: true, force: true });
});
