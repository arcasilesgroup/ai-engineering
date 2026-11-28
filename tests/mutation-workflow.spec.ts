// mutation.yml is the mutation tier's whole contract: what it mutates on a pull
// request, what it mutates nightly, and the ceiling each campaign runs under. The
// failure this file exists to prevent is quiet: a ceiling below the work cancels the
// job, and a cancelled check reads like coverage.
import { afterEach, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

type Step = { name?: string; id?: string; uses?: string; run?: string; if?: string; env?: Record<string, unknown> };
type Job = { if?: string; "timeout-minutes"?: number; steps?: Step[] };
type Workflow = { jobs?: Record<string, Job> };

const REPO = join(import.meta.dir, "..");
const WORKFLOW_PATH = join(REPO, ".github", "workflows", "mutation.yml");
const WORKFLOW = readFileSync(WORKFLOW_PATH, "utf8");
const workflow = Bun.YAML.parse(WORKFLOW) as Workflow;
const jobs: Record<string, Job> = workflow.jobs ?? {};

const PR_JOB = "changed-files";
const FULL_JOB = "full";

function stepsOf(jobName: string): Step[] {
  const job = jobs[jobName];
  if (!job) throw new Error(`mutation.yml has no \`${jobName}\` job`);
  return job.steps ?? [];
}

function findStep(jobName: string, matches: (step: Step) => boolean, label: string): Step {
  const step = stepsOf(jobName).find(matches);
  if (!step) throw new Error(`the \`${jobName}\` job has no step that ${label}`);
  return step;
}

function preflightStep(jobName: string): Step {
  return findStep(jobName, (step) => (step.run ?? "").includes("scripts/mutation-plan.ts"), "runs the mutation plan");
}

function campaignStep(jobName: string): Step {
  return findStep(jobName, (step) => /\bbunx stryker run\b/.test(step.run ?? ""), "runs the campaign");
}

function indexOfStep(jobName: string, step: Step): number {
  return stepsOf(jobName).indexOf(step);
}

const scratchRoots: string[] = [];

afterEach(() => {
  for (const root of scratchRoots.splice(0)) rmSync(root, { recursive: true, force: true });
});

function scratch(): string {
  const root = mkdtempSync(join(tmpdir(), "mutation-workflow-"));
  scratchRoots.push(root);
  return root;
}

function isolatedGitEnv(root: string): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = { ...process.env };
  for (const name of ["GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"]) delete env[name];
  const globalConfig = join(root, "gitconfig");
  writeFileSync(globalConfig, "");
  return {
    ...env,
    GIT_CONFIG_GLOBAL: globalConfig,
    GIT_CONFIG_NOSYSTEM: "1",
    GIT_AUTHOR_NAME: "mutation-test",
    GIT_AUTHOR_EMAIL: "mutation-test@example.invalid",
    GIT_COMMITTER_NAME: "mutation-test",
    GIT_COMMITTER_EMAIL: "mutation-test@example.invalid",
  };
}

function git(cwd: string, env: NodeJS.ProcessEnv, args: string[]): string {
  const result = spawnSync("git", ["-c", "commit.gpgsign=false", ...args], { cwd, env, encoding: "utf8" });
  if (result.status !== 0) throw new Error(`git ${args.join(" ")} failed: ${result.stderr}`);
  return result.stdout.trim();
}

/** A repository whose `origin/main` is the base commit and whose branch is the pull request. */
function pullRequestRepo(root: string, env: NodeJS.ProcessEnv): string {
  const repo = join(root, "repo");
  mkdirSync(join(repo, "src", "guards"), { recursive: true });
  mkdirSync(join(repo, "src", "chain"), { recursive: true });
  git(repo, env, ["init", "-q", "-b", "main"]);
  writeFileSync(join(repo, "src/guards/kept.ts"), "export const kept = 1;\n");
  writeFileSync(join(repo, "src/guards/gone.ts"), "export const gone = 1;\n");
  writeFileSync(join(repo, "README.md"), "base\n");
  git(repo, env, ["add", "-A"]);
  git(repo, env, ["commit", "-q", "-m", "base"]);
  git(repo, env, ["update-ref", "refs/remotes/origin/main", "HEAD"]);
  git(repo, env, ["checkout", "-q", "-b", "feature"]);
  writeFileSync(join(repo, "src/guards/kept.ts"), "export const kept = 2;\n");
  writeFileSync(join(repo, "src/chain/fresh.ts"), "export const fresh = 1;\n");
  rmSync(join(repo, "src/guards/gone.ts"));
  writeFileSync(join(repo, "README.md"), "changed\n");
  git(repo, env, ["add", "-A"]);
  git(repo, env, ["commit", "-q", "-m", "change"]);
  return repo;
}

function runStepScript(step: Step, cwd: string, env: NodeJS.ProcessEnv, scratchRoot: string) {
  const script = join(scratchRoot, "step.sh");
  writeFileSync(script, step.run ?? "");
  const output = join(scratchRoot, "github-output");
  writeFileSync(output, "");
  const result = spawnSync("bash", ["--noprofile", "--norc", "-eo", "pipefail", script], {
    cwd,
    env: { ...env, GITHUB_OUTPUT: output },
    encoding: "utf8",
  });
  return { status: result.status, stdout: result.stdout, stderr: result.stderr, output: readFileSync(output, "utf8") };
}

function surfaceOf(output: string): string[] {
  const value = output.split("\n").find((line) => line.startsWith("surface="))?.slice("surface=".length) ?? "";
  return value === "" ? [] : value.split(",");
}

describe("mutation.yml — each job runs under the ceiling its preflight was told", () => {
  test("the preflight's ceiling is the job's own timeout, in both jobs", () => {
    for (const jobName of [PR_JOB, FULL_JOB]) {
      const job = jobs[jobName];
      if (!job) throw new Error(`mutation.yml has no \`${jobName}\` job`);
      const timeout = job["timeout-minutes"];
      expect({ jobName, hasTimeout: typeof timeout }).toEqual({ jobName, hasTimeout: "number" });
      expect({ jobName, ceiling: preflightStep(jobName).env?.["MUTATION_CEILING"] }).toEqual({
        jobName,
        ceiling: String(timeout),
      });
    }
  });

  test("the nightly ceiling is the measured one, above what the campaign actually takes", () => {
    // 12,183 mutants at the measured 280 a minute plus the dry run and the checkout.
    expect(jobs[FULL_JOB]?.["timeout-minutes"]).toBe(90);
    expect(jobs[PR_JOB]?.["timeout-minutes"]).toBe(30);
  });

  test("the preflight runs after the results are restored and before the campaign, in both jobs", () => {
    for (const jobName of [PR_JOB, FULL_JOB]) {
      const restore = indexOfStep(jobName, findStep(jobName, (step) => step.uses?.startsWith("actions/cache") ?? false, "restores the cache"));
      const preflight = indexOfStep(jobName, preflightStep(jobName));
      const campaign = indexOfStep(jobName, campaignStep(jobName));
      expect({ jobName, ordered: restore < preflight && preflight < campaign }).toEqual({ jobName, ordered: true });
    }
  });
});

describe("mutation.yml — the pull request mutates its own surface, the nightly mutates the core", () => {
  test("the pull-request job passes the changed files to Stryker and the nightly job passes nothing", () => {
    expect(campaignStep(PR_JOB).run).toContain("--mutate");
    expect(campaignStep(PR_JOB).run).toContain("steps.surface.outputs.surface");
    expect(campaignStep(FULL_JOB).run?.includes("--mutate") ?? false).toBe(false);
  });

  test("both campaigns are skipped when there is no surface to mutate", () => {
    expect(campaignStep(PR_JOB).if).toContain("steps.surface.outputs.surface != ''");
    expect(preflightStep(PR_JOB).if).toContain("steps.surface.outputs.surface != ''");
  });

  test("the pull-request job only restores the baseline, the nightly job owns it", () => {
    const restoring = (jobName: string) =>
      findStep(jobName, (step) => step.uses?.startsWith("actions/cache") ?? false, "restores the cache").uses ?? "";
    expect(restoring(PR_JOB).startsWith("actions/cache/restore@")).toBe(true);
    expect(restoring(FULL_JOB).startsWith("actions/cache@")).toBe(true);
  });

  test("the triggers and the governance path filter are unchanged", () => {
    expect(WORKFLOW).toContain('cron: "17 3 * * *"');
    expect(WORKFLOW).toContain("workflow_dispatch:");
    for (const path of ['"src/guards/**"', '"src/chain/**"', '"src/floor/**"']) expect(WORKFLOW).toContain(path);
  });
});

describe("mutation.yml — the comments carry measurements, not a calibration", () => {
  test("the measured runs are named and the laptop calibration is gone", () => {
    for (const run of ["45018016173", "45999985299", "46138418750"]) expect(WORKFLOW).toContain(run);
    expect(WORKFLOW).not.toContain("laptop");
    expect(WORKFLOW).not.toContain("4m29s");
    expect(WORKFLOW).not.toContain("11m21s");
  });
});

describe("mutation.yml — the surface step lists what the pull request changed", () => {
  test("governance files that still exist are listed, a deletion never is, and other paths never are", () => {
    const root = scratch();
    const env = isolatedGitEnv(root);
    const repo = pullRequestRepo(root, env);

    const result = runStepScript(findStep(PR_JOB, (step) => step.id === "surface", "computes the surface"), repo, { ...env, BASE_REF: "main" }, root);

    expect(result.status).toBe(0);
    expect(surfaceOf(result.output).sort()).toEqual(["src/chain/fresh.ts", "src/guards/kept.ts"].sort());
  });

  test("a pull request that only deletes governance files has no surface, and that is not an error", () => {
    const root = scratch();
    const env = isolatedGitEnv(root);
    const repo = pullRequestRepo(root, env);
    git(repo, env, ["checkout", "-q", "main"]);
    git(repo, env, ["checkout", "-q", "-b", "deletions-only"]);
    rmSync(join(repo, "src/guards/gone.ts"));
    git(repo, env, ["add", "-A"]);
    git(repo, env, ["commit", "-q", "-m", "delete"]);

    const result = runStepScript(findStep(PR_JOB, (step) => step.id === "surface", "computes the surface"), repo, { ...env, BASE_REF: "main" }, root);

    expect({ status: result.status, surface: surfaceOf(result.output) }).toEqual({ status: 0, surface: [] });
  });

  test("a diff that cannot be computed fails the step instead of reporting an empty surface", () => {
    const root = scratch();
    const env = isolatedGitEnv(root);
    const repo = pullRequestRepo(root, env);

    const result = runStepScript(
      findStep(PR_JOB, (step) => step.id === "surface", "computes the surface"),
      repo,
      { ...env, BASE_REF: "no-such-base" },
      root,
    );

    expect(result.status).not.toBe(0);
    expect(result.stdout).toContain("::error::");
  });
});
