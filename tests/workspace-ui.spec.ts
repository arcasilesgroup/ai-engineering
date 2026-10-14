import { describe, expect, test } from "bun:test";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { Script } from "node:vm";

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

interface TestTreeNode {
  dataset: Record<string, string>;
  attributes: Record<string, string>;
  children: TestTreeNode[];
  className: string;
  id: string;
  hidden: boolean;
  innerHTML: string;
  textContent: string;
  setAttribute(name: string, value: string): void;
  getAttribute(name: string): string | null;
  append(...nodes: TestTreeNode[]): void;
  replaceChildren(): void;
  contains(): boolean;
  querySelectorAll(): TestTreeNode[];
  focus(): void;
}

function createTestTreeNode(): TestTreeNode {
  return {
    dataset: {},
    attributes: {},
    children: [],
    className: "",
    id: "",
    hidden: false,
    innerHTML: "",
    textContent: "",
    setAttribute(name, value) { this.attributes[name] = value; },
    getAttribute(name) { return this.attributes[name] ?? null; },
    append(...nodes) { this.children.push(...nodes); },
    replaceChildren() { this.children = []; },
    contains() { return false; },
    querySelectorAll() { return []; },
    focus() {},
  };
}

const UI_MODULE = join(import.meta.dir, "..", "src", "workspace", "ui.ts");
const WORKSPACE_TEMPLATE = join(import.meta.dir, "..", "templates", "workspace.html.tpl");
const WORKSPACE_STATES = join(import.meta.dir, "..", ".ai-engineering", "workflow", "prototypes", "001-worktree-overview.states.json");
const CHECKPOINTS = join(import.meta.dir, "..", ".ai-engineering", "workflow", "checkpoints", "worktree-lifecycle-governance.json");
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

function workspaceEmptyMessage(): (project: { worktrees: WorkspaceItem[] }, filter: WorkspaceFilter) => string {
  const template = readFileSync(WORKSPACE_TEMPLATE, "utf8");
  const start = template.indexOf("function worktreeEmptyMessage(");
  const end = template.indexOf("\nfunction renderWorktreeRows(", start);
  expect(start).toBeGreaterThanOrEqual(0);
  expect(end).toBeGreaterThan(start);
  return new Script(`${template.slice(start, end)}\nworktreeEmptyMessage;`).runInNewContext({
    STATUS_LABELS: {
      "needs-review": "Needs review",
      "in-progress": "In progress",
      blocked: "Blocked",
      closed: "Closed",
      unknown: "Unknown",
    },
  }) as (project: { worktrees: WorkspaceItem[] }, filter: WorkspaceFilter) => string;
}

function workspaceDiagnostics(): (messages: string[]) => string {
  const template = readFileSync(WORKSPACE_TEMPLATE, "utf8");
  const escapeStart = template.indexOf("function escapeHtml(");
  const escapeEnd = template.indexOf("\nfunction projectName(", escapeStart);
  const renderStart = template.indexOf("function renderDiagnostics(");
  const renderEnd = template.indexOf("\nfunction renderAllProjects(", renderStart);
  expect(escapeStart).toBeGreaterThanOrEqual(0);
  expect(escapeEnd).toBeGreaterThan(escapeStart);
  expect(renderStart).toBeGreaterThan(escapeEnd);
  expect(renderEnd).toBeGreaterThan(renderStart);
  return new Script(
    `${template.slice(escapeStart, escapeEnd)}\n${template.slice(renderStart, renderEnd)}\nrenderDiagnostics;`,
  ).runInNewContext() as (messages: string[]) => string;
}

function workspaceMainViewTransition(globals: Record<string, unknown>): (viewId: string) => void {
  const template = readFileSync(WORKSPACE_TEMPLATE, "utf8");
  const start = template.indexOf("function showMainView(id) {");
  const end = template.indexOf("\nfunction showFeedback(", start);
  expect(start).toBeGreaterThanOrEqual(0);
  expect(end).toBeGreaterThan(start);
  return new Script(`${template.slice(start, end)}\nshowMainView;`).runInNewContext(globals) as (viewId: string) => void;
}

function workspaceProjectOverview(globals: Record<string, unknown>): () => void {
  const template = readFileSync(WORKSPACE_TEMPLATE, "utf8");
  const start = template.indexOf("function renderProjectOverview() {");
  const end = template.indexOf("\nfunction showAllProjects(", start);
  expect(start).toBeGreaterThanOrEqual(0);
  expect(end).toBeGreaterThan(start);
  return new Script(`${template.slice(start, end)}\nrenderProjectOverview;`).runInNewContext(globals) as () => void;
}

function workspaceLoader(globals: Record<string, unknown>): {
  getProjects(): Array<{ path: string }>;
  loadWorkspace(showLoading?: boolean): Promise<void>;
  refreshWorkspace(): Promise<void>;
} {
  const template = readFileSync(WORKSPACE_TEMPLATE, "utf8");
  const start = template.indexOf("async function loadWorkspace(showLoading = true) {");
  const end = template.indexOf("\nfunction handleProjectTreeClick(", start);
  expect(start).toBeGreaterThanOrEqual(0);
  expect(end).toBeGreaterThan(start);
  return new Script(
    `${template.slice(start, end)}\n({ getProjects: () => projects, loadWorkspace, refreshWorkspace });`,
  ).runInNewContext(globals) as {
    getProjects(): Array<{ path: string }>;
    loadWorkspace(showLoading?: boolean): Promise<void>;
    refreshWorkspace(): Promise<void>;
  };
}

function workspaceProjectTree(globals: Record<string, unknown>): {
  renderProjectTree(): void;
  handleProjectTreeClick(event: { target: { closest(selector: string): TestTreeNode | null } }): void;
} {
  const template = readFileSync(WORKSPACE_TEMPLATE, "utf8");
  const renderStart = template.indexOf("function renderProjectTree() {");
  const renderEnd = template.indexOf("\nfunction renderSummary(", renderStart);
  const clickStart = template.indexOf("function handleProjectTreeClick(event) {");
  const clickEnd = template.indexOf('\n$("project-tree").addEventListener("click", handleProjectTreeClick);', clickStart);
  expect(renderStart).toBeGreaterThanOrEqual(0);
  expect(renderEnd).toBeGreaterThan(renderStart);
  expect(clickStart).toBeGreaterThan(renderEnd);
  expect(clickEnd).toBeGreaterThan(clickStart);
  return new Script(`${template.slice(renderStart, renderEnd)}\n${template.slice(clickStart, clickEnd)}\n({ renderProjectTree, handleProjectTreeClick });`)
    .runInNewContext(globals) as ReturnType<typeof workspaceProjectTree>;
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
    expect(ui.filterWorkspaceItems([{ slug: "active", status: "in-progress" }], "blocked")).toEqual([]);
  });

  test("distinguishes an empty inventory from a status filter with no matches", () => {
    const emptyMessage = workspaceEmptyMessage();

    expect(emptyMessage({ worktrees: [] }, "blocked")).toBe("No worktrees are present for this project.");
    expect(emptyMessage({ worktrees: [{ slug: "active", status: "in-progress" }] }, "blocked"))
      .toBe("No worktrees match the Blocked filter.");
  });

  test("keeps repository evidence issues in a collapsed and escaped disclosure", () => {
    const render = workspaceDiagnostics();

    expect(render([])).toBe("");
    expect(render(["missing <checkpoint>", "malformed & unreadable"]))
      .toBe('<details class="workspace-diagnostics"><summary>Workspace evidence issues (2)</summary><ul><li>missing &lt;checkpoint&gt;</li><li>malformed &amp; unreadable</li></ul></details>');
  });

  test("resets page and content scrolling when a main view changes", () => {
    const viewIds = ["all-projects-view", "project-overview-view", "loading-state", "empty-state", "error-state"];
    const elements: Record<string, { hidden: boolean; scrollTop?: number; contains?: () => boolean }> = {};
    for (const viewId of viewIds) elements[viewId] = { hidden: false };
    elements["project-tree"] = { hidden: false, contains: () => false };
    elements["main-pane"] = { hidden: false, scrollTop: 126 };
    const pageScrolls: number[][] = [];
    const documentStub = { activeElement: {}, body: { dataset: { mobilePane: "explorer" } } };
    const windowStub = {
      scrollTo: (x: number, y: number) => pageScrolls.push([x, y]),
      matchMedia: () => ({ matches: false }),
    };
    const showMainView = workspaceMainViewTransition({
      $: (id: string) => elements[id],
      document: documentStub,
      window: windowStub,
    });

    showMainView("project-overview-view");

    expect(pageScrolls).toEqual([[0, 0]]);
    expect(elements["main-pane"]?.scrollTop).toBe(0);
    expect(elements["all-projects-view"]?.hidden).toBe(true);
    expect(elements["project-overview-view"]?.hidden).toBe(false);
    expect(documentStub.body.dataset.mobilePane).toBe("content");
  });

  test("history navigation leaves the overview toolbar at the reset scroll position", () => {
    const project = { path: "/repos/alpha", worktrees: [], history: [], errors: [] };
    const scrollIntoViewCalls: unknown[] = [];
    const pageScrolls: number[][] = [];
    const viewIds = ["all-projects-view", "project-overview-view", "loading-state", "empty-state", "error-state"];
    const elements: Record<string, { hidden?: boolean; innerHTML?: string; contains?: () => boolean; scrollTop?: number; scrollIntoView?: (...args: unknown[]) => void; focus?: () => void }> = {};
    for (const viewId of viewIds) elements[viewId] = { hidden: false };
    const overview = elements["project-overview-view"]!;
    overview.contains = () => false;
    elements["project-tree"] = { contains: () => false };
    elements["main-pane"] = { scrollTop: 126 };
    elements["mobile-explorer-back"] = { focus: () => {} };
    const documentStub = { activeElement: {}, body: { dataset: { mobilePane: "explorer" } } };
    const windowStub = {
      scrollTo: (x: number, y: number) => pageScrolls.push([x, y]),
      matchMedia: () => ({ matches: false }),
    };
    elements["project-history-section"] = {
      scrollIntoView: (...args: unknown[]) => scrollIntoViewCalls.push(args),
    };
    const showMainView = workspaceMainViewTransition({
      $: (id: string) => elements[id],
      document: documentStub,
      window: windowStub,
    });
    const renderOverview = workspaceProjectOverview({
      $: (id: string) => elements[id],
      currentProjectData: () => project,
      projectCounts: () => ({ worktrees: 0, needsYou: 0, history: 0 }),
      selectedFilter: "all",
      selectedProjectPage: "history",
      escapeHtml: (value: string) => value,
      renderDiagnostics: workspaceDiagnostics(),
      projectName: () => "alpha",
      statusLabel: (status: string) => status,
      STATUS_FILTERS: [],
      worktreeEmptyMessage: () => "",
      renderWorktreeRows: () => "",
      showMainView,
      document: documentStub,
    });

    renderOverview();

    expect(pageScrolls).toEqual([[0, 0]]);
    expect(elements["main-pane"]?.scrollTop).toBe(0);
    expect(documentStub.body.dataset.mobilePane).toBe("content");
    expect(overview.innerHTML).toContain('id="project-history-section"');
    expect(overview.innerHTML).not.toContain('class="project-tabs"');
    expect(scrollIntoViewCalls).toEqual([]);
  });

  test("renders collapsed tree groups and keeps artifact rows display-only", () => {
    const tree = createTestTreeNode();
    const expandedProjects = new Set(["/repos/alpha"]);
    const expandedProjectGroups = new Set<string>();
    const projectOpenCalls: unknown[][] = [];
    const project = {
      path: "/repos/alpha",
      worktrees: [{ slug: "active", branch: "feat/active", status: "in-progress" as const }],
      history: [{ slug: "closed", branch: "feat/closed", status: "closed" as const }],
    };
    const workspaceTree = workspaceProjectTree({
      $: (id: string) => id === "project-tree" ? tree : createTestTreeNode(),
      document: { activeElement: {}, createElement: createTestTreeNode },
      projects: [project],
      selectedProject: null,
      selectedProjectPage: "overview",
      selectedHistorySlug: null,
      expandedProjects,
      expandedProjectGroups,
      projectName: () => "alpha",
      escapeHtml: (value: string) => value,
      statusLabel: (status: string) => status === "closed" ? "Closed" : "In progress",
      showProject: (...args: unknown[]) => projectOpenCalls.push(args),
      showAllProjects: () => {},
    });

    workspaceTree.renderProjectTree();

    const projectChildren = tree.children[1]!.children[1]!;
    expect(projectChildren.children[0]?.getAttribute("aria-label")).toBe("Open overview for alpha");
    const groupSections = projectChildren.children.slice(1);
    expect(groupSections.map((section) => section.children[0]?.getAttribute("aria-label"))).toEqual([
      "Expand project files for alpha",
      "Expand worktrees for alpha",
      "Expand history for alpha",
    ]);
    expect(groupSections.every((section) => section.children[1]?.hidden)).toBe(true);
    expect(groupSections.every((section) =>
      section.children[0]?.getAttribute("aria-controls") === section.children[1]?.id
    )).toBe(true);
    const projectFiles = groupSections[0]!.children[1]!.children;
    expect(projectFiles.map((entry) => entry.innerHTML)).toEqual([
      '<span aria-hidden="true">▤</span><span class="tree-label">brainstorm.html</span>',
      '<span aria-hidden="true">▤</span><span class="tree-label">PRD.html</span>',
    ]);
    expect(projectFiles.every((entry) => entry.dataset.action === undefined)).toBe(true);

    const toggles = groupSections.map((section) => section.children[0]!);
    for (const toggle of toggles) {
      workspaceTree.handleProjectTreeClick({ target: { closest: () => toggle } });
    }
    const expandedSections = tree.children[1]!.children[1]!.children.slice(1);
    expect(expandedSections.every((section) => section.children[1]?.hidden === false)).toBe(true);
    expect(expandedSections[1]!.children[1]!.children[0]?.dataset.action).toBe("open-project");
    const closedHistory = expandedSections[2]!.children[1]!.children[0]!;
    expect(closedHistory.dataset.action).toBe("open-history");
    expect(closedHistory.getAttribute("aria-label")).toBe("Open history for feat/closed in alpha. Status: Closed");
    workspaceTree.handleProjectTreeClick({ target: { closest: () => closedHistory } });
    expect(projectOpenCalls).toEqual([["/repos/alpha", "history", "closed"]]);
  });

  test("keeps CP10 overview and resize capture steps supported at the checkpoint route", () => {
    const states = JSON.parse(readFileSync(WORKSPACE_STATES, "utf8")) as {
      route: string;
      viewports?: number[][];
      states: Array<{
        name: string;
        regions: string[];
        steps: Array<Record<string, string>>;
        viewports?: number[][];
        live?: boolean;
        live_note?: string;
      }>;
    };
    const checkpoints = JSON.parse(readFileSync(CHECKPOINTS, "utf8")) as {
      checkpoints: Array<{ id: number; ui: { route: string; scope: string[]; states: string[] } }>;
    };
    const cp10 = checkpoints.checkpoints.find((checkpoint) => checkpoint.id === 10)!;

    expect(states.route).toBe(cp10.ui.route);
    expect(cp10.ui.scope).toContain("project-documents");
    expect(states.viewports).toBeUndefined();
    for (const projectName of ["ai-engineering", "checkout-api"]) {
      const desktop = states.states.find((state) => state.name === `${projectName}-project-overview`)!;
      expect(desktop.viewports).toEqual([[1440, 900]]);
      expect(desktop.steps).toEqual([
        { click: `Expand project ${projectName}`, role: "button" },
        { scroll: "#main-pane", to: "bottom" },
        { click: `Open overview for ${projectName}`, role: "button" },
      ]);
      expect(desktop.regions).toContain("project-documents");

      const mobile = states.states.find((state) => state.name === `${projectName}-project-overview-mobile`)!;
      expect(mobile.viewports).toEqual([[375, 812]]);
      expect(mobile.steps).toEqual([
        { click: "← Explorer", role: "button" },
        { click: `Expand project ${projectName}`, role: "button" },
        { scroll: ".explorer", to: "bottom" },
        { click: `Open overview for ${projectName}`, role: "button" },
      ]);
      expect(mobile.regions).not.toContain("project-documents");
      expect(cp10.ui.states).toContain(mobile.name);
    }

    const chooseRoot = states.states.find((state) => state.name === "choose-search-root")!;
    expect(chooseRoot.steps).toEqual([
      { click: "Settings", role: "button" },
      { click: "Choose folder", role: "button" },
    ]);
    expect(chooseRoot.live).toBe(false);
    expect(cp10.ui.states).toContain(chooseRoot.name);

    const mobileTreeScenarios = [
      "expand-and-collapse-project-tree-mobile",
      "expanded-worktree-actions-mobile",
      "project-tree-disclosure-groups-mobile",
    ];
    for (const name of ["expand-and-collapse-project-tree", "expanded-worktree-actions", "project-tree-disclosure-groups"]) {
      const desktop = states.states.find((state) => state.name === name)!;
      expect(desktop.viewports).toEqual([[1440, 900]]);
      expect(desktop.steps[0]).not.toEqual({ click: "← Explorer", role: "button" });
    }
    for (const name of mobileTreeScenarios) {
      const mobile = states.states.find((state) => state.name === name)!;
      expect(mobile.viewports).toEqual([[375, 812]]);
      expect(mobile.steps[0]).toEqual({ click: "← Explorer", role: "button" });
      expect(cp10.ui.states).toContain(name);
    }
    const groupScenario = states.states.find((state) => state.name === "project-tree-disclosure-groups")!;
    expect(groupScenario.steps.slice(-3)).toEqual([
      { click: "Expand project files for ai-engineering", role: "button" },
      { click: "Expand worktrees for ai-engineering", role: "button" },
      { click: "Expand history for ai-engineering", role: "button" },
    ]);
    expect(cp10.ui.states).toContain("project-tree-disclosure-groups");
    expect(states.states.find((state) => state.name === "empty-project-list")?.live_note)
      .toContain("none are AI Engineering-governed");
    const resize = states.states.find((state) => state.name === "resize-project-explorer")!;
    const viewportOverrides: Record<string, number[][]> = {
      "ai-engineering-project-overview": [[1440, 900]],
      "ai-engineering-project-overview-mobile": [[375, 812]],
      "checkout-api-project-overview": [[1440, 900]],
      "checkout-api-project-overview-mobile": [[375, 812]],
      "expand-and-collapse-project-tree": [[1440, 900]],
      "expand-and-collapse-project-tree-mobile": [[375, 812]],
      "expanded-worktree-actions": [[1440, 900]],
      "expanded-worktree-actions-mobile": [[375, 812]],
      "project-tree-disclosure-groups": [[1440, 900]],
      "project-tree-disclosure-groups-mobile": [[375, 812]],
      "resize-project-explorer": [[1440, 900]],
      "drag-resize-project-explorer": [[1440, 900]],
    };
    expect(resize.viewports).toEqual([[1440, 900]]);
    expect(resize.steps).toEqual([
      { click: "Resize project explorer", role: "separator" },
      { press: "ArrowRight" },
    ]);
    const dragResize = states.states.find((state) => state.name === "drag-resize-project-explorer")!;
    expect(dragResize.steps).toEqual([
      { drag: "Resize project explorer", target: "explorer-resize-handle" },
    ]);
    expect(cp10.ui.states).toContain("resize-project-explorer");
    expect(cp10.ui.states).toContain(dragResize.name);
    for (const state of states.states) {
      if (state.name in viewportOverrides) {
        expect(state.viewports).toEqual(viewportOverrides[state.name]);
        continue;
      }
      expect(state.viewports).toBeUndefined();
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
      title: "No AI Engineering-governed projects found",
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

  test("refreshes projects after the transient tree loading node was removed", async () => {
    let isTreeLoadingPresent = true;
    let projectLoads = 0;
    let treeRenders = 0;
    const mainViews: string[] = [];
    const rootCount = { textContent: "" };
    const errorMessage = { textContent: "" };
    const treeLoading = { remove: () => { isTreeLoadingPresent = false; } };
    const elements: Record<string, { textContent: string }> = {
      "root-count": rootCount,
      "error-message": errorMessage,
    };
    const api = workspaceLoader({
      $: (id: string) => id === "tree-loading"
        ? isTreeLoadingPresent ? treeLoading : null
        : elements[id],
      requestJson: async (url: string) => {
        if (url === "/api/refresh") return {};
        if (url === "/api/projects") {
          projectLoads += 1;
          const paths = projectLoads === 1 ? ["/repos/alpha"] : ["/repos/alpha", "/repos/beta"];
          return { projects: paths.map((path) => ({ path, errors: [] })), errors: [] };
        }
        if (url === "/api/settings") return { roots: ["/repos"] };
        if (url.startsWith("/api/worktrees?")) return { worktrees: [], errors: [] };
        if (url.startsWith("/api/history?")) return { history: [], errors: [] };
        throw new Error(`Unexpected request: ${url}`);
      },
      projects: [],
      savedRoots: [],
      rootErrors: [],
      renderProjectTree: () => { treeRenders += 1; },
      showMainView: (viewId: string) => { mainViews.push(viewId); },
      showAllProjects: () => { mainViews.push("all-projects-view"); },
      showFeedback: () => {},
    });

    await api.loadWorkspace();
    await api.refreshWorkspace();

    expect(projectLoads).toBe(2);
    expect(errorMessage.textContent).toBe("");
    expect(rootCount.textContent).toBe("1 root");
    expect(api.getProjects().map((project) => project.path)).toEqual(["/repos/alpha", "/repos/beta"]);
    expect(mainViews.at(-1)).toBe("all-projects-view");
    expect(treeRenders).toBe(2);
  });
});
