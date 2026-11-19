// The merge gate belongs to the project, not to the editor that happens to be
// attached: every adapter-bearing surface receives the workflow, not only the
// claude-code case.
//
// The rules the template must satisfy live here rather than in a proof script: this
// file runs on every push through `bun test`, and scripts/proof-installed-ci.sh proves
// (P2) that what `init` installs is byte-identical to templates/ci.yml.tpl.
import { test, expect, beforeAll, afterAll } from "bun:test";
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { hasAdapter } from "../src/commands/init-shared.ts";
import { SURFACES } from "../src/surfaces/adapters.ts";

const WORKFLOW = ".github/workflows/ai-eng-check.yml";
const PIPELINE = ".azure-pipelines/ai-eng-check.yml";
const TEMPLATE = join(import.meta.dir, "..", "templates", "ci.yml.tpl");
const AZURE_TEMPLATE = join(import.meta.dir, "..", "templates", "azure-pipelines.yml.tpl");
const cli = join(import.meta.dir, "..", "src", "cli.ts");

let sandbox: string;
let home: string;

beforeAll(() => {
  sandbox = mkdtempSync(join(tmpdir(), "ai-eng-installed-ci-"));
  home = join(sandbox, "home");
  mkdirSync(home, { recursive: true });
});

afterAll(() => {
  rmSync(sandbox, { recursive: true, force: true });
});

/** A real repo, a real init: the only way to know what a surface actually receives. */
function init(surface: string, dir: string, extra: string[] = []): { status: number | null; stderr: string } {
  mkdirSync(dir, { recursive: true });
  const run = spawnSync(process.execPath, [cli, "init", "--yes", "--surface", surface, ...extra], {
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
    expect(existsSync(join(dir, WORKFLOW)), `${surface.id} installed no CI workflow`).toBe(true);
  }
});

// release.yml is dispatched from the default branch, so every attestation records
// refs/heads/main: a tag source-ref made every client's governor install fail.
test("the provenance check does not demand a tag ref the release never records", () => {
  expect(readFileSync(TEMPLATE, "utf8")).not.toMatch(/--source-ref\s+\S/);
});

test("the installed template cannot be skipped anywhere, and names one version", () => {
  const template = readFileSync(TEMPLATE, "utf8");
  const unpinned = template.split("\n").filter((line) => line.includes("uses: ") && !/@[0-9a-f]{40}/.test(line));
  expect(unpinned, `unpinned actions: ${unpinned.join(" | ")}`).toEqual([]);
});

// The CI host is the repo's choice, not the surface's: one flag, one file, recorded in
// config.toml so update re-installs the same gate.
test("--ci azure-pipelines installs the Azure gate, byte-identical to its template, and no GitHub workflow", () => {
  const dir = join(sandbox, "repos", "ci-azure");
  const run = init("claude-code", dir, ["--ci", "azure-pipelines"]);
  expect(run.status, run.stderr).toBe(0);
  expect(readFileSync(join(dir, PIPELINE), "utf8")).toBe(readFileSync(AZURE_TEMPLATE, "utf8"));
  expect(existsSync(join(dir, WORKFLOW))).toBe(false);
  expect(readFileSync(join(dir, ".ai-engineering", "config.toml"), "utf8")).toContain('provider = "azure-pipelines"');
});

test("--ci=none installs no CI file at all", () => {
  const dir = join(sandbox, "repos", "ci-none");
  const run = init("claude-code", dir, ["--ci=none"]);
  expect(run.status, run.stderr).toBe(0);
  expect(existsSync(join(dir, WORKFLOW))).toBe(false);
  expect(existsSync(join(dir, PIPELINE))).toBe(false);
});

test("an unknown --ci value is refused before anything is written", () => {
  const dir = join(sandbox, "repos", "ci-unknown");
  const run = init("claude-code", dir, ["--ci", "jenkins"]);
  expect(run.status).toBe(2);
  expect(existsSync(join(dir, ".ai-engineering", "config.toml"))).toBe(false);
});

test("an Azure DevOps origin is the suggestion when --ci is not given", () => {
  const dir = join(sandbox, "repos", "ci-detected");
  mkdirSync(dir, { recursive: true });
  spawnSync("git", ["init", "-q"], { cwd: dir });
  spawnSync("git", ["remote", "add", "origin", "https://dev.azure.com/org/project/_git/repo"], { cwd: dir });
  const run = init("claude-code", dir);
  expect(run.status, run.stderr).toBe(0);
  expect(existsSync(join(dir, PIPELINE))).toBe(true);
  expect(existsSync(join(dir, WORKFLOW))).toBe(false);
});

// Azure YAML has no actionlint: what can be checked here is checked here.
test("the Azure template parses, runs on push, and pins what the GitHub one pins", () => {
  const azure = readFileSync(AZURE_TEMPLATE, "utf8");
  const github = readFileSync(TEMPLATE, "utf8");
  const parsed = Bun.YAML.parse(azure) as { trigger?: unknown; jobs?: Array<{ job: string }> };
  expect(parsed.trigger).toBeDefined();
  expect((parsed.jobs ?? []).map((job) => job.job)).toEqual(["check", "security"]);
  // No marketplace task: a task version floats, and an organization may not allow it.
  expect(azure).not.toMatch(/^\s*-?\s*task:/m);
  expect(azure).not.toMatch(/--source-ref\s+\S/);
  const versionOf = (text: string): string | undefined => /AI_ENG_VERSION: (v[\d.]+)/.exec(text)?.[1];
  const bunOf = (text: string): string | undefined => /bun@([\d.]+)/.exec(text)?.[1];
  expect(versionOf(azure)).toBe(versionOf(github));
  expect(bunOf(azure)).toBe(bunOf(github));
});
