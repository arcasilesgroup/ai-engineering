import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { join, sep } from "node:path";

interface WorkspaceServer {
  hostname: string;
  port: number;
  url: URL;
  stop(force?: boolean): void;
}

type FolderPicker = () => string | null | Promise<string | null>;

const activeServers = new Set<Pick<Bun.Server<undefined>, "stop"> | WorkspaceServer>();
const serverModulePath = new URL("../src/workspace/server.ts", import.meta.url).href;
const savedHome = process.env.AI_ENG_HOME;
let testHome = "";

beforeEach(() => {
  testHome = mkdtempSync(join(import.meta.dir, "..", "..", ".workspace-server-"));
  process.env.AI_ENG_HOME = testHome;
});

afterEach(async () => {
  for (const server of activeServers) await server.stop(true);
  activeServers.clear();
  if (savedHome === undefined) delete process.env.AI_ENG_HOME;
  else process.env.AI_ENG_HOME = savedHome;
  rmSync(testHome, { recursive: true, force: true });
  testHome = "";
});

async function startWorkspaceServer(port = 0, folderPicker?: FolderPicker): Promise<WorkspaceServer> {
  const serverModule = (await import(serverModulePath)) as {
    startWorkspaceServer?: (options: {
      port: number;
      folderPicker?: FolderPicker;
    }) => Promise<WorkspaceServer> | WorkspaceServer;
  };
  if (typeof serverModule.startWorkspaceServer !== "function") {
    throw new Error("Expected src/workspace/server.ts to export startWorkspaceServer");
  }

  const server = await serverModule.startWorkspaceServer({
    port,
    ...(folderPicker === undefined ? {} : { folderPicker }),
  });
  activeServers.add(server);
  return server;
}

function git(repository: string, ...args: string[]): string {
  return execFileSync("git", ["-C", repository, ...args], {
    encoding: "utf8",
    env: {
      ...process.env,
      GIT_CONFIG_GLOBAL: "/dev/null",
      GIT_CONFIG_NOSYSTEM: "1",
      GIT_TERMINAL_PROMPT: "0",
    },
  });
}

function createRepository(repository: string, worktreesRoot?: string): void {
  mkdirSync(repository, { recursive: true });
  git(repository, "init", "--quiet", "-b", "main");
  git(repository, "config", "user.name", "Workspace fixture");
  git(repository, "config", "user.email", "workspace-fixture@example.invalid");
  git(repository, "config", "commit.gpgsign", "false");
  mkdirSync(join(repository, ".ai-engineering"), { recursive: true });
  if (worktreesRoot) {
    writeFileSync(
      join(repository, ".ai-engineering", "config.toml"),
      `[git]\nworktrees_dir = ${JSON.stringify(worktreesRoot)}\n`,
    );
  }
  writeFileSync(join(repository, "README.md"), "# local fixture\n");
  git(repository, "add", "-A");
  git(repository, "commit", "--quiet", "-m", "fixture base");
}

function addWorktree(repository: string, worktreesRoot: string, slug: string): string {
  const worktree = join(worktreesRoot, slug);
  mkdirSync(worktreesRoot, { recursive: true });
  git(repository, "worktree", "add", "--quiet", "-b", `feat/${slug}`, worktree, "refs/heads/main");
  return worktree;
}

function writeCheckpoint(worktree: string, slug: string, phase: string, isComplete = false): string {
  const gate = (status: string) => ({ status, attempts: isComplete ? 1 : 0, findings: [] });
  const path = join(worktree, ".ai-engineering", "workflow", "checkpoints", `${slug}.json`);
  mkdirSync(join(worktree, ".ai-engineering", "workflow", "checkpoints"), { recursive: true });
  writeFileSync(path, `${JSON.stringify({
    slug,
    checkpoints: [{
      id: 1,
      status: isComplete ? "passed" : "pending",
      gates: {
        behavior: gate(isComplete ? "passed" : "pending"),
        ui: gate(isComplete ? "passed" : "pending"),
        review: gate(isComplete ? "passed" : "pending"),
      },
      files: [],
    }],
    lifecycle: {
      phase,
      plan_approval: phase === "awaiting-plan-approval" ? "pending" : "approved",
      app_review: isComplete ? "approved" : phase === "awaiting-app-review" ? "pending" : "not-started",
      reviewed_main: null,
    },
  }, null, 2)}\n`);
  return path;
}

async function getJson(server: WorkspaceServer, path: string): Promise<unknown> {
  const response = await fetch(new URL(path, server.url));
  expect(response.status).toBe(200);
  return response.json();
}

async function saveWorkspaceRoots(server: WorkspaceServer, roots: string[]): Promise<Response> {
  return fetch(new URL("/api/settings", server.url), {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ roots }),
  });
}

function records(payload: unknown, key: "projects" | "worktrees" | "history"): Record<string, unknown>[] {
  const body = payload as Record<string, unknown>;
  expect(Array.isArray(body[key])).toBe(true);
  return body[key] as Record<string, unknown>[];
}

describe("workspace server", () => {
  test("binds only to 127.0.0.1", async () => {
    const server = await startWorkspaceServer();

    expect(server.hostname).toBe("127.0.0.1");
  });

  test("answers the health route", async () => {
    const server = await startWorkspaceServer();
    const response = await fetch(new URL("/health", server.url));

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ service: "ai-eng-workspace", status: "ok" });
  });

  test("reuses a healthy instance on a second start", async () => {
    const first = await startWorkspaceServer();
    const second = await startWorkspaceServer(first.port);

    expect(second).toBe(first);
  });

  test("reports an actionable error for an occupied unhealthy port without starting another server", async () => {
    const occupiedServer = Bun.serve({
      hostname: "127.0.0.1",
      port: 0,
      fetch: () => new Response("unrelated service", { status: 503 }),
    });
    activeServers.add(occupiedServer);

    let competingServer: WorkspaceServer | undefined;
    let startupError: unknown;
    try {
      competingServer = await startWorkspaceServer(occupiedServer.port);
    } catch (error) {
      startupError = error;
    }
    if (competingServer) activeServers.add(competingServer);

    expect(competingServer).toBeUndefined();
    expect(startupError).toBeInstanceOf(Error);
    expect((startupError as Error).message).toMatch(/occupied|already in use/i);
    expect((startupError as Error).message).toMatch(/stop|close|free|another port|restart/i);
    expect(await (await fetch(occupiedServer.url)).text()).toBe("unrelated service");
  });

  test("refuses a generic health response without starting a competing server", async () => {
    const occupiedServer = Bun.serve({
      hostname: "127.0.0.1",
      port: 0,
      fetch: () => Response.json({ ok: true, status: "ok" }),
    });
    activeServers.add(occupiedServer);

    let competingServer: WorkspaceServer | undefined;
    let startupError: unknown;
    try {
      competingServer = await startWorkspaceServer(occupiedServer.port);
    } catch (error) {
      startupError = error;
    }
    if (competingServer) activeServers.add(competingServer);

    expect(competingServer).toBeUndefined();
    expect(startupError).toBeInstanceOf(Error);
    expect((startupError as Error).message).toMatch(/occupied|already in use/i);
    expect(await (await fetch(new URL("/health", occupiedServer.url))).json()).toEqual({ ok: true, status: "ok" });
  });

  test("A4 reads, adds, removes, and saves configured roots", async () => {
    const server = await startWorkspaceServer();
    const firstRoot = join(testHome, "first-root");
    const secondRoot = join(testHome, "second-root");
    mkdirSync(firstRoot);
    mkdirSync(secondRoot);

    expect(await getJson(server, "/api/settings")).toEqual({ roots: [] });

    const addResponse = await saveWorkspaceRoots(server, [firstRoot, secondRoot]);
    expect(addResponse.status).toBe(200);
    expect(await getJson(server, "/api/settings")).toEqual({ roots: [firstRoot, secondRoot] });

    const removeResponse = await saveWorkspaceRoots(server, [secondRoot]);
    expect(removeResponse.status).toBe(200);
    expect(await getJson(server, "/api/settings")).toEqual({ roots: [secondRoot] });
  });

  test("A4 rejects duplicate and traversal roots without changing saved settings", async () => {
    const server = await startWorkspaceServer();
    const root = join(testHome, "configured-root");
    mkdirSync(root);

    expect((await saveWorkspaceRoots(server, [root])).status).toBe(200);
    const settingsPath = join(testHome, "workspace.json");
    const originalSettings = await Bun.file(settingsPath).text();

    const duplicateResponse = await saveWorkspaceRoots(server, [root, root]);
    expect(duplicateResponse.status).toBe(400);
    expect(await Bun.file(settingsPath).text()).toBe(originalSettings);

    const traversal = [testHome, "configured-root", "missing", "..", "configured-root"].join(sep);
    const traversalResponse = await saveWorkspaceRoots(server, [traversal]);
    expect(traversalResponse.status).toBe(400);
    expect(await Bun.file(settingsPath).text()).toBe(originalSettings);
  });

  test("A4 leaves previously saved roots unchanged when the folder picker is cancelled", async () => {
    const priorRoot = join(testHome, "prior-root");
    mkdirSync(priorRoot);
    const settingsPath = join(testHome, "workspace.json");
    const originalSettings = `${JSON.stringify({ roots: [priorRoot] }, null, 2)}\n`;
    writeFileSync(settingsPath, originalSettings);

    const server = await startWorkspaceServer(0, () => null);
    const response = await fetch(new URL("/api/settings/pick", server.url), { method: "POST" });

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ path: null });
    expect(await Bun.file(settingsPath).text()).toBe(originalSettings);
  });

  test("A2 lists only configured repositories and registered worktrees, plus an explicit pre-worktree approval", async () => {
    const configuredRoot = join(testHome, "configured");
    const repository = join(configuredRoot, "inside");
    const outsideRepository = join(testHome, "outside", "repository");
    const externalWorktreesRoot = join(testHome, "external-worktrees");
    mkdirSync(configuredRoot, { recursive: true });
    createRepository(repository, externalWorktreesRoot);
    createRepository(outsideRepository);

    const registeredWorktree = addWorktree(repository, externalWorktreesRoot, "registered");
    const unregisteredWorktree = join(externalWorktreesRoot, "not-registered");
    mkdirSync(unregisteredWorktree, { recursive: true });
    writeFileSync(join(unregisteredWorktree, "README.md"), "not registered by Git\n");

    const approvalSlug = "approved-before-start";
    const approvalPath = join(repository, ".ai-eng-lifecycle", `${approvalSlug}.json`);
    mkdirSync(join(repository, ".ai-eng-lifecycle"), { recursive: true });
    writeFileSync(approvalPath, `${JSON.stringify({
      schema_version: 1,
      slug: approvalSlug,
      state: "approval-before-start",
      timestamp: new Date().toISOString(),
      branch: `feat/${approvalSlug}`,
      repository,
      worktrees_dir: externalWorktreesRoot,
      worktree_path: join(externalWorktreesRoot, approvalSlug),
    }, null, 2)}\n`);
    writeFileSync(join(testHome, "workspace.json"), `${JSON.stringify({ roots: [configuredRoot] })}\n`);

    const server = await startWorkspaceServer();
    const projects = records(await getJson(server, "/api/projects"), "projects");
    expect(projects.map((project) => project.path)).toEqual([repository]);
    expect(JSON.stringify(projects)).not.toContain(outsideRepository);

    const worktrees = records(
      await getJson(server, `/api/worktrees?project=${encodeURIComponent(repository)}&status=all`),
      "worktrees",
    );
    expect(worktrees.some((worktree) => worktree.path === registeredWorktree)).toBe(true);
    expect(JSON.stringify(worktrees)).not.toContain(unregisteredWorktree);
    expect(JSON.stringify(worktrees)).not.toContain(outsideRepository);
    expect(worktrees).toContainEqual(expect.objectContaining({
      slug: approvalSlug,
      status: "needs-review",
    }));
  });

  test("A3 filters evidence-backed statuses, serves closed history, and keeps partial read failures visible", async () => {
    const configuredRoot = join(testHome, "configured");
    const repository = join(configuredRoot, "project");
    const worktreesRoot = join(testHome, "project-worktrees");
    mkdirSync(configuredRoot, { recursive: true });
    createRepository(repository, worktreesRoot);

    const needsReview = addWorktree(repository, worktreesRoot, "needs-review");
    writeCheckpoint(needsReview, "needs-review", "awaiting-plan-approval");
    const inProgress = addWorktree(repository, worktreesRoot, "in-progress");
    writeCheckpoint(inProgress, "in-progress", "implementation");
    const blocked = addWorktree(repository, worktreesRoot, "blocked");
    writeCheckpoint(blocked, "blocked", "blocked");
    const unknown = addWorktree(repository, worktreesRoot, "missing-checkpoint");
    writeFileSync(join(unknown, "dirty-only.txt"), "dirty status is not lifecycle evidence\n");
    const checkpointFailure = addWorktree(repository, worktreesRoot, "checkpoint-failure");
    const failedCheckpointPath = join(
      checkpointFailure,
      ".ai-engineering",
      "workflow",
      "checkpoints",
      "checkpoint-failure.json",
    );
    mkdirSync(failedCheckpointPath, { recursive: true });

    git(repository, "checkout", "--quiet", "-b", "feat/closed");
    writeFileSync(join(repository, "closed-feature.txt"), "merged into local main\n");
    writeCheckpoint(repository, "closed", "implementation");
    git(repository, "add", "-A");
    git(repository, "commit", "--quiet", "-m", "closed feature");
    const featureCommit = git(repository, "rev-parse", "HEAD").trim();
    git(repository, "checkout", "--quiet", "main");
    git(repository, "merge", "--quiet", "--no-ff", "--no-edit", "feat/closed");
    const mergedMain = git(repository, "rev-parse", "HEAD").trim();
    writeCheckpoint(repository, "closed", "complete", true);
    const closedCheckpoint = join(repository, ".ai-engineering", "workflow", "checkpoints", "closed.json");
    const closedPlan = JSON.parse(await Bun.file(closedCheckpoint).text()) as {
      lifecycle: Record<string, unknown>;
    };
    closedPlan.lifecycle.reviewed_main = mergedMain;
    closedPlan.lifecycle.reviewed_feature = featureCommit;
    writeFileSync(closedCheckpoint, `${JSON.stringify(closedPlan, null, 2)}\n`);
    git(repository, "add", closedCheckpoint);
    git(repository, "commit", "--quiet", "-m", "record closed lifecycle");

    const partialGitRepository = join(configuredRoot, "git-read-failure");
    createRepository(partialGitRepository);
    writeFileSync(join(partialGitRepository, ".git", "HEAD"), "not-a-valid-git-head\n");
    writeFileSync(join(testHome, "workspace.json"), `${JSON.stringify({ roots: [configuredRoot] })}\n`);

    const server = await startWorkspaceServer();
    const allWorktrees = records(
      await getJson(server, `/api/worktrees?project=${encodeURIComponent(repository)}&status=all`),
      "worktrees",
    );
    expect(allWorktrees.map((worktree) => worktree.slug)).toEqual(expect.arrayContaining([
      "needs-review",
      "in-progress",
      "blocked",
      "missing-checkpoint",
      "checkpoint-failure",
      "closed",
    ]));
    const expectedByStatus: Record<string, string> = {
      "needs-review": "needs-review",
      "in-progress": "in-progress",
      blocked: "blocked",
      closed: "closed",
      unknown: "missing-checkpoint",
    };
    for (const [status, expectedSlug] of Object.entries(expectedByStatus)) {
      const worktrees = records(
        await getJson(server, `/api/worktrees?project=${encodeURIComponent(repository)}&status=${status}`),
        "worktrees",
      );
      expect(worktrees.every((worktree) => worktree.status === status)).toBe(true);
      expect(worktrees.map((worktree) => worktree.slug)).toContain(expectedSlug);
    }
    const unknownWorktrees = records(
      await getJson(server, `/api/worktrees?project=${encodeURIComponent(repository)}&status=unknown`),
      "worktrees",
    );
    expect(unknownWorktrees.map((worktree) => worktree.slug)).toContain("checkpoint-failure");
    const history = records(
      await getJson(server, `/api/history?project=${encodeURIComponent(repository)}`),
      "history",
    );
    expect(history).toContainEqual(expect.objectContaining({ slug: "closed", status: "closed" }));

    const partialGitResponse = await getJson(
      server,
      `/api/worktrees?project=${encodeURIComponent(partialGitRepository)}&status=all`,
    );
    expect(JSON.stringify(partialGitResponse)).toMatch(/git-read-failure|git.*(error|failed)|error/i);
    const partialCheckpointResponse = await getJson(
      server,
      `/api/worktrees?project=${encodeURIComponent(repository)}&status=unknown`,
    );
    expect(JSON.stringify(partialCheckpointResponse)).toMatch(/checkpoint-failure|checkpoint.*(error|failed|read)|EISDIR/i);

    const refreshResponse = await fetch(new URL("/api/refresh", server.url), { method: "POST" });
    expect(refreshResponse.status).toBe(200);
    const refreshBody = await refreshResponse.json() as {
      projects: string[];
      errors: Array<{ root: string; detail: string }>;
    };
    expect(refreshBody.projects).toContain(repository);
    expect(refreshBody.errors).toEqual(expect.arrayContaining([
      expect.objectContaining({
        root: repository,
        detail: expect.stringMatching(/checkpoint-failure/),
      }),
      expect.objectContaining({
        root: partialGitRepository,
        detail: expect.any(String),
      }),
    ]));
  });
});
