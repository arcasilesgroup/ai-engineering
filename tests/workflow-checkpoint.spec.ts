import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import {
  assertCheckpointTransition,
  parseBrainstormApproval,
  readCheckpoint,
  serializeCheckpoint,
  type Checkpoint,
  type CheckpointContext,
} from "../src/workflow/checkpoint.ts";

interface GitFixture {
  repoPath: string;
  slug: string;
  base: string;
  feature: string;
}

interface GitResult {
  status: number;
  stdout: string;
  stderr: string;
}

let fixtureRoot = "";
let emptyGitConfig = "";
let fixture: GitFixture;

function runGit(args: string[], cwd: string): GitResult {
  const result = spawnSync("git", args, {
    cwd,
    encoding: "utf8",
    env: {
      ...process.env,
      GIT_CONFIG_GLOBAL: emptyGitConfig,
      GIT_CONFIG_SYSTEM: emptyGitConfig,
      GIT_TERMINAL_PROMPT: "0",
    },
  });
  return {
    status: result.status ?? 1,
    stdout: result.stdout ?? "",
    stderr: result.stderr ?? "",
  };
}

function git(args: string[], cwd: string): string {
  const result = runGit(args, cwd);
  if (result.status !== 0) throw new Error(`git ${args.join(" ")} failed: ${result.stderr}`);
  return result.stdout.trim();
}

function createGitFixture(name: string): GitFixture {
  const repoPath = join(fixtureRoot, name);
  mkdirSync(repoPath);
  git(["init", "-q", "-b", "main"], repoPath);
  git(["config", "user.name", "Checkpoint Test"], repoPath);
  git(["config", "user.email", "checkpoint@example.invalid"], repoPath);
  git(["config", "commit.gpgsign", "false"], repoPath);
  writeFileSync(join(repoPath, "base.txt"), "base\n");
  git(["add", "base.txt"], repoPath);
  git(["commit", "-q", "-m", "base"], repoPath);
  const base = git(["rev-parse", "HEAD"], repoPath);

  const slug = "checkpoint-fixture";
  git(["switch", "-q", "-c", `feat/${slug}`], repoPath);
  writeFileSync(join(repoPath, "feature.txt"), "feature\n");
  git(["add", "feature.txt"], repoPath);
  git(["commit", "-q", "-m", "feature"], repoPath);
  const feature = git(["rev-parse", "HEAD"], repoPath);
  return { repoPath, slug, base, feature };
}

function contextFor(gitFixture: GitFixture): CheckpointContext {
  return { repoPath: gitFixture.repoPath, slug: gitFixture.slug, baseRef: "refs/heads/main" };
}

function lifecycle(
  phase: Checkpoint["lifecycle"]["phase"],
  overrides: Partial<Checkpoint["lifecycle"]> = {},
): Checkpoint["lifecycle"] {
  const defaults: Checkpoint["lifecycle"] = {
    phase: "implementation",
    plan_approval: "approved",
    app_review: "not-started",
    base_ref: null,
    reviewed_base: null,
    reviewed_feature: null,
  };
  if (phase === "awaiting-plan-approval") {
    defaults.plan_approval = "pending";
  } else if (phase === "awaiting-app-review") {
    defaults.app_review = "pending";
    defaults.base_ref = "refs/heads/main";
    defaults.reviewed_base = fixture.base;
    defaults.reviewed_feature = fixture.feature;
  } else if (phase === "ready-to-merge") {
    defaults.app_review = "approved";
    defaults.base_ref = "refs/heads/main";
    defaults.reviewed_base = fixture.base;
    defaults.reviewed_feature = fixture.feature;
  }
  return { ...defaults, phase, ...overrides };
}

function checkpoint(
  slug: string,
  phase: Checkpoint["lifecycle"]["phase"],
  lifecycleOverrides: Partial<Checkpoint["lifecycle"]> = {},
): Checkpoint {
  const gate = (status: string) => ({ status, attempts: 1, findings: [] });
  return {
    slug,
    checkpoints: [{
      id: 1,
      title: "Test checkpoint",
      goal: "Keep the fixture meaningful",
      tasks: [],
      files: ["src/example.ts"],
      acceptance: [],
      verify: [],
      ui: null,
      status: "passed",
      changed_files: [],
      gates: {
        behavior: gate("passed"),
        ui: gate("passed"),
        review: gate("passed"),
      },
    }],
    lifecycle: lifecycle(phase, lifecycleOverrides),
  };
}

function checkpointFile(repoPath: string, fileSlug: string, value: unknown | string): string {
  const directory = join(repoPath, ".ai-engineering", "workflow", "checkpoints");
  mkdirSync(directory, { recursive: true });
  const path = join(directory, `${fileSlug}.json`);
  writeFileSync(path, typeof value === "string" ? value : JSON.stringify(value));
  return path;
}

function readPlan(
  gitFixture: GitFixture,
  value: unknown | string,
  fileSlug = gitFixture.slug,
): Checkpoint {
  return readCheckpoint(
    checkpointFile(gitFixture.repoPath, fileSlug, value),
    contextFor(gitFixture),
  );
}

function brainstorm(slug: string, date: string, status = `complete · ${date}`): string {
  return [
    "<!doctype html><html><head>",
    `<meta name="ai-feature" content="${slug}">`,
    `<meta name="ai-approved" content="${date}">`,
    `</head><body><p class="meta">${status}</p></body></html>`,
  ].join("");
}

describe("workflow checkpoint state (CP4)", () => {
  beforeAll(() => {
    fixtureRoot = join(import.meta.dir, `.workflow-checkpoint-${process.pid}-${randomUUID()}`);
    mkdirSync(fixtureRoot);
    emptyGitConfig = join(fixtureRoot, "empty-gitconfig");
    writeFileSync(emptyGitConfig, "");
    fixture = createGitFixture("reader");
  });

  afterAll(() => rmSync(fixtureRoot, { recursive: true, force: true }));

  test("reads every current and legacy phase with normalized lifecycle fields", () => {
    const cases = [
      ["implementation", lifecycle("implementation")],
      ["blocked", lifecycle("blocked")],
      ["awaiting-app-review", lifecycle("awaiting-app-review")],
      ["ready-to-merge", lifecycle("ready-to-merge")],
      ["awaiting-plan-approval", {
        phase: "awaiting-plan-approval",
        plan_approval: "pending",
        app_review: "not-started",
        base_ref: null,
        reviewed_base: null,
        reviewed_feature: null,
      }],
      ["complete", lifecycle("ready-to-merge")],
      ["reviewed_main", {
        phase: "awaiting-app-review",
        plan_approval: "approved",
        app_review: "pending",
        base_ref: "refs/heads/main",
        reviewed_base: fixture.base,
        reviewed_feature: fixture.feature,
      }],
    ] as const;

    for (const [phase, expected] of cases) {
      const value = checkpoint(
        fixture.slug,
        phase === "complete" || phase === "reviewed_main" ? "ready-to-merge" : phase,
      );
      if (phase === "awaiting-plan-approval") {
        value.lifecycle = {
          phase,
          plan_approval: "pending",
          app_review: "not-started",
          reviewed_main: null,
          reviewed_feature: null,
        } as Checkpoint["lifecycle"];
      }
      if (phase === "complete") {
        value.lifecycle = {
          phase,
          plan_approval: "approved",
          app_review: "approved",
          reviewed_main: fixture.base,
          reviewed_feature: fixture.feature,
        } as Checkpoint["lifecycle"];
      }
      if (phase === "reviewed_main") {
        value.lifecycle = {
          phase: "awaiting-app-review",
          plan_approval: "approved",
          app_review: "pending",
          reviewed_feature: fixture.feature,
          reviewed_main: fixture.base,
        } as Checkpoint["lifecycle"];
      }
      expect(readPlan(fixture, value).lifecycle).toEqual(expected);
    }

    const unsupported = checkpoint(fixture.slug, "implementation");
    unsupported.lifecycle = { ...unsupported.lifecycle, phase: "approval-before-start" } as Checkpoint["lifecycle"];
    expect(() => readPlan(fixture, unsupported)).toThrow(/phase/i);
  });

  test("serializes legacy review fields under the new names and preserves other fields", () => {
    const legacy = checkpoint(fixture.slug, "awaiting-app-review");
    legacy.lifecycle = {
      phase: "awaiting-app-review",
      plan_approval: "approved",
      app_review: "pending",
      reviewed_feature: fixture.feature,
      reviewed_main: fixture.base,
    } as Checkpoint["lifecycle"];
    const parsed = readPlan(fixture, legacy);
    const serialized = JSON.parse(serializeCheckpoint(parsed)) as Checkpoint;

    expect(serialized.lifecycle).toEqual({
      phase: "awaiting-app-review",
      plan_approval: "approved",
      app_review: "pending",
      base_ref: "refs/heads/main",
      reviewed_base: fixture.base,
      reviewed_feature: fixture.feature,
    });
    expect(Object.hasOwn(serialized.lifecycle, "reviewed_main")).toBe(false);
    expect(serialized.checkpoints).toEqual(legacy.checkpoints);
    expect(serialized.slug).toBe(legacy.slug);
  });

  test("rejects malformed schemas and checkpoint slug/path mismatches by field", () => {
    const valid = checkpoint(fixture.slug, "implementation");
    const one = valid.checkpoints[0]!;
    const malformed = [
      ["checkpoints", { slug: fixture.slug, lifecycle: valid.lifecycle }],
      ["checkpoints", { ...valid, checkpoints: [] }],
      ["checkpoints", { ...valid, checkpoints: null }],
      ["checkpoints", { ...valid, checkpoints: [null] }],
      ["gates", { ...valid, checkpoints: [{ id: 1 }] }],
      ["status", {
        ...valid,
        checkpoints: [{
          ...one,
          gates: { ...one.gates as object, behavior: { status: "unknown", attempts: 0, findings: [] } },
        }],
      }],
      ["id", JSON.stringify({ ...valid, checkpoints: [{ ...one, id: "1e999" }] })
        .replace('"id":"1e999"', '"id":1e999')],
    ] as const;

    for (const [field, value] of malformed) {
      expect(() => readPlan(fixture, value)).toThrow(new RegExp(field, "i"));
    }
    expect(() => readPlan(fixture, valid, "another-slug")).toThrow(/slug|path|file/i);
    expect(() => readPlan(fixture, { ...valid, slug: "another-slug" })).toThrow(/slug/i);
  });

  test("accepts only full known commit SHAs with reviewed-feature ancestry", () => {
    const unrelated = git(
      ["commit-tree", `${fixture.base}^{tree}`, "-m", "unrelated root"],
      fixture.repoPath,
    );
    expect(runGit(["cat-file", "-e", `${fixture.base}^{commit}`], fixture.repoPath).status).toBe(0);
    expect(runGit(["cat-file", "-e", `${fixture.feature}^{commit}`], fixture.repoPath).status).toBe(0);
    expect(runGit(["cat-file", "-e", `${unrelated}^{commit}`], fixture.repoPath).status).toBe(0);
    expect(runGit(["merge-base", "--is-ancestor", fixture.base, fixture.feature], fixture.repoPath).status).toBe(0);
    expect(runGit(["merge-base", "--is-ancestor", fixture.base, unrelated], fixture.repoPath).status).not.toBe(0);

    const valid = checkpoint(fixture.slug, "awaiting-app-review");
    expect(readPlan(fixture, valid).lifecycle.reviewed_base).toBe(fixture.base);
    expect(() => readPlan(fixture, checkpoint(fixture.slug, "awaiting-app-review", {
      reviewed_base: fixture.base.slice(0, 12),
    }))).toThrow(/reviewed_base/i);
    expect(() => readPlan(fixture, checkpoint(fixture.slug, "awaiting-app-review", {
      reviewed_base: "0".repeat(40),
    }))).toThrow(/reviewed_base/i);
    expect(() => readPlan(fixture, checkpoint(fixture.slug, "awaiting-app-review", {
      reviewed_feature: fixture.feature.slice(0, 12),
    }))).toThrow(/reviewed_feature/i);
    expect(() => readPlan(fixture, checkpoint(fixture.slug, "awaiting-app-review", {
      reviewed_feature: "0".repeat(40),
    }))).toThrow(/reviewed_feature/i);
    expect(() => readPlan(fixture, checkpoint(fixture.slug, "awaiting-app-review", {
      reviewed_feature: unrelated,
    }))).toThrow(/reviewed_feature|ancestor/i);
  });

  test("allows review transitions, request-changes reset, approval, and blocked round-trip", () => {
    const context = contextFor(fixture);
    const implementation = checkpoint(fixture.slug, "implementation");
    const review = checkpoint(fixture.slug, "awaiting-app-review");
    const returned = checkpoint(fixture.slug, "implementation");
    const ready = checkpoint(fixture.slug, "ready-to-merge");
    const blocked = checkpoint(fixture.slug, "blocked", {
      app_review: "approved",
      base_ref: "refs/heads/main",
      reviewed_base: fixture.base,
      reviewed_feature: fixture.feature,
    });

    expect(() => assertCheckpointTransition(implementation, review, context)).not.toThrow();
    expect(() => assertCheckpointTransition(review, returned, context)).not.toThrow();
    expect(returned.lifecycle.reviewed_base).toBeNull();
    expect(returned.lifecycle.reviewed_feature).toBeNull();
    expect(() => assertCheckpointTransition(review, ready, context)).not.toThrow();
    expect(() => assertCheckpointTransition(ready, blocked, context)).not.toThrow();
    expect(blocked.lifecycle).toMatchObject({
      plan_approval: "approved",
      app_review: "approved",
      reviewed_base: fixture.base,
      reviewed_feature: fixture.feature,
    });
    expect(() => assertCheckpointTransition(blocked, ready, context)).not.toThrow();
  });

  test("invalidates a review when the detected base ref loses its pinned compare-and-swap", () => {
    const casFixture = createGitFixture("cas");
    const pinned = checkpoint(casFixture.slug, "awaiting-app-review", {
      base_ref: "refs/heads/main",
      reviewed_base: casFixture.base,
      reviewed_feature: casFixture.feature,
    });
    git(["switch", "-q", "main"], casFixture.repoPath);
    writeFileSync(join(casFixture.repoPath, "base-advanced.txt"), "advance\n");
    git(["add", "base-advanced.txt"], casFixture.repoPath);
    git(["commit", "-q", "-m", "advance base"], casFixture.repoPath);
    const currentBase = git(["rev-parse", "refs/heads/main"], casFixture.repoPath);
    expect(currentBase).not.toBe(casFixture.base);
    expect(runGit(["cat-file", "-e", `${casFixture.base}^{commit}`], casFixture.repoPath).status).toBe(0);

    const invalidated = checkpoint(casFixture.slug, "implementation");
    expect(() => assertCheckpointTransition(
      pinned,
      invalidated,
      contextFor(casFixture),
    )).not.toThrow();
    expect(invalidated.lifecycle.reviewed_base).toBeNull();
    expect(invalidated.lifecycle.reviewed_feature).toBeNull();
  });

  test("refuses skipped, incomplete, SHA-changing, and already-current invalidations", () => {
    const context = contextFor(fixture);
    const implementation = checkpoint(fixture.slug, "implementation");
    const review = checkpoint(fixture.slug, "awaiting-app-review");
    const unchangedBase = checkpoint(fixture.slug, "implementation");
    const pendingPlan = checkpoint(fixture.slug, "implementation", { plan_approval: "pending" });
    const skipped = checkpoint(fixture.slug, "ready-to-merge");
    const incomplete = checkpoint(fixture.slug, "awaiting-app-review");
    incomplete.checkpoints[0]!.status = "in_progress";
    (incomplete.checkpoints[0]!.gates as Record<string, { status: string }>).behavior!.status = "failed";
    const keepsSha = checkpoint(fixture.slug, "implementation", {
      reviewed_base: fixture.base,
    });
    const changesSha = checkpoint(fixture.slug, "ready-to-merge", {
      app_review: "approved",
      reviewed_feature: fixture.base,
    });
    const pendingApproval = checkpoint(fixture.slug, "ready-to-merge", { app_review: "pending" });
    const complete = checkpoint(fixture.slug, "implementation");
    complete.lifecycle = { ...complete.lifecycle, phase: "complete" } as Checkpoint["lifecycle"];

    expect(() => assertCheckpointTransition(
      checkpoint(fixture.slug, "awaiting-plan-approval"),
      pendingPlan,
      context,
    )).toThrow();
    expect(() => assertCheckpointTransition(implementation, skipped, context)).toThrow();
    expect(() => assertCheckpointTransition(implementation, incomplete, context)).toThrow(/gate/i);
    expect(() => assertCheckpointTransition(review, keepsSha, context)).toThrow(/reviewed_base|SHA/i);
    expect(() => assertCheckpointTransition(review, changesSha, context)).toThrow(/reviewed_base|reviewed_feature|SHA/i);
    expect(() => assertCheckpointTransition(review, pendingApproval, context)).toThrow(/app_review/i);
    expect(() => assertCheckpointTransition(implementation, complete, context)).toThrow(/phase/i);
    expect(() => assertCheckpointTransition(review, unchangedBase, context)).toThrow(/base|CAS|invalidate/i);
  });

  test("parses fresh brainstorm approval only for the matching slug and exact single status line", () => {
    const now = new Date("2026-10-27T12:00:00.000Z");
    expect(parseBrainstormApproval(brainstorm("checkpoint-fixture", "2026-10-27"), "checkpoint-fixture", now))
      .toEqual({ slug: "checkpoint-fixture", approvedOn: "2026-10-27" });
    expect(parseBrainstormApproval(brainstorm("checkpoint-fixture", "2026-10-13"), "checkpoint-fixture", now))
      .toEqual({ slug: "checkpoint-fixture", approvedOn: "2026-10-13" });
    for (const input of [
      [brainstorm("checkpoint-fixture", "2026-10-12"), "checkpoint-fixture"],
      [brainstorm("another-slug", "2026-10-27"), "checkpoint-fixture"],
      [brainstorm("checkpoint-fixture", "2026-10-27", "draft · 2026-10-27"), "checkpoint-fixture"],
      [brainstorm("checkpoint-fixture", "2026-10-27", "complete · 2026-10-26"), "checkpoint-fixture"],
      [brainstorm("checkpoint-fixture", "2026-10-27").replace("</body>", '<p class="meta">complete · 2026-10-27</p></body>'), "checkpoint-fixture"],
      [brainstorm("checkpoint-fixture", "2026-02-30"), "checkpoint-fixture"],
      ["<html><body></body></html>", "checkpoint-fixture"],
    ] as const) {
      expect(parseBrainstormApproval(input[0], input[1], now)).toBeNull();
    }
  });
});
