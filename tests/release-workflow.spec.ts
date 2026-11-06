// The release workflow proves what it ships: every job checks out the dispatched SHA, a
// verify job runs the full gate on it first, one job packs one tarball and records its
// digest, smoke-tests it and describes it with a runtime SBOM, and publish ships that
// same file — checked against its digest — without packing anything again.
import { afterEach, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, delimiter, dirname, join } from "node:path";
import { releaseFlags } from "../scripts/release-flags.ts";

type Step = {
  name?: string;
  uses?: string;
  run?: string;
  with?: Record<string, unknown>;
  env?: Record<string, unknown>;
};
type Job = { needs?: string | string[]; steps?: Step[] };
type Workflow = { jobs?: Record<string, Job> };

const REPO = join(import.meta.dir, "..");
const WORKFLOW = readFileSync(join(REPO, ".github/workflows/release.yml"), "utf8");
const DISPATCHED_SHA = "${{ github.sha }}";
const CHECKOUT = "actions/checkout@";
const UPLOAD_ARTIFACT = "actions/upload-artifact@";
const DOWNLOAD_ARTIFACT = "actions/download-artifact@";

const workflow = Bun.YAML.parse(WORKFLOW) as Workflow;
const jobs: Record<string, Job> = workflow.jobs ?? {};

function requireJob(name: string): Job {
  const job = jobs[name];
  if (!job) throw new Error(`release.yml has no \`${name}\` job`);
  return job;
}

function stepsOf(jobName: string): Step[] {
  return requireJob(jobName).steps ?? [];
}

function needsOf(jobName: string): string[] {
  const needs = requireJob(jobName).needs;
  if (needs === undefined) return [];
  return Array.isArray(needs) ? needs : [needs];
}

function transitiveNeeds(jobName: string): string[] {
  const seen = new Set<string>();
  const pending = [...needsOf(jobName)];
  for (let next = pending.pop(); next !== undefined; next = pending.pop()) {
    if (seen.has(next)) continue;
    seen.add(next);
    pending.push(...needsOf(next));
  }
  return [...seen].sort();
}

/** The shell commands a step runs: comments and blank lines are not commands. */
function commandLines(step: Step): string[] {
  return (step.run ?? "")
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line !== "" && !line.startsWith("#"));
}

function runsCommand(step: Step, command: RegExp): boolean {
  return commandLines(step).some((line) => command.test(line));
}

function stepIndex(jobName: string, matches: (step: Step) => boolean): number {
  return stepsOf(jobName).findIndex(matches);
}

function commandStepIndex(jobName: string, command: RegExp): number {
  return stepIndex(jobName, (step) => runsCommand(step, command));
}

const LINES_PER_STEP = 10_000;

/** Where a step or command sits in a job, so two commands sharing one step still order. */
function stepPosition(jobName: string, matches: (step: Step) => boolean): number {
  const index = stepIndex(jobName, matches);
  return index < 0 ? -1 : index * LINES_PER_STEP;
}

function commandPosition(jobName: string, command: RegExp): number {
  const steps = stepsOf(jobName);
  for (const [index, step] of steps.entries()) {
    const line = commandLines(step).findIndex((candidate) => command.test(candidate));
    if (line >= 0) return index * LINES_PER_STEP + line + 1;
  }
  return -1;
}

function expectStrictOrder(positions: number[]): void {
  expect(positions.every((position) => position >= 0)).toBe(true);
  expect(positions).toEqual([...positions].sort((left, right) => left - right));
  expect(new Set(positions).size).toBe(positions.length);
}

function requireStep(jobName: string, matches: (step: Step) => boolean, label: string): Step {
  const step = stepsOf(jobName).find(matches);
  if (!step) throw new Error(`the \`${jobName}\` job has no step that ${label}`);
  return step;
}

function allSteps(): Array<{ jobName: string; step: Step }> {
  return Object.entries(jobs).flatMap(([jobName, job]) => (job.steps ?? []).map((step) => ({ jobName, step })));
}

function isCheckout(step: Step): boolean {
  return step.uses?.startsWith(CHECKOUT) ?? false;
}

function pathEntries(step: Step): string[] {
  const path = step.with?.["path"];
  if (typeof path !== "string") return [];
  return path.split("\n").map((entry) => entry.trim()).filter((entry) => entry !== "");
}

function packageUpload(): Step {
  return requireStep("package", (step) => step.uses?.startsWith(UPLOAD_ARTIFACT) ?? false, "uploads an artifact");
}

/** `sha256sum <tarball> > <digest file>`: the digest file the package job records. */
function digestFile(): string {
  const line = stepsOf("package")
    .flatMap(commandLines)
    .find((command) => /\bsha256sum\b[^>]*>\s*\S/.test(command));
  const target = line?.match(/>\s*"?([^"\s);&|]+)/)?.[1];
  if (!target) throw new Error("the package job records no sha256 digest file (`sha256sum … > <file>`)");
  return target;
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function packageSbomEntry(): string {
  const entry = pathEntries(packageUpload()).find((path) => /sbom|cdx/i.test(basename(path)));
  if (!entry) throw new Error("the package artifact carries no SBOM file");
  return entry;
}

const scratchRoots: string[] = [];

afterEach(() => {
  for (const root of scratchRoots.splice(0)) rmSync(root, { recursive: true, force: true });
});

function newScratchRoot(): string {
  const root = mkdtempSync(join(tmpdir(), "release-workflow-"));
  scratchRoots.push(root);
  return root;
}

/** Git with no user/global/system configuration and no inherited repository location. */
function isolatedGitEnv(root: string): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = { ...process.env };
  for (const name of ["GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_CEILING_DIRECTORIES"]) {
    delete env[name];
  }
  const globalConfig = join(root, "gitconfig");
  writeFileSync(globalConfig, "");
  return {
    ...env,
    GIT_CONFIG_GLOBAL: globalConfig,
    GIT_CONFIG_NOSYSTEM: "1",
    GIT_AUTHOR_NAME: "release-test",
    GIT_AUTHOR_EMAIL: "release-test@example.invalid",
    GIT_COMMITTER_NAME: "release-test",
    GIT_COMMITTER_EMAIL: "release-test@example.invalid",
  };
}

function git(cwd: string, env: NodeJS.ProcessEnv, args: string[]): string {
  const result = spawnSync("git", ["-c", "commit.gpgsign=false", ...args], { cwd, env, encoding: "utf8" });
  if (result.status !== 0) throw new Error(`git ${args.join(" ")} failed: ${result.stderr}`);
  return result.stdout.trim();
}

function commit(cwd: string, env: NodeJS.ProcessEnv, message: string): string {
  git(cwd, env, ["commit", "--allow-empty", "-q", "-m", message]);
  return git(cwd, env, ["rev-parse", "HEAD"]);
}

/** Runs a step's script the way a GitHub-hosted runner's default bash shell does. */
function runStepScript(step: Step, cwd: string, env: NodeJS.ProcessEnv, scratch: string) {
  const script = join(scratch, `step-${scratchRoots.length}-${Math.random().toString(36).slice(2)}.sh`);
  writeFileSync(script, step.run ?? "");
  return spawnSync("bash", ["--noprofile", "--norc", "-eo", "pipefail", script], { cwd, env, encoding: "utf8" });
}

describe("release.yml — every job builds from the dispatched SHA", () => {
  test("verify, package, build and publish each check out exactly the dispatched SHA", () => {
    for (const jobName of ["verify", "package", "build", "publish"]) {
      const checkouts = stepsOf(jobName).filter(isCheckout);
      expect({ jobName, count: checkouts.length }).toEqual({ jobName, count: 1 });
    }
    const refs = allSteps()
      .filter(({ step }) => isCheckout(step))
      .map(({ jobName, step }) => ({ jobName, ref: step.with?.["ref"] }));
    expect(refs.length).toBeGreaterThan(0);
    expect(refs).toEqual(refs.map(({ jobName }) => ({ jobName, ref: DISPATCHED_SHA })));
  });

  test("release builds, packing and publication all wait for verify", () => {
    expect(needsOf("package")).toContain("verify");
    expect(transitiveNeeds("build")).toContain("verify");
    expect(transitiveNeeds("publish")).toEqual(expect.arrayContaining(["build", "package", "verify"]));
    expect(needsOf("publish")).toEqual(expect.arrayContaining(["build", "package"]));
  });
});

describe("release.yml — the verify job gates the exact SHA", () => {
  test("the SHA assertion passes when HEAD is the dispatched SHA and fails when it is not", () => {
    const shaCheck = requireStep("verify", (step) => runsCommand(step, /git rev-parse HEAD/), "runs `git rev-parse HEAD`");
    expect(shaCheck.run).toContain("$GITHUB_SHA");
    const scratch = newScratchRoot();
    const repo = join(scratch, "repo");
    mkdirSync(repo);
    const env = isolatedGitEnv(scratch);
    git(repo, env, ["init", "-q", "-b", "main"]);
    const dispatched = commit(repo, env, "dispatched");
    const later = commit(repo, env, "later");
    expect(git(repo, env, ["rev-parse", "HEAD"])).toBe(later);
    expect(later).not.toBe(dispatched);

    const matching = runStepScript(shaCheck, repo, { ...env, GITHUB_SHA: later }, scratch);
    const mismatching = runStepScript(shaCheck, repo, { ...env, GITHUB_SHA: dispatched }, scratch);

    expect({ status: matching.status, stderr: matching.stderr }).toEqual({ status: 0, stderr: "" });
    expect(mismatching.status).not.toBe(0);
    expect(`${mismatching.stdout}${mismatching.stderr}`).toContain(dispatched);
  });

  test("checkout, SHA check, lint, typecheck, the serial full suite and build run in that order", () => {
    expectStrictOrder([
      stepPosition("verify", isCheckout),
      commandPosition("verify", /git rev-parse HEAD/),
      commandPosition("verify", /^bun run lint(\s|$)/),
      commandPosition("verify", /^bun run typecheck(\s|$)/),
      commandPosition("verify", /^bun test --parallel=1$/),
      commandPosition("verify", /^bun run build(\s|$)/),
    ]);
  });
});

describe("release.yml — one tarball, packed once, proven, then published", () => {
  test("the package job packs, digests, smoke-tests, inventories and uploads, in that order", () => {
    const upload = packageUpload();
    expectStrictOrder([
      stepPosition("package", isCheckout),
      commandPosition("package", /(^|[\s;&|(])npm pack(\s|$)/),
      commandPosition("package", /\bsha256sum\b[^>]*>\s*\S/),
      commandPosition("package", /scripts\/package-consumer-smoke\.ts\s+--tarball[=\s]\S+/),
      commandPosition("package", /scripts\/release-sbom\.ts/),
      stepPosition("package", (step) => step === upload),
    ]);
  });

  test("the package artifact carries the tarball, its digest and the SBOM", () => {
    const entries = pathEntries(packageUpload());
    expect(entries.filter((entry) => entry.endsWith(".tgz")).length).toBe(1);
    const digestName = basename(digestFile());
    expect(entries.filter((entry) => basename(entry) === digestName).length).toBe(1);
    expect(basename(packageSbomEntry())).not.toBe(digestName);
    expect(typeof packageUpload().with?.["name"]).toBe("string");
  });

  test("the workflow packs exactly once — in the package job — and never runs cdxgen", () => {
    const packs = allSteps().flatMap(({ jobName, step }) =>
      commandLines(step)
        .filter((line) => /(^|[\s;&|(])npm pack(\s|$)/.test(line))
        .map(() => jobName),
    );
    expect(packs).toEqual(["package"]);
    const cdxgen = allSteps().filter(({ step }) => /cdxgen/i.test(`${step.uses ?? ""}\n${commandLines(step).join("\n")}`));
    expect(cdxgen.map(({ jobName, step }) => `${jobName}: ${step.name ?? step.uses ?? "run"}`)).toEqual([]);
  });

  test("publish downloads the package artifact and checks its digest before any publication", () => {
    const artifactName = packageUpload().with?.["name"];
    const digestName = escapeRegExp(basename(digestFile()));
    expectStrictOrder([
      stepPosition(
        "publish",
        (step) => (step.uses?.startsWith(DOWNLOAD_ARTIFACT) ?? false) && step.with?.["name"] === artifactName,
      ),
      commandPosition("publish", new RegExp(`\\bsha256sum\\s+(-c|--check)\\b.*${digestName}`)),
      commandPosition("publish", /^npm publish\b/),
      commandPosition("publish", /^gh release create\b/),
    ]);
  });

  test("npm publish ships the downloaded .tgz instead of packing the checkout", () => {
    const publishStep = requireStep("publish", (step) => runsCommand(step, /^npm publish\b/), "runs `npm publish`");
    const lines = commandLines(publishStep);
    const publishLine = lines.find((line) => /^npm publish\b/.test(line)) ?? "";
    const tokens = publishLine.split(/\s+/).slice(2);
    const flagsWithValue = new Set(["--tag", "--access", "--registry", "--otp", "--workspace"]);
    const positional: string[] = [];
    for (let index = 0; index < tokens.length; index += 1) {
      const token = tokens[index] ?? "";
      if (flagsWithValue.has(token)) index += 1;
      else if (!token.startsWith("-")) positional.push(token.replace(/^"|"$/g, ""));
    }
    expect(positional.length).toBe(1);
    const target = positional[0] ?? "";
    const variable = target.match(/^\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?$/)?.[1];
    const resolved = variable
      ? lines.find((line) => line.startsWith(`${variable}=`) || line.startsWith(`export ${variable}=`)) ?? ""
      : target;
    expect(resolved).toMatch(/\.tgz/);
  });

  test("the release checksums cover the tarball and the package SBOM, and the SBOM is a release asset", () => {
    const sbomName = basename(packageSbomEntry());
    const checksums = requireStep(
      "publish",
      (step) => runsCommand(step, /CHECKSUMS-SHA256\.txt/) && runsCommand(step, /\bsha256sum\b/),
      "writes CHECKSUMS-SHA256.txt",
    );
    const checksumLines = commandLines(checksums).join("\n");
    expect(checksumLines).toMatch(new RegExp(`\\.tgz|${escapeRegExp(basename(digestFile()))}`));
    expect(checksumLines).toContain(sbomName);
    const releaseUpload = stepsOf("publish")
      .flatMap(commandLines)
      .find((line) => /^gh release upload\b/.test(line)) ?? "";
    expect(releaseUpload).toContain(sbomName);
    expect(releaseUpload).toContain("CHECKSUMS-SHA256.txt");
  });
});

describe("release.yml — the existing release guards are preserved", () => {
  function guardRunsBeforePublication(step: Step): boolean {
    const owner = allSteps().find((candidate) => candidate.step === step)?.jobName ?? "";
    if (owner === "publish") return stepsOf("publish").indexOf(step) < commandStepIndex("publish", /^npm publish\b/);
    return transitiveNeeds("publish").includes(owner);
  }

  test("the version decides the flags and the channel must agree with it, before publication", () => {
    const flagsStep = allSteps().find(({ step }) => runsCommand(step, /scripts\/release-flags\.ts/))?.step;
    if (!flagsStep) throw new Error("no step runs scripts/release-flags.ts");
    expect(flagsStep.env?.["CHANNEL"]).toBe("${{ inputs.channel }}");
    expect(guardRunsBeforePublication(flagsStep)).toBe(true);

    const version = (JSON.parse(readFileSync(join(REPO, "package.json"), "utf8")) as { version: string }).version;
    const flags = releaseFlags(version);
    const agreeing = flags.prerelease ? "integration" : "production";
    const disagreeing = flags.prerelease ? "production" : "integration";
    const scratch = newScratchRoot();
    const PATH = [dirname(process.execPath), process.env["PATH"] ?? ""].join(delimiter);
    const outcome = (channel: string) => {
      const output = join(scratch, `github-output-${channel}`);
      writeFileSync(output, "");
      const result = runStepScript(flagsStep, REPO, { ...process.env, PATH, CHANNEL: channel, GITHUB_OUTPUT: output }, scratch);
      return { status: result.status, output: readFileSync(output, "utf8") };
    };

    expect(outcome(agreeing)).toEqual({ status: 0, output: `tag=${flags.tag}\nprerelease=${flags.prerelease}\n` });
    expect(outcome(disagreeing)).toEqual({ status: 1, output: "" });
  });

  test("the released revision must be on main, before publication", () => {
    const mainStep = allSteps().find(({ step }) =>
      runsCommand(step, /git merge-base --is-ancestor "\$GITHUB_SHA" FETCH_HEAD/),
    )?.step;
    if (!mainStep) throw new Error("no step proves the released revision is on main");
    expect(commandLines(mainStep)).toContain("git fetch --depth=1 origin main");
    expect(guardRunsBeforePublication(mainStep)).toBe(true);
  });
});
