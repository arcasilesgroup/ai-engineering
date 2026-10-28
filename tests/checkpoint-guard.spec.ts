import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import { randomUUID } from "node:crypto";
import { spawnSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  readFileSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { join } from "node:path";
import { normalise, type Payload } from "../src/payload.ts";
import { runCheckpointGuard } from "../src/guards/checkpoint.ts";

type GateState = { status: string; attempts: number; findings: string[] };
type CheckpointState = {
  id: number;
  title: string;
  goal: string;
  tasks: string[];
  files: string[];
  acceptance: string[];
  verify: string[];
  ui: null | { route: string; prototype: string; scope: string; states: string[] };
  status: string;
  changed_files: string[];
  gates: { behavior: GateState; ui: GateState; review: GateState };
};
type LifecycleState = {
  phase: string;
  plan_approval: "pending" | "approved";
  app_review: "not-started" | "pending" | "approved";
  base_ref: string | null;
  reviewed_base: string | null;
  reviewed_feature: string | null;
};
type CheckpointPlan = {
  slug: string;
  feature: string;
  summary: string;
  lifecycle: LifecycleState;
  halted: null | { reason: string; checkpoint: number };
  assumptions: string[];
  notes: string[];
  checkpoints: CheckpointState[];
  [key: string]: unknown;
};
type Fixture = {
  root: string;
  slug: string;
  baseBranch: string;
  featureBranch: string;
  baseSha: string;
  featureSha: string;
  planPath: string;
  brainstormPath: string;
  transcriptPath: string;
};
type GuardResult = ReturnType<typeof runCheckpointGuard>;

let fixtureRoot = "";
let emptyGitConfig = "";
let fixtureIndex = 0;

function runGit(args: string[], cwd: string) {
  const env: NodeJS.ProcessEnv = {
    ...process.env,
    GIT_CONFIG_GLOBAL: emptyGitConfig,
    GIT_CONFIG_SYSTEM: emptyGitConfig,
    GIT_CONFIG_NOSYSTEM: "1",
    GIT_TERMINAL_PROMPT: "0",
  };
  delete env.GIT_DIR;
  delete env.GIT_WORK_TREE;
  delete env.GIT_COMMON_DIR;
  delete env.GIT_INDEX_FILE;
  const result = spawnSync("git", args, { cwd, env, encoding: "utf8" });
  return { status: result.status ?? 1, stdout: result.stdout ?? "", stderr: result.stderr ?? "" };
}

function git(args: string[], cwd: string): string {
  const result = runGit(args, cwd);
  if (result.status !== 0) throw new Error(`git ${args.join(" ")} failed: ${result.stderr}`);
  return result.stdout.trim();
}

function createFixture(options: { slug?: string; baseBranch?: string; featureBranch?: string } = {}): Fixture {
  const slug = options.slug ?? "demo";
  const baseBranch = options.baseBranch ?? "main";
  const featureBranch = options.featureBranch ?? `feat/${slug}`;
  const root = join(fixtureRoot, `repo-${fixtureIndex++}`);
  mkdirSync(root);
  git(["init", "-q", "-b", baseBranch], root);
  git(["config", "user.name", "Checkpoint Test"], root);
  git(["config", "user.email", "checkpoint@example.invalid"], root);
  git(["config", "commit.gpgsign", "false"], root);
  mkdirSync(join(root, ".ai-engineering"), { recursive: true });
  writeFileSync(
    join(root, ".ai-engineering", "config.toml"),
    `[surfaces]\nenabled = ["claude-code"]\n\n[git]\nbase = "${baseBranch}"\nworktrees_dir = "selected-worktrees"\n`,
  );
  writeFileSync(join(root, "base.txt"), "base\n");
  git(["add", ".ai-engineering/config.toml", "base.txt"], root);
  git(["commit", "-q", "-m", "base"], root);
  const baseSha = git(["rev-parse", `refs/heads/${baseBranch}`], root);
  git(["switch", "-q", "-c", featureBranch], root);
  writeFileSync(join(root, "feature.txt"), "feature\n");
  git(["add", "feature.txt"], root);
  git(["commit", "-q", "-m", "feature"], root);
  const featureSha = git(["rev-parse", `refs/heads/${featureBranch}`], root);

  const planDirectory = join(root, ".ai-engineering", "workflow", "checkpoints");
  mkdirSync(planDirectory, { recursive: true });
  const fixture = {
    root,
    slug,
    baseBranch,
    featureBranch,
    baseSha,
    featureSha,
    planPath: join(planDirectory, `${slug}.json`),
    brainstormPath: join(root, ".ai-engineering", "brainstorm.html"),
    transcriptPath: join(root, "orchestrator.jsonl"),
  };
  expect(git(["symbolic-ref", "--short", "HEAD"], root)).toBe(featureBranch);
  expect(git(["rev-parse", `refs/heads/${baseBranch}`], root)).toBe(baseSha);
  expect(runGit(["merge-base", "--is-ancestor", baseSha, featureSha], root).status).toBe(0);
  return fixture;
}

function withFixture<T>(
  action: (fixture: Fixture) => T,
  options: { slug?: string; baseBranch?: string; featureBranch?: string } = {},
): T {
  const fixture = createFixture(options);
  try {
    return action(fixture);
  } finally {
    rmSync(fixture.root, { recursive: true, force: true });
  }
}

function gate(status: string): GateState {
  return { status, attempts: 0, findings: [] };
}

function checkpoint(
  id: number,
  options: {
    status?: string;
    behavior?: string;
    ui?: string;
    review?: string;
  } = {},
): CheckpointState {
  return {
    id,
    title: `Checkpoint ${id}`,
    goal: `Test checkpoint ${id}`,
    tasks: [],
    files: [],
    acceptance: [],
    verify: [],
    ui: null,
    status: options.status ?? "pending",
    changed_files: [],
    gates: {
      behavior: gate(options.behavior ?? "pending"),
      ui: gate(options.ui ?? "n/a"),
      review: gate(options.review ?? "pending"),
    },
  };
}

function lifecycle(
  phase = "implementation",
  options: Partial<LifecycleState> = {},
): LifecycleState {
  const defaults: LifecycleState = {
    phase,
    plan_approval: phase === "awaiting-plan-approval" ? "pending" : "approved",
    app_review: phase === "awaiting-app-review" ? "pending" : phase === "ready-to-merge" ? "approved" : "not-started",
    base_ref: null,
    reviewed_base: null,
    reviewed_feature: null,
  };
  return { ...defaults, ...options };
}

function plan(
  slug = "demo",
  checkpoints: CheckpointState[] = [
    checkpoint(1, { status: "passed", behavior: "passed", ui: "n/a", review: "passed" }),
    checkpoint(2),
    checkpoint(3),
  ],
  state = lifecycle(),
): CheckpointPlan {
  return {
    slug,
    feature: `Feature ${slug}`,
    summary: "Guard fixture",
    lifecycle: state,
    halted: null,
    assumptions: [],
    notes: [],
    checkpoints,
  };
}

function copyPlan(value: CheckpointPlan): CheckpointPlan {
  return JSON.parse(JSON.stringify(value)) as CheckpointPlan;
}

function withGate(
  value: CheckpointPlan,
  id: number,
  name: keyof CheckpointState["gates"],
  status: string,
): CheckpointPlan {
  const next = copyPlan(value);
  const item = next.checkpoints.find((candidate) => candidate.id === id);
  if (!item) throw new Error(`missing checkpoint ${id}`);
  item.gates[name].status = status;
  return next;
}

function withCheckpointStatus(value: CheckpointPlan, id: number, status: string): CheckpointPlan {
  const next = copyPlan(value);
  const item = next.checkpoints.find((candidate) => candidate.id === id);
  if (!item) throw new Error(`missing checkpoint ${id}`);
  item.status = status;
  return next;
}

function withLifecycle(value: CheckpointPlan, state: LifecycleState): CheckpointPlan {
  return { ...copyPlan(value), lifecycle: state };
}

function allGatesPassed(value: CheckpointPlan): CheckpointPlan {
  const next = copyPlan(value);
  for (const item of next.checkpoints) {
    item.status = "passed";
    item.gates.behavior.status = "passed";
    item.gates.ui.status = "n/a";
    item.gates.review.status = "passed";
  }
  return next;
}

function writePlan(fixture: Fixture, value: CheckpointPlan | string, path = fixture.planPath): void {
  writeFileSync(path, typeof value === "string" ? value : JSON.stringify(value, null, 2));
}

function tool(tool_name: string, tool_input: Record<string, unknown>): Payload {
  return { tool_name, tool_input };
}

function writePayload(fixture: Fixture, value: CheckpointPlan | string, path = fixture.planPath): Payload {
  return tool("Write", {
    file_path: path,
    content: typeof value === "string" ? value : JSON.stringify(value, null, 2),
  });
}

function marker(slug: string, id: number, stage: string, toolName = "Agent"): Payload {
  return tool(toolName, { prompt: `[checkpoint ${slug}#${id} ${stage}]\nDo the work.` });
}

function run(fixture: Fixture, payload: Payload): GuardResult {
  return runCheckpointGuard(payload, fixture.root);
}

function expectAllowed(result: GuardResult): void {
  expect(result?.deny ?? false).toBe(false);
}

function expectDenied(result: GuardResult, ...reasonParts: string[]): string {
  if (!result || result.deny !== true) throw new Error(`expected refusal, got ${JSON.stringify(result)}`);
  expect(result.reason.trim().length).toBeGreaterThan(0);
  expect(result.reason).toMatch(/next:/i);
  for (const part of reasonParts) expect(result.reason).toContain(part);
  return result.reason;
}

function dateDaysAgo(days: number): string {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() - days);
  return date.toISOString().slice(0, 10);
}

function brainstorm(slug: string, approvedOn: string, status = `complete · ${approvedOn}`): string {
  return [
    "<!doctype html><html><head>",
    `<meta name="ai-feature" content="${slug}">`,
    `<meta name="ai-approved" content="${approvedOn}">`,
    `</head><body><div class="meta"><b>${status}</b></div></body></html>`,
  ].join("");
}

function serializedPlan(value: CheckpointPlan): string {
  return JSON.stringify(value, null, 2);
}

function orchestratorTranscript(fixture: Fixture): void {
  writeFileSync(
    fixture.transcriptPath,
    `{"name":"Skill","input":{"skill":"ai-orchestrator"}} read .ai-engineering/workflow/checkpoints/${fixture.slug}.json\n`,
  );
}

function stopPayload(
  fixture: Fixture,
  session: string = randomUUID(),
  options: { transcriptPath?: string; reason?: string } = {},
): Payload {
  return {
    tool_name: "",
    tool_input: {},
    hook_event_name: "Stop",
    _event: "Stop",
    session_id: session,
    transcript_path: options.transcriptPath ?? fixture.transcriptPath,
    stop_reason: options.reason ?? "end_turn",
  };
}

function symlinkUnavailable(error: unknown): string | null {
  if (!(error instanceof Error)) return null;
  const details = error as NodeJS.ErrnoException & { winerror?: number };
  if (details.winerror === 1314) return "winerror 1314";
  return ["EACCES", "EPERM", "ENOSYS", "ENOTSUP", "EOPNOTSUPP"].includes(details.code ?? "")
    ? details.code ?? null
    : null;
}

beforeAll(() => {
  fixtureRoot = join(import.meta.dir, `.checkpoint-guard-${process.pid}-${randomUUID()}`);
  mkdirSync(fixtureRoot);
  emptyGitConfig = join(fixtureRoot, "empty-git-config");
  writeFileSync(emptyGitConfig, "");
});

afterAll(() => {
  if (fixtureRoot) rmSync(fixtureRoot, { recursive: true, force: true });
});

describe("checkpoint guard G1 — plan schema, file slug, and malformed input", () => {
  const invalidPlans: Array<[string, (value: CheckpointPlan) => unknown]> = [
    ["missing checkpoints", (value) => ({ ...value, checkpoints: undefined })],
    ["empty checkpoints", (value) => ({ ...value, checkpoints: [] })],
    ["null checkpoint entry", (value) => ({ ...value, checkpoints: [null] })],
    ["checkpoint missing required fields", (value) => ({ ...value, checkpoints: [{ id: 1 }] })],
    ["unknown gate status", (value) => {
      const next = copyPlan(value);
      next.checkpoints[1]!.gates.behavior.status = "unknown";
      return next;
    }],
  ];

  test.each(invalidPlans)("%s is refused", (_name, invalid) => {
    withFixture((fixture) => {
      const current = plan(fixture.slug);
      writePlan(fixture, current);
      expectDenied(run(fixture, writePayload(fixture, JSON.stringify(invalid(current)))));
    });
  });

  test("a plan whose slug differs from its filename is refused", () => {
    withFixture((fixture) => {
      const otherPath = join(fixture.root, ".ai-engineering", "workflow", "checkpoints", "other.json");
      const invalid = plan(fixture.slug);
      writeFileSync(fixture.brainstormPath, brainstorm(fixture.slug, dateDaysAgo(0)));
      expectDenied(run(fixture, writePayload(fixture, invalid, otherPath)));
    });
  });

  test.each(["missing file", "malformed JSON"])("an unreadable plan (%s) denies with its absolute path and a next step", (kind) => {
    withFixture((fixture) => {
      if (kind === "malformed JSON") writePlan(fixture, "{ malformed");
      const reason = expectDenied(run(fixture, marker(fixture.slug, 2, "implement")), fixture.planPath);
      expect(reason).toMatch(/checkpoint|CP/i);
    });
  });

  test.each([
    ["wrong slug", (value: CheckpointPlan) => ({ ...value, slug: "other" })],
    ["null prior checkpoint", (value: CheckpointPlan) => ({ ...value, checkpoints: [null] })],
    ["empty prior checkpoint list", (value: CheckpointPlan) => ({ ...value, checkpoints: [] })],
    ["missing prior checkpoint fields", (value: CheckpointPlan) => ({ ...value, checkpoints: [{ id: 1 }] })],
  ])("%s prior plan cannot authorize a first lifecycle approval", (_name, invalidPrior) => {
    withFixture((fixture) => {
      const initial = plan(fixture.slug);
      const awaitingApproval = withLifecycle(initial, lifecycle("awaiting-plan-approval"));
      const approved = withLifecycle(initial, lifecycle("implementation"));
      writeFileSync(fixture.brainstormPath, brainstorm(fixture.slug, dateDaysAgo(0)));
      writePlan(fixture, JSON.stringify(invalidPrior(initial)));
      expectDenied(run(fixture, writePayload(fixture, awaitingApproval)));
      writePlan(fixture, JSON.stringify(invalidPrior(initial)));
      expectDenied(run(fixture, writePayload(fixture, approved)));
    });
  });
});

describe("checkpoint guard G2 — first plan approval", () => {
  const today = dateDaysAgo(0);
  const firstWriteCases: Array<[string, string | null, boolean]> = [
    ["no brainstorm", null, false],
    ["fresh brainstorm", brainstorm("demo", today), true],
    ["15-day-old brainstorm", brainstorm("demo", dateDaysAgo(15)), false],
    ["another slug's brainstorm", brainstorm("other", today), false],
    ["draft brainstorm", brainstorm("demo", today, `draft · ${today}`), false],
  ];

  test.each(firstWriteCases)("%s", (_name, artifact, shouldAllow) => {
    withFixture((fixture) => {
      if (artifact !== null) writeFileSync(fixture.brainstormPath, artifact);
      const proposal = plan(fixture.slug);
      const result = run(fixture, writePayload(fixture, proposal));
      if (shouldAllow) expectAllowed(result);
      else expectDenied(result);
    });
  });

  test("a rejected pending first write cannot self-authorize a later approval", () => {
    withFixture((fixture) => {
      const pending = withLifecycle(plan(fixture.slug), lifecycle("awaiting-plan-approval"));
      const approved = withLifecycle(plan(fixture.slug), lifecycle("implementation"));
      expectDenied(run(fixture, writePayload(fixture, pending)));
      expect(existsSync(fixture.planPath)).toBe(false);
      expectDenied(run(fixture, writePayload(fixture, approved)));
      expect(existsSync(fixture.planPath)).toBe(false);
    });
  });

  test("a pending plan approval blocks implementation markers", () => {
    withFixture((fixture) => {
      writePlan(fixture, withLifecycle(plan(fixture.slug), lifecycle("awaiting-plan-approval")));
      expectDenied(run(fixture, marker(fixture.slug, 2, "implement")));
    });
  });

  test.each([
    ["omitted lifecycle", (value: CheckpointPlan) => {
      const withoutLifecycle = copyPlan(value);
      Reflect.deleteProperty(withoutLifecycle, "lifecycle");
      return withoutLifecycle;
    }],
    ["pending app review", (value: CheckpointPlan) => withLifecycle(value, lifecycle("implementation", { app_review: "pending" }))],
    ["approved app review", (value: CheckpointPlan) => withLifecycle(value, lifecycle("implementation", {
      app_review: "approved",
      base_ref: "refs/heads/main",
      reviewed_base: "a".repeat(40),
      reviewed_feature: "b".repeat(40),
    }))],
    ["reviewed base before review", (value: CheckpointPlan) => withLifecycle(value, lifecycle("implementation", {
      base_ref: "refs/heads/main",
      reviewed_base: "a".repeat(40),
    }))],
    ["reviewed feature before review", (value: CheckpointPlan) => withLifecycle(value, lifecycle("implementation", {
      base_ref: "refs/heads/main",
      reviewed_feature: "b".repeat(40),
    }))],
  ])("a first write with %s lifecycle is refused", (_name, invalid) => {
    withFixture((fixture) => {
      writeFileSync(fixture.brainstormPath, brainstorm(fixture.slug, today));
      expectDenied(run(fixture, writePayload(fixture, invalid(plan(fixture.slug)))));
    });
  });

  test("S3: an approved plan is accepted in a regular feature checkout", () => {
    withFixture((fixture) => {
      expect(git(["rev-parse", "--git-dir"], fixture.root)).toBe(git(["rev-parse", "--git-common-dir"], fixture.root));
      expect(git(["symbolic-ref", "--short", "HEAD"], fixture.root)).toBe("feature/pagos");
      writeFileSync(fixture.brainstormPath, brainstorm(fixture.slug, today));
      expectAllowed(run(fixture, writePayload(fixture, plan(fixture.slug))));
    }, { slug: "pagos", featureBranch: "feature/pagos" });
  });
});

describe("checkpoint guard G3 — checkpoint order", () => {
  const markerCases: Array<[string, (fixture: Fixture) => CheckpointPlan, number, string, string, boolean]> = [
    ["next checkpoint after a passed predecessor", (fixture) => plan(fixture.slug), 2, "implement", "Agent", false],
    ["later checkpoint while its predecessor is open", (fixture) => plan(fixture.slug), 3, "implement", "Agent", true],
    ["already-passed checkpoint", (fixture) => plan(fixture.slug), 1, "fix", "Agent", true],
    ["unknown checkpoint id", (fixture) => plan(fixture.slug), 9, "implement", "Agent", true],
    ["marker slug differs from the plan", (fixture) => plan(fixture.slug), 2, "implement", "Task", true],
    ["passed predecessor has an incomplete gate", (fixture) => {
      const value = plan(fixture.slug);
      value.checkpoints[0]!.gates.review.status = "pending";
      return value;
    }, 2, "implement", "Agent", true],
    ["passed predecessor has an incomplete gate without lifecycle", (fixture) => {
      const value = plan(fixture.slug);
      value.checkpoints[0]!.gates.review.status = "pending";
      Reflect.deleteProperty(value, "lifecycle");
      return value;
    }, 2, "implement", "Agent", true],
  ];

  test.each(markerCases)("%s", (_name, makePlan, id, stage, toolName, shouldDeny) => {
    withFixture((fixture) => {
      writePlan(fixture, makePlan(fixture));
      const markerSlug = _name === "marker slug differs from the plan" ? "other" : fixture.slug;
      const result = run(fixture, marker(markerSlug, id, stage, toolName));
      if (shouldDeny) expectDenied(result);
      else expectAllowed(result);
    });
  });

  test("a non-finite predecessor id cannot bypass an open gate", () => {
    withFixture((fixture) => {
      const malformed = serializedPlan(plan(fixture.slug)).replace('"id": 1,', '"id": 1e999,');
      writePlan(fixture, malformed);
      expectDenied(run(fixture, marker(fixture.slug, 2, "implement")));
    });
  });

  test.each(["Write", "Edit", "MultiEdit"])("%s cannot pass checkpoint 3 while checkpoint 2 is open", (toolName) => {
    withFixture((fixture) => {
      const current = plan(fixture.slug);
      const updated = allGatesPassed(current);
      updated.checkpoints[1] = current.checkpoints[1]!;
      writePlan(fixture, current);
      let payload: Payload;
      if (toolName === "Write") {
        payload = writePayload(fixture, updated);
      } else {
        payload = {
          tool_name: toolName,
          tool_input: {
            file_path: fixture.planPath,
            ...(toolName === "Edit"
              ? { old_string: serializedPlan(current), new_string: serializedPlan(updated) }
              : { edits: [{ old_string: serializedPlan(current), new_string: serializedPlan(updated) }] }),
          },
        };
      }
      expectDenied(run(fixture, payload));
    });
  });
});

describe("checkpoint guard G4 — stage and gate order", () => {
  test.each([
    ["unknown stage", (fixture: Fixture) => plan(fixture.slug), 2, "unknown", true],
    ["ui marker before behavior passes", (fixture: Fixture) => plan(fixture.slug), 2, "ui", true],
    ["review marker before behavior passes", (fixture: Fixture) => plan(fixture.slug), 2, "review", true],
    ["review marker while ui is pending", (fixture: Fixture) => {
      const value = plan(fixture.slug);
      value.checkpoints[1]!.gates.behavior.status = "passed";
      value.checkpoints[1]!.gates.ui.status = "pending";
      return value;
    }, 2, "review", true],
    ["review marker after ui is not applicable", (fixture: Fixture) => {
      const value = plan(fixture.slug);
      value.checkpoints[1]!.gates.behavior.status = "passed";
      value.checkpoints[1]!.gates.ui.status = "n/a";
      return value;
    }, 2, "review", false],
  ])("%s", (_name, makePlan, id, stage, shouldDeny) => {
    withFixture((fixture) => {
      writePlan(fixture, makePlan(fixture));
      const result = run(fixture, marker(fixture.slug, id, stage));
      if (shouldDeny) expectDenied(result);
      else expectAllowed(result);
    });
  });

  test.each([
    ["ui passed before behavior", "pending", "passed", true],
    ["ui passed after behavior", "passed", "passed", false],
  ])("a write with %s", (_name, behavior, ui, shouldDeny) => {
    withFixture((fixture) => {
      const current = plan(fixture.slug);
      const updated = withGate(withGate(current, 2, "behavior", behavior), 2, "ui", ui);
      writePlan(fixture, current);
      const result = run(fixture, writePayload(fixture, updated));
      if (shouldDeny) expectDenied(result);
      else expectAllowed(result);
    });
  });

  test("S4: ui marker and ui gate write work in a regular checkout after behavior passes", () => {
    withFixture((fixture) => {
      expect(git(["rev-parse", "--git-dir"], fixture.root)).toBe(git(["rev-parse", "--git-common-dir"], fixture.root));
      const current = plan(fixture.slug);
      const readyForUi = withGate(current, 2, "behavior", "passed");
      writePlan(fixture, readyForUi);
      expectAllowed(run(fixture, marker(fixture.slug, 2, "ui")));
      const uiPassed = withGate(readyForUi, 2, "ui", "passed");
      expectAllowed(run(fixture, writePayload(fixture, uiPassed)));
    });
  });
});

describe("checkpoint guard G5 — passed requires closed gates", () => {
  test.each(["pending", "failed", "blocked"])("status passed with a %s gate is refused", (gateStatus) => {
    withFixture((fixture) => {
      const current = plan(fixture.slug);
      const updated = withCheckpointStatus(
        withGate(allGatesPassed(current), 2, "review", gateStatus),
        2,
        "passed",
      );
      writePlan(fixture, current);
      expectDenied(run(fixture, writePayload(fixture, updated)));
    });
  });

  test("status passed with only passed or n/a gates is allowed", () => {
    withFixture((fixture) => {
      const current = plan(fixture.slug);
      const updated = withCheckpointStatus(allGatesPassed(current), 2, "passed");
      writePlan(fixture, current);
      expectAllowed(run(fixture, writePayload(fixture, updated)));
    });
  });

  test("writing a failed behavior gate is allowed", () => {
    withFixture((fixture) => {
      const current = plan(fixture.slug);
      const updated = withGate(current, 2, "behavior", "failed");
      writePlan(fixture, current);
      expectAllowed(run(fixture, writePayload(fixture, updated)));
    });
  });
});

describe("checkpoint guard G2 path safety — symlinked first plans", () => {
  test.each(["alias plan", "symlinked target file", "symlinked directory component"])(
    "%s cannot initialize lifecycle",
    (caseName) => {
      withFixture((fixture) => {
        const proposed = withLifecycle(plan(fixture.slug), lifecycle("implementation"));
        writeFileSync(fixture.brainstormPath, brainstorm(fixture.slug, dateDaysAgo(0)));
        const checkpoints = join(fixture.root, ".ai-engineering", "workflow", "checkpoints");
        let targetPath = fixture.planPath;
        if (caseName === "alias plan") {
          writePlan(fixture, plan(fixture.slug));
          targetPath = join(checkpoints, "alias.json");
          try {
            symlinkSync(fixture.planPath, targetPath);
          } catch (error) {
            const reason = symlinkUnavailable(error);
            if (reason !== null) {
              console.warn(`SKIP symlink test: this platform cannot create symlinks (${reason})`);
              return;
            }
            throw error;
          }
        } else if (caseName === "symlinked target file") {
          const target = join(checkpoints, "target.json");
          writePlan(fixture, plan(fixture.slug), target);
          try {
            symlinkSync(target, fixture.planPath);
          } catch (error) {
            const reason = symlinkUnavailable(error);
            if (reason !== null) {
              console.warn(`SKIP symlink test: this platform cannot create symlinks (${reason})`);
              return;
            }
            throw error;
          }
        } else {
          const target = `${checkpoints}-target`;
          mkdirSync(target, { recursive: true });
          const planContents = join(target, `${fixture.slug}.json`);
          writePlan(fixture, plan(fixture.slug), planContents);
          rmSync(checkpoints, { recursive: true, force: true });
          try {
            symlinkSync(target, checkpoints, "dir");
          } catch (error) {
            mkdirSync(checkpoints, { recursive: true });
            const reason = symlinkUnavailable(error);
            if (reason !== null) {
              console.warn(`SKIP symlink test: this platform cannot create symlinks (${reason})`);
              return;
            }
            throw error;
          }
        }
        expectDenied(run(fixture, writePayload(fixture, proposed, targetPath)));
      });
    },
  );
});

describe("checkpoint guard G6 — lifecycle and detected base", () => {
  test("I24: valid lifecycle transitions use develop when main does not exist", () => {
    withFixture((fixture) => {
      expect(git(["branch", "--list", "main"], fixture.root)).toBe("");
      const baseRef = `refs/heads/${fixture.baseBranch}`;
      const completed = allGatesPassed(plan(fixture.slug, undefined, lifecycle("implementation", { base_ref: baseRef })));
      const blocked = withLifecycle(completed, lifecycle("blocked", { base_ref: baseRef }));
      writePlan(fixture, completed);
      expectAllowed(run(fixture, writePayload(fixture, blocked)));

      const resumed = withLifecycle(blocked, lifecycle("implementation", { base_ref: baseRef }));
      writePlan(fixture, blocked);
      expectAllowed(run(fixture, writePayload(fixture, resumed)));

      const review = withLifecycle(resumed, lifecycle("awaiting-app-review", {
        base_ref: baseRef,
        reviewed_base: fixture.baseSha,
        reviewed_feature: fixture.featureSha,
      }));
      writePlan(fixture, resumed);
      expectAllowed(run(fixture, writePayload(fixture, review)));

      const ready = withLifecycle(review, lifecycle("ready-to-merge", {
        base_ref: baseRef,
        reviewed_base: fixture.baseSha,
        reviewed_feature: fixture.featureSha,
      }));
      writePlan(fixture, review);
      expectAllowed(run(fixture, writePayload(fixture, ready)));

      const blockedWithApproval = withLifecycle(ready, lifecycle("blocked", {
        base_ref: baseRef,
        app_review: "approved",
        reviewed_base: fixture.baseSha,
        reviewed_feature: fixture.featureSha,
      }));
      writePlan(fixture, ready);
      expectAllowed(run(fixture, writePayload(fixture, blockedWithApproval)));
      writePlan(fixture, blockedWithApproval);
      expectAllowed(run(fixture, writePayload(fixture, ready)));
    }, { baseBranch: "develop" });
  });

  test("legacy reviewed_main plans remain writable against the detected base", () => {
    withFixture((fixture) => {
      const completed = allGatesPassed(plan(fixture.slug));
      const legacyReview = {
        phase: "awaiting-app-review",
        plan_approval: "approved",
        app_review: "pending",
        reviewed_main: fixture.baseSha,
        reviewed_feature: fixture.featureSha,
      };
      const legacyReady = {
        ...legacyReview,
        phase: "ready-to-merge",
        app_review: "approved",
      };
      const awaiting = { ...completed, lifecycle: legacyReview };
      const ready = { ...completed, lifecycle: legacyReady };
      writePlan(fixture, JSON.stringify(awaiting));
      expectAllowed(run(fixture, writePayload(fixture, JSON.stringify(ready))));
    }, { baseBranch: "develop" });
  });

  test.each([
    ["missing phase", (value: CheckpointPlan) => {
      const next = copyPlan(value);
      Reflect.deleteProperty(next.lifecycle, "phase");
      return next;
    }],
    ["unknown phase", (value: CheckpointPlan) => withLifecycle(value, lifecycle("unrecognized"))],
    ["invalid plan approval", (value: CheckpointPlan) => withLifecycle(value, {
      ...lifecycle("awaiting-plan-approval"),
      plan_approval: "yes",
    } as unknown as LifecycleState)],
    ["invalid app review", (value: CheckpointPlan) => withLifecycle(value, {
      ...lifecycle("awaiting-plan-approval"),
      app_review: "approved",
    })],
  ])("invalid lifecycle with %s is refused", (_name, invalid) => {
    withFixture((fixture) => {
      const current = plan(fixture.slug);
      writePlan(fixture, current);
      expectDenied(run(fixture, writePayload(fixture, invalid(current))));
    });
  });

  test.each([
    ["implementation while approval is pending", "awaiting-plan-approval", "implementation", "pending"],
    ["skipping plan approval to app review", "awaiting-plan-approval", "awaiting-app-review", "approved"],
    ["skipping app review to ready-to-merge", "implementation", "ready-to-merge", "approved"],
  ])("%s is refused", (_name, previousPhase, nextPhase, planApproval) => {
    withFixture((fixture) => {
      const previous = allGatesPassed(plan(fixture.slug, undefined, lifecycle(previousPhase)));
      const baseRef = `refs/heads/${fixture.baseBranch}`;
      const next = withLifecycle(previous, lifecycle(nextPhase, {
        plan_approval: planApproval as "pending" | "approved",
        base_ref: baseRef,
        reviewed_base: fixture.baseSha,
        reviewed_feature: fixture.featureSha,
      }));
      writePlan(fixture, previous);
      expectDenied(run(fixture, writePayload(fixture, next)));
    });
  });

  test.each([
    ["missing reviewed base", null, "current"],
    ["missing reviewed feature", "current", null],
    ["abbreviated reviewed base", "1234", "current"],
    ["abbreviated reviewed feature", "current", "1234"],
    ["unknown reviewed base", "f".repeat(40), "current"],
    ["unknown reviewed feature", "current", "e".repeat(40)],
  ])("%s is refused before app review", (_name, reviewedBase, reviewedFeature) => {
    withFixture((fixture) => {
      const current = allGatesPassed(plan(fixture.slug));
      const baseRef = `refs/heads/${fixture.baseBranch}`;
      const invalidReview = withLifecycle(current, lifecycle("awaiting-app-review", {
        base_ref: baseRef,
        reviewed_base: reviewedBase === "current" ? fixture.baseSha : reviewedBase,
        reviewed_feature: reviewedFeature === "current" ? fixture.featureSha : reviewedFeature,
      }));
      writePlan(fixture, current);
      expectDenied(run(fixture, writePayload(fixture, invalidReview)));
    });
  });

  test("app review waits for every checkpoint gate", () => {
    withFixture((fixture) => {
      const current = plan(fixture.slug);
      const baseRef = `refs/heads/${fixture.baseBranch}`;
      const review = withLifecycle(current, lifecycle("awaiting-app-review", {
        base_ref: baseRef,
        reviewed_base: fixture.baseSha,
        reviewed_feature: fixture.featureSha,
      }));
      writePlan(fixture, current);
      expectDenied(run(fixture, writePayload(fixture, review)));
    });
  });

  test("reviewed feature must descend from the detected base", () => {
    withFixture((fixture) => {
      git(["switch", "-q", "--orphan", "orphan-feature"], fixture.root);
      git(["rm", "-rf", "--ignore-unmatch", "."], fixture.root);
      writeFileSync(join(fixture.root, "orphan.txt"), "unrelated history\n");
      git(["add", "orphan.txt"], fixture.root);
      git(["commit", "-q", "-m", "unrelated feature"], fixture.root);
      const unrelatedSha = git(["rev-parse", "HEAD"], fixture.root);
      git(["switch", "-q", fixture.featureBranch], fixture.root);
      git(["update-ref", `refs/heads/${fixture.featureBranch}`, unrelatedSha], fixture.root);

      const current = allGatesPassed(plan(fixture.slug));
      const invalid = withLifecycle(current, lifecycle("awaiting-app-review", {
        base_ref: `refs/heads/${fixture.baseBranch}`,
        reviewed_base: fixture.baseSha,
        reviewed_feature: unrelatedSha,
      }));
      writePlan(fixture, current);
      expectDenied(run(fixture, writePayload(fixture, invalid)));
    });
  });

  test("approval cannot change a reviewed SHA", () => {
    withFixture((fixture) => {
      const current = allGatesPassed(plan(fixture.slug));
      const baseRef = `refs/heads/${fixture.baseBranch}`;
      const awaiting = withLifecycle(current, lifecycle("awaiting-app-review", {
        base_ref: baseRef,
        reviewed_base: fixture.baseSha,
        reviewed_feature: fixture.featureSha,
      }));
      const changed = withLifecycle(awaiting, lifecycle("ready-to-merge", {
        base_ref: baseRef,
        reviewed_base: fixture.baseSha,
        reviewed_feature: fixture.baseSha,
      }));
      writePlan(fixture, awaiting);
      expectDenied(run(fixture, writePayload(fixture, changed)));
    });
  });

  test("app-review handoff refuses checkpoint task changes", () => {
    withFixture((fixture) => {
      const current = allGatesPassed(plan(fixture.slug));
      const baseRef = `refs/heads/${fixture.baseBranch}`;
      const changed = copyPlan(current);
      changed.checkpoints[0]!.tasks = ["expanded at app-review handoff"];
      const review = withLifecycle(changed, lifecycle("awaiting-app-review", {
        base_ref: baseRef,
        reviewed_base: fixture.baseSha,
        reviewed_feature: fixture.featureSha,
      }));
      writePlan(fixture, current);
      expectDenied(run(fixture, writePayload(fixture, review)));
    });
  });

  test.each(["tasks", "acceptance", "files"])("app-review approval refuses changed checkpoint %s", (field) => {
    withFixture((fixture) => {
      const completed = allGatesPassed(plan(fixture.slug));
      const baseRef = `refs/heads/${fixture.baseBranch}`;
      const awaiting = withLifecycle(completed, lifecycle("awaiting-app-review", {
        base_ref: baseRef,
        reviewed_base: fixture.baseSha,
        reviewed_feature: fixture.featureSha,
      }));
      const changed = copyPlan(awaiting);
      const item = changed.checkpoints[0]!;
      if (field === "tasks") item.tasks = ["expanded after review"];
      if (field === "acceptance") item.acceptance = ["changed after review"];
      if (field === "files") item.files = ["src/unreviewed.ts"];
      const ready = withLifecycle(changed, lifecycle("ready-to-merge", {
        base_ref: baseRef,
        reviewed_base: fixture.baseSha,
        reviewed_feature: fixture.featureSha,
      }));
      writePlan(fixture, awaiting);
      expectDenied(run(fixture, writePayload(fixture, ready)));
    });
  });

  test("app review allows runtime gate status and finding updates", () => {
    withFixture((fixture) => {
      const completed = allGatesPassed(plan(fixture.slug));
      const baseRef = `refs/heads/${fixture.baseBranch}`;
      const awaiting = withLifecycle(completed, lifecycle("awaiting-app-review", {
        base_ref: baseRef,
        reviewed_base: fixture.baseSha,
        reviewed_feature: fixture.featureSha,
      }));
      const updated = copyPlan(awaiting);
      updated.checkpoints[0]!.gates.behavior.attempts += 1;
      updated.checkpoints[0]!.gates.behavior.findings.push("gate rerun");
      writePlan(fixture, awaiting);
      expectAllowed(run(fixture, writePayload(fixture, updated)));
    });
  });

  test("ready-to-merge rejects a stale reviewed base", () => {
    withFixture((fixture) => {
      const current = allGatesPassed(plan(fixture.slug));
      const baseRef = `refs/heads/${fixture.baseBranch}`;
      const awaiting = withLifecycle(current, lifecycle("awaiting-app-review", {
        base_ref: baseRef,
        reviewed_base: fixture.baseSha,
        reviewed_feature: fixture.featureSha,
      }));
      git(["switch", "-q", fixture.baseBranch], fixture.root);
      writeFileSync(join(fixture.root, "advanced-base.txt"), "new base\n");
      git(["add", "advanced-base.txt"], fixture.root);
      git(["commit", "-q", "-m", "advance base"], fixture.root);
      git(["switch", "-q", fixture.featureBranch], fixture.root);
      const ready = withLifecycle(awaiting, lifecycle("ready-to-merge", {
        base_ref: baseRef,
        reviewed_base: fixture.baseSha,
        reviewed_feature: fixture.featureSha,
      }));
      writePlan(fixture, awaiting);
      expectDenied(run(fixture, writePayload(fixture, ready)));
    });
  });

  test("review invalidation is refused while the reviewed base is still current", () => {
    withFixture((fixture) => {
      const current = allGatesPassed(plan(fixture.slug));
      const baseRef = `refs/heads/${fixture.baseBranch}`;
      const awaiting = withLifecycle(current, lifecycle("awaiting-app-review", {
        base_ref: baseRef,
        reviewed_base: fixture.baseSha,
        reviewed_feature: fixture.featureSha,
      }));
      const invalidated = withLifecycle(awaiting, lifecycle("implementation"));
      writePlan(fixture, awaiting);
      expectDenied(run(fixture, writePayload(fixture, invalidated)));
    });
  });

  test("invalidating a stale review clears both SHAs and returns to implementation", () => {
    withFixture((fixture) => {
      const current = allGatesPassed(plan(fixture.slug));
      const baseRef = `refs/heads/${fixture.baseBranch}`;
      const awaiting = withLifecycle(current, lifecycle("awaiting-app-review", {
        base_ref: baseRef,
        reviewed_base: fixture.baseSha,
        reviewed_feature: fixture.featureSha,
      }));
      git(["switch", "-q", fixture.baseBranch], fixture.root);
      writeFileSync(join(fixture.root, "advanced-base.txt"), "new base\n");
      git(["add", "advanced-base.txt"], fixture.root);
      git(["commit", "-q", "-m", "advance base"], fixture.root);
      git(["switch", "-q", fixture.featureBranch], fixture.root);
      writePlan(fixture, awaiting);
      expectAllowed(run(fixture, writePayload(fixture, withLifecycle(awaiting, lifecycle("implementation")))));
    });
  });

  test("the removed complete phase is not writable", () => {
    withFixture((fixture) => {
      const current = allGatesPassed(plan(fixture.slug));
      const baseRef = `refs/heads/${fixture.baseBranch}`;
      const ready = withLifecycle(current, lifecycle("ready-to-merge", {
        base_ref: baseRef,
        reviewed_base: fixture.baseSha,
        reviewed_feature: fixture.featureSha,
      }));
      const complete = withLifecycle(ready, lifecycle("complete", {
        base_ref: baseRef,
        app_review: "approved",
        reviewed_base: fixture.baseSha,
        reviewed_feature: fixture.featureSha,
      }));
      writePlan(fixture, ready);
      expectDenied(run(fixture, writePayload(fixture, complete)));
    });
  });
});

describe("checkpoint guard G7 — Bash writes to checkpoint JSON", () => {
  const relativePlan = ".ai-engineering/workflow/checkpoints/demo.json";
  const deniedCommands = [
    ["heredoc redirection", `cat > ${relativePlan} <<EOF\n{}\nEOF`],
    ["append redirection", `printf x >> ${relativePlan}`],
    ["sed -i", `sed -i 's/a/b/' ${relativePlan}`],
    ["tee", `printf x | tee ${relativePlan}`],
    ["cp", `cp source.json ${relativePlan}`],
    ["mv", `mv source.json ${relativePlan}`],
    ["python open for write", `python3 -c "open('${relativePlan}','w')"`],
    ["node write", `node -e "require('fs').writeFileSync('${relativePlan}','{}')"`],
    ["perl write", `perl -e "open(F,'>','${relativePlan}')"`],
    ["jq redirected write", `jq . source.json > ${relativePlan}`],
    ["truncate", `truncate -s 0 ${relativePlan}`],
    ["Git-prefixed compound copy", `git status --short && cp source.json ${relativePlan}`],
    ["Git-prefixed compound redirection", `git status --short; printf x > ${relativePlan}`],
  ] as const;

  test.each(deniedCommands)("denies %s", (_name, command) => {
    withFixture((fixture) => expectDenied(run(fixture, tool("Bash", { command }))));
  });

  test.each([
    ["git add", `git add ${relativePlan}`],
    ["read-only git status", `git status --short -- ${relativePlan}`],
    ["cat read", `cat ${relativePlan}`],
  ])("allows %s", (_name, command) => {
    withFixture((fixture) => {
      writePlan(fixture, plan(fixture.slug));
      expectAllowed(run(fixture, tool("Bash", { command })));
    });
  });

  test("Cursor Shell is normalized to Bash before the guard sees the write", () => {
    withFixture((fixture) => {
      const cursorShell = normalise(
        { tool_name: "Shell", tool_input: { command: `cat > ${relativePlan} <<EOF\n{}\nEOF` } },
        "cursor",
      );
      expect(cursorShell.tool_name).toBe("Bash");
      expectDenied(run(fixture, cursorShell));
    });
  });
});

describe("checkpoint guard G8 — Stop and consecutive block limit", () => {
  const midPlan = (fixture: Fixture) => withGate(plan(fixture.slug), 2, "behavior", "failed");
  const donePlan = (fixture: Fixture) => allGatesPassed(plan(fixture.slug));
  const invalidPlan = (fixture: Fixture) => withCheckpointStatus(allGatesPassed(plan(fixture.slug)), 3, "invalid");

  test.each([
    ["orchestrator session mid-checkpoint", "orchestrated", "end_turn", "mid", true],
    ["different session mid-checkpoint", "unrelated", "end_turn", "mid", false],
    ["user interrupt", "orchestrated", "user_interrupt", "mid", false],
    ["ask-user-question stop", "orchestrated", "ask_user_question", "mid", false],
    ["halted checkpoint", "orchestrated", "end_turn", "halted", false],
    ["all gates passed", "orchestrated", "end_turn", "done", false],
    ["no gate started", "orchestrated", "end_turn", "initial", false],
    ["invalid state written behind hooks", "orchestrated", "end_turn", "invalid", true],
  ])("%s", (_name, transcriptKind, reason, state, shouldDeny) => {
    withFixture((fixture) => {
      if (transcriptKind === "orchestrated") orchestratorTranscript(fixture);
      else writeFileSync(fixture.transcriptPath, "unrelated session\n");
      let current: CheckpointPlan;
      switch (state) {
        case "mid":
          current = midPlan(fixture);
          break;
        case "halted":
          current = { ...midPlan(fixture), halted: { reason: "circuit breaker", checkpoint: 2 } };
          break;
        case "done":
          current = donePlan(fixture);
          break;
        case "invalid":
          current = invalidPlan(fixture);
          break;
        default:
          current = plan(fixture.slug);
      }
      writePlan(fixture, current);
      const result = run(fixture, stopPayload(fixture, randomUUID(), { reason }));
      if (shouldDeny) expectDenied(result, fixture.planPath);
      else expectAllowed(result);
    });
  });

  test("three consecutive Stop refusals are allowed on the fourth, independently per session", () => {
    withFixture((fixture) => {
      orchestratorTranscript(fixture);
      writePlan(fixture, midPlan(fixture));
      const firstSession = `stop-a-${randomUUID()}`;
      const secondSession = `stop-b-${randomUUID()}`;
      for (let attempt = 0; attempt < 3; attempt += 1) {
        expectDenied(run(fixture, stopPayload(fixture, firstSession)));
      }
      expectDenied(run(fixture, stopPayload(fixture, secondSession)));
      expectAllowed(run(fixture, stopPayload(fixture, firstSession)));
      expectDenied(run(fixture, stopPayload(fixture, secondSession)));
    });
  });
});

describe("checkpoint guard U28-U29 — trigger scope and refusal guidance", () => {
  test("unrelated writes and plain prompts allow without reading an unreadable plan", () => {
    withFixture((fixture) => {
      writePlan(fixture, "{ malformed");
      expectAllowed(run(fixture, tool("Write", { file_path: join(fixture.root, "notes.md"), content: "x" })));
      expectAllowed(run(fixture, tool("Edit", { file_path: join(fixture.root, "notes.md"), old_string: "a", new_string: "b" })));
      expectAllowed(run(fixture, tool("Agent", { prompt: "Please add a feature." })));
      expect(readFileSync(fixture.planPath, "utf8")).toBe("{ malformed");
    });
  });

  test.each([
    ["skipped checkpoint", (fixture: Fixture) => {
      writePlan(fixture, plan(fixture.slug));
      return marker(fixture.slug, 3, "implement");
    }, ["CP3", "Next:"]],
    ["pending review gate", (fixture: Fixture) => {
      const value = plan(fixture.slug);
      value.checkpoints[1]!.gates.behavior.status = "passed";
      value.checkpoints[1]!.gates.ui.status = "pending";
      writePlan(fixture, value);
      return marker(fixture.slug, 2, "review");
    }, ["CP2", "review", "Next:"]],
  ])("refusal for %s names the checkpoint, gate and next step", (_name, makePayload, expectedParts) => {
    withFixture((fixture) => {
      const reason = expectDenied(run(fixture, makePayload(fixture)), ...expectedParts);
      expect(reason).toMatch(/next:\s+\S+/i);
    });
  });
});
