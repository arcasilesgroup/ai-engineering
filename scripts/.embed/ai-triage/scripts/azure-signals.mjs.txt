const DUE_FIELD = "Microsoft.VSTS.Scheduling.DueDate";
const TARGET_FIELD = "Microsoft.VSTS.Scheduling.TargetDate";
const DAY_MS = 86_400_000;

function gap(status, reason, nextAction = "Retry the selected item's evidence read.") {
  return { status, reason, nextAction };
}

function readGap(read) {
  return gap(read.status, read.reason ?? "evidence-unavailable", read.nextAction);
}

function instant(value) {
  if (typeof value !== "string") return undefined;
  const match = value.match(
    /^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(Z|[+-]\d{2}:\d{2})$/,
  );
  if (!match || Number(match[2]) > 23 || Number(match[3]) > 59 || Number(match[4]) > 59) {
    return undefined;
  }
  const calendar = Date.parse(`${match[1]}T00:00:00Z`);
  const timestamp = Date.parse(value);
  if (
    !Number.isFinite(calendar) || !Number.isFinite(timestamp) ||
    new Date(calendar).toISOString().slice(0, 10) !== match[1]
  ) return undefined;
  return timestamp;
}

export function readAzureFieldMetadata(response) {
  const fields = response?.value;
  if (
    !Array.isArray(fields) ||
    (response.count !== undefined && response.count !== fields.length) ||
    fields.some((field) =>
      typeof field?.referenceName !== "string" || !field.referenceName ||
      typeof field.type !== "string" || !field.type
    ) ||
    new Set(fields.map((field) => field.referenceName)).size !== fields.length
  ) {
    return gap("partial", "invalid-field-metadata", "Retry project field metadata.");
  }
  return {
    status: "complete",
    fields: fields.map(({ referenceName, type }) => ({ referenceName, type })),
  };
}

function continuation(page, workItemId, endpoint, projectId) {
  const token = page.continuationToken;
  const hasToken = token !== undefined && token !== null && token !== "";
  if (hasToken && typeof token !== "string") return false;
  if (page.nextPage === undefined || page.nextPage === null || page.nextPage === "") return true;
  if (!hasToken || typeof page.nextPage !== "string") return false;
  let url;
  try {
    url = new URL(page.nextPage);
  } catch {
    return false;
  }
  if (
    url.protocol !== "https:" || url.username || url.password || url.hash ||
    !url.pathname.endsWith(`/_apis/wit/workItems/${workItemId}/comments`)
  ) return false;
  if (endpoint) {
    const selected = new URL(endpoint);
    const suffix = `/_apis/wit/workItems/${workItemId}/comments`;
    const projectPrefix = selected.pathname.slice(0, -suffix.length);
    const organizationPrefix = projectPrefix.slice(0, projectPrefix.lastIndexOf("/") + 1);
    const hasVerifiedProjectPath = typeof projectId === "string" &&
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(projectId) &&
      url.pathname.startsWith(organizationPrefix) &&
      url.pathname.slice(organizationPrefix.length).toLowerCase() === `${projectId}${suffix}`.toLowerCase();
    if (
      url.origin !== selected.origin ||
      (url.pathname !== selected.pathname && !hasVerifiedProjectPath)
    ) return false;
  }
  const nextToken = url.searchParams.get("continuationToken");
  const version = url.searchParams.get("api-version");
  return (nextToken === null || nextToken === token) &&
    (version === null || version === "7.1-preview.4") &&
    url.searchParams.getAll("continuationToken").length <= 1 &&
    url.searchParams.getAll("api-version").length <= 1;
}

function normalizeComment(comment, workItemId) {
  if (comment?.id !== undefined && comment.commentId !== undefined && comment.id !== comment.commentId) {
    return "conflicting-comment-id";
  }
  const id = comment?.id ?? comment?.commentId;
  if (!Number.isSafeInteger(id) || id <= 0) return "invalid-comment-id";
  if (comment.workItemId !== workItemId) return "comment-item-mismatch";
  if (!Number.isSafeInteger(comment.version) || comment.version <= 0) return "invalid-comment-version";
  if (comment.isDeleted !== undefined && typeof comment.isDeleted !== "boolean") {
    return "invalid-comment-deletion";
  }
  const isDeleted = comment.isDeleted === true;
  if (!isDeleted && typeof comment.text !== "string") return "invalid-comment-text";
  const created = instant(comment.createdDate);
  const modified = instant(comment.modifiedDate);
  if (created === undefined || modified === undefined) return "invalid-comment-date";
  if (modified < created) return "inconsistent-comment-dates";
  return {
    id, workItemId, version: comment.version,
    ...(!isDeleted ? { text: comment.text } : {}),
    createdDate: comment.createdDate,
    modifiedDate: comment.modifiedDate,
    isDeleted,
    ...(!isDeleted ? { sourceId: `comment:${workItemId}:${id}:v${comment.version}` } : {}),
  };
}

export function normalizeAzureDiscussion({ workItemId, read, endpoint, projectId }) {
  const comments = [];
  const ids = new Set();
  const tokens = new Set();
  let totalCount;
  const partial = (reason) => ({
    ...gap("partial", reason, "Retry all comment pages for the selected item."),
    ...(totalCount !== undefined ? { totalCount } : {}),
    comments,
  });
  const pages = read.pages ?? [];
  for (const [index, page] of pages.entries()) {
    if (
      !Array.isArray(page?.comments) ||
      !Number.isSafeInteger(page.totalCount) || page.totalCount < 0 ||
      !Number.isSafeInteger(page.count) || page.count < 0
    ) return partial("invalid-comment-page");
    if (page.count !== page.comments.length) return partial("comment-count-mismatch");
    if (totalCount !== undefined && totalCount !== page.totalCount) return partial("comment-total-drift");
    totalCount = page.totalCount;
    for (const comment of page.comments) {
      const normalized = normalizeComment(comment, workItemId);
      if (typeof normalized === "string") return partial(normalized);
      if (ids.has(normalized.id)) return partial("duplicate-comment-id");
      ids.add(normalized.id);
      comments.push(normalized);
    }
    if (!continuation(page, workItemId, endpoint, projectId)) return partial("contradictory-continuation");
    const token = page.continuationToken;
    if (token) {
      if (tokens.has(token)) return partial("repeated-continuation-token");
      tokens.add(token);
    } else if (index !== pages.length - 1) {
      return partial("contradictory-continuation");
    }
    if (comments.length > totalCount) return partial("comment-count-mismatch");
  }
  if (read.status === "partial" || read.status === "inaccessible") {
    return { ...readGap(read), ...(totalCount !== undefined ? { totalCount } : {}), comments };
  }
  if (!pages.length || pages.at(-1).continuationToken || comments.length !== totalCount) {
    return partial("missing-comment-page");
  }
  return { status: totalCount === 0 ? "absent" : "complete", totalCount, comments };
}

function fieldSource(item, referenceName, sources) {
  const value = item.fields[referenceName];
  if (value === undefined) return undefined;
  const id = `field:${item.id}:r${item.rev}:${referenceName}`;
  if (!sources.some((source) => source.id === id)) {
    sources.push({ id, workItemId: item.id, revision: item.rev, referenceName, value });
  }
  return id;
}

function dateSignal(item, referenceName, observed, sources) {
  const value = item.fields[referenceName];
  const sourceId = fieldSource(item, referenceName, sources);
  const context = { ...(value !== undefined ? { value } : {}), ...(sourceId ? { sourceId } : {}) };
  const nextAction = `Check ${referenceName} on the selected work item.`;
  if (value === undefined) return { ...context, ...gap("absent", "not-returned", nextAction) };
  if (value === null || value === "") return { ...context, ...gap("absent", "unset", nextAction) };
  const timestamp = instant(value);
  if (timestamp === undefined) return { ...context, ...gap("partial", "invalid-date", nextAction) };
  if (timestamp > observed) return { ...context, ...gap("partial", "future-date", nextAction) };
  return { ...context, status: "complete", elapsedDays: Math.floor((observed - timestamp) / DAY_MS) };
}

function itemDates(item, observed, sources) {
  const created = dateSignal(item, "System.CreatedDate", observed, sources);
  let changed = dateSignal(item, "System.ChangedDate", observed, sources);
  if (created.status === "complete" && changed.status === "complete" && instant(changed.value) < instant(created.value)) {
    const { elapsedDays, ...context } = changed;
    changed = {
      ...context,
      ...gap("partial", "changed-before-created", "Check the work item's creation and change timestamps."),
    };
  }
  return { created, changed };
}

function deliverySignals(item, metadata, sources) {
  const fields = metadata.status === "complete" && Array.isArray(metadata.fields) ? metadata.fields : [];
  const entries = [];
  const references = new Set([
    DUE_FIELD, TARGET_FIELD,
    ...fields.filter((field) => field.type === "dateTime" && item.fields[field.referenceName] !== undefined)
      .map((field) => field.referenceName),
    // Without a definition, retain custom context without guessing its type or meaning.
    ...Object.keys(item.fields).filter((referenceName) =>
      referenceName.startsWith("Custom.") &&
      !fields.some((field) => field.referenceName === referenceName)
    ),
  ]);
  // Creation/change timestamps describe age, not delivery context.
  references.delete("System.CreatedDate");
  references.delete("System.ChangedDate");
  for (const referenceName of references) {
    const value = item.fields[referenceName];
    const field = fields.find((candidate) => candidate.referenceName === referenceName);
    const isStandard = referenceName === DUE_FIELD || referenceName === TARGET_FIELD;
    const sourceId = fieldSource(item, referenceName, sources);
    const entry = {
      referenceName, ...(value !== undefined ? { value } : {}),
      semantics: "unrecognized", ...(sourceId ? { sourceId } : {}),
    };
    const nextAction = `Check the definition and value of ${referenceName}.`;
    if (metadata.status !== "complete") {
      entries.push({ ...entry, ...readGap(metadata) });
    } else if (!field) {
      entries.push({ ...entry, ...gap("absent", "unsupported-field", nextAction) });
    } else if (field.type !== "dateTime") {
      entries.push({ ...entry, ...gap("partial", "wrong-field-type", nextAction) });
    } else {
      entry.semantics = isStandard ? (referenceName === DUE_FIELD ? "due" : "forecast") : "unrecognized";
      if (value === undefined) entries.push({ ...entry, ...gap("absent", "not-returned", nextAction) });
      else if (value === null || value === "") entries.push({ ...entry, ...gap("absent", "unset", nextAction) });
      else if (instant(value) === undefined) entries.push({ ...entry, ...gap("partial", "invalid-date", nextAction) });
      else entries.push({ ...entry, status: "complete" });
    }
  }
  if (metadata.status !== "complete") return { ...readGap(metadata), entries };
  const missing = entries.find((entry) => entry.status !== "complete");
  return missing
    ? { ...gap(entries.some((entry) => entry.status === "complete") ? "partial" : missing.status, missing.reason,
        missing.nextAction), entries }
    : { status: "complete", entries };
}

function importanceSignal(item, referenceName, type, metadata, sources) {
  const value = item.fields[referenceName];
  const sourceId = fieldSource(item, referenceName, sources);
  const context = { ...(value !== undefined ? { value } : {}), ...(sourceId ? { sourceId } : {}) };
  const nextAction = `Check the direct parent's ${referenceName} definition and value.`;
  if (metadata.status !== "complete") return { ...context, ...readGap(metadata) };
  const field = metadata.fields?.find((candidate) => candidate.referenceName === referenceName);
  if (!field) return { ...context, ...gap("absent", "unsupported-field", nextAction) };
  if (field.type !== type) return { ...context, ...gap("partial", "wrong-field-type", nextAction) };
  if (value === undefined) return { ...context, ...gap("absent", "not-returned", nextAction) };
  if (value === null || value === "") return { ...context, ...gap("absent", "unset", nextAction) };
  const isValid = type === "integer" ? Number.isSafeInteger(value) && value > 0
    : typeof value === "string" && value.trim().length > 0;
  return { ...context, ...(isValid ? { status: "complete" } : gap("partial", "invalid-value", nextAction)) };
}

function iterationSignal(item, read, observed, sources) {
  if (read.status !== "complete") return readGap(read);
  const path = item.fields["System.IterationPath"];
  if (typeof path !== "string" || !path) {
    return gap("absent", "iteration-path-not-returned", "Check the selected item's iteration path.");
  }
  const response = read.response;
  const value = response?.value;
  const values = response?.values;
  if (value !== undefined && values !== undefined && JSON.stringify(value) !== JSON.stringify(values)) {
    return gap("partial", "conflicting-iteration-envelope", "Retry the selected team's iterations.");
  }
  const iterations = value ?? values;
  if (
    !Array.isArray(iterations) ||
    (response.count !== undefined && response.count !== iterations.length) ||
    iterations.some((iteration) => typeof iteration?.path !== "string" || !iteration.path)
  ) return gap("partial", "invalid-iteration-envelope", "Retry the selected team's iterations.");
  const matches = iterations.filter((iteration) => iteration.path === path);
  if (!matches.length) return gap("absent", "iteration-path-unmatched", "Check the item's path against the selected team's iterations.");
  if (matches.length !== 1) return gap("partial", "duplicate-iteration-path", "Resolve duplicate paths in the selected team's iterations.");
  const iteration = matches[0];
  const timeFrame = iteration.attributes?.timeFrame;
  if (
    typeof iteration.id !== "string" || !iteration.id ||
    typeof iteration.name !== "string" || !iteration.name ||
    (timeFrame !== undefined && !["past", "current", "future"].includes(timeFrame))
  ) {
    return gap("partial", "invalid-iteration-envelope", "Retry the selected team's iterations.");
  }
  const start = iteration.attributes?.startDate;
  const finish = iteration.attributes?.finishDate;
  const sourceId = `iteration:${iteration.id}`;
  const context = { id: iteration.id, path, name: iteration.name, sourceId };
  sources.push({
    id: sourceId, workItemId: item.id, iterationId: iteration.id, path, name: iteration.name,
    ...(typeof start === "string" || start === null ? { startDate: start } : {}),
    ...(typeof finish === "string" || finish === null ? { finishDate: finish } : {}),
    ...(timeFrame !== undefined ? { timeFrame } : {}),
  });
  if (start === undefined || start === null || finish === undefined || finish === null) {
    return { ...context, ...gap("absent", "iteration-dates-unset", "Set or confirm the selected iteration's planning dates.") };
  }
  const startTime = instant(start);
  const finishTime = instant(finish);
  if (
    startTime === undefined || finishTime === undefined ||
    !/T00:00:00(?:\.0+)?Z$/.test(start) || !/T00:00:00(?:\.0+)?Z$/.test(finish)
  ) {
    return { ...context, ...gap("partial", "invalid-iteration-dates", "Check the selected iteration's UTC-midnight dates.") };
  }
  if (finishTime < startTime) {
    return { ...context, ...gap("partial", "reversed-iteration-range", "Correct the selected iteration's planning date range.") };
  }
  const calendarDay = new Date(observed).toISOString().slice(0, 10);
  const startDate = start.slice(0, 10);
  const finishDate = finish.slice(0, 10);
  return {
    ...context, status: "complete", startDate, finishDate,
    ...(timeFrame !== undefined ? { timeFrame } : {}),
    calendarPosition: calendarDay < startDate ? "before" : calendarDay > finishDate ? "after" : "within",
  };
}

export function normalizeAzureSignals({ item, observedAt, discussion, fieldMetadata, iterations, parent }) {
  const observed = instant(observedAt);
  if (observed === undefined) throw new Error("Invalid Azure signal observation timestamp.");
  if (
    !Number.isSafeInteger(item?.id) || item.id <= 0 ||
    !Number.isSafeInteger(item.rev) || item.rev <= 0 ||
    !item.fields || typeof item.fields !== "object" || Array.isArray(item.fields)
  ) throw new Error("Invalid Azure signal work-item revision or fields.");
  const sources = [];
  fieldSource(item, "Microsoft.VSTS.Common.Priority", sources);
  fieldSource(item, "Microsoft.VSTS.Common.Severity", sources);
  fieldSource(item, "System.IterationPath", sources);
  const normalizedDiscussion = normalizeAzureDiscussion({ workItemId: item.id, read: discussion });
  for (const comment of normalizedDiscussion.comments) {
    if (!comment.isDeleted) {
      const { sourceId, isDeleted, ...context } = comment;
      const { id: commentId, ...evidence } = context;
      sources.push({ id: sourceId, commentId, ...evidence });
    }
  }
  const dates = itemDates(item, observed, sources);
  const delivery = deliverySignals(item, fieldMetadata, sources);
  const iteration = iterationSignal(item, iterations, observed, sources);
  let normalizedParent;
  if (parent.status === "absent") {
    normalizedParent = gap("absent", parent.reason ?? "no-direct-parent", parent.nextAction ?? "No direct parent to read.");
  } else if (parent.status !== "complete") {
    normalizedParent = readGap(parent);
  } else if (
    !Number.isSafeInteger(parent.item?.id) || parent.item.id <= 0 ||
    !Number.isSafeInteger(parent.item.rev) || parent.item.rev <= 0 ||
    !parent.item.fields || typeof parent.item.fields !== "object" || Array.isArray(parent.item.fields)
  ) {
    normalizedParent = gap("partial", "parent-details-unavailable", "Retry the direct parent's detail read.");
  } else {
    const parentItem = parent.item;
    const priority = importanceSignal(parentItem, "Microsoft.VSTS.Common.Priority", "integer", fieldMetadata, sources);
    const severity = importanceSignal(parentItem, "Microsoft.VSTS.Common.Severity", "string", fieldMetadata, sources);
    const missingImportance = [priority, severity].find((signal) => signal.status !== "complete");
    normalizedParent = {
      ...(missingImportance ? gap("partial", missingImportance.reason, missingImportance.nextAction) : { status: "complete" }),
      workItemId: parentItem.id,
      importance: { priority, severity },
      ...(priority.status === "complete" ? { priority: priority.value } : {}),
      ...(severity.status === "complete" ? { severity: severity.value } : {}),
      dates: itemDates(parentItem, observed, sources),
      delivery: deliverySignals(parentItem, fieldMetadata, sources),
    };
  }
  if (!normalizedParent.delivery) {
    normalizedParent.delivery = {
      status: normalizedParent.status, reason: normalizedParent.reason,
      nextAction: normalizedParent.nextAction, entries: [],
    };
  }
  const signals = [dates.created, dates.changed, delivery, iteration, normalizedParent];
  if (normalizedParent.dates) {
    signals.push(normalizedParent.dates.created, normalizedParent.dates.changed, normalizedParent.delivery);
  }
  const hasDiscussion = normalizedDiscussion.status === "complete" || normalizedDiscussion.status === "absent";
  const hasEvidence = hasDiscussion || normalizedDiscussion.comments.some((comment) => !comment.isDeleted) ||
    signals.some((signal) => signal.status === "complete") ||
    delivery.entries.some((entry) => entry.status === "complete" && entry.semantics !== "unrecognized");
  const isSufficient = hasDiscussion &&
    signals.every((signal) => signal.status === "complete" || signal.reason === "no-direct-parent");
  return {
    observedAt, discussion: normalizedDiscussion, dates, delivery, iteration, parent: normalizedParent, sources,
    coverage: isSufficient ? "sufficient" : hasEvidence ? "limited" : "not-assessable",
  };
}
