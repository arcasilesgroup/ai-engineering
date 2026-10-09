import type { WorkspaceDiscoveryResult } from "./discovery.ts";
import type { WorkspaceFilter, WorkspaceProject } from "./status.ts";
import { discoverWorkspace } from "./discovery.ts";
import { readWorkspaceRoots } from "./settings.ts";

function json(body: unknown, status = 200): Response {
  return Response.json(body, {
    status,
    headers: { "cache-control": "no-store" },
  });
}

function projectFor(snapshot: WorkspaceDiscoveryResult, requestedPath: string | null): WorkspaceProject | undefined {
  return snapshot.projects.find((project) => project.root === requestedPath);
}

export async function handleWorkspaceApi(
  request: Request,
  getSnapshot: () => WorkspaceDiscoveryResult,
  refresh: () => Promise<WorkspaceDiscoveryResult>,
): Promise<Response | null> {
  const url = new URL(request.url);
  if (url.pathname === "/api/projects" && request.method === "GET") {
    const snapshot = getSnapshot();
    return json({
      projects: snapshot.projects.map((project) => ({
        path: project.root,
        errors: project.errors,
      })),
      errors: snapshot.errors,
    });
  }

  if (url.pathname === "/api/worktrees" && request.method === "GET") {
    const snapshot = getSnapshot();
    const project = projectFor(snapshot, url.searchParams.get("project"));
    if (project === undefined) return json({ error: "Project is not in the configured workspace roots.", worktrees: [] }, 404);
    const requestedFilter = url.searchParams.get("status") ?? "all";
    const validFilters: WorkspaceFilter[] = ["all", "needs-review", "in-progress", "blocked", "closed", "unknown"];
    if (!validFilters.includes(requestedFilter as WorkspaceFilter)) {
      return json({ error: "Unknown worktree status filter.", worktrees: [] }, 400);
    }
    const worktrees = requestedFilter === "all"
      ? project.items
      : project.items.filter((item) => item.status === requestedFilter);
    return json({
      worktrees: worktrees.map((item) => ({ ...item, path: item.worktreePath })),
      errors: project.errors,
    });
  }

  if (url.pathname === "/api/history" && request.method === "GET") {
    const snapshot = getSnapshot();
    const project = projectFor(snapshot, url.searchParams.get("project"));
    if (project === undefined) return json({ error: "Project is not in the configured workspace roots.", history: [] }, 404);
    return json({ history: project.history, errors: project.errors });
  }

  if (url.pathname === "/api/refresh" && request.method === "POST") {
    const snapshot = await refresh();
    return json({
      status: "ok",
      projects: snapshot.projects.map((project) => project.root),
      errors: snapshot.errors,
    });
  }

  return null;
}

export async function discoverConfiguredWorkspace(): Promise<WorkspaceDiscoveryResult> {
  try {
    return discoverWorkspace(readWorkspaceRoots());
  } catch (error) {
    return {
      projects: [],
      errors: [{
        root: "workspace settings",
        detail: error instanceof Error ? error.message : String(error),
      }],
    };
  }
}
