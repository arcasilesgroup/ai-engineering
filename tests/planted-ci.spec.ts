// The merge gate belongs to the project, not to the editor that happens to be
// attached. The workflow hung off the claude-code case, so six of the seven
// adapter-bearing surfaces planted guards and no CI at all (measured 2026-09-10).
//
// The rules the template must satisfy live here rather than in a proof script: this
// file runs on every push through `bun test`, and scripts/proof-planted-ci.sh proves
// (P2) that what `init` plants is byte-identical to templates/ci.yml.tpl.
import { test, expect, beforeAll, afterAll } from "bun:test";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { hasAdapter } from "../src/commands/init-shared.ts";
import { SURFACES } from "../src/surfaces/adapters.ts";

const WORKFLOW = ".github/workflows/ai-eng-check.yml";
const TEMPLATE = join(import.meta.dir, "..", "templates", "ci.yml.tpl");
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

/** A real repo, a real init: the only way to know what a surface actually receives. */
function init(surface: string, dir: string): { status: number | null; stderr: string } {
  mkdirSync(dir, { recursive: true });
  const run = spawnSync(process.execPath, [cli, "init", "--yes", "--surface", surface], {
    cwd: dir,
    encoding: "utf8",
    env: { ...process.env, AI_ENG_HOME: home, NO_COLOR: "1", CI: "1", AI_ENG_NO_UPDATE_NOTICES: "1" },
  });
  return { status: run.status, stderr: run.stderr ?? "" };
}

test("every surface with an adapter receives the workflow", () => {
  const governing = SURFACES.filter((surface) => hasAdapter(surface.id));
  expect(governing.length).toBeGreaterThan(1);
  for (const surface of governing) {
    const dir = join(sandbox, "repos", surface.id);
    const run = init(surface.id, dir);
    expect(run.status, `${surface.id}: ${run.stderr}`).toBe(0);
    expect(existsSync(join(dir, WORKFLOW)), `${surface.id} planted no CI workflow`).toBe(true);
  }
});

test("the planted template cannot be skipped anywhere, and names one version", () => {
  const template = readFileSync(TEMPLATE, "utf8");
  expect(template).not.toContain("|| true");
  expect(template).not.toContain("bun add -g ai-engineering");
  const unpinned = template.split("\n").filter((line) => line.includes("uses: ") && !/@[0-9a-f]{40}/.test(line));
  expect(unpinned, `unpinned actions: ${unpinned.join(" | ")}`).toEqual([]);
  expect(template.match(/AI_ENG_VERSION:/g)?.length, "the governor version is declared exactly once").toBe(1);
  expect(template).toMatch(/AI_ENG_VERSION: v\d+\.\d+\.\d+/);
});
