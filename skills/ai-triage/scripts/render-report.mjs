import { randomUUID } from "node:crypto";
import { open, readFile, rename, unlink } from "node:fs/promises";

const REPORT_PATH = ".ai-engineering/triage.html";
const MAX_CONCURRENT_ANALYSES = 5;
const TEMPLATE_URL = new URL("../../../templates/triage.html.tpl", import.meta.url);
const PRIORITY_ORDER = new Map([
  ["P0", 0],
  ["P1", 1],
  ["P2", 2],
  ["P3", 3],
  ["P4", 4],
  ["P5", 5],
]);
const HIERARCHY_RELATIONS = new Map([
  ["System.LinkTypes.Hierarchy-Reverse", "Parent"],
  ["System.LinkTypes.Hierarchy-Forward", "Child"],
]);

function requireRecord(value, label) {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(`Invalid Azure report ${label}`);
  }
  return value;
}

function requireText(value, label) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`Invalid Azure report ${label}`);
  }
  return value;
}

function requireSegment(value, label) {
  const segment = requireText(value, label);
  if (
    segment === "." ||
    segment === ".." ||
    /[\/\\\u0000-\u001f\u007f]/.test(segment)
  ) {
    throw new Error(`Invalid Azure report ${label}`);
  }
  return segment;
}

function redactAuthentication(value) {
  return value
    .replace(/\b(?:Bearer|Basic)\s+[A-Za-z0-9._~+/-]+=*/gi, "[redacted]")
    .replace(
      /\b(?:access[_-]?token|refresh[_-]?token|id[_-]?token|authorization|password|passwd|client[_-]?secret|api[_-]?key|secret|credential)\s*[:=]\s*(?:"[^"]*"|'[^']*'|[^\s,;]+)/gi,
      "[redacted]",
    )
    .replace(
      /\b(?:gh[pousr]_[A-Za-z0-9_]{10,}|github_pat_[A-Za-z0-9_]{10,}|azdpat_[A-Za-z0-9_]{10,})\b/gi,
      "[redacted]",
    )
    .replace(
      /\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\b/g,
      "[redacted]",
    )
    .replace(
      /\bhttps?:\/\/[^/\s@]+:[^@\s/]+@[^\s"'<>]+/gi,
      "[redacted URL]",
    );
}

export function escapeHtml(value) {
  if (typeof value !== "string") {
    throw new TypeError("HTML text must be a string");
  }
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function sanitizeEvidenceUrl(value) {
  if (
    typeof value !== "string" ||
    !/^https:\/\//i.test(value) ||
    /[\u0000-\u0020\u007f]/.test(value)
  ) {
    return null;
  }

  try {
    const url = new URL(value);
    if (
      url.protocol !== "https:" ||
      !url.hostname ||
      url.username ||
      url.password ||
      /(?:token|auth|password|secret|credential|api[_-]?key|signature)/i.test(
        url.hash,
      ) ||
      [...url.searchParams.keys()].some((key) =>
        /(?:token|auth|password|secret|credential|api[_-]?key|signature|(?:^|[_-])sig(?:$|[_-]))/i.test(
          key,
        ),
      )
    ) {
      return null;
    }
    return value;
  } catch {
    return null;
  }
}

function visibleText(value) {
  return typeof value === "string"
    ? escapeHtml(redactAuthentication(value))
    : "";
}

function validateScope(scope) {
  requireRecord(scope, "scope");
  if (scope.provider !== "azure-devops") {
    throw new Error("Invalid Azure report provider");
  }

  const organization = requireText(scope.organization, "organization");
  let organizationUrl;
  try {
    organizationUrl = new URL(organization);
  } catch {
    throw new Error("Invalid Azure report organization");
  }
  const isAzureHost =
    organizationUrl.hostname === "dev.azure.com" ||
    /^[a-z0-9-]+\.visualstudio\.com$/i.test(organizationUrl.hostname);
  if (
    organizationUrl.protocol !== "https:" ||
    !isAzureHost ||
    organizationUrl.username ||
    organizationUrl.password ||
    organizationUrl.port ||
    organizationUrl.search ||
    organizationUrl.hash ||
    (organizationUrl.hostname === "dev.azure.com" &&
      organizationUrl.pathname.split("/").filter(Boolean).length !== 1) ||
    (organizationUrl.hostname !== "dev.azure.com" &&
      organizationUrl.pathname !== "/" &&
      organizationUrl.pathname !== "")
  ) {
    throw new Error("Invalid Azure report organization");
  }

  return {
    organization: organizationUrl.origin + organizationUrl.pathname.replace(/\/+$/, ""),
    project: requireSegment(scope.project, "project"),
    team: requireSegment(scope.team, "team"),
    backlogId: requireSegment(scope.backlogId, "backlog ID"),
    backlogName: requireText(scope.backlogName, "backlog name"),
  };
}

function validateInventory(inventory) {
  requireRecord(inventory, "inventory");
  if (inventory.complete !== true || !Array.isArray(inventory.items)) {
    throw new Error("Azure inventory is incomplete");
  }

  const ids = new Set();
  for (const item of inventory.items) {
    requireRecord(item, "work item");
    if (!Number.isSafeInteger(item.id) || item.id <= 0 || ids.has(item.id)) {
      throw new Error("Azure inventory contains an invalid or duplicate work-item ID");
    }
    ids.add(item.id);
    requireRecord(item.fields, "work-item fields");
    requireText(item.fields["System.WorkItemType"], "work-item type");
    requireText(item.fields["System.State"], "work-item state");
    if (item.relations !== undefined && !Array.isArray(item.relations)) {
      throw new Error("Invalid Azure report relations");
    }
  }
  return inventory.items;
}

function hierarchyFor(item) {
  const relations = [];
  for (const relation of item.relations ?? []) {
    requireRecord(relation, "work-item relation");
    const relationKind = HIERARCHY_RELATIONS.get(relation.rel);
    if (relationKind === undefined) continue;

    const url = sanitizeEvidenceUrl(relation.url);
    if (url === null) {
      throw new Error("Azure inventory contains an unsafe relationship URL");
    }
    const relatedId = new URL(url).pathname.match(/\/workItems\/(\d+)\/?$/i)?.[1];
    if (relatedId === undefined) {
      throw new Error("Azure inventory contains an invalid relationship URL");
    }
    relations.push({ kind: relationKind, id: relatedId, url });
  }
  return relations;
}

function normalizeAnalysis(analysis, itemId) {
  requireRecord(analysis, "analysis");
  if (
    (analysis.id !== undefined && analysis.id !== itemId) ||
    (analysis.itemId !== undefined && analysis.itemId !== itemId)
  ) {
    throw new Error("Azure analysis does not match its work item");
  }
  if (analysis.status === "UNASSESSED") {
    return { status: "UNASSESSED" };
  }
  if (analysis.status !== "ASSESSED") {
    throw new Error("Azure analysis is missing or has an invalid status");
  }
  const summary = requireText(analysis.summary, "analysis summary");
  const priority =
    typeof analysis.priority === "string" && PRIORITY_ORDER.has(analysis.priority)
      ? analysis.priority
      : "P3";
  if (analysis.evidence !== undefined && !Array.isArray(analysis.evidence)) {
    throw new Error("Invalid Azure analysis evidence");
  }

  const evidence = (analysis.evidence ?? []).map((entry) => {
    requireRecord(entry, "evidence");
    const label = requireText(entry.label, "evidence label");
    const url = sanitizeEvidenceUrl(entry.url);
    if (url === null) {
      throw new Error("Azure analysis contains an unsafe evidence URL");
    }
    return { label, url };
  });
  return { status: "ASSESSED", priority, summary, evidence };
}

async function analyzeInventory(items, analyzeItem) {
  if (typeof analyzeItem !== "function") {
    throw new Error("Azure item analysis is required");
  }
  const analyses = new Array(items.length);
  let nextIndex = 0;
  const worker = async () => {
    while (nextIndex < items.length) {
      const index = nextIndex++;
      const item = items[index];
      if (item === undefined) throw new Error("Azure inventory changed during analysis");
      analyses[index] = normalizeAnalysis(await analyzeItem(item), item.id);
    }
  };
  await Promise.all(
    Array.from(
      { length: Math.min(MAX_CONCURRENT_ANALYSES, items.length) },
      () => worker(),
    ),
  );
  if (analyses.some((analysis) => analysis === undefined)) {
    throw new Error("Azure analysis did not cover the complete inventory");
  }
  return analyses;
}

function link(label, url) {
  const safeUrl = sanitizeEvidenceUrl(url);
  if (safeUrl === null) throw new Error("Refusing an unsafe Azure report link");
  return `<a href="${escapeHtml(safeUrl)}" rel="noreferrer noopener">${visibleText(label)}</a>`;
}

function itemUrl(scope, id) {
  const project = encodeURIComponent(scope.project);
  return `${scope.organization}/${project}/_workitems/edit/${id}`;
}

function renderItem(item, analysis, relations, scope) {
  const fields = item.fields;
  const title = visibleText(
    typeof fields["System.Title"] === "string"
      ? fields["System.Title"]
      : `Work item ${item.id}`,
  );
  const itemLink = link(`#${item.id}`, itemUrl(scope, item.id));
  const status = analysis.status === "UNASSESSED"
    ? '<span class="pill p-dim">UNASSESSED</span>'
    : `<span class="band band-${analysis.priority.toLowerCase()}">${analysis.priority}</span>`;
  const description = visibleText(
    typeof fields["System.Description"] === "string"
      ? fields["System.Description"]
      : "No description provided.",
  );
  const area = visibleText(
    typeof fields["System.AreaPath"] === "string"
      ? fields["System.AreaPath"]
      : "Not specified",
  );
  const relationLinks =
    relations.length === 0
      ? "No parent or child links were returned."
      : relations
          .map(({ kind, id, url }) => `${kind} ${link(`#${id}`, url)}`)
          .join(" · ");
  const evidence =
    analysis.status === "ASSESSED" && analysis.evidence.length > 0
      ? analysis.evidence
          .map(({ label, url }) => link(label, url))
          .join(" · ")
      : "No verified evidence links.";
  const summary =
    analysis.status === "ASSESSED"
      ? visibleText(analysis.summary)
      : "This item was inventoried but not assessed.";

  return `<details class="item" id="i${item.id}">
  <summary>${status}<span class="iid">${itemLink}</span><span class="ititle">${title}</span><span class="imeta">${visibleText(fields["System.State"])}</span></summary>
  <div class="ibody">
    <div class="kv"><span class="ilbl">Type</span><span>${visibleText(fields["System.WorkItemType"])}</span></div>
    <div class="kv"><span class="ilbl">Analysis</span><span>${summary}</span></div>
    <div class="kv"><span class="ilbl">Description</span><span>${description}</span></div>
    <div class="kv"><span class="ilbl">Area</span><span>${area}</span></div>
    <div class="kv"><span class="ilbl">Related context</span><span class="xref">${relationLinks}</span></div>
    <div class="kv"><span class="ilbl">Evidence</span><span class="xref">${evidence}</span></div>
  </div>
</details>`;
}

function renderTypeStateTable(items) {
  const counts = new Map();
  for (const item of items) {
    const type = item.fields["System.WorkItemType"];
    const state = item.fields["System.State"];
    const key = `${type}\u0000${state}`;
    counts.set(key, { type, state, count: (counts.get(key)?.count ?? 0) + 1 });
  }
  const rows = [...counts.values()]
    .sort(
      (first, second) =>
        first.type.localeCompare(second.type) ||
        first.state.localeCompare(second.state),
    )
    .map(
      ({ type, state, count }) =>
        `<tr><td>${visibleText(type)}</td><td>${visibleText(state)}</td><td>${count}</td></tr>`,
    )
    .join("");
  return `<div class="tbl-wrap"><table>
  <thead><tr><th>Work item type</th><th>State</th><th>Inventory count</th></tr></thead>
  <tbody>${rows}</tbody>
</table></div>`;
}

function renderRelatedContext(items, hierarchy) {
  const rows = [];
  items.forEach((item, index) => {
    const relations = hierarchy[index] ?? [];
    for (const relation of relations) {
      rows.push(
        `<li>Work item #${item.id} · ${relation.kind.toLowerCase()} ${link(`#${relation.id}`, relation.url)}</li>`,
      );
    }
  });
  return rows.length === 0
    ? '<p>No parent or child context was returned. Related items are never counted as backlog inventory.</p>'
    : `<p>These links provide hierarchy context only; they do not add work-item rows or change the inventory total.</p><ul>${rows.join("")}</ul>`;
}

function renderSections(scope, items, analyses, hierarchy) {
  const assessedCount = analyses.filter((analysis) => analysis.status === "ASSESSED").length;
  const unassessedCount = items.length - assessedCount;
  const rankedItems = items
    .map((item, index) => ({ item, index, analysis: analyses[index] }))
    .sort((first, second) => {
      const firstRank =
        first.analysis?.status === "ASSESSED"
          ? (PRIORITY_ORDER.get(first.analysis.priority) ?? 3)
          : 6;
      const secondRank =
        second.analysis?.status === "ASSESSED"
          ? (PRIORITY_ORDER.get(second.analysis.priority) ?? 3)
          : 6;
      return firstRank - secondRank || first.index - second.index;
    });
  const itemsHtml = rankedItems
    .map(({ item, index, analysis }) => {
      const itemHierarchy = hierarchy[index];
      if (item === undefined || analysis === undefined || itemHierarchy === undefined) {
        throw new Error("Azure report lost an inventory item");
      }
      return renderItem(item, analysis, itemHierarchy, scope);
    })
    .join("\n");
  const date = new Date().toISOString().slice(0, 10);
  const sections = `<section id="s01">
  <h2><span class="num">01 · Snapshot</span>Backlog snapshot</h2>
  <h3>Azure DevOps scope</h3>
  <div class="stats">
    <div class="stat"><div class="v">${items.length}</div><div class="l">inventory items</div></div>
    <div class="stat"><div class="v">${assessedCount}</div><div class="l">assessed</div></div>
    <div class="stat"><div class="v">${unassessedCount}</div><div class="l">UNASSESSED</div></div>
  </div>
  <p>${visibleText(scope.organization)} · ${visibleText(scope.project)} · ${visibleText(scope.team)} · ${visibleText(scope.backlogName)}</p>
</section>

<section id="s02">
  <h2><span class="num">02 · Ranked work</span>What to work on first</h2>
  <p>Every item in the complete selected-backlog inventory appears once below. Assessed items are ordered by priority; items without a usable assessment remain visible as UNASSESSED.</p>
  <div class="items">${itemsHtml}</div>
</section>

<section id="s03">
  <h2><span class="num">03 · Work item types</span>Types and states</h2>
  <h3>Work item types and states</h3>
  <p>Counts are grouped from the selected backlog inventory. The rows below are type/state summaries, not additional work items.</p>
  ${renderTypeStateTable(items)}
</section>

<section id="s04">
  <h2><span class="num">04 · Related</span>Parent and child context</h2>
  <h3>Related work items</h3>
  ${renderRelatedContext(items, hierarchy)}
</section>

<section id="s05">
  <h2><span class="num">05 · Method</span>Coverage and method</h2>
  <h3>Method</h3>
  <p>Read-only Azure DevOps Services report for the explicitly selected team backlog level “${visibleText(scope.backlogName)}”. The complete inventory was validated before per-item analysis; parent and child links remain context.</p>
  <p>Coverage: ${items.length} inventoried work items, ${assessedCount} assessed, ${unassessedCount} explicitly UNASSESSED. The type/state counts sum to ${items.length}.</p>
</section>`;
  return { date, sections, assessedCount, unassessedCount };
}

function replaceContent(template, startMarker, endMarker, content) {
  const start = template.indexOf(startMarker);
  const end = template.indexOf(endMarker, start + startMarker.length);
  if (start < 0 || end < 0) throw new Error("Triage template is missing report markers");
  return (
    template.slice(0, start) +
    content +
    template.slice(end + endMarker.length)
  );
}

function renderTemplate(template, scope, date, sections) {
  const nav = [
    "Snapshot",
    "Ranked work",
    "Work item types",
    "Related context",
    "Method",
  ]
    .map(
      (label, index) =>
        `<a href="#s0${index + 1}"><b>0${index + 1}</b>${label}</a>`,
    )
    .join("\n");
  let output = template.replace(/<nav>[\s\S]*?<\/nav>/, `<nav>\n${nav}\n</nav>`);
  output = replaceContent(
    output,
    "<!-- report-content-start -->",
    "<!-- report-content-end -->",
    sections,
  );
  const projectLabel = `${scope.organization}/${scope.project}`;
  const substitutions = new Map([
    ["{{repo}}", escapeHtml(projectLabel)],
    ["{{date}}", escapeHtml(date)],
    ["{{title}}", escapeHtml(`Azure DevOps · ${scope.backlogName}`)],
    [
      "{{subtitle}}",
      escapeHtml("Complete inventory · read-only triage · related links are context only"),
    ],
    [
      "{{meta}}",
      escapeHtml(
        `${scope.organization} · ${scope.project} · ${scope.team} · ${scope.backlogName}`,
      ),
    ],
    ["{{footer}}", escapeHtml("Complete inventory · read-only report")],
  ]);
  for (const [placeholder, value] of substitutions) {
    output = output.replaceAll(placeholder, value);
  }
  return output;
}

async function atomicWriteReport(path, contents) {
  const temporaryPath = `${path}.${randomUUID()}.tmp`;
  let handle;
  try {
    handle = await open(temporaryPath, "wx", 0o600);
    await handle.writeFile(contents, "utf8");
    await handle.sync();
    await handle.close();
    handle = undefined;
    await rename(temporaryPath, path);
  } catch (error) {
    await handle?.close().catch(() => {});
    await unlink(temporaryPath).catch(() => {});
    throw error;
  }
}

export async function writeAzureTriageReport({
  scope,
  inventory,
  analyzeItem,
  writeFile = atomicWriteReport,
}) {
  if (typeof writeFile !== "function") {
    throw new Error("Azure report writer is invalid");
  }
  const validatedScope = validateScope(scope);
  const items = validateInventory(inventory);
  const hierarchy = items.map(hierarchyFor);
  const analyses = await analyzeInventory(items, analyzeItem);
  const template = await readFile(TEMPLATE_URL, "utf8");
  const rendered = renderSections(validatedScope, items, analyses, hierarchy);
  const report = renderTemplate(
    template,
    validatedScope,
    rendered.date,
    rendered.sections,
  );

  await writeFile(REPORT_PATH, report);
}
