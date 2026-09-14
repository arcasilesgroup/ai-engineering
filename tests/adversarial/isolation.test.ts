// Adversarial: AI_ENG_HOME must isolate EVERYTHING a test install touches. The
// canon honors the override (env.home()), the mirrors follow it — and so must the one
// machine setting this repo writes OUTSIDE a home: the global `init.templateDir`, which
// git keeps in a config file no sandbox covers. Without the last one, every `bun test`
// pointed the developer's own global git config at a sandbox path that the test's cleanup
// then deleted: a dangling setting, left on the machine of whoever ran the suite.
import { test, expect, beforeAll, afterAll } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import { join } from "node:path";
import { mirrorTargets } from "../../src/surfaces/adapters.ts";
import { currentTemplateDir, installTemplateDir } from "../../src/floor/template.ts";

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

test("the git floor's global setting is isolated too, and restored", () => {
  // The developer's own global git config, read the way git reads it for real.
  const realGlobal = spawnSync("git", ["config", "--global", "--get", "init.templateDir"], { encoding: "utf8" }).stdout.trim();
  // This test is about the DEFAULT path, so it owns both variables it depends on: another
  // file that borrowed GIT_CONFIG_GLOBAL for its own fixture must not decide what this sees.
  const borrowed = process.env["GIT_CONFIG_GLOBAL"];
  delete process.env["GIT_CONFIG_GLOBAL"];
  process.env.AI_ENG_HOME = override;
  const report = installTemplateDir();
  expect(report.status).toBe("created");
  // It landed inside the override…
  expect(currentTemplateDir()).toBe(join(override, "git-template"));
  // …and the developer's config never saw it.
  const after = spawnSync("git", ["config", "--global", "--get", "init.templateDir"], { encoding: "utf8" }).stdout.trim();
  expect(after).toBe(realGlobal);
  if (borrowed === undefined) delete process.env["GIT_CONFIG_GLOBAL"];
  else process.env["GIT_CONFIG_GLOBAL"] = borrowed;
});

afterAll(() => {
  rmSync(override, { recursive: true, force: true });
});
