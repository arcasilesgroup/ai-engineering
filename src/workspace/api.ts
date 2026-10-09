import type { WorkspaceDiscoveryResult } from "./discovery.ts";
import type { WorkspaceFilter, WorkspaceProject } from "./status.ts";
import { discoverWorkspace } from "./discovery.ts";
import { pickWorkspaceFolder, validateWorkspaceRoot, type WorkspaceFolderSelection } from "./folder-picker.ts";
import { readWorkspaceRoots, writeWorkspaceRoots } from "./settings.ts";

export type WorkspaceFolderPicker = () =>
  | string
  | null
  | WorkspaceFolderSelection
  | Promise<string | null | WorkspaceFolderSelection>;

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
  folderPicker: WorkspaceFolderPicker = pickWorkspaceFolder,
): Promise<Response | null> {
  const url = new URL(request.url);
  if (url.pathname === "/api/settings" && request.method === "GET") {
    return json({ roots: readWorkspaceRoots() });
  }

  if (url.pathname === "/api/settings" && request.method === "PUT") {
    let body: unknown;
    try {
      body = await request.json();
    } catch {
      return json({ error: "Settings request must contain a JSON roots array." }, 400);
    }
    if (!isSettingsBody(body)) {
      return json({ error: "Settings request must contain only a roots array of paths." }, 400);
    }
    try {
      writeWorkspaceRoots(body.roots);
    } catch (error) {
      return json({ error: error instanceof Error ? error.message : String(error) }, 400);
    }
    await refresh();
    return json({ roots: readWorkspaceRoots() });
  }

  if (url.pathname === "/api/settings/pick" && request.method === "POST") {
    let selection: string | null | WorkspaceFolderSelection;
    try {
      selection = await folderPicker();
    } catch (error) {
      return json({ error: error instanceof Error ? error.message : String(error) }, 500);
    }
    if (selection === null || (typeof selection === "object" && selection.status === "cancelled")) {
      return json({ path: null });
    }
    if (typeof selection === "object" && selection.status === "unsupported") {
      return json({ status: "unsupported", error: selection.reason }, 501);
    }
    const selectedPath = typeof selection === "string" ? selection : selection.path;
    try {
      return json({ path: validateWorkspaceRoot(selectedPath) });
    } catch (error) {
      return json({ error: error instanceof Error ? error.message : String(error) }, 400);
    }
  }

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
      errors: [
        ...snapshot.errors,
        ...snapshot.projects.flatMap((project) =>
          project.errors.map((detail) => ({ root: project.root, detail }))
        ),
      ],
    });
  }

  return null;
}

function isSettingsBody(value: unknown): value is { roots: string[] } {
  return value !== null
    && typeof value === "object"
    && !Array.isArray(value)
    && Object.keys(value).length === 1
    && Array.isArray((value as Record<string, unknown>).roots)
    && (value as { roots: unknown[] }).roots.every((root) => typeof root === "string");
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
