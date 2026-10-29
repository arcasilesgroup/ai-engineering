import { azurePriority, sanitizeEvidenceUrl } from "./render-report.mjs";

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

    function invalidClaim() {
      throw new Error("Invalid Azure evidence claim.");
    }

    function claimSources(item, claim) {
      const signals = item.signals;
      return claim.sourceIds.map((id) => {
        const matches = signals.sources.filter((source) => source.id === id);
        if (matches.length !== 1) return invalidClaim();
        const source = matches[0];
        const isParent = source.workItemId === signals.parent.workItemId;
        if (source.workItemId !== item.id && (!isParent || claim.parentId !== source.workItemId)) {
          return invalidClaim();
        }
        if (source.commentId !== undefined) {
          const comment = signals.discussion.comments.find((candidate) =>
            candidate.sourceId === id && !candidate.isDeleted);
          if (
            !comment || source.workItemId !== item.id ||
            id !== `comment:${item.id}:${comment.id}:v${comment.version}` ||
            source.commentId !== comment.id || source.version !== comment.version ||
            source.text !== comment.text || source.createdDate !== comment.createdDate ||
            source.modifiedDate !== comment.modifiedDate
          ) return invalidClaim();
        } else if (source.referenceName !== undefined) {
          if (id !== `field:${source.workItemId}:r${source.revision}:${source.referenceName}`) return invalidClaim();
          if (source.workItemId === item.id &&
            (source.revision !== item.rev || !Object.is(source.value, item.fields[source.referenceName]))) {
            return invalidClaim();
          }
          if (source.workItemId !== item.id) {
            const parent = signals.parent;
            const linkedSignal = [
              parent.importance?.priority, parent.importance?.severity,
              parent.dates?.created, parent.dates?.changed, ...parent.delivery.entries,
            ].find((signal) => signal?.sourceId === id);
            if (!linkedSignal || !Object.is(source.value, linkedSignal.value)) return invalidClaim();
          }
        } else if (source.iterationId !== undefined) {
          if (source.workItemId !== item.id || id !== signals.iteration.sourceId ||
            source.iterationId !== signals.iteration.id || source.path !== signals.iteration.path) {
            return invalidClaim();
          }
        } else return invalidClaim();
        return source;
      });
    }

    export function validateAzureClaims(item, analysis) {
      if (!item?.signals || !Array.isArray(item.signals.sources)) {
        throw new Error("Azure evidence sources are required.");
      }
      if (instant(item.signals.observedAt) === undefined) {
        throw new Error("Invalid Azure evidence observation timestamp.");
      }
      if (!analysis) throw new Error("Azure evidence assessment is required.");
      if ((analysis.id !== undefined && analysis.id !== item.id) ||
        (analysis.itemId !== undefined && analysis.itemId !== item.id)) {
        throw new Error("Azure evidence assessment item mismatch.");
      }
      if (analysis.status === "UNASSESSED") {
        if (analysis.claims !== undefined && (!Array.isArray(analysis.claims) || analysis.claims.length)) {
          return invalidClaim();
        }
        return [];
      }
      if (
        analysis.status !== "ASSESSED" || typeof analysis.summary !== "string" ||
        !analysis.summary.trim() || !Array.isArray(analysis.claims)
      ) return invalidClaim();
      for (const claim of analysis.claims) {
        if (
          !claim || !["blocker", "blocker-resolved", "commitment", "parent-dependency", "context"].includes(claim.type) ||
          !Array.isArray(claim.sourceIds) || !claim.sourceIds.length ||
          claim.sourceIds.some((id) => typeof id !== "string") ||
          new Set(claim.sourceIds).size !== claim.sourceIds.length ||
          !["team-reported", "code-verified"].includes(claim.provenance) ||
          (claim.url !== undefined && sanitizeEvidenceUrl(claim.url) === null)
        ) return invalidClaim();
        const sources = claimSources(item, claim);
        if (claim.parentId !== undefined && (
          claim.parentId !== item.signals.parent.workItemId ||
          !sources.some((source) => source.workItemId === claim.parentId)
        )) return invalidClaim();
        if (claim.type === "parent-dependency" && claim.parentId === undefined) return invalidClaim();
        if (claim.isOutstanding !== undefined && typeof claim.isOutstanding !== "boolean") return invalidClaim();
        if (claim.excerpt !== undefined && (typeof claim.excerpt !== "string" || !claim.excerpt.trim())) {
          return invalidClaim();
        }
        const hasExcerpt = typeof claim.excerpt === "string" && claim.excerpt.trim().length > 0;
        const hasValue = Object.hasOwn(claim, "value");
        if (
          (!hasExcerpt && !hasValue) ||
          (hasExcerpt && !sources.some((source) => typeof source.text === "string" && source.text.includes(claim.excerpt))) ||
          (hasValue && !sources.some((source) => Object.is(source.value, claim.value)))
        ) return invalidClaim();
        if (["blocker", "blocker-resolved", "commitment", "parent-dependency"].includes(claim.type) && !hasExcerpt) {
          return invalidClaim();
        }
        if (["blocker", "blocker-resolved", "commitment", "parent-dependency"].includes(claim.type)) {
          const supportingComments = sources.filter((source) =>
            source.commentId !== undefined && source.text.includes(claim.excerpt));
          if (supportingComments.length !== 1 ||
            instant(supportingComments[0].modifiedDate) > instant(item.signals.observedAt)) return invalidClaim();
        }
        if ((["blocker", "blocker-resolved"].includes(claim.type) || claim.issueId !== undefined) &&
          (typeof claim.issueId !== "string" || !claim.issueId.trim())) return invalidClaim();
        if (claim.type === "commitment" || claim.date !== undefined) {
          const delivery = claim.parentId === undefined ? item.signals.delivery : item.signals.parent.delivery;
          if (instant(claim.date) === undefined || !delivery.entries.some((entry) =>
            entry.status === "complete" && entry.semantics !== "unrecognized" &&
            entry.value === claim.date && claim.sourceIds.includes(entry.sourceId))) return invalidClaim();
        }
        // A Board assertion, even with an HTTPS link, cannot certify a code fact.
        if (claim.provenance === "code-verified") return invalidClaim();
      }
      return analysis.claims;
    }

    function sourceDescription(source) {
      if (source.commentId !== undefined) {
        return `comment #${source.commentId} v${source.version}, created ${source.createdDate}, modified ${source.modifiedDate}: “${source.text}” (team-reported)`;
      }
      if (source.referenceName !== undefined) {
        return `#${source.workItemId} revision ${source.revision} ${source.referenceName}: ${String(source.value)}`;
      }
      return `${source.path} · ${source.startDate ?? "dates unset"} through ${source.finishDate ?? "dates unset"} (planning context)`;
    }

    function claimComment(item, claim) {
      return claimSources(item, claim).find((source) =>
        source.commentId !== undefined && source.text.includes(claim.excerpt));
    }

    function sameIssue(first, second) {
      return first.issueId === undefined || second.issueId === undefined || first.issueId === second.issueId;
    }

    function outstandingChronology(item, reports, updates, matches) {
      const outstanding = [];
      const superseded = [];
      const conflicts = [];
      for (const report of reports) {
        const origin = claimComment(item, report);
        // A renewed report ends historical conflict pairs, but not edits overlapping that renewal.
        if (updates.some((update) => matches(report, update)) &&
          reports.some((renewal) => {
            if (report.issueId === undefined || renewal.issueId !== report.issueId ||
              !matches(report, renewal)) return false;
            const confirmation = claimComment(item, renewal);
            return instant(confirmation.createdDate) === instant(confirmation.modifiedDate) &&
              instant(confirmation.createdDate) > instant(origin.modifiedDate);
          })) continue;
        let hasCounterclaim = false;
        for (const update of updates) {
          if (!matches(report, update)) continue;
          const counterclaim = claimComment(item, update);
          if (instant(counterclaim.modifiedDate) < instant(origin.createdDate)) continue;
          hasCounterclaim = true;
          // Edits expose only the current version, not when its asserted event occurred.
          if (instant(counterclaim.createdDate) > instant(origin.modifiedDate) &&
            instant(counterclaim.createdDate) === instant(counterclaim.modifiedDate)) {
            superseded.push(report, update);
          } else {
            conflicts.push(report, update);
          }
        }
        if (!hasCounterclaim) outstanding.push(report);
      }
      return { outstanding, superseded, conflicts };
    }

    function dependencySupports(item, dependency, commitment) {
      if (dependency.parentId !== commitment.parentId) return false;
      if (dependency.issueId !== undefined && commitment.issueId !== undefined) {
        return dependency.issueId === commitment.issueId;
      }
      // A shared parent field establishes the date, not which delivery requires this child.
      return claimComment(item, dependency).id === claimComment(item, commitment).id;
    }

    export function buildAzureRecommendation(item, analysis) {
      const claims = validateAzureClaims(item, analysis);
      const signals = item.signals;
      const nativePriority = azurePriority(item);
      let dependencyReason = "";
      let dependencyIds = [];
      const advice = (kind, orderGroup, recommendation, nextAction, whyNow, sourceIds = []) => ({
        kind, orderGroup, nativePriority, recommendation, nextAction, whyNow: whyNow + dependencyReason,
        sourceIds: [...new Set([...sourceIds, ...dependencyIds])], coverage: signals.coverage,
      });
      if (analysis.status === "UNASSESSED") {
        return { ...advice("not-assessable", "unassessed", "Not assessable.",
          `Assess the evidence for item #${item.id} before recommending work.`,
          "No justified urgency: this item was inventoried but not assessed."), coverage: "not-assessable" };
      }
      const chronology = outstandingChronology(item,
        claims.filter((claim) => claim.type === "blocker"),
        claims.filter((claim) => claim.type === "blocker-resolved"),
        (report, update) => report.issueId === update.issueId);
      const discussionIsComplete = ["complete", "absent"].includes(signals.discussion.status);
      const references = (selectedClaims) => [...new Set(selectedClaims.flatMap((claim) => claim.sourceIds))];
      const describe = (ids) => ids.map((id) => sourceDescription(signals.sources.find((source) => source.id === id))).join("; ");
      const resolvedIds = discussionIsComplete ? references(chronology.superseded) : [];
      const resolutionReason = resolvedIds.length
        ? ` Blocker ${chronology.superseded[0].issueId} was resolved: ${describe(resolvedIds)}.` : "";
      if (nativePriority === "P0") {
        const source = signals.sources.find((candidate) => candidate.workItemId === item.id &&
          candidate.referenceName === "Microsoft.VSTS.Common.Severity");
        return advice("critical-risk", "critical", "Address critical risk.",
          `Validate the critical risk reported for item #${item.id} before shipping.`,
          `${source ? sourceDescription(source) : "Native Azure critical risk"} calls for validation before shipping.`,
          source ? [source.id] : []);
      }
      if (signals.coverage === "not-assessable") {
        return advice("not-assessable", "native", "Not assessable.",
          `Read the missing evidence for item #${item.id} before recommending work.`,
          "The inventory is complete, but the signals cannot support an assessment.");
      }
      if (!discussionIsComplete && claims.some((claim) => claim.type !== "context")) {
        return advice("confirm-evidence", "native", "Confirm the current evidence.",
          signals.discussion.nextAction, `Discussion is ${signals.discussion.status}: ${signals.discussion.reason}. Known reports cannot establish current work until chronology is complete.`,
          references(claims));
      }
      if (chronology.conflicts.length) {
        const ids = references(chronology.conflicts);
        return advice("confirm-evidence", "native", "Clarify the current evidence.",
          `Clarify the conflicting blocker reports for item #${item.id}.`,
          `Conflicting creation and modification chronology: ${describe(ids)}.`, ids);
      }
      const parentCommitments = claims.filter((claim) =>
        claim.type === "commitment" && claim.parentId !== undefined && claim.isOutstanding === true);
      const dependencies = claims.filter((claim) => claim.type === "parent-dependency" &&
        parentCommitments.some((commitment) =>
          commitment.parentId === claim.parentId && sameIssue(commitment, claim)));
      const dependencyReports = dependencies.filter((claim) => claim.isOutstanding === true);
      const matchesDependency = (report, update) =>
        report.parentId === update.parentId && sameIssue(report, update);
      const dependencyChronology = outstandingChronology(item,
        dependencyReports,
        dependencies.filter((claim) => claim.isOutstanding !== true),
        matchesDependency);
      const unknownDependencyChronology = outstandingChronology(item,
        dependencies.filter((claim) => claim.isOutstanding === undefined),
        dependencyChronology.outstanding, matchesDependency);
      const uncertainDependencies = [
        ...dependencyChronology.conflicts,
        ...unknownDependencyChronology.outstanding,
        ...unknownDependencyChronology.conflicts,
        ...dependencyChronology.outstanding.filter((dependency) =>
          parentCommitments.some((commitment) => commitment.parentId === dependency.parentId &&
            sameIssue(commitment, dependency) && !dependencySupports(item, dependency, commitment))),
      ];
      if (uncertainDependencies.length) {
        const ids = references([
          ...dependencyChronology.superseded.filter((claim) => claim.isOutstanding === true &&
            unknownDependencyChronology.outstanding.some((unknown) => matchesDependency(claim, unknown))),
          ...uncertainDependencies, ...parentCommitments,
        ]);
        return advice("confirm-evidence", "native", "Clarify the current dependency.",
          `Confirm whether item #${item.id} is still required for its parent's delivery.`,
          `Conflicting or unknown child dependency status: ${describe(ids)}.`, ids);
      }
      const withdrawnDependencies = references(outstandingChronology(item,
        dependencyReports, dependencies.filter((claim) => claim.isOutstanding === false),
        matchesDependency).superseded);
      if (withdrawnDependencies.length) {
        dependencyIds = withdrawnDependencies;
        dependencyReason = ` An explicit later withdrawal removes the earlier child dependency: ${describe(withdrawnDependencies)}.`;
      }
      const commitments = claims.filter((claim) => claim.type === "commitment" &&
        claim.isOutstanding === true && (claim.parentId === undefined ||
          dependencyChronology.outstanding.some((dependency) => dependencySupports(item, dependency, claim))));
      const commitmentChronology = outstandingChronology(item, commitments,
        claims.filter((claim) => claim.type === "commitment" && claim.isOutstanding !== true),
        (report, update) => report.parentId === update.parentId && sameIssue(report, update) &&
          (report.issueId !== undefined && update.issueId !== undefined || report.date === update.date));
      const supersededCommitments = [...commitmentChronology.superseded, ...commitmentChronology.conflicts];
      if (supersededCommitments.length) {
        const ids = references(supersededCommitments);
        return advice("confirm-evidence", "native", "Clarify the current commitment.",
          `Confirm the current delivery status for item #${item.id}.`,
          `Later delivery updates supersede or conflict with the earlier outstanding report: ${describe(ids)}.`, ids);
      }
      const currentDates = [...new Set(commitments.map((claim) => instant(claim.date)))];
      if (currentDates.length > 1) {
        const ids = references(commitments);
        return advice("confirm-evidence", "native", "Clarify the current commitment.",
          `Confirm the current delivery date for item #${item.id}.`,
          `Conflicting current delivery dates: ${describe(ids)}.`, ids);
      }
      if (discussionIsComplete && chronology.outstanding.length) {
        const blocker = chronology.outstanding[0];
        const ids = references(chronology.outstanding);
        return advice("unblock", "attention", "Unblock the work.",
          `Resolve blocker ${blocker.issueId} for item #${item.id}.`,
          `Outstanding blocker ${blocker.issueId}: ${describe(ids)}.`, ids);
      }
      const observedDay = Math.floor(instant(signals.observedAt) / DAY_MS);
      const nearCommitments = commitments.filter((claim) => Math.floor(instant(claim.date) / DAY_MS) - observedDay <= 7);
      if (nearCommitments.length) {
        const ids = references([
          ...nearCommitments,
          ...dependencyChronology.outstanding.filter((dependency) =>
            nearCommitments.some((commitment) => dependencySupports(item, dependency, commitment))),
        ]);
        return advice("meet-commitment", "attention", "Meet the commitment.",
          `Complete the outstanding work for item #${item.id} or confirm a revised delivery date.`,
          `Current outstanding delivery commitment: ${describe(ids)}.`, ids);
      }
      const due = signals.delivery.entries.find((entry) => entry.semantics === "due" && entry.status === "complete");
      if (due && Math.floor(instant(due.value) / DAY_MS) - observedDay <= 7 &&
        !claims.some((claim) => claim.type === "commitment")) {
        return advice("confirm-evidence", "native", "Clarify the current commitment.",
          `Confirm whether item #${item.id} still has outstanding work for the recorded delivery date.`,
          `${describe([due.sourceId])} records a scheduling commitment, but current outstanding work is not established.${resolutionReason}`,
          [due.sourceId, ...resolvedIds]);
      }
      const changed = signals.dates.changed;
      if (changed.status === "complete" && changed.elapsedDays >= 30) {
        return advice("review-relevance", "native", "Review relevance.",
          `Confirm whether item #${item.id} still belongs in the backlog.`,
          `${describe([changed.sourceId])} is ${changed.elapsedDays} days old. Review relevance, not urgency.${resolutionReason}`,
          [changed.sourceId, ...resolvedIds]);
      }
      if (signals.iteration.status === "complete" && signals.iteration.calendarPosition === "after") {
        return advice("update-planning", "native", "Update planning.",
          `Confirm the current iteration for item #${item.id}.`,
          `${signals.iteration.path} ended ${signals.iteration.finishDate}; update stale planning, not a delivery deadline.${resolutionReason}`,
          [signals.iteration.sourceId, ...resolvedIds]);
      }
      return advice("keep-native-order", "native", "Keep native order.",
        `Continue item #${item.id} in native Azure priority order.`,
        `No grounded current reason changes native Azure order.${resolutionReason}`, resolvedIds);
    }
