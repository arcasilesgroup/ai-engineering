<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<title>ai-engineering · Local project explorer</title>
<style>
:root {
  color-scheme: dark;
  --bg: #001E2B;
  --surface: #112733;
  --raised: #1C2D38;
  --line: rgba(61, 79, 88, .6);
  --accent: #00ED64;
  --accent-soft: #71F6BA;
  --focus: #0498EC;
  --text: #E8EDEB;
  --muted: #C1C7C6;
  --danger: #FF9A9A;
  --explorer-width: 344px;
  --radius: 6px;
  font-family: "Archivo Variable", "Archivo", system-ui, -apple-system, "Segoe UI", sans-serif;
}
* { box-sizing: border-box; }
html { min-width: 320px; background: var(--bg); }
body { min-height: 100dvh; margin: 0; overflow-x: hidden; background: var(--bg); color: var(--text); font-size: 15px; line-height: 1.55; }
button, input, select { color: inherit; font: inherit; }
button { background: transparent; }
[hidden] { display: none !important; }
:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
.skip-link { position: fixed; z-index: 10; top: 8px; left: 8px; display: inline-flex; min-height: 44px; align-items: center; transform: translateY(-150%); border: 1px solid var(--muted); border-radius: var(--radius); padding: 8px 12px; background: var(--raised); color: var(--text); }
.skip-link:focus { transform: none; }
.app-header { position: sticky; z-index: 3; top: 0; display: flex; min-height: 64px; align-items: center; justify-content: space-between; gap: 16px; border-bottom: 1px solid var(--line); padding-inline: clamp(16px, 2vw, 28px); background: var(--bg); }
.brand { display: inline-flex; min-width: 0; min-height: 48px; align-items: center; border: 0; border-radius: var(--radius); margin-left: -8px; padding: 4px 8px; color: var(--text); cursor: pointer; text-align: left; }
.brand-wordmark { display: inline-flex; align-items: baseline; color: #fff; font-size: 19px; font-weight: 700; line-height: 1.2; letter-spacing: -.025em; }
.brand-brace { color: var(--accent); }
.brand-wordmark-name { margin-left: 6px; color: var(--text); font-size: 16px; font-weight: 600; }
.header-context:empty { display: none; }
.button { display: inline-flex; min-height: 44px; align-items: center; justify-content: center; border: 0; border-radius: var(--radius); padding: 9px 14px; background: var(--raised); cursor: pointer; font-size: 14px; }
.button:hover { background: #263A45; }
.button:disabled { cursor: wait; opacity: .65; }
.button.primary { background: #087A40; color: #fff; }
.button.primary:hover { background: #09934D; }
.app-shell { display: grid; grid-template-columns: minmax(240px, var(--explorer-width)) 8px minmax(0, 1fr); min-height: calc(100dvh - 64px); }
.explorer { position: sticky; top: 64px; min-width: 0; height: calc(100dvh - 64px); overflow: auto; border-right: 1px solid var(--line); background: var(--surface); }
.explorer-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 24px 18px 10px; }
.explorer-head h2 { margin: 0; font-size: 15px; font-weight: 650; }
.root-count { color: var(--muted); font: 12px/1.4 ui-monospace, monospace; white-space: nowrap; }
.tree-nav { display: grid; gap: 3px; padding: 4px 12px 24px; }
.tree-button { display: flex; width: 100%; min-height: 40px; align-items: center; gap: 9px; border: 0; border-radius: var(--radius); padding: 7px 10px; color: var(--text); cursor: pointer; text-align: left; }
.tree-button:hover, .tree-button[aria-current="page"] { background: var(--raised); }
.tree-button .tree-label { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tree-button .tree-count { margin-left: auto; color: var(--muted); font-size: 12px; }
.tree-children { display: grid; gap: 2px; padding: 3px 0 7px 14px; }
.tree-children[hidden] { display: none; }
.tree-group-children { display: grid; gap: 2px; padding: 3px 0 7px 14px; }
.tree-group-children[hidden] { display: none; }
.tree-child { min-height: 36px; font-size: 13px; }
.tree-entry { display: flex; min-height: 36px; align-items: center; gap: 9px; padding: 7px 10px; color: var(--muted); font-size: 13px; }
.tree-status { margin-left: auto; color: var(--muted); font-size: 11px; white-space: nowrap; }
.tree-loading { display: block; padding: 12px 10px; color: var(--muted); font-size: 13px; }
.resize-handle { position: relative; z-index: 2; cursor: col-resize; touch-action: none; }
.resize-handle::before { position: absolute; inset: 0 auto 0 3px; width: 1px; background: var(--line); content: ""; }
.main-pane { min-width: 0; padding: 30px clamp(20px, 3vw, 44px) 64px; overflow-wrap: anywhere; }
.pane-content { max-width: 1050px; }
.pane-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; margin-bottom: 22px; }
.pane-eyebrow { margin: 0 0 7px; color: var(--accent-soft); font-size: 12px; font-weight: 650; letter-spacing: .04em; }
h1 { margin: 0 0 8px; color: #fff; font-size: clamp(24px, 3vw, 32px); line-height: 1.2; letter-spacing: -.025em; }
.pane-subtitle { max-width: 64ch; margin: 0; color: var(--muted); }
.surface { border: 1px solid var(--line); border-radius: 9px; background: var(--surface); }
.summary-strip { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin: 22px 0 32px; }
.summary-item { display: grid; gap: 4px; padding: 16px 18px; }
.summary-item + .summary-item { border-left: 1px solid var(--line); }
.summary-value { color: #fff; font-size: 22px; font-weight: 700; }
.summary-item.attention .summary-value { color: var(--accent-soft); }
.summary-label { color: var(--muted); font-size: 12px; }
.content-section { margin: 26px 0; }
.section-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 10px; }
.section-heading h2 { margin: 0; color: var(--accent-soft); font-size: 14px; font-weight: 650; }
.section-heading > span { color: var(--muted); font-size: 12px; }
.project-list, .activity-list, .feature-list { overflow: hidden; }
.project-row { display: flex; width: 100%; align-items: center; justify-content: space-between; gap: 18px; border: 0; border-bottom: 1px solid var(--line); padding: 16px 18px; color: var(--text); cursor: pointer; text-align: left; }
.project-row:last-child, .activity-row:last-child, .feature-row:last-child { border-bottom: 0; }
.project-row:hover, .activity-row:hover, .feature-row:hover { background: var(--raised); }
.project-name { display: block; color: #fff; font-weight: 650; }
.project-path, .feature-path { display: block; margin-top: 3px; color: var(--muted); font: 12px/1.45 ui-monospace, monospace; }
.row-counts { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px 16px; color: var(--muted); font-size: 12px; }
.activity-row, .feature-row { display: flex; width: 100%; min-height: 60px; align-items: center; justify-content: space-between; gap: 14px; border: 0; border-bottom: 1px solid var(--line); padding: 12px 16px; color: var(--text); cursor: pointer; text-align: left; }
.activity-row strong, .feature-row strong { color: #fff; font-weight: 600; }
.empty-inline { padding: 16px; color: var(--muted); }
.status-badge { display: inline-flex; align-items: center; border: 1px solid var(--line); border-radius: 999px; padding: 2px 8px; color: var(--muted); font-size: 11px; white-space: nowrap; }
.status-badge.needs-review, .status-badge.blocked { border-color: rgba(255,154,154,.55); color: #ffb2b2; }
.status-badge.in-progress { border-color: rgba(113,246,186,.5); color: var(--accent-soft); }
.status-badge.closed { color: var(--muted); }
.status-badge.unknown { border-style: dashed; color: #fff; }
.pane-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 22px; }
.breadcrumb { color: var(--muted); font-size: 13px; }
.breadcrumb button { border: 0; padding: 0; color: var(--accent-soft); cursor: pointer; }
.project-hero { margin-bottom: 18px; }
.project-hero h1 { margin-bottom: 7px; }
.project-root-path { margin: 0; color: var(--muted); font: 12px/1.5 ui-monospace, monospace; overflow-wrap: anywhere; }
.project-statline { display: flex; flex-wrap: wrap; gap: 12px 28px; margin: 18px 0 26px; padding: 15px 18px; color: var(--muted); }
.project-statline strong { color: #fff; }
.workspace-diagnostics { margin: 18px 0; border: 1px solid rgba(255,154,154,.35); border-radius: 9px; padding: 10px 14px; background: rgba(255,154,154,.04); color: var(--muted); font-size: 12px; }
.workspace-diagnostics summary { display: flex; min-height: 44px; align-items: center; color: #ffb2b2; cursor: pointer; font-weight: 600; }
.workspace-diagnostics ul { margin: 10px 0 0; padding-left: 18px; }
.workspace-diagnostics li { margin: 5px 0; color: var(--text); overflow-wrap: anywhere; }
.docs-row { display: flex; flex-wrap: wrap; gap: 10px; padding: 14px; }
.doc-item { display: inline-flex; min-height: 42px; align-items: center; gap: 9px; border-radius: var(--radius); padding: 8px 10px; background: var(--raised); color: var(--text); }
.file-type { color: var(--accent-soft); font: 10px ui-monospace, monospace; }
.filter-control { display: flex; align-items: center; gap: 9px; color: var(--muted); font-size: 13px; }
.filter-control select { min-height: 40px; border: 1px solid var(--line); border-radius: var(--radius); padding: 6px 30px 6px 10px; background: var(--raised); }
.state-panel { max-width: 650px; margin: 48px 0; padding: 0; }
.state-panel p { max-width: 62ch; color: var(--muted); }
.state-panel .button { margin-top: 8px; }
.skeleton-line, .skeleton-row { display: block; border-radius: 5px; margin: 18px 0; background: var(--surface); animation: pulse 1.2s ease-in-out infinite alternate; }
.skeleton-line { width: min(460px, 75%); height: 16px; }
.skeleton-line.short { width: min(300px, 52%); }
.skeleton-row { width: min(700px, 100%); height: 60px; }
@keyframes pulse { to { opacity: .45; } }
.error-copy { color: var(--danger) !important; }
.mobile-explorer-back { display: none; min-height: 44px; align-items: center; gap: 7px; border: 0; border-radius: var(--radius); margin-bottom: 14px; padding: 8px 11px; background: var(--raised); color: var(--text); cursor: pointer; }
.mobile-explorer-back:hover { background: #263A45; }
.action-feedback { max-width: min(520px, calc(100vw - 32px)); border: 1px solid var(--line); border-radius: 8px; margin: 0 0 16px; padding: 12px 16px; background: var(--raised); color: #fff; box-shadow: 0 10px 35px rgba(0,0,0,.35); }
.workspace-settings { width: min(560px, calc(100vw - 28px)); max-height: min(85dvh, 760px); overflow: auto; border: 1px solid var(--line); border-radius: 12px; padding: 0; background: var(--bg); color: var(--text); }
.workspace-settings::backdrop { background: rgba(0,15,21,.76); }
.settings-panel { display: grid; gap: 16px; padding: 24px; }
.settings-heading-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.settings-title { margin: 0; color: #fff; font-size: 19px; }
.settings-description { margin: 6px 0 0; color: var(--muted); }
.settings-close { width: 40px; height: 40px; border: 0; border-radius: var(--radius); cursor: pointer; font-size: 24px; }
.settings-close:hover { background: var(--raised); }
.settings-callout { border-left: 3px solid var(--accent); padding: 10px 12px; background: var(--surface); color: var(--muted); font-size: 13px; }
.settings-section-label { margin: 0 0 9px; color: #fff; font-size: 13px; }
.settings-root-list { display: grid; gap: 7px; }
.settings-root-row { display: flex; align-items: flex-start; gap: 12px; border: 1px solid var(--line); border-radius: var(--radius); padding: 9px 10px; background: var(--surface); }
.settings-root-path { min-width: 0; flex: 1; overflow-wrap: anywhere; color: #fff; font: 12px/1.5 ui-monospace, monospace; }
.settings-root-warning { display: block; margin-top: 4px; color: var(--danger); font-size: 11px; }
.settings-remove { flex: none; min-height: 36px; border: 0; border-radius: var(--radius); padding: 6px 10px; color: var(--muted); cursor: pointer; }
.settings-remove:hover { background: var(--raised); color: #fff; }
.settings-root-form { display: grid; gap: 8px; margin-top: 14px; }
.settings-root-form label { color: #fff; font-size: 13px; font-weight: 600; }
.settings-add-row { display: grid; grid-template-columns: minmax(0,1fr) auto auto; gap: 8px; }
.settings-root-input { min-width: 0; min-height: 44px; border: 1px solid var(--line); border-radius: var(--radius); padding: 8px 11px; background: var(--surface); }
.settings-helper, .settings-prototype-note { margin: 0; color: var(--muted); font-size: 12px; }
.settings-prototype-note { color: var(--accent-soft); }
.settings-validation { margin: 0; color: var(--danger); font-size: 12px; }
.settings-actions { display: flex; justify-content: flex-end; gap: 8px; border-top: 1px solid var(--line); padding-top: 14px; }
@media (max-width: 900px) { :root { --explorer-width: 300px; } .main-pane { padding-inline: 24px; } }
@media (max-width: 760px) {
  .app-shell { display: block; min-height: calc(100dvh - 64px); }
  .explorer { display: none; height: auto; border: 0; }
  .main-pane { display: block; height: calc(100dvh - 64px); overflow: auto; padding: 16px 16px 36px; }
  body[data-mobile-pane="explorer"] .explorer { display: block; height: calc(100dvh - 64px); }
  body[data-mobile-pane="content"] .explorer { display: none; }
  body[data-mobile-pane="content"] .mobile-explorer-back { display: inline-flex; }
  .resize-handle { display: none; }
  .summary-strip { grid-template-columns: repeat(2, minmax(0,1fr)); }
  .summary-item:nth-child(3) { border-left: 0; border-top: 1px solid var(--line); }
  .summary-item:nth-child(4) { border-top: 1px solid var(--line); }
  .pane-header { align-items: flex-start; }
  .project-row, .activity-row, .feature-row { align-items: flex-start; flex-direction: column; }
  .row-counts { justify-content: flex-start; }
}
@media (max-width: 520px) {
  .app-header { padding-inline: 12px; gap: 6px; }
  .brand-wordmark { font-size: 17px; }
  .brand-wordmark-name { font-size: 14px; }
  .main-pane { padding: 14px 12px 30px; }
  .pane-header { flex-direction: column; }
  .settings-panel { gap: 14px; padding: 18px; }
  .settings-add-row { grid-template-columns: minmax(0,1fr); }
  .settings-add-row .button { width: 100%; }
  .settings-actions { flex-direction: column-reverse; }
}
</style>
</head>
<body data-mobile-pane="content">
<a class="skip-link" href="#main-pane">Skip to main content</a>
<header class="app-header" data-region="app-header">
  <button class="brand" type="button" id="all-projects-link" aria-label="All projects">
    <span class="brand-wordmark"><span class="brand-brace">{</span>ai<span class="brand-brace">}</span><span class="brand-wordmark-name">engineering</span></span>
  </button>
  <div class="header-context" id="header-context" data-region="header-context"></div>
  <button class="button workspace-settings-trigger" type="button" id="open-workspace-settings" data-region="settings-trigger" aria-haspopup="dialog">Settings</button>
</header>

<dialog class="workspace-settings" id="workspace-settings-dialog" data-region="settings-dialog" aria-labelledby="workspace-settings-title">
  <div class="settings-panel">
    <div class="settings-heading-row">
      <div>
        <h2 class="settings-title" id="workspace-settings-title">Workspace settings</h2>
        <p class="settings-description">Choose the folders this workspace searches for repositories.</p>
      </div>
      <button class="settings-close" type="button" id="close-workspace-settings" aria-label="Close settings">×</button>
    </div>
    <div class="settings-callout" data-region="settings-guidance">Repositories are discovered under selected roots. Worktrees come from Git.</div>
    <section aria-labelledby="settings-roots-heading">
      <h3 class="settings-section-label" id="settings-roots-heading">Search roots</h3>
      <div class="settings-root-list" id="settings-root-list" data-region="settings-root-list"></div>
      <form class="settings-root-form" id="settings-root-form" data-region="settings-add-root" novalidate>
        <label for="settings-root-input">Additional folder path</label>
        <div class="settings-add-row">
          <input class="settings-root-input" id="settings-root-input" name="searchRoot" type="text" placeholder="For example, ~/src" autocomplete="off">
          <button class="button" type="submit">Add root</button>
          <button class="button" id="choose-workspace-folder" type="button">Choose folder</button>
        </div>
        <p class="settings-helper">Use a specific folder, such as <code>~/repos</code> or <code>~/src</code>. If folder selection is unavailable, enter an absolute path here.</p>
        <p class="settings-validation" id="settings-validation" data-region="settings-validation" role="alert" hidden></p>
      </form>
    </section>
    <p class="settings-prototype-note" data-region="settings-prototype-note">Manual path entry is available if the native folder chooser is unavailable.</p>
    <div class="settings-actions">
      <button class="button" type="button" id="cancel-workspace-settings">Cancel</button>
      <button class="button primary" type="button" id="save-workspace-settings">Save settings</button>
    </div>
  </div>
</dialog>

<div class="app-shell" id="app-shell">
  <aside class="explorer" data-region="project-explorer" aria-label="Project explorer">
    <div class="explorer-head">
      <h2>Project explorer</h2>
      <span class="root-count" id="root-count">Loading roots</span>
    </div>
    <nav class="tree-nav" id="project-tree" data-region="project-tree" aria-label="Projects, files, and worktrees">
      <div class="tree-loading" id="tree-loading">Loading project roots</div>
    </nav>
  </aside>
  <div class="resize-handle" id="explorer-resize-handle" data-region="explorer-resize-handle" role="separator" tabindex="0" aria-label="Resize project explorer" aria-orientation="vertical" aria-valuemin="240" aria-valuemax="520" aria-valuenow="344"></div>
  <main class="main-pane" id="main-pane" data-region="main-pane">
    <div class="action-feedback" id="action-feedback" data-region="action-feedback" role="status" aria-live="polite" hidden></div>
    <button class="mobile-explorer-back" type="button" id="mobile-explorer-back" data-region="mobile-explorer-back">← Explorer</button>
    <section class="pane-content" id="all-projects-view" data-region="all-projects-view" hidden></section>
    <section class="pane-content" id="project-overview-view" data-region="project-overview" hidden></section>
    <section class="state-panel" id="loading-state" data-region="loading-state" aria-label="Loading projects">
      <p class="pane-eyebrow">Project explorer</p>
      <h1>Loading local projects</h1>
      <div class="skeleton-line"></div><div class="skeleton-line short"></div>
      <div class="skeleton-row"></div><div class="skeleton-row"></div>
    </section>
    <section class="state-panel" id="empty-state" data-region="empty-state" hidden>
      <p class="pane-eyebrow">Project explorer</p>
      <h1>No AI Engineering-governed projects found</h1>
      <p>No governed repositories were found under the configured roots. Repositories appear here after AI Engineering governance is established.</p>
    </section>
    <section class="state-panel" id="error-state" data-region="error-state" role="alert" hidden>
      <p class="pane-eyebrow">Project explorer</p>
      <h1>Local project roots could not be loaded</h1>
      <p class="error-copy" id="error-message">The hub cannot read its local project list. No worktree or feature has been marked as closed.</p>
      <button class="button primary" id="retry" type="button">Try again</button>
    </section>
  </main>
</div>

<script>
const $ = (id) => document.getElementById(id);
const STATUS_LABELS = {
  "needs-review": "Needs review",
  "in-progress": "In progress",
  blocked: "Blocked",
  closed: "Closed",
  unknown: "Unknown"
};
const STATUS_FILTERS = [
  ["all", "All projects"],
  ["needs-review", "Needs review"],
  ["in-progress", "In progress"],
  ["blocked", "Blocked"],
  ["closed", "Closed"],
  ["unknown", "Unknown"]
];
let projects = [];
let savedRoots = [];
let draftRoots = [];
let rootErrors = [];
let selectedProject = null;
let selectedProjectPage = "overview";
let selectedHistorySlug = null;
let selectedFilter = "all";
let expandedProjects = new Set();
let expandedProjectGroups = new Set();
let feedbackTimer;

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[character]);
}

function projectName(path) {
  return path.replace(/[\\/]+$/, "").split(/[\\/]/).pop() || path;
}

function statusLabel(status) {
  return STATUS_LABELS[status] || "Unknown";
}

function statusBadge(status) {
  const safeStatus = STATUS_LABELS[status] ? status : "unknown";
  return `<span class="status-badge ${safeStatus}">${statusLabel(safeStatus)}</span>`;
}

async function requestJson(path, options = {}) {
  const response = await fetch(path, { cache: "no-store", ...options });
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error(`The workspace returned an unreadable response (${response.status}).`);
  }
  if (!response.ok) throw new Error(payload.error || `The workspace request failed (${response.status}).`);
  return payload;
}

function showMainView(id) {
  for (const viewId of ["all-projects-view", "project-overview-view", "loading-state", "empty-state", "error-state"]) {
    $(viewId).hidden = viewId !== id;
  }
  const cameFromExplorer = $("project-tree").contains(document.activeElement);
  document.body.dataset.mobilePane = "content";
  window.scrollTo(0, 0);
  $("main-pane").scrollTop = 0;
  if (cameFromExplorer && window.matchMedia("(max-width: 760px)").matches) {
    $("mobile-explorer-back").focus({ preventScroll: true });
  }
}

function showFeedback(message) {
  const feedback = $("action-feedback");
  feedback.textContent = message;
  feedback.hidden = false;
  clearTimeout(feedbackTimer);
  feedbackTimer = setTimeout(() => { feedback.hidden = true; }, 5000);
}

function currentProjectData() {
  return projects.find((project) => project.path === selectedProject);
}

function projectCounts(project) {
  return {
    worktrees: project.worktrees.length,
    needsYou: project.worktrees.filter((item) => ["needs-review", "blocked", "unknown"].includes(item.status)).length,
    history: project.history.length
  };
}

function allWorktrees() {
  return projects.flatMap((project) => project.worktrees.map((item) => ({ ...item, projectPath: project.path })));
}

function renderProjectTree() {
  const tree = $("project-tree");
  const activeButton = tree.contains(document.activeElement)
    ? document.activeElement.closest("button[data-action]")
    : null;
  const focusTarget = activeButton && {
    action: activeButton.dataset.action,
    project: activeButton.dataset.project,
    group: activeButton.dataset.group,
    label: activeButton.getAttribute("aria-label")
  };
  tree.replaceChildren();
  const all = document.createElement("button");
  all.type = "button";
  all.className = "tree-button";
  all.dataset.action = "all-projects";
  all.setAttribute("aria-current", selectedProject === null ? "page" : "false");
  all.innerHTML = `<span aria-hidden="true">⌂</span><span class="tree-label">All projects</span><span class="tree-count">${projects.length}</span>`;
  tree.append(all);

  for (const [projectIndex, project] of projects.entries()) {
    const isExpanded = expandedProjects.has(project.path);
    const name = projectName(project.path);
    const group = document.createElement("div");
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "tree-button";
    toggle.dataset.action = "toggle-project";
    toggle.dataset.project = project.path;
    toggle.setAttribute("aria-expanded", String(isExpanded));
    toggle.setAttribute("aria-controls", `project-children-${projectIndex}`);
    toggle.setAttribute("aria-label", `${isExpanded ? "Collapse" : "Expand"} project ${name}`);
    toggle.innerHTML = `<span aria-hidden="true">${isExpanded ? "▾" : "▸"}</span><span class="tree-label">${escapeHtml(name)}</span><span class="tree-count">${project.worktrees.length}</span>`;
    group.append(toggle);
    const children = document.createElement("div");
    children.className = "tree-children";
    children.id = `project-children-${projectIndex}`;
    children.hidden = !isExpanded;
    if (isExpanded) {
      const overview = document.createElement("button");
      overview.type = "button";
      overview.className = "tree-button tree-child";
      overview.dataset.action = "open-project";
      overview.dataset.project = project.path;
      overview.setAttribute("aria-current", selectedProject === project.path && selectedProjectPage === "overview" ? "page" : "false");
      overview.setAttribute("aria-label", `Open overview for ${name}`);
      overview.innerHTML = `<span aria-hidden="true">⌂</span><span class="tree-label">Overview</span>`;
      children.append(overview);

      const treeGroups = [
        { id: "files", label: "Project files", icon: "▱", items: [] },
        { id: "worktrees", label: "Worktrees", icon: "⑂", items: project.worktrees },
        { id: "history", label: "History", icon: "◷", items: project.history }
      ];
      for (const treeGroup of treeGroups) {
        const groupKey = `${project.path}:${treeGroup.id}`;
        const isGroupExpanded = expandedProjectGroups.has(groupKey);
        const groupSection = document.createElement("div");
        groupSection.className = "tree-group";
        const groupToggle = document.createElement("button");
        groupToggle.type = "button";
        groupToggle.className = "tree-button tree-group-button";
        groupToggle.dataset.action = "toggle-group";
        groupToggle.dataset.project = project.path;
        groupToggle.dataset.group = treeGroup.id;
        groupToggle.setAttribute("aria-expanded", String(isGroupExpanded));
        groupToggle.setAttribute("aria-controls", `project-${projectIndex}-${treeGroup.id}`);
        groupToggle.setAttribute("aria-label", `${isGroupExpanded ? "Collapse" : "Expand"} ${treeGroup.label.toLowerCase()} for ${name}`);
        groupToggle.innerHTML = `<span aria-hidden="true">${treeGroup.icon}</span><span class="tree-label">${treeGroup.label}</span>${treeGroup.id === "files" ? "" : `<span class="tree-count">${treeGroup.items.length}</span>`}`;

        const groupItems = document.createElement("div");
        groupItems.className = "tree-group-children";
        groupItems.id = `project-${projectIndex}-${treeGroup.id}`;
        groupItems.hidden = !isGroupExpanded;
        if (treeGroup.id === "files") {
          for (const fileName of ["brainstorm.html", "PRD.html"]) {
            const file = document.createElement("div");
            file.className = "tree-entry tree-child";
            file.innerHTML = `<span aria-hidden="true">▤</span><span class="tree-label">${fileName}</span>`;
            groupItems.append(file);
          }
        } else {
          for (const item of treeGroup.items) {
            const worktree = document.createElement("button");
            const isHistoryItem = treeGroup.id === "history";
            worktree.type = "button";
            worktree.className = "tree-button tree-child";
            worktree.dataset.action = isHistoryItem ? "open-history" : "open-project";
            worktree.dataset.project = project.path;
            worktree.dataset.slug = item.slug;
            worktree.setAttribute(
              "aria-current",
              isHistoryItem && selectedProject === project.path && selectedProjectPage === "history" && selectedHistorySlug === item.slug ? "page" : "false",
            );
            worktree.setAttribute(
              "aria-label",
              `${isHistoryItem ? "Open history for" : "Open worktree"} ${item.branch || item.slug} in ${name}. Status: ${statusLabel(item.status)}`,
            );
            worktree.innerHTML = `<span aria-hidden="true">${treeGroup.icon}</span><span class="tree-label">${escapeHtml(item.branch || item.slug)}</span><span class="tree-status">${statusLabel(item.status)}</span>`;
            groupItems.append(worktree);
          }
          if (treeGroup.items.length === 0) {
            const empty = document.createElement("span");
            empty.className = "tree-entry";
            empty.textContent = treeGroup.id === "worktrees" ? "No active worktrees" : "No closed features";
            groupItems.append(empty);
          }
        }
        groupSection.append(groupToggle, groupItems);
        children.append(groupSection);
      }
    }
    group.append(children);
    tree.append(group);
  }
  if (focusTarget) {
    const buttons = [...tree.querySelectorAll("button[data-action]")];
    const matchesActionAndProject = (button) =>
      button.dataset.action === focusTarget.action
      && button.dataset.project === focusTarget.project
      && button.dataset.group === focusTarget.group;
    const replacement = buttons.find((button) =>
      matchesActionAndProject(button) && button.getAttribute("aria-label") === focusTarget.label
    ) || buttons.find(matchesActionAndProject) || buttons[0];
    replacement?.focus({ preventScroll: true });
  }
}

function renderSummary(projectCount, worktreeCount, attentionCount, historyCount) {
  return `<div class="summary-strip surface" data-region="summary">
    <div class="summary-item"><span class="summary-value">${projectCount}</span><span class="summary-label">Project roots</span></div>
    <div class="summary-item"><span class="summary-value">${worktreeCount}</span><span class="summary-label">Worktrees</span></div>
    <div class="summary-item attention"><span class="summary-value">${attentionCount}</span><span class="summary-label">Needs you</span></div>
    <div class="summary-item"><span class="summary-value">${historyCount}</span><span class="summary-label">History</span></div>
  </div>`;
}

function renderDiagnostics(messages) {
  const uniqueMessages = [...new Set(messages)];
  if (uniqueMessages.length === 0) return "";
  return `<details class="workspace-diagnostics"><summary>Workspace evidence issues (${uniqueMessages.length})</summary><ul>${uniqueMessages.map((message) => `<li>${escapeHtml(message)}</li>`).join("")}</ul></details>`;
}

function renderAllProjects() {
  const items = allWorktrees();
  const active = items.filter((item) => item.status !== "closed");
  const attention = items.filter((item) => ["needs-review", "blocked", "unknown"].includes(item.status));
  const historyCount = projects.reduce((count, project) => count + project.history.length, 0);
  const allErrors = [
    ...rootErrors.map((entry) => `${entry.root}: ${entry.detail}`),
    ...projects.flatMap((project) => project.errors.map((message) => `${project.path}: ${message}`))
  ];
  $("all-projects-view").innerHTML = `
    <header class="pane-header">
      <div><p class="pane-eyebrow">Project activity</p><h1>All projects</h1><p class="pane-subtitle">Projects discovered under your selected roots, with worktree status from Git and checkpoint evidence.</p></div>
      <button class="button" type="button" data-action="refresh">Refresh</button>
    </header>
    ${renderDiagnostics(allErrors)}
    ${renderSummary(projects.length, active.length, attention.length, historyCount)}
    <section class="content-section" data-region="project-roots">
      <div class="section-heading"><h2>Project roots</h2><span>${projects.length} projects</span></div>
      <div class="project-list surface">${projects.length ? projects.map((project) => {
        const counts = projectCounts(project);
        return `<button class="project-row" type="button" data-action="open-project" data-project="${escapeHtml(project.path)}" aria-label="Open project overview for ${escapeHtml(projectName(project.path))}">
          <span><span class="project-name">${escapeHtml(projectName(project.path))}</span><span class="project-path">${escapeHtml(project.path)}</span></span>
          <span class="row-counts"><span>${counts.worktrees} worktrees</span><span>${counts.needsYou} need you</span><span>${counts.history} closed</span></span>
        </button>`;
      }).join("") : `<p class="empty-inline">No AI Engineering-governed projects found under the configured roots.</p>`}</div>
    </section>
    <section class="content-section" data-region="attention-list">
      <div class="section-heading"><h2>Needs your attention</h2><span>${attention.length} items</span></div>
      <div class="activity-list surface">${attention.length ? attention.map((item) => `<button class="activity-row" type="button" data-action="open-project" data-project="${escapeHtml(item.projectPath)}">
        <span><strong>${escapeHtml(item.branch || item.slug)}</strong><span class="feature-path">${escapeHtml(projectName(item.projectPath))}</span></span>${statusBadge(item.status)}
      </button>`).join("") : `<p class="empty-inline">No work needs your attention.</p>`}</div>
    </section>`;
  showMainView("all-projects-view");
}

function worktreeEmptyMessage(project, filter) {
  if (project.worktrees.length === 0 || filter === "all") {
    return "No worktrees are present for this project.";
  }
  return `No worktrees match the ${STATUS_LABELS[filter]} filter.`;
}

function renderWorktreeRows(project, worktrees, emptyMessage) {
  return worktrees.length ? worktrees.map((item) => `<button class="feature-row" type="button" data-action="open-project" data-project="${escapeHtml(project.path)}" aria-label="Open worktree ${escapeHtml(item.branch || item.slug)} in ${escapeHtml(projectName(project.path))}. Status: ${statusLabel(item.status)}">
      <span><strong>${escapeHtml(item.branch || item.slug)}</strong><span class="feature-path">${escapeHtml(item.worktreePath || item.path || "")}</span></span>${statusBadge(item.status)}
    </button>`).join("") : `<p class="empty-inline">${escapeHtml(emptyMessage)}</p>`;
}

function renderProjectOverview() {
  const project = currentProjectData();
  if (!project) return showAllProjects(false);
  const counts = projectCounts(project);
  const visibleWorktrees = selectedFilter === "all"
    ? project.worktrees
    : project.worktrees.filter((item) => item.status === selectedFilter);
  const shouldRestoreFilterFocus = $("project-overview-view").contains(document.activeElement)
    && document.activeElement.id === "worktree-status-filter";
  const errors = renderDiagnostics(project.errors);
  $("project-overview-view").innerHTML = `
    <div class="pane-toolbar"><span class="breadcrumb"><button type="button" data-action="all-projects">All projects</button> <span aria-hidden="true">/</span> <strong>${escapeHtml(projectName(project.path))}</strong></span>
      <button class="button" type="button" data-action="refresh">Refresh</button></div>
    <header class="project-hero"><p class="pane-eyebrow">Local project root</p><h1>${escapeHtml(projectName(project.path))}</h1><p class="project-root-path">${escapeHtml(project.path)}</p></header>
    ${errors}
    <div class="project-statline surface" data-region="project-summary"><span><strong>${counts.worktrees}</strong> worktrees</span><span><strong>${counts.needsYou}</strong> need you</span><span><strong>${counts.history}</strong> in history</span></div>
    <section class="content-section" data-region="project-documents">
      <div class="section-heading"><h2>Project files</h2><span>.ai-engineering/</span></div>
      <div class="docs-row surface"><span class="doc-item"><span class="file-type">HTML</span>brainstorm.html</span><span class="doc-item"><span class="file-type">HTML</span>PRD.html</span></div>
    </section>
    <section class="content-section" data-region="project-worktrees">
      <div class="section-heading"><h2>Worktrees</h2><label class="filter-control">Filter worktrees
        <select id="worktree-status-filter" aria-label="Filter worktrees by status">${STATUS_FILTERS.map(([value,label]) => `<option value="${value}" ${value === selectedFilter ? "selected" : ""}>${label}</option>`).join("")}</select>
      </label></div>
      <div class="feature-list surface">${renderWorktreeRows(project, visibleWorktrees, worktreeEmptyMessage(project, selectedFilter))}</div>
    </section>
    <section class="content-section" data-region="project-history" id="project-history-section">
      <div class="section-heading"><h2>History</h2><span>${project.history.length} closed</span></div>
      <div class="feature-list surface">${renderWorktreeRows(project, project.history, "No closed worktrees are recorded for this project.")}</div>
    </section>`;
  showMainView("project-overview-view");
  if (shouldRestoreFilterFocus) $("worktree-status-filter").focus({ preventScroll: true });
}

function showAllProjects(updateTree = true) {
  selectedProject = null;
  selectedProjectPage = "overview";
  selectedHistorySlug = null;
  if (updateTree) renderProjectTree();
  renderAllProjects();
}

function showProject(path, page = "overview", historySlug = null) {
  if (!projects.some((project) => project.path === path)) return;
  selectedProject = path;
  selectedProjectPage = page;
  selectedHistorySlug = page === "history" ? historySlug : null;
  expandedProjects.add(path);
  renderProjectTree();
  renderProjectOverview();
}

function renderWorkspaceRoots(focusTarget = null) {
  const list = $("settings-root-list");
  if (focusTarget === null) {
    const focusedRoot = document.activeElement?.dataset.removeRoot;
    if (focusedRoot !== undefined) {
      focusTarget = { root: focusedRoot, index: draftRoots.indexOf(focusedRoot) };
    }
  }
  list.replaceChildren();
  for (const root of draftRoots) {
    const warning = rootErrors.find((entry) => entry.root === root);
    const row = document.createElement("div");
    row.className = "settings-root-row";
    const path = document.createElement("span");
    path.className = "settings-root-path";
    path.textContent = root;
    if (warning) {
      const detail = document.createElement("span");
      detail.className = "settings-root-warning";
      detail.textContent = `Needs attention: ${warning.detail}`;
      path.append(detail);
    }
    const remove = document.createElement("button");
    remove.className = "settings-remove";
    remove.type = "button";
    remove.textContent = "Remove";
    remove.setAttribute("aria-label", `Remove ${root}`);
    remove.dataset.removeRoot = root;
    row.append(path, remove);
    list.append(row);
  }
  if (focusTarget) {
    const nextRoot = draftRoots.includes(focusTarget.root)
      ? focusTarget.root
      : draftRoots[Math.max(0, Math.min(focusTarget.index, draftRoots.length - 1))];
    const removeButtons = [...list.querySelectorAll("button[data-remove-root]")];
    const replacement = removeButtons.find((button) => button.dataset.removeRoot === nextRoot);
    (replacement || $("settings-root-input")).focus({ preventScroll: true });
  }
}

function showSettingsError(message) {
  $("settings-root-input").setAttribute("aria-invalid", "true");
  $("settings-root-input").setAttribute("aria-describedby", "settings-validation");
  const validation = $("settings-validation");
  validation.textContent = message;
  validation.hidden = false;
}

function clearSettingsError() {
  $("settings-root-input").removeAttribute("aria-invalid");
  $("settings-root-input").removeAttribute("aria-describedby");
  const validation = $("settings-validation");
  validation.textContent = "";
  validation.hidden = true;
}

function openWorkspaceSettings() {
  draftRoots = [...savedRoots];
  renderWorkspaceRoots();
  $("settings-root-input").value = "";
  clearSettingsError();
  $("workspace-settings-dialog").showModal();
  $("settings-root-input").focus();
}

function closeWorkspaceSettings() {
  const dialog = $("workspace-settings-dialog");
  if (dialog.open) dialog.close();
  draftRoots = [...savedRoots];
  renderWorkspaceRoots();
  clearSettingsError();
}

function addRootFromInput(event) {
  event.preventDefault();
  const field = $("settings-root-input");
  const root = field.value.trim().replace(/[\\/]+$/, "");
  const normalized = field.value.replace(/\\/g, "/");
  if (normalized.split("/").some((part) => part === ".." || part === ".")) {
    showSettingsError("Parent-directory segments are not allowed in a search root.");
    field.focus();
    return;
  }
  if (!root || !(root.startsWith("/") || /^[A-Za-z]:[\\/]/.test(root) || /^\\\\[^\\]+\\[^\\]+/.test(root) || root.startsWith("~/") || root.startsWith("~\\")) || root === "/") {
    showSettingsError("Enter a specific absolute folder path, not a filesystem root.");
    field.focus();
    return;
  }
  const normalize = (value) => value.replace(/\\/g, "/").replace(/\/+$/, "").toLowerCase();
  if (draftRoots.some((entry) => normalize(entry) === normalize(root))) {
    showSettingsError("That search root is already listed.");
    field.focus();
    return;
  }
  draftRoots.push(root);
  renderWorkspaceRoots();
  field.value = "";
  clearSettingsError();
  field.focus();
}

async function chooseWorkspaceFolder() {
  const button = $("choose-workspace-folder");
  button.disabled = true;
  clearSettingsError();
  try {
    const result = await requestJson("/api/settings/pick", { method: "POST" });
    if (result.path === null) return;
    $("settings-root-input").value = result.path;
    $("settings-root-input").focus();
  } catch (error) {
    showSettingsError(`${error.message} Enter an absolute path manually if folder selection is unavailable.`);
    $("settings-root-input").focus();
  } finally {
    button.disabled = false;
  }
}

async function saveWorkspaceSettings() {
  const button = $("save-workspace-settings");
  button.disabled = true;
  clearSettingsError();
  try {
    const result = await requestJson("/api/settings", {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ roots: draftRoots })
    });
    savedRoots = result.roots;
    closeWorkspaceSettings();
    await loadWorkspace(false);
    showFeedback("Settings updated.");
  } catch (error) {
    showSettingsError(error.message);
  } finally {
    button.disabled = false;
  }
}

async function loadWorkspace(showLoading = true) {
  if (showLoading) showMainView("loading-state");
  try {
    const [projectResponse, settingsResponse] = await Promise.all([
      requestJson("/api/projects"),
      requestJson("/api/settings")
    ]);
    savedRoots = settingsResponse.roots;
    rootErrors = projectResponse.errors || [];
    projects = await Promise.all(projectResponse.projects.map(async (entry) => {
      const [worktreeResult, historyResult] = await Promise.all([
        requestJson(`/api/worktrees?project=${encodeURIComponent(entry.path)}&status=all`),
        requestJson(`/api/history?project=${encodeURIComponent(entry.path)}`)
      ]);
      return {
        path: entry.path,
        worktrees: worktreeResult.worktrees,
        history: historyResult.history,
        errors: [
          ...(entry.errors || []),
          ...(worktreeResult.errors || []),
          ...(historyResult.errors || [])
        ]
      };
    }));
    $("root-count").textContent = `${savedRoots.length} ${savedRoots.length === 1 ? "root" : "roots"}`;
    $("tree-loading")?.remove();
    renderProjectTree();
    if (projects.length === 0 && rootErrors.length === 0) {
      showMainView("empty-state");
      return;
    }
    showAllProjects(false);
  } catch (error) {
    $("error-message").textContent = `${error.message} No worktree or feature has been marked as closed.`;
    showMainView("error-state");
  }
}

async function refreshWorkspace() {
  try {
    await requestJson("/api/refresh", { method: "POST" });
    await loadWorkspace(false);
    showFeedback("Workspace refreshed.");
  } catch (error) {
    showFeedback(`Refresh failed: ${error.message}`);
  }
}

function handleProjectTreeClick(event) {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  if (button.dataset.action === "toggle-project") {
    const path = button.dataset.project;
    if (expandedProjects.has(path)) expandedProjects.delete(path);
    else expandedProjects.add(path);
    renderProjectTree();
  } else if (button.dataset.action === "toggle-group") {
    const groupKey = `${button.dataset.project}:${button.dataset.group}`;
    if (expandedProjectGroups.has(groupKey)) expandedProjectGroups.delete(groupKey);
    else expandedProjectGroups.add(groupKey);
    renderProjectTree();
  } else if (button.dataset.action === "open-project") {
    showProject(button.dataset.project);
  } else if (button.dataset.action === "open-history") {
    showProject(button.dataset.project, "history", button.dataset.slug);
  } else if (button.dataset.action === "all-projects") {
    showAllProjects();
  }
}

$("project-tree").addEventListener("click", handleProjectTreeClick);

document.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button || $("project-tree").contains(button)) return;
  if (button.dataset.action === "open-project") showProject(button.dataset.project);
  if (button.dataset.action === "open-history") showProject(button.dataset.project, "history", button.dataset.slug);
  if (button.dataset.action === "all-projects") showAllProjects();
  if (button.dataset.action === "refresh") void refreshWorkspace();
});

$("all-projects-link").addEventListener("click", () => showAllProjects());
$("open-workspace-settings").addEventListener("click", openWorkspaceSettings);
$("settings-root-form").addEventListener("submit", addRootFromInput);
$("choose-workspace-folder").addEventListener("click", () => void chooseWorkspaceFolder());
$("settings-root-list").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-remove-root]");
  if (!button) return;
  const focusTarget = { root: button.dataset.removeRoot, index: draftRoots.indexOf(button.dataset.removeRoot) };
  draftRoots = draftRoots.filter((root) => root !== button.dataset.removeRoot);
  renderWorkspaceRoots(focusTarget);
  clearSettingsError();
});
$("save-workspace-settings").addEventListener("click", () => void saveWorkspaceSettings());
$("cancel-workspace-settings").addEventListener("click", closeWorkspaceSettings);
$("close-workspace-settings").addEventListener("click", closeWorkspaceSettings);
$("workspace-settings-dialog").addEventListener("cancel", () => {
  draftRoots = [...savedRoots];
  clearSettingsError();
});
$("workspace-settings-dialog").addEventListener("click", (event) => {
  if (event.target === $("workspace-settings-dialog")) closeWorkspaceSettings();
});
$("retry").addEventListener("click", () => void loadWorkspace(true));
$("mobile-explorer-back").addEventListener("click", () => {
  document.body.dataset.mobilePane = "explorer";
  const active = $("project-tree").querySelector('[aria-current="page"]') || $("project-tree").querySelector("button");
  active?.focus({ preventScroll: true });
});
$("project-overview-view").addEventListener("change", (event) => {
  if (event.target.id !== "worktree-status-filter") return;
  selectedFilter = event.target.value;
  renderProjectOverview();
});

const resizeHandle = $("explorer-resize-handle");
function setExplorerWidth(width) {
  const maxWidth = Math.max(240, Math.min(520, window.innerWidth - 360));
  const nextWidth = Math.max(240, Math.min(maxWidth, width));
  document.documentElement.style.setProperty("--explorer-width", `${nextWidth}px`);
  resizeHandle.setAttribute("aria-valuemax", String(maxWidth));
  resizeHandle.setAttribute("aria-valuenow", String(Math.round(nextWidth)));
}
let resizePointerId = null;
let resizePointerOffset = 0;
resizeHandle.addEventListener("pointerdown", (event) => {
  if (event.button !== 0 || window.matchMedia("(max-width: 760px)").matches) return;
  event.preventDefault();
  resizePointerId = event.pointerId;
  resizePointerOffset = event.clientX - resizeHandle.getBoundingClientRect().left;
  resizeHandle.setPointerCapture(event.pointerId);
});
resizeHandle.addEventListener("pointermove", (event) => {
  if (event.pointerId === resizePointerId) setExplorerWidth(event.clientX - resizePointerOffset);
});
function stopResize(event) {
  if (event.pointerId === resizePointerId) resizePointerId = null;
}
resizeHandle.addEventListener("pointerup", stopResize);
resizeHandle.addEventListener("pointercancel", stopResize);
resizeHandle.addEventListener("keydown", (event) => {
  const currentWidth = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--explorer-width"));
  if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
    event.preventDefault();
    setExplorerWidth(currentWidth + (event.key === "ArrowLeft" ? -16 : 16));
  }
});
if (!window.matchMedia("(max-width: 760px)").matches) {
  setExplorerWidth(parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--explorer-width")));
}
window.addEventListener("resize", () => {
  if (!window.matchMedia("(max-width: 760px)").matches) {
    setExplorerWidth(parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--explorer-width")));
  }
});

void loadWorkspace();
</script>
</body>
</html>
