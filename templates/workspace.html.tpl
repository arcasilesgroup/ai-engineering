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
  --surface-raised: #1C2D38;
  --divider: rgba(61, 79, 88, .6);
  --accent: #00ED64;
  --accent-soft: #71F6BA;
  --focus: #0498EC;
  --text: #E8EDEB;
  --heading: #FFFFFF;
  --muted: #C1C7C6;
  --subtle: #C1C7C6;
  --font-sans: "Archivo Variable", "Archivo", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-mono: "JetBrains Mono", "Fira Code", "SF Mono", Consolas, monospace;
  --radius-small: 6px;
  --radius-control: 4px;
  --explorer-width: 344px;
}

* { box-sizing: border-box; }
html { min-width: 320px; background: var(--bg); }
body {
  min-height: 100dvh;
  margin: 0;
  overflow-x: hidden;
  background: var(--bg);
  color: var(--text);
  font: 15px/1.55 var(--font-sans);
  -webkit-font-smoothing: antialiased;
}
button { color: inherit; font: inherit; background: transparent; }
[hidden] { display: none !important; }
:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
.skip-link {
  position: fixed;
  top: 8px;
  left: 8px;
  z-index: 10;
  transform: translateY(-150%);
  border: 1px solid var(--muted);
  border-radius: var(--radius-control);
  padding: 8px 12px;
  background: var(--surface-raised);
  color: var(--text);
}
.skip-link:focus { transform: none; }
.app-header {
  position: sticky;
  top: 0;
  z-index: 3;
  display: flex;
  min-height: 64px;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--divider);
  padding-inline: clamp(16px, 2vw, 28px);
  background: var(--bg);
}
.brand {
  display: inline-flex;
  min-width: 0;
  min-height: 48px;
  align-items: center;
  border: 0;
  border-radius: var(--radius-small);
  margin-left: -8px;
  padding: 4px 8px;
  color: var(--text);
  cursor: pointer;
  text-align: left;
}
.brand-wordmark { display: inline-flex; align-items: baseline; color: var(--heading); font-size: 19px; font-weight: 700; line-height: 1.2; letter-spacing: -.025em; }
.brand-brace { color: var(--accent); }
.brand-wordmark-name { margin-left: 6px; color: var(--text); font-size: 16px; font-weight: 600; }
.header-context:empty { display: none; }
.button {
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: var(--radius-small);
  padding: 9px 14px;
  background: var(--surface-raised);
  cursor: pointer;
  font-size: 14px;
}
.button:hover { background: #263A45; }
.app-shell {
  display: grid;
  grid-template-columns: minmax(240px, var(--explorer-width)) 8px minmax(0, 1fr);
  min-height: calc(100dvh - 64px);
}
.explorer {
  position: sticky;
  top: 64px;
  min-width: 0;
  height: calc(100dvh - 64px);
  overflow: auto;
  border-right: 1px solid var(--divider);
  background: var(--surface);
}
.explorer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 24px 18px 10px;
}
.explorer-head h2 { margin: 0; font-size: 15px; font-weight: 650; }
.root-count { color: var(--subtle); font: 12px/1.4 var(--font-mono); white-space: nowrap; }
.tree-nav { padding: 4px 12px 24px; }
.tree-loading { display: block; padding: 12px 10px; color: var(--muted); font-size: 13px; }
.tree-loading::before { content: "Loading project roots"; }
.tree-loading span { display: none; }
.resize-handle { position: relative; z-index: 2; }
.resize-handle::before { position: absolute; inset: 0 auto 0 3px; width: 1px; background: var(--divider); content: ""; }
.main-pane { min-width: 0; padding: 30px clamp(20px, 3vw, 44px) 64px; overflow-wrap: anywhere; }
.state-panel { max-width: 650px; margin: 48px 0; border: 0; padding: 0; background: transparent; }
.pane-eyebrow { margin: 0 0 8px; color: var(--accent-soft); font-size: 12px; font-weight: 600; }
h1 { margin: 0 0 8px; font-size: 28px; line-height: 1.2; letter-spacing: -.025em; }
.skeleton-line, .skeleton-row { display: none; }
.mobile-explorer-back { display: none; }
@media (max-width: 900px) {
  :root { --explorer-width: 300px; }
  .main-pane { padding-inline: 24px; }
}
@media (max-width: 760px) {
  .app-shell { display: block; min-height: calc(100dvh - 64px); }
  .explorer { display: none; height: auto; border: 0; }
  .main-pane { display: block; height: calc(100dvh - 64px); overflow: auto; padding: 16px 16px 36px; }
  body[data-mobile-pane="explorer"] .explorer { display: block; height: calc(100dvh - 64px); }
  body[data-mobile-pane="content"] .explorer { display: none; }
  body[data-mobile-pane="content"] .mobile-explorer-back { display: inline-flex; }
  .resize-handle { display: none; }
}
@media (max-width: 520px) {
  .app-header { padding-inline: 12px; gap: 6px; }
  .brand-wordmark { font-size: 17px; }
  .brand-wordmark-name { font-size: 14px; }
  .main-pane { padding: 14px 12px 30px; }
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
<div class="app-shell" id="app-shell">
  <aside class="explorer" data-region="project-explorer" aria-label="Project explorer">
    <div class="explorer-head">
      <h2>Project explorer</h2>
      <span class="root-count" id="root-count">3 roots</span>
    </div>
    <nav class="tree-nav" id="project-tree" data-region="project-tree" aria-label="Projects, files, and worktrees">
      <div class="tree-loading"><span></span><span></span><span></span></div>
    </nav>
  </aside>
  <div class="resize-handle" id="explorer-resize-handle" role="separator" aria-label="Resize project explorer" aria-orientation="vertical"></div>
  <main class="main-pane" id="main-pane" data-region="main-pane">
    <button class="mobile-explorer-back" type="button" id="mobile-explorer-back" data-region="mobile-explorer-back">← Explorer</button>
    <section class="pane-content" id="all-projects-view" data-region="all-projects-view" hidden></section>
    <section class="pane-content" id="project-overview-view" data-region="project-overview" hidden></section>
    <section class="pane-content" id="feature-viewer-view" data-region="feature-viewer" hidden></section>
    <section class="pane-content" id="document-view" data-region="document-preview" hidden></section>
    <section class="state-panel" id="loading-state" data-region="loading-state" aria-label="Loading projects">
      <p class="pane-eyebrow">Project explorer</p>
      <h1>Loading local projects</h1>
      <div class="skeleton-line"></div>
      <div class="skeleton-line short"></div>
      <div class="skeleton-row"></div>
      <div class="skeleton-row"></div>
    </section>
    <section class="state-panel" id="empty-state" data-region="empty-state" hidden>
      <p class="pane-eyebrow">Project explorer</p>
      <h1>No local projects found</h1>
      <p>Open the hub from a repository to add its root, then its worktrees and project documents will appear here.</p>
    </section>
    <section class="state-panel error" id="error-state" data-region="error-state" role="alert" hidden>
      <p class="pane-eyebrow">Project explorer</p>
      <h1>Local project roots could not be loaded</h1>
      <p>The hub cannot read its local project list. No worktree or feature has been marked as closed.</p>
      <button class="button primary" id="retry" type="button">Try again</button>
    </section>
  </main>
</div>
</body>
</html>
