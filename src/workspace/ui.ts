export type WorkspaceStatus = "needs-review" | "in-progress" | "blocked" | "closed" | "unknown";
export type WorkspaceFilter = "all" | WorkspaceStatus;

export interface WorkspaceItem {
  slug: string;
  status: WorkspaceStatus;
  [key: string]: unknown;
}

export interface WorkspaceProject {
  root: string;
  items: WorkspaceItem[];
  history: WorkspaceItem[];
  [key: string]: unknown;
}

export interface WorkspaceUiState {
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

export type WorkspaceUiAction =
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

export type WorkspaceUiView =
  | { kind: "loading"; title: string }
  | { kind: "empty"; title: string }
  | { kind: "error"; title: string; message: string; retryLabel: string }
  | { kind: "all-projects"; title: string; projects: WorkspaceProject[] }
  | { kind: "project-overview"; title: string; project: WorkspaceProject }
  | { kind: "project-history"; title: string; project: WorkspaceProject; history: WorkspaceItem[] };

export const WORKSPACE_STATUS_FILTERS: Array<{ value: WorkspaceFilter; label: string }> = [
  { value: "all", label: "All projects" },
  { value: "needs-review", label: "Needs review" },
  { value: "in-progress", label: "In progress" },
  { value: "blocked", label: "Blocked" },
  { value: "closed", label: "Closed" },
  { value: "unknown", label: "Unknown" },
];

export function createWorkspaceUiState(options: {
  projects?: WorkspaceProject[];
  roots?: string[];
  isLoading?: boolean;
} = {}): WorkspaceUiState {
  const savedRoots = [...(options.roots ?? [])];
  return {
    projects: options.projects ?? [],
    isLoading: options.isLoading ?? true,
    loadError: null,
    selectedProjectRoot: null,
    selectedProjectPage: "overview",
    isSettingsOpen: false,
    savedRoots,
    draftRoots: [...savedRoots],
    settingsError: null,
  };
}

export function reduceWorkspaceUiState(
  state: WorkspaceUiState,
  action: WorkspaceUiAction,
): WorkspaceUiState {
  switch (action.type) {
    case "projects-loaded":
      return { ...state, projects: action.projects, isLoading: false, loadError: null };
    case "projects-failed":
      return { ...state, isLoading: false, loadError: action.message };
    case "retry":
      return { ...state, isLoading: true, loadError: null };
    case "select-project":
      return state.projects.some((project) => project.root === action.root)
        ? { ...state, selectedProjectRoot: action.root, selectedProjectPage: "overview" }
        : state;
    case "select-history":
      return state.selectedProjectRoot === null
        ? state
        : { ...state, selectedProjectPage: "history" };
    case "show-all-projects":
      return { ...state, selectedProjectRoot: null, selectedProjectPage: "overview" };
    case "open-settings":
      return { ...state, isSettingsOpen: true, draftRoots: [...state.savedRoots], settingsError: null };
    case "add-search-root":
      return addSearchRoot(state, action.root);
    case "remove-search-root":
      return {
        ...state,
        draftRoots: state.draftRoots.filter((root) => root !== action.root),
        settingsError: null,
      };
    case "cancel-settings":
      return { ...state, isSettingsOpen: false, draftRoots: [...state.savedRoots], settingsError: null };
    case "save-settings":
      return {
        ...state,
        isSettingsOpen: false,
        savedRoots: [...state.draftRoots],
        draftRoots: [...state.draftRoots],
        settingsError: null,
      };
  }
}

function addSearchRoot(state: WorkspaceUiState, input: string): WorkspaceUiState {
  const root = input.trim().replace(/[\\/]+$/, "");
  const normalizedInput = input.replace(/\\/g, "/");
  const hasTraversal = normalizedInput.split("/").some((segment) => segment === "." || segment === "..");
  const isAbsoluteRoot = root.startsWith("/") || /^[A-Za-z]:[\\/]/.test(root) || /^\\\\[^\\]+\\[^\\]+/.test(root);
  if (hasTraversal) {
    return { ...state, settingsError: "Parent-directory segments are not allowed in a search root." };
  }
  if (!root || !(isAbsoluteRoot || root.startsWith("~/") || root.startsWith("~\\")) || /^\/$/.test(root)) {
    return { ...state, settingsError: "Enter a specific absolute folder path, not a filesystem root." };
  }
  if (state.draftRoots.some((savedRoot) => comparableRoot(savedRoot) === comparableRoot(root))) {
    return { ...state, settingsError: "That search root is already listed." };
  }
  return { ...state, draftRoots: [...state.draftRoots, root], settingsError: null };
}

function comparableRoot(root: string): string {
  return root.replace(/\\/g, "/").replace(/\/+$/, "").toLowerCase();
}

export function getWorkspaceView(state: WorkspaceUiState): WorkspaceUiView {
  if (state.isLoading) return { kind: "loading", title: "Loading local projects" };
  if (state.loadError !== null) {
    return {
      kind: "error",
      title: "Local project roots could not be loaded",
      message: state.loadError,
      retryLabel: "Retry",
    };
  }
  if (state.selectedProjectRoot !== null) {
    const project = state.projects.find((entry) => entry.root === state.selectedProjectRoot);
    if (project !== undefined) {
      return state.selectedProjectPage === "history"
        ? { kind: "project-history", title: `${projectName(project.root)} history`, project, history: project.history }
        : { kind: "project-overview", title: projectName(project.root), project };
    }
  }
  if (state.projects.length === 0) return { kind: "empty", title: "No AI Engineering-governed projects found" };
  return { kind: "all-projects", title: "All projects", projects: state.projects };
}

function projectName(root: string): string {
  return root.replace(/[\\/]+$/, "").split(/[\\/]/).pop() || root;
}

export function filterWorkspaceItems(items: WorkspaceItem[], filter: WorkspaceFilter): WorkspaceItem[] {
  return filter === "all" ? items : items.filter((item) => item.status === filter);
}
