// The merge gate belongs to the project, not to the editor that happens to be
// attached. The workflow hung off the claude-code case, so choosing OpenCode, OMP,
// Codex, Cursor, Copilot or Pi planted guards and adapters and no CI at all — and
// the init summary never said so (measured 2026-09-10, fixed here).
import { test, expect, beforeAll, afterAll } from "bun:test";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { hasAdapter, planEntries } from "../src/commands/init-shared.ts";
import { SURFACES } from "../src/surfaces/adapters.ts";

const WORKFLOW = ".github/workflows/ai-eng-check.yml";
const cli = join(import.meta.dir, "..", "src", "cli.ts");

let sandbox: string;
let home: string;

beforeAll(() => {
  sandbox = mkdtempSync(join(tmpdir(), "ai-eng-planted-ci-"));
  home = join(sandbox, "home");
  mkdirSync(home, { recursive: true });
});

afterAll(() => {
  rmSync(sandbox, { recursive: true, force: true });
});

test("every surface with an adapter receives the planted workflow", () => {
  const governing = SURFACES.filter((surface) => hasAdapter(surface.id));
  expect(governing.length).toBeGreaterThan(0);
  for (const surface of governing) {
    const paths = planEntries([surface.id]).map((entry) => entry.path);
    expect(paths, `${surface.id} plans no CI workflow`).toContain(WORKFLOW);
  }
});

test("a repo governed by a non-claude surface gets the workflow on disk", () => {
  const repo = join(sandbox, "opencode-repo");
  mkdirSync(repo, { recursive: true });
  const run = spawnSync(process.execPath, [cli, "init", "--yes", "--surface", "opencode"], {
    cwd: repo,
    encoding: "utf8",
    env: { ...process.env, AI_ENG_HOME: home, NO_COLOR: "1", CI: "1", AI_ENG_NO_UPDATE_NOTICES: "1" },
  });
  expect(run.status, run.stderr).toBe(0);
  expect(existsSync(join(repo, WORKFLOW))).toBe(true);
  expect(existsSync(join(repo, ".opencode/plugins/ai-eng.ts"))).toBe(true);
});
