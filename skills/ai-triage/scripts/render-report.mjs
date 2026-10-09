import { randomUUID } from "node:crypto";
import {
  lstat,
  mkdtemp,
  open,
  readFile,
  rename,
  rmdir,
  unlink,
} from "node:fs/promises";
import { join } from "node:path";

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
const SEVERITY_RANK = new Map([
  ["critical", 0],
  ["high", 1],
  ["medium", 2],
  ["low", 3],
]);
const CONFIDENCE_LEVELS = new Set(["HIGH", "MEDIUM", "LOW"]);
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

function isCredentialAssignmentKey(key) {
  const normalizedKey = key.replace(/([a-z0-9])([A-Z])/g, "$1_$2").toLowerCase();
  const compactKey = normalizedKey.replace(/[_-]/g, "");
  return (
    /(?:token|pat|auth|authorization|bearer|password|passwd|secret|credential|signature)$/.test(
      compactKey,
    ) ||
    /(?:^|[_-])key$/.test(normalizedKey) ||
    /(?:api|access|private|secretaccess)key$/.test(compactKey)
  );
}

function redactCredentialAssignments(value) {
  const assignmentPattern =
    /(?=(\b([A-Za-z][A-Za-z0-9_-]*)\s*[:=]\s*(?:"[^"]*"|'[^']*'|[^\s,;'"<>]+)))/g;
  const replacements = [];
  let replacedUntil = 0;

  for (const match of value.matchAll(assignmentPattern)) {
    const start = match.index;
    const end = start + (match[1]?.length ?? 0);
    if (start < replacedUntil || !isCredentialAssignmentKey(match[2] ?? "")) {
      continue;
    }
    replacements.push({ start, end });
    replacedUntil = end;
  }

  let redactedValue = value;
  for (const { start, end } of replacements.reverse()) {
    redactedValue =
      redactedValue.slice(0, start) +
      "[redacted]" +
      redactedValue.slice(end);
  }
  return redactedValue;
}

function redactAuthentication(value) {
  return redactCredentialAssignments(
    value.replace(/\b(?:Bearer|Basic)\s+[A-Za-z0-9._~+/-]+=*/gi, "[redacted]"),
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

function percentDecodedValues(value) {
  const decodedValues = [];
  let candidate = value;
  let isRawValue = true;
  while (true) {
    decodedValues.push(candidate);
    if (!candidate.includes("%")) return decodedValues;
    if (/%(?![a-f\d]{2})/i.test(candidate)) {
      return !isRawValue && !/%[a-f\d]{2}/i.test(candidate)
        ? decodedValues
        : null;
    }
    let decoded;
    try {
      decoded = decodeURIComponent(candidate);
    } catch {
      return null;
    }
    if (decoded === candidate) return decodedValues;
    candidate = decoded;
    isRawValue = false;
  }
}

function containsAuthentication(value) {
  const candidates = percentDecodedValues(value);
  return (
    candidates === null ||
    candidates.some((candidate) => redactAuthentication(candidate) !== candidate)
  );
}

function containsSensitiveQueryKey(key) {
  const candidates = percentDecodedValues(key);
  return (
    candidates === null ||
    candidates.some((candidate) =>
      /(?:token|auth|password|secret|bearer|credential|api[_-]?key|signature|(?:^|[_-])sig(?:$|[_-]))/i.test(
        candidate,
      ),
    )
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
      [
        value,
        url.protocol,
        url.host,
        url.username,
        url.password,
        url.pathname,
        url.search,
        ...[...url.searchParams.entries()].flat(),
        url.hash,
      ].some(containsAuthentication) ||
      /(?:token|auth|password|secret|credential|api[_-]?key|signature)/i.test(
        url.hash,
      ) ||
      [...url.searchParams.keys()].some(containsSensitiveQueryKey)
    ) {
      return null;
    }
    return value;
  } catch {
    return null;
  }
}

function redactedText(value) {
  if (typeof value !== "string") return "";
  const decodedValues = percentDecodedValues(value);
  if (decodedValues === null) return "[redacted]";
  const redactedValue = redactAuthentication(value);
  if (redactedValue !== value) return redactedValue;
  if (
    decodedValues.some(
      (candidate) => redactAuthentication(candidate) !== candidate,
    )
  ) {
    return "[redacted]";
  }
  return value;
}

function visibleText(value) {
  return escapeHtml(redactedText(value));
}

export function renderAnalysis(value) {
  if (typeof value !== "string") {
    throw new TypeError("Analysis text must be a string");
  }
  const tokens = /`([^`\n]+)`|\[([^\]\n]+)\]\(([^)\s]+)\)|\*\*([^*\n]+)\*\*|\*([^*\n]+)\*/g;
  for (const match of value.matchAll(tokens)) {
    if (match[3] !== undefined && sanitizeEvidenceUrl(match[3]) === null) {
      throw new Error("Invalid analysis link");
    }
  }
  const text = redactedText(value);
  let rendered = "";
  let nextIndex = 0;
  for (const match of text.matchAll(tokens)) {
    rendered += escapeHtml(text.slice(nextIndex, match.index));
    if (match[1] !== undefined) {
      rendered += `<code>${escapeHtml(match[1])}</code>`;
    } else if (match[2] !== undefined) {
      rendered += link(match[2], workItemEvidenceUrl(match[3]));
    } else if (match[4] !== undefined) {
      rendered += `<strong>${escapeHtml(match[4])}</strong>`;
    } else {
      rendered += `<em>${escapeHtml(match[5])}</em>`;
    }
    nextIndex = match.index + match[0].length;
  }
  return rendered + escapeHtml(text.slice(nextIndex));
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
    normalizeComments(item.comments, "work-item comments");
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
    const relatedId =
      url === null
        ? undefined
        : new URL(url).pathname.match(/\/workItems\/(\d+)\/?$/i)?.[1];
    let relatedItem;
    if (relation.relatedItem !== undefined) {
      requireRecord(relation.relatedItem, "related work item");
      if (
        !Number.isSafeInteger(relation.relatedItem.id) ||
        relation.relatedItem.id !== Number(relatedId)
      ) {
        throw new Error("Invalid Azure related work-item ID");
      }
      relatedItem = {
        type: requireText(relation.relatedItem.type, "related work-item type"),
        state: requireText(relation.relatedItem.state, "related work-item state"),
        title: requireText(relation.relatedItem.title, "related work-item title"),
        comments: normalizeComments(
          relation.relatedItem.comments,
          "related work-item comments",
        ),
      };
    }
    relations.push({
      kind: relationKind,
      id: relatedId,
      url: relatedId === undefined ? null : url,
      relatedItem,
    });
  }
  return relations;
}

function normalizeComments(value, label) {
  if (value === undefined) return undefined;
  requireRecord(value, label);
  if (
    !Number.isSafeInteger(value.totalCount) ||
    value.totalCount < 0 ||
    !Array.isArray(value.items) ||
    value.items.length > 5 ||
    value.items.length > value.totalCount
  ) {
    throw new Error(`Invalid Azure report ${label}`);
  }
  const ids = new Set();
  return {
    totalCount: value.totalCount,
    items: value.items.map((comment) => {
      requireRecord(comment, label);
      if (
        !Number.isSafeInteger(comment.id) ||
        comment.id <= 0 ||
        ids.has(comment.id) ||
        typeof comment.text !== "string" ||
        typeof comment.createdDate !== "string" ||
        !Number.isFinite(Date.parse(comment.createdDate))
      ) {
        throw new Error(`Invalid Azure report ${label}`);
      }
      ids.add(comment.id);
      return {
        id: comment.id,
        text: comment.text,
        createdDate: comment.createdDate,
      };
    }),
  };
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
  const whyNow =
    typeof analysis.whyNow === "string" && analysis.whyNow.trim() !== ""
      ? analysis.whyNow
      : "Not assessed; no timing signal supplied.";
  const confidence = CONFIDENCE_LEVELS.has(analysis.confidence)
    ? analysis.confidence
    : "NOT STATED";
  const confidenceBasis =
    typeof analysis.confidenceBasis === "string" &&
    analysis.confidenceBasis.trim() !== ""
      ? analysis.confidenceBasis
      : "No confidence basis provided.";
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
    return { label, url };
  });
  return {
    status: "ASSESSED",
    priority,
    summary,
    whyNow,
    confidence,
    confidenceBasis,
    evidence,
  };
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
  if (safeUrl === null) return visibleText(label);
  return `<a href="${escapeHtml(safeUrl)}" target="_blank" rel="noreferrer noopener">${visibleText(label)}</a>`;
}

function itemUrl(scope, id) {
  if (
    containsAuthentication(scope.organization) ||
    containsAuthentication(scope.project)
  ) {
    return null;
  }
  const project = encodeURIComponent(scope.project);
  return `${scope.organization}/${project}/_workitems/edit/${id}`;
}

function workItemEvidenceUrl(url) {
  const safeUrl = sanitizeEvidenceUrl(url);
  if (safeUrl === null) return null;
  const parsed = new URL(safeUrl);
  const match = parsed.pathname.match(
    /^\/(?:([^/]+)\/)?([^/]+)\/_apis\/wit\/workItems\/(\d+)\/?$/i,
  );
  if (!match?.[2] || !match[3]) return safeUrl;
  if (parsed.hostname.toLowerCase() === "dev.azure.com") {
    if (!match[1]) return safeUrl;
    return `${parsed.origin}/${match[1]}/${match[2]}/_workitems/edit/${match[3]}`;
  }
  if (/^[a-z0-9-]+\.visualstudio\.com$/i.test(parsed.hostname)) {
    if (match[1]) return safeUrl;
    return `${parsed.origin}/${match[2]}/_workitems/edit/${match[3]}`;
  }
  return safeUrl;
}

function typeChip(item) {
  return `<span class="type-chip">${visibleText(item.fields["System.WorkItemType"])}</span>`;
}

function prioritySignals(item) {
  const priority = item.fields["Microsoft.VSTS.Common.Priority"];
  const severity = item.fields["Microsoft.VSTS.Common.Severity"];
  return [
    `Priority ${priority == null ? "not set" : visibleText(String(priority))}`,
    `Severity ${severity == null ? "not set" : visibleText(String(severity))}`,
  ].join(" · ");
}

function azurePriority(item) {
  const fields = item.fields;
  const candidates = [];
  const priority = Number(fields["Microsoft.VSTS.Common.Priority"]);
  if (Number.isInteger(priority) && priority >= 1 && priority <= 4) {
    candidates.push(priority);
  }

  const severity = String(fields["Microsoft.VSTS.Common.Severity"] ?? "")
    .toLowerCase()
    .match(/critical|high|medium|low/);
  const severityRank = severity?.[0] ? SEVERITY_RANK.get(severity[0]) : undefined;
  if (severityRank !== undefined) candidates.push(severityRank);

  return `P${candidates.length === 0 ? 5 : Math.min(...candidates)}`;
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
    : `<span class="band band-${azurePriority(item).toLowerCase()}">${azurePriority(item)}</span>`;
  const area = visibleText(
    typeof fields["System.AreaPath"] === "string"
      ? fields["System.AreaPath"]
      : "Not specified",
  );
  const relationContext = relations.length === 0
    ? "No parent or child links were returned."
    : `<div class="tree-list" role="list">${renderHierarchyTree(item, relations, scope)}</div>`;
  const evidence =
    analysis.status === "ASSESSED" && analysis.evidence.length > 0
      ? analysis.evidence
          .map(({ label, url }) => link(label, workItemEvidenceUrl(url)))
          .join(" · ")
      : "No verified evidence links.";
  const summary =
    analysis.status === "ASSESSED"
      ? renderAnalysis(analysis.summary)
      : "This item was inventoried but not assessed.";
  const whyNow =
    analysis.status === "ASSESSED"
      ? renderAnalysis(analysis.whyNow)
      : "Not assessed.";
  const confidence =
    analysis.status === "ASSESSED"
      ? `${visibleText(analysis.confidence)} · ${renderAnalysis(analysis.confidenceBasis)}`
      : "Not assessed.";
  const recentComments = renderRecentComments(item, relations);

  return `<details class="item" id="i${item.id}">
    <summary>${status}${typeChip(item)}<span class="iid">${itemLink}</span><span class="ititle">${title}</span><span class="imeta">${visibleText(fields["System.State"])}</span></summary>
  <div class="ibody">
    <div class="kv"><span class="ilbl">Type</span><span>${visibleText(fields["System.WorkItemType"])}</span></div>
    <div class="kv"><span class="ilbl">Azure priority</span><span>${prioritySignals(item)}</span></div>
    <div class="kv"><span class="ilbl">Analysis</span><span class="analysis">${summary}</span></div>
    <div class="kv"><span class="ilbl">Why now</span><span class="analysis">${whyNow}</span></div>
    <div class="kv"><span class="ilbl">Confidence</span><span class="analysis">${confidence}</span></div>
    <div class="kv"><span class="ilbl">Area</span><span>${area}</span></div>
    <div class="kv"><span class="ilbl">Related context</span><div class="xref">${relationContext}</div></div>
    <div class="kv"><span class="ilbl">Recent comments</span>${recentComments}</div>
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

function renderHierarchyTree(item, relations, scope) {
  const relatedNode = (relation) => ({
    ...relation.relatedItem,
    label: relation.id === undefined ? "work item" : `#${relation.id}`,
    url: relation.relatedItem === undefined ? null : itemUrl(scope, Number(relation.id)),
  });
  return renderHierarchy({
    current: {
      label: `#${item.id}`,
      url: itemUrl(scope, item.id),
      type: item.fields["System.WorkItemType"],
      title: item.fields["System.Title"] ?? `Work item ${item.id}`,
      state: item.fields["System.State"],
    },
    parents: relations.filter((relation) => relation.kind === "Parent").map(relatedNode),
    children: relations.filter((relation) => relation.kind === "Child").map(relatedNode),
  });
}

function renderRecentComments(item, relations) {
  const groups = [
    {
      label: `This item #${item.id}`,
      comments: item.comments,
    },
    ...relations.map((relation) => ({
      label: `${relation.kind} #${relation.id ?? "unknown"}${
        relation.relatedItem?.title ? ` · ${relation.relatedItem.title}` : ""
      }`,
      comments: relation.relatedItem?.comments,
    })),
  ].filter(({ comments }) => (comments?.totalCount ?? 0) > 0);
  if (groups.length === 0) return "No comments were returned for this item or its direct parent/children.";

  return `<div class="comment-list">${groups
    .map(({ label, comments }) => {
      if (comments === undefined) throw new Error("Azure report lost comment context");
      const countLabel =
        comments.totalCount > comments.items.length
          ? `Latest ${comments.items.length} of ${comments.totalCount}`
          : `${comments.totalCount}`;
      return `<div class="comment-group"><strong>${visibleText(label)}</strong><span class="dim"> · ${countLabel} comment${comments.totalCount === 1 ? "" : "s"}</span>${comments.items
        .map(
          (comment) =>
            `<div class="comment-entry"><time>${visibleText(comment.createdDate)}</time><div class="analysis">${visibleText(comment.text)}</div></div>`,
        )
        .join("")}</div>`;
    })
    .join("")}</div>`;
}

export function renderHierarchy({ current, parents = [], children = [] }) {
  const renderNode = (node) => {
    const target = link(node.label, node.url);
    if (node.type === undefined) return target;
    return `<span class="type-chip">${visibleText(node.type)}</span> ${target} <span class="tree-title">${visibleText(node.title)}</span> <span class="tree-state">${visibleText(node.state)}</span>`;
  };
  const parentRows = parents
    .map((node) => `<div class="tree-row tree-parent"><span class="tree-role">Parent</span> ${renderNode(node)}</div>`)
    .join("");
  const childRows = children.length === 0
    ? ""
    : `<div class="tree-children">${children.map((node) => `<div class="tree-row tree-child"><span class="tree-role">Child</span> ${renderNode(node)}</div>`).join("")}</div>`;
  const currentBranch = `<div class="tree-row tree-current"><span class="tree-role">In backlog</span>${renderNode(current)}</div>${childRows}`;
  return `<div class="tree-group" role="listitem">${parentRows}${parents.length === 0 ? currentBranch : `<div class="tree-branch">${currentBranch}</div>`}</div>`;
}

function renderSections(scope, items, analyses, hierarchy) {
  const assessedCount = analyses.filter((analysis) => analysis.status === "ASSESSED").length;
  const unassessedCount = items.length - assessedCount;
  const rankedItems = items
    .map((item, index) => ({ item, index, analysis: analyses[index] }))
    .sort((first, second) => {
      const firstRank =
        first.analysis?.status === "ASSESSED"
          ? (PRIORITY_ORDER.get(azurePriority(first.item)) ?? 5)
          : 6;
      const secondRank =
        second.analysis?.status === "ASSESSED"
          ? (PRIORITY_ORDER.get(azurePriority(second.item)) ?? 5)
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
  <p>Every selected item appears once. Azure priority and severity fields set urgency; workflow states remain unchanged and do not imply priority. Missing priority data appears last.</p>
  <div class="items">${itemsHtml}</div>
</section>

<section id="s03">
  <h2><span class="num">03 · Work item types</span>Types and states</h2>
  <h3>Work item types and states</h3>
  <p>Counts are grouped from the selected backlog inventory. The rows below are type/state summaries, not additional work items.</p>
  ${renderTypeStateTable(items)}
</section>

<section id="s04">
  <h2><span class="num">04 · Method</span>Coverage and method</h2>
  <h3>Method</h3>
  <p>Read-only Azure DevOps Services report for the explicitly selected team backlog level “${visibleText(scope.backlogName)}”. Ranking uses the standard Azure Priority field (1 highest) and Severity field (Critical to Low), taking the strongest signal. Workflow state is displayed verbatim and is not treated as urgency.</p>
  <p>Coverage: ${items.length} inventoried work items, ${assessedCount} assessed, ${unassessedCount} explicitly UNASSESSED. The type/state counts sum to ${items.length}.</p>
</section>`;
  return { date, sections, assessedCount, unassessedCount };
}

function renderTemplate(template, scope, date, sections) {
  if (!/<!-- report-content-start -->[\s\S]*?<!-- report-content-end -->/.test(template)) {
    throw new Error("Triage template is missing report markers");
  }
  const nav = [
    "Snapshot",
    "Ranked work",
    "Work item types",
    "Method",
  ]
    .map(
      (label, index) =>
        `<a href="#s0${index + 1}"><b>0${index + 1}</b>${label}</a>`,
    )
    .join("\n");
  const projectLabel = `${scope.organization}/${scope.project}`;
  const substitutions = new Map([
    ["{{repo}}", visibleText(projectLabel)],
    ["{{date}}", visibleText(date)],
    ["{{title}}", visibleText(`Azure DevOps · ${scope.backlogName}`)],
    [
      "{{subtitle}}",
      visibleText("Complete inventory · read-only triage · related links are context only"),
    ],
    [
      "{{meta}}",
      visibleText(
        `${scope.organization} · ${scope.project} · ${scope.team} · ${scope.backlogName}`,
      ),
    ],
    ["{{footer}}", visibleText("Complete inventory · read-only report")],
  ]);
  return template.replace(
    /<nav>[\s\S]*?<\/nav>|<!-- report-content-start -->[\s\S]*?<!-- report-content-end -->|\{\{(?:repo|date|title|subtitle|meta|footer)\}\}/g,
    (placeholder) => {
      if (placeholder.startsWith("<nav>")) return `<nav>\n${nav}\n</nav>`;
      if (placeholder.startsWith("<!-- report-content-start -->")) return sections;
      return substitutions.get(placeholder) ?? placeholder;
    },
  );
}

export async function atomicWriteReport(
  path,
  contents,
  { writeTemporaryFile, beforeReplace } = {},
) {
  const temporaryDirectory = await mkdtemp(`${path}.${randomUUID()}.tmp-`);
  const temporaryPath = join(temporaryDirectory, "report");
  let handle;
  let ownsTemporaryFile = false;
  let temporaryIdentity;
  try {
    handle = await open(temporaryPath, "wx", 0o600);
    ownsTemporaryFile = true;
    temporaryIdentity = await handle.stat();
    await (writeTemporaryFile ?? ((file, text) => file.writeFile(text, "utf8")))(
      handle,
      contents,
      temporaryPath,
    );
    await handle.sync();
    await beforeReplace?.(temporaryPath, path);
    const stagedFile = await lstat(temporaryPath).catch(() => undefined);
    if (
      stagedFile === undefined ||
      stagedFile.dev !== temporaryIdentity.dev ||
      stagedFile.ino !== temporaryIdentity.ino
    ) {
      throw new Error("Temporary report file changed before replacement");
    }
    await rename(temporaryPath, path);
    await handle.close().catch(() => {});
    handle = undefined;
    await rmdir(temporaryDirectory).catch(() => {});
  } catch (error) {
    if (ownsTemporaryFile && temporaryIdentity !== undefined) {
      const stagedFile = await lstat(temporaryPath).catch(() => undefined);
      if (
        stagedFile?.dev === temporaryIdentity.dev &&
        stagedFile.ino === temporaryIdentity.ino
      ) {
        await unlink(temporaryPath).catch(() => {});
      }
    }
    await handle?.close().catch(() => {});
    await rmdir(temporaryDirectory).catch(() => {});
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
