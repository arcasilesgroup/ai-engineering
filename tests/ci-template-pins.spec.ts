import { afterAll, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { copyFileSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { delimiter, dirname, join, resolve } from "node:path";

const ROOT = resolve(import.meta.dir, "..");
const TEMPLATE = resolve(ROOT, "templates/ci.yml.tpl");
const WORKFLOWS = resolve(ROOT, ".github/workflows");
const TOOLCHAIN = resolve(ROOT, "scripts/toolchain.sh");

const template = readFileSync(TEMPLATE, "utf8");
const azureTemplate = readFileSync(resolve(ROOT, "templates/azure-pipelines.yml.tpl"), "utf8");
const packageVersion = (JSON.parse(readFileSync(resolve(ROOT, "package.json"), "utf8")) as { version: string }).version;
const toolchain = readFileSync(TOOLCHAIN, "utf8");

function pinOf(source: string, name: string): string | undefined {
  return source.match(new RegExp(`${name}@([0-9a-f]{40})(?: # (v[\\d.]+))?`))?.[0];
}

function toolchainValue(key: string): string {
  return toolchain.match(new RegExp(`^${key}=(.+)$`, "m"))?.[1] ?? "";
}

// The template embeds version + sha256 inline ("ver=X" + "echo "<sha>  name.tgz").
function templateToolPin(tool: string, source: string = template): string {
  const ver = source.match(new RegExp(`ver=([\\d.]+)[\\s\\S]{0,120}?${tool}_`))?.[1] ?? "";
  const sha256 = source.match(new RegExp(`"([0-9a-f]{64})\\s+${tool}\\.tgz"`))?.[1] ?? "";
  return `${ver} ${sha256}`;
}

function aiEngVersion(source: string): string {
  return source.match(/^ {2}AI_ENG_VERSION: (v\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)$/m)?.[1] ?? "";
}

function toolchainToolPin(prefix: string): string {
  return `${toolchainValue(`${prefix}_VERSION`)} ${toolchainValue(`${prefix}_SHA256`)}`;
}

// Failures name the file to regenerate, not just the diff.
function expectSamePin(actual: string, expected: string, regenerate: string): void {
  expect(`${regenerate} pins ${actual} — regenerate it to pin ${expected}`).toBe(
    `${regenerate} pins ${expected} — regenerate it to pin ${expected}`,
  );
}

describe("ci template pins track their source of truth", () => {
  test("AI_ENG_VERSION in both templates tracks package.json", () => {
    const expected = `v${packageVersion}`;
    expectSamePin(aiEngVersion(template), expected, "templates/ci.yml.tpl (source of truth: package.json)");
    expectSamePin(aiEngVersion(azureTemplate), expected, "templates/azure-pipelines.yml.tpl (source of truth: package.json)");
  });

  test("actions/checkout is one pin across the template and every workflow", () => {
    const expected = pinOf(template, "actions/checkout") ?? "(none)";
    const offenders = readdirSync(WORKFLOWS)
      .filter((name) => name.endsWith(".yml"))
      .map((name) => ({ name, pin: pinOf(readFileSync(resolve(WORKFLOWS, name), "utf8"), "actions/checkout") }))
      .filter((entry) => entry.pin !== undefined && entry.pin !== expected)
      .map((entry) => `${entry.name} pins ${entry.pin}`);
    expectSamePin(offenders.join(", ") || expected, expected, "templates/ci.yml.tpl (source of truth: every .github/workflows/*.yml)");
  });

  test("gitleaks version + sha256 match scripts/toolchain.sh", () => {
    expectSamePin(
      templateToolPin("gitleaks"),
      toolchainToolPin("GITLEAKS"),
      "templates/ci.yml.tpl (source of truth: scripts/toolchain.sh)",
    );
  });

  test("trivy version + sha256 match scripts/toolchain.sh", () => {
    expectSamePin(
      templateToolPin("trivy"),
      toolchainToolPin("TRIVY"),
      "templates/ci.yml.tpl (source of truth: scripts/toolchain.sh)",
    );
  });

  for (const tool of ["gitleaks", "trivy"]) {
    test(`${tool} version + sha256 in the Azure template match scripts/toolchain.sh`, () => {
      expectSamePin(
        templateToolPin(tool, azureTemplate),
        toolchainToolPin(tool.toUpperCase()),
        "templates/azure-pipelines.yml.tpl (source of truth: scripts/toolchain.sh)",
      );
    });
  }
});

// A pin that tracks package.json is only true until the next bump, so the mechanism that
// maintains it is covered here too: a scratch tree carrying a bumped package.json, never
// the real templates. The sync runs as the version workflow runs it, through the script.
const SYNC = resolve(ROOT, "scripts/sync-ci-template-pins.ts");
const PINNED_TEMPLATES = ["templates/ci.yml.tpl", "templates/azure-pipelines.yml.tpl"];
const scratchRoots: string[] = [];

afterAll(() => {
  for (const root of scratchRoots) rmSync(root, { recursive: true, force: true });
});

function scratchTree(version: string): string {
  const root = mkdtempSync(join(tmpdir(), "ci-template-pins-"));
  scratchRoots.push(root);
  mkdirSync(join(root, "templates"), { recursive: true });
  writeFileSync(join(root, "package.json"), JSON.stringify({ version }));
  for (const file of PINNED_TEMPLATES) copyFileSync(resolve(ROOT, file), join(root, file));
  return root;
}

const runSync = (root: string) => spawnSync(process.execPath, [SYNC, root], { encoding: "utf8" });
const templateIn = (root: string, file: string): string => readFileSync(join(root, file), "utf8");
// Blank the value so two pins compare equal only when every other byte matches too.
const withoutPinValue = (text: string): string => text.replace(/^( *AI_ENG_VERSION: )v\S+$/m, "$1<value>");

describe("the version bump rewrites the template pins", () => {
  for (const version of ["9.9.9", "3.3.0-rc.1"]) {
    test(`both templates follow a bumped package.json (${version}), and nothing else is touched`, () => {
      const root = scratchTree(version);
      const before = PINNED_TEMPLATES.map((file) => templateIn(root, file));
      const run = runSync(root);
      expect(run.stderr).toBe("");
      expect(run.status).toBe(0);
      PINNED_TEMPLATES.forEach((file, index) => {
        const after = templateIn(root, file);
        expect(aiEngVersion(after)).toBe(`v${version}`);
        expect(withoutPinValue(after)).toBe(withoutPinValue(before[index] ?? ""));
      });
    });
  }

  test("a second run writes nothing", () => {
    const root = scratchTree("9.9.9");
    expect(runSync(root).status).toBe(0);
    const settled = PINNED_TEMPLATES.map((file) => templateIn(root, file));
    const rerun = runSync(root);
    expect(rerun.status).toBe(0);
    expect(rerun.stdout).toContain("already pins this version");
    expect(PINNED_TEMPLATES.map((file) => templateIn(root, file))).toEqual(settled);
  });

  test("a template that lost its pin fails loudly, naming the file and the key", () => {
    const root = scratchTree("9.9.9");
    const orphan = PINNED_TEMPLATES[1] ?? "";
    writeFileSync(join(root, orphan), templateIn(root, orphan).replace(/^ *AI_ENG_VERSION: .*$/m, ""));
    const run = runSync(root);
    expect(run.status).toBe(2);
    expect(run.stderr).toContain(orphan);
    expect(run.stderr).toContain("AI_ENG_VERSION");
  });
});

// The fix is only a fix if the release runs it. The command comes from the changesets/action
// step's `version-script` input (the input name is the action's published contract) and runs
// for real in a scratch tree: one pending patch changeset, so semver says the bump lands on
// 9.9.9 (or 9.9.9-rc.0 in `rc` pre mode), and both pins must name it afterwards.
type WorkflowStep = { uses?: string; with?: Record<string, string> };
type Workflow = { jobs: Record<string, { steps?: WorkflowStep[] }> };

function versionCommand(): string {
  const workflow = Bun.YAML.parse(readFileSync(resolve(WORKFLOWS, "version.yml"), "utf8")) as Workflow;
  const steps = Object.values(workflow.jobs).flatMap((job) => job.steps ?? []);
  const changesets = steps.find((step) => step.uses?.startsWith("changesets/action@"));
  return changesets?.with?.["version-script"] ?? "changeset version";
}

function releaseTree(preTag?: string): string {
  const root = mkdtempSync(join(tmpdir(), "ci-template-release-"));
  scratchRoots.push(root);
  const { name, scripts } = JSON.parse(readFileSync(resolve(ROOT, "package.json"), "utf8")) as {
    name: string;
    scripts: Record<string, string>;
  };
  writeFileSync(join(root, "package.json"), JSON.stringify({ name, version: "9.9.8", scripts }, null, 2));
  mkdirSync(join(root, ".changeset"));
  writeFileSync(join(root, ".changeset/config.json"), JSON.stringify({ changelog: false, commit: false, baseBranch: "main" }));
  writeFileSync(join(root, ".changeset/bump.md"), `---\n"${name}": patch\n---\n\nbump\n`);
  if (preTag) {
    writeFileSync(
      join(root, ".changeset/pre.json"),
      JSON.stringify({ mode: "pre", tag: preTag, initialVersions: { [name]: "9.9.8" }, changesets: [] }),
    );
  }
  for (const dir of ["templates", "scripts"]) mkdirSync(join(root, dir));
  for (const file of [...PINNED_TEMPLATES, "scripts/sync-ci-template-pins.ts", "scripts/release-flags.ts"]) {
    copyFileSync(resolve(ROOT, file), join(root, file));
  }
  symlinkSync(resolve(ROOT, "node_modules"), join(root, "node_modules"), "dir");
  return root;
}

describe("the version workflow bumps the version and the pins in one command", () => {
  for (const { preTag, expected } of [
    { preTag: undefined, expected: "9.9.9" },
    { preTag: "rc", expected: "9.9.9-rc.0" },
  ]) {
    test(`a pending patch changeset lands as ${expected} in package.json and both pins`, () => {
      const root = releaseTree(preTag);
      const run = spawnSync("sh", ["-c", versionCommand()], {
        cwd: root,
        encoding: "utf8",
        env: { ...process.env, PATH: `${dirname(process.execPath)}${delimiter}${process.env.PATH ?? ""}` },
      });
      expect(run.status).toBe(0);
      const { version } = JSON.parse(templateIn(root, "package.json")) as { version: string };
      expect(version).toBe(expected);
      for (const file of PINNED_TEMPLATES) expect(aiEngVersion(templateIn(root, file))).toBe(`v${expected}`);
    });
  }
});
