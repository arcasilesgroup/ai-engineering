import { describe, expect, test } from "bun:test";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

type WorkspaceStatus = "needs-review" | "in-progress" | "blocked" | "closed" | "unknown";
type WorkspaceFilter = "all" | WorkspaceStatus;

interface WorkspaceItem {
  slug: string;
  status: WorkspaceStatus;
}

interface WorkspaceProject {
  root: string;
  items: WorkspaceItem[];
  history: WorkspaceItem[];
}

interface WorkspaceUiState {
  projects: WorkspaceProject[];
  isLoading: boolean;
  loadError: string | null;
  selectedProjectRoot: string | null;
  selectedProjectPage: "overview" | "history";
  isSettingsOpen: boolean;
  savedRoots: string[];
  draftRoots: string[];
  settingsError: string | null;
}

type WorkspaceUiAction =
  | { type: "projects-loaded"; projects: WorkspaceProject[] }
  | { type: "projects-failed"; message: string }
  | { type: "retry" }
  | { type: "select-project"; root: string }
  | { type: "select-history" }
  | { type: "show-all-projects" }
  | { type: "open-settings" }
  | { type: "add-search-root"; root: string }
  | { type: "remove-search-root"; root: string }
  | { type: "cancel-settings" }
  | { type: "save-settings" };

interface WorkspaceUiView {
  kind: "loading" | "empty" | "error" | "all-projects" | "project-overview" | "project-history";
  title?: string;
  message?: string;
  retryLabel?: string;
  project?: WorkspaceProject;
  projects?: WorkspaceProject[];
  history?: WorkspaceItem[];
}

interface WorkspaceUiApi {
  WORKSPACE_STATUS_FILTERS: Array<{ value: WorkspaceFilter; label: string }>;
  createWorkspaceUiState(options?: {
    projects?: WorkspaceProject[];
    roots?: string[];
    isLoading?: boolean;
  }): WorkspaceUiState;
  reduceWorkspaceUiState(state: WorkspaceUiState, action: WorkspaceUiAction): WorkspaceUiState;
  getWorkspaceView(state: WorkspaceUiState): WorkspaceUiView;
  filterWorkspaceItems(items: WorkspaceItem[], filter: WorkspaceFilter): WorkspaceItem[];
}

const UI_MODULE = join(import.meta.dir, "..", "src", "workspace", "ui.ts");
let uiApi: WorkspaceUiApi | undefined;
let uiImportError: unknown;
if (existsSync(UI_MODULE)) {
  try {
    uiApi = (await import(pathToFileURL(UI_MODULE).href)) as WorkspaceUiApi;
  } catch (error) {
    uiImportError = error;
  }
}

function workspaceUi(): WorkspaceUiApi {
  expect(existsSync(UI_MODULE), "src/workspace/ui.ts must expose the pure workspace UI model").toBe(true);
  if (uiImportError !== undefined) throw uiImportError;
  expect(typeof uiApi?.createWorkspaceUiState, "createWorkspaceUiState export is required").toBe("function");
  expect(typeof uiApi?.reduceWorkspaceUiState, "reduceWorkspaceUiState export is required").toBe("function");
  expect(typeof uiApi?.getWorkspaceView, "getWorkspaceView export is required").toBe("function");
  expect(typeof uiApi?.filterWorkspaceItems, "filterWorkspaceItems export is required").toBe("function");
  expect(Array.isArray(uiApi?.WORKSPACE_STATUS_FILTERS), "WORKSPACE_STATUS_FILTERS export is required").toBe(true);
  return uiApi!;
}

function project(name = "alpha"): WorkspaceProject {
  return {
    root: `/repos/${name}`,
    items: [
      { slug: "active", status: "in-progress" },
      { slug: "review", status: "needs-review" },
    ],
    history: [{ slug: "closed", status: "closed" }],
  };
}

describe("workspace UI logic", () => {
  test("exposes English all-projects and status filter labels", () => {
    const ui = workspaceUi();

    expect(ui.WORKSPACE_STATUS_FILTERS).toEqual([
      { value: "all", label: "All projects" },
      { value: "needs-review", label: "Needs review" },
      { value: "in-progress", label: "In progress" },
      { value: "blocked", label: "Blocked" },
      { value: "closed", label: "Closed" },
      { value: "unknown", label: "Unknown" },
    ]);
  });

  test("filters project worktrees by each evidence-backed status", () => {
    const ui = workspaceUi();
    const items: WorkspaceItem[] = [
      { slug: "review", status: "needs-review" },
      { slug: "active", status: "in-progress" },
      { slug: "stuck", status: "blocked" },
      { slug: "done", status: "closed" },
      { slug: "uncertain", status: "unknown" },
    ];

    expect(ui.filterWorkspaceItems(items, "all")).toEqual(items);
    for (const item of items) {
      expect(ui.filterWorkspaceItems(items, item.status)).toEqual([item]);
    }
  });

  test("selects a project's overview and history without losing project identity", () => {
    const ui = workspaceUi();
    const selectedProject = project();
    let state = ui.createWorkspaceUiState({ projects: [selectedProject], isLoading: false });

    expect(ui.getWorkspaceView(state)).toMatchObject({ kind: "all-projects", title: "All projects" });

    state = ui.reduceWorkspaceUiState(state, { type: "select-project", root: selectedProject.root });
    expect(ui.getWorkspaceView(state)).toMatchObject({
      kind: "project-overview",
      project: selectedProject,
    });

    state = ui.reduceWorkspaceUiState(state, { type: "select-history" });
    expect(ui.getWorkspaceView(state)).toMatchObject({
      kind: "project-history",
      project: selectedProject,
      history: selectedProject.history,
    });
  });

  test("cancels settings by discarding draft root edits", () => {
    const ui = workspaceUi();
    const savedRoot = "/repos/saved";
    let state = ui.createWorkspaceUiState({ roots: [savedRoot], isLoading: false });
    state = ui.reduceWorkspaceUiState(state, { type: "open-settings" });
    state = ui.reduceWorkspaceUiState(state, { type: "add-search-root", root: "/repos/draft" });

    state = ui.reduceWorkspaceUiState(state, { type: "cancel-settings" });

    expect(state.isSettingsOpen).toBe(false);
    expect(state.savedRoots).toEqual([savedRoot]);
    expect(state.draftRoots).toEqual([savedRoot]);
  });

  test("saves settings draft roots and closes the dialog", () => {
    const ui = workspaceUi();
    let state = ui.createWorkspaceUiState({ roots: ["/repos/first"], isLoading: false });
    state = ui.reduceWorkspaceUiState(state, { type: "open-settings" });
    state = ui.reduceWorkspaceUiState(state, { type: "add-search-root", root: "/repos/second" });
    state = ui.reduceWorkspaceUiState(state, { type: "remove-search-root", root: "/repos/first" });

    state = ui.reduceWorkspaceUiState(state, { type: "save-settings" });

    expect(state.isSettingsOpen).toBe(false);
    expect(state.savedRoots).toEqual(["/repos/second"]);
    expect(state.draftRoots).toEqual(["/repos/second"]);
  });

  test("shows inline English validation for duplicate and traversal roots", () => {
    const ui = workspaceUi();
    let state = ui.createWorkspaceUiState({ roots: ["/repos/alpha"], isLoading: false });
    state = ui.reduceWorkspaceUiState(state, { type: "open-settings" });

    state = ui.reduceWorkspaceUiState(state, { type: "add-search-root", root: "/repos/alpha" });
    expect(state.settingsError).toBe("That search root is already listed.");
    expect(state.draftRoots).toEqual(["/repos/alpha"]);

    state = ui.reduceWorkspaceUiState(state, { type: "add-search-root", root: "/repos/../outside" });
    expect(state.settingsError).toBe("Parent-directory segments are not allowed in a search root.");
    expect(state.draftRoots).toEqual(["/repos/alpha"]);
  });

  test("renders loading, empty, and retryable error views", () => {
    const ui = workspaceUi();
    const loading = ui.createWorkspaceUiState({ isLoading: true });
    expect(ui.getWorkspaceView(loading)).toMatchObject({
      kind: "loading",
      title: "Loading local projects",
    });

    const empty = ui.createWorkspaceUiState({ isLoading: false });
    expect(ui.getWorkspaceView(empty)).toMatchObject({
      kind: "empty",
      title: "No local projects found",
    });

    let failed = ui.reduceWorkspaceUiState(empty, {
      type: "projects-failed",
      message: "Project list unavailable.",
    });
    expect(ui.getWorkspaceView(failed)).toMatchObject({
      kind: "error",
      message: "Project list unavailable.",
      retryLabel: "Retry",
    });

    failed = ui.reduceWorkspaceUiState(failed, { type: "retry" });
    expect(failed.isLoading).toBe(true);
    expect(failed.loadError).toBeNull();
    expect(ui.getWorkspaceView(failed)).toMatchObject({ kind: "loading" });
  });
});
