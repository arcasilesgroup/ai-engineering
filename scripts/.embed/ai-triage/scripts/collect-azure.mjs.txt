import { execFile } from "node:child_process";
import { promisify } from "node:util";
import {
  normalizeAzureDiscussion,
  normalizeAzureSignals,
  readAzureFieldMetadata,
} from "./azure-signals.mjs";

const API_VERSION = "7.1";
const AZURE_DEVOPS_RESOURCE = "499b84ac-1321-427f-aa17-267ca6975798";
const AZURE_PROJECT_ID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const MAX_BATCH_SIZE = 200;
const RELATED_ITEM_FIELDS = [
  "System.WorkItemType",
  "System.State",
  "System.Title",
];
const PARENT_SIGNAL_FIELDS = [
  "Microsoft.VSTS.Common.Priority",
  "Microsoft.VSTS.Common.Severity",
  "System.CreatedDate",
  "System.ChangedDate",
  "Microsoft.VSTS.Scheduling.DueDate",
  "Microsoft.VSTS.Scheduling.TargetDate",
];

function parentProjection(metadata) {
  return [
    ...RELATED_ITEM_FIELDS,
    ...PARENT_SIGNAL_FIELDS.filter((referenceName) => {
      const type = referenceName === "Microsoft.VSTS.Common.Priority" ? "integer"
        : referenceName === "Microsoft.VSTS.Common.Severity" ? "string" : "dateTime";
      return metadata.status === "complete" &&
        metadata.fields.some((field) => field.referenceName === referenceName && field.type === type);
    }),
  ];
}

class AzureReadError extends Error {
  constructor(category) {
    super(`Azure read failed: ${category}`);
    this.name = "AzureReadError";
    this.category = category;
  }
}

function classifyReadFailure(error) {
  if (error instanceof AzureReadError) return error;
  const stderr = typeof error?.stderr === "string" ? error.stderr : "";
  if (/^ERROR: Unauthorized(?=$|[({\r\n])/.test(stderr)) return new AzureReadError("unauthorized");
  if (/^ERROR: Forbidden(?=$|[({\r\n])/.test(stderr)) return new AzureReadError("forbidden");
  if (/^ERROR: (?:Too Many Requests|Internal Server Error|Not Implemented|Bad Gateway|Service Unavailable|Gateway Timeout|HTTP Version Not Supported|Variant Also Negotiates|Insufficient Storage|Loop Detected|Not Extended)(?=$|[({\r\n])/.test(stderr)) {
    return new AzureReadError("transient");
  }
  if (
    error?.code === "ERR_CHILD_PROCESS_STDIO_MAXBUFFER" ||
    error?.code === "ETIMEDOUT" ||
    (error?.killed === true && error?.signal === "SIGTERM")
  ) return new AzureReadError("interrupted");
  return new AzureReadError("unknown");
}

function optionalReadGap(error, nextAction, hasEarlierEvidence = false) {
  const failure = classifyReadFailure(error);
  if (!["forbidden", "transient", "interrupted", "invalid-response"].includes(failure.category)) {
    throw failure;
  }
  return {
    status: hasEarlierEvidence || failure.category !== "forbidden" ? "partial" : "inaccessible",
    reason: failure.category === "forbidden" ? "permission-denied"
      : failure.category === "invalid-response" ? "invalid-response" : "read-interrupted",
    nextAction,
  };
}

class IncompleteAzureInventoryError extends Error {
  constructor(reason) {
    super(`Azure backlog collection incomplete: ${reason}`);
    this.name = "IncompleteAzureInventoryError";
  }
}

function incomplete(reason) {
  return new IncompleteAzureInventoryError(reason);
}

function encodeSegment(value, name) {
  if (
    typeof value !== "string" ||
    value.length === 0 ||
    /[\u0000-\u001f\u007f/\\]/.test(value) ||
    value === "." || value === ".."
  ) {
    throw incomplete(`invalid ${name}`);
  }
  return encodeURIComponent(value);
}

function explicitOrganization(value) {
  if (typeof value !== "string" || value.length === 0) {
    throw incomplete("an explicit organization is required");
  }

  let url;
  try {
    url = new URL(
      value.includes("://")
        ? value
        : `https://dev.azure.com/${encodeSegment(value, "organization")}`,
    );
  } catch {
    throw incomplete("invalid organization");
  }

  const isDevAzure = url.hostname === "dev.azure.com";
  const isVisualStudio = /^[a-z0-9-]+\.visualstudio\.com$/i.test(
    url.hostname,
  );
  const organizationPart = isDevAzure
    ? url.pathname.split("/").filter(Boolean).length === 1
    : url.pathname === "/" || url.pathname === "";
  if (
    url.protocol !== "https:" ||
    url.username ||
    url.password ||
    url.port ||
    url.search ||
    url.hash ||
    (!isDevAzure && !isVisualStudio) ||
    !organizationPart
  ) {
    throw incomplete("only an explicit Azure DevOps Services organization is supported");
  }

  return url.origin + url.pathname.replace(/\/+$/, "");
}

function requireArray(value, property, source) {
  const list = value?.[property];
  if (!Array.isArray(list)) throw incomplete(`invalid ${source} response`);
  return list;
}

function requireWorkItemType(item) {
  const workItemType = item?.fields?.["System.WorkItemType"];
  if (typeof workItemType !== "string" || !workItemType) {
    throw incomplete("a work item has no type value");
  }
  return workItemType;
}

function requireWorkItemState(item) {
  const state = item?.fields?.["System.State"];
  if (typeof state !== "string" || !state) {
    throw incomplete("a work item has no state value");
  }
  return state;
}

function requireWorkItemTitle(item) {
  const title = item?.fields?.["System.Title"];
  if (typeof title !== "string" || !title) {
    throw incomplete("a related work item has no title");
  }
  return title;
}

const execFileAsync = promisify(execFile);

async function executeAz(args) {
  const { stdout } = await execFileAsync("az", args, {
    encoding: "utf8",
    maxBuffer: 20 * 1024 * 1024,
    timeout: 60_000,
  });
  return stdout;
}

export function createAzureDevOpsInvoker({
  organization,
  project,
  team,
  backlogId,
  run = executeAz,
}) {
  const selectedScope = {
    organization: explicitOrganization(organization),
    project,
    team,
    backlogId,
  };
  const encodedProject = encodeSegment(project, "project");
  const encodedTeam = encodeSegment(team, "team");
  const encodedBacklog = encodeSegment(backlogId, "backlog");
  const backlogLevelsPath = `/${encodedProject}/${encodedTeam}/_apis/work/backlogs`;
  const backlogItemsPath = `${backlogLevelsPath}/${encodedBacklog}/workItems`;
  const projectPath = `/_apis/projects/${encodedProject}`;
  const workItemBatchPath = `/${encodedProject}/_apis/wit/workitemsbatch`;
  const fieldsPath = `/${encodedProject}/_apis/wit/fields`;
  const iterationsPath = `/${encodedProject}/${encodedTeam}/_apis/work/teamsettings/iterations`;
  let selectedIds = new Set();
  const selectedDetails = new Map();
  let selectedProjectId;
  let parentFields = RELATED_ITEM_FIELDS;

  return async (request) => {
    if (
      !request || typeof request !== "object" ||
      Object.keys(request).some((key) =>
        !["method", "path", "organization", "project", "team", "backlogId", "apiVersion", "query", "body"].includes(key)
      ) ||
      request.organization !== selectedScope.organization ||
      request.project !== selectedScope.project ||
      request.team !== selectedScope.team ||
      request.backlogId !== selectedScope.backlogId
    ) {
      throw incomplete("an Azure request escaped the selected scope");
    }

    const commentId = [...selectedIds].find((id) =>
      request.path === `/${encodedProject}/_apis/wit/workItems/${id}/comments`
    );
    const isCommentRead = request.method === "GET" && commentId !== undefined &&
      request.apiVersion === "7.1-preview.4" &&
      request.query && typeof request.query === "object" && !Array.isArray(request.query) &&
      Object.keys(request.query).every((key) =>
        ["$top", "order", "includeDeleted", "continuationToken"].includes(key)
      ) &&
      request.query["$top"] === 200 && request.query.order === "asc" &&
      request.query.includeDeleted === true &&
      (request.query.continuationToken === undefined ||
        (typeof request.query.continuationToken === "string" && request.query.continuationToken.length > 0));
    const isAllowedGet = request.body === undefined &&
      request.method === "GET" &&
      (isCommentRead || (request.apiVersion === API_VERSION && request.query === undefined &&
        (request.path === backlogLevelsPath ||
        request.path === backlogItemsPath ||
        request.path === projectPath ||
        request.path === fieldsPath ||
        request.path === iterationsPath)));
    const isInventoryBatch =
      request.method === "POST" &&
      request.path === workItemBatchPath &&
      Array.isArray(request.body?.ids) &&
      request.body["$expand"] === "Relations" &&
      request.body.fields === undefined &&
      request.body.errorPolicy === "Fail" &&
      Object.keys(request.body).every((key) =>
        ["ids", "errorPolicy", "$expand"].includes(key),
      );
    const isRelatedContextBatch =
      request.method === "POST" &&
      request.path === workItemBatchPath &&
      Array.isArray(request.body?.ids) &&
      request.body["$expand"] === undefined &&
      Array.isArray(request.body.fields) &&
      request.body.fields.length === RELATED_ITEM_FIELDS.length &&
      request.body.fields.every(
        (field, index) => field === RELATED_ITEM_FIELDS[index],
      ) &&
      request.body.errorPolicy === "Fail" &&
      Object.keys(request.body).every((key) =>
        ["ids", "errorPolicy", "fields"].includes(key),
      );
    const isParentSignalBatch =
      request.method === "POST" && request.path === workItemBatchPath &&
      Array.isArray(request.body?.ids) &&
      request.body.ids.every((id) => [...selectedDetails.values()].some((item) =>
        (item.relations ?? []).some((relation) => {
          if (relation.rel !== "System.LinkTypes.Hierarchy-Reverse") return false;
          const target = relatedWorkItemTarget(relation, selectedScope.organization);
          return target?.id === id &&
            target.projectId.toLowerCase() === selectedProjectId?.toLowerCase();
        })
      )) &&
      Array.isArray(request.body?.fields) && request.body["$expand"] === undefined &&
      parentFields.length > RELATED_ITEM_FIELDS.length &&
      request.body.fields.length === parentFields.length &&
      request.body.fields.every((field, index) => field === parentFields[index]) &&
      request.body.errorPolicy === "Fail" &&
      Object.keys(request.body).every((key) => ["ids", "errorPolicy", "fields"].includes(key));
    const ids = request.body?.ids;
    const isAllowedBatch = request.apiVersion === API_VERSION && request.query === undefined &&
      (isInventoryBatch || isRelatedContextBatch || isParentSignalBatch) &&
      Array.isArray(ids) && ids.length > 0 && ids.length <= MAX_BATCH_SIZE &&
      ids.every((id) => Number.isSafeInteger(id) && id > 0) && new Set(ids).size === ids.length;
    if (!isAllowedGet && !isAllowedBatch) {
      throw incomplete("an Azure request did not match the read allowlist");
    }

    const query = new URLSearchParams({ "api-version": request.apiVersion });
    for (const [key, value] of Object.entries(request.query ?? {})) query.set(key, String(value));
    const args = [
      "rest",
      "--method",
      request.method.toLowerCase(),
      "--url",
      `${selectedScope.organization}${request.path}?${query}`,
      "--resource",
      AZURE_DEVOPS_RESOURCE,
      "--only-show-errors",
      "--output",
      "json",
    ];
    if (isAllowedBatch) {
      args.push("--body", JSON.stringify(request.body));
    }

    if (request.path === backlogItemsPath) {
      selectedIds = new Set();
      selectedDetails.clear();
      selectedProjectId = undefined;
    }
    if (request.path === fieldsPath) parentFields = RELATED_ITEM_FIELDS;
    let output;
    try {
      output = await run(args);
    } catch (error) {
      throw classifyReadFailure(error);
    }
    let response;
    try {
      response = JSON.parse(output);
    } catch {
      throw new AzureReadError("invalid-response");
    }
    if (request.path === backlogItemsPath) {
      const references = requireArray(response, "workItems", "backlog work items");
      const membership = references.map((reference) => reference?.target?.id);
      if (
        membership.some((id) => !Number.isSafeInteger(id) || id <= 0) ||
        new Set(membership).size !== membership.length
      ) throw incomplete("invalid selected membership for comment reads");
      selectedIds = new Set(membership);
    }
    if (request.path === fieldsPath) parentFields = parentProjection(readAzureFieldMetadata(response));
    if (request.path === projectPath && AZURE_PROJECT_ID_PATTERN.test(response?.id ?? "")) {
      selectedProjectId = response.id;
    }
    if (isInventoryBatch && Array.isArray(response?.value)) {
      for (const item of response.value) {
        if (ids.includes(item?.id) && selectedIds.has(item.id)) selectedDetails.set(item.id, item);
      }
    }
    return response;
  };
}

function relatedWorkItemTarget(relation, organization) {
  if (
    relation?.rel !== "System.LinkTypes.Hierarchy-Forward" &&
    relation?.rel !== "System.LinkTypes.Hierarchy-Reverse"
  ) {
    return undefined;
  }

  let url;
  try {
    url = new URL(relation.url);
  } catch {
    return undefined;
  }

  const organizationUrl = new URL(organization);
  const organizationPath = organizationUrl.pathname.replace(/\/+$/, "");
  if (
    url.origin !== organizationUrl.origin ||
    url.username ||
    url.password ||
    !url.pathname.startsWith(`${organizationPath}/`)
  ) {
    return undefined;
  }

  const relativePath = url.pathname.slice(organizationPath.length);
  const match = relativePath.match(
    /^\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\/_apis\/wit\/workItems\/(\d+)\/?$/i,
  );
  if (!match) return undefined;
  const [, projectId, idText] = match;
  const id = Number(idText);
  if (!projectId || !Number.isSafeInteger(id) || id <= 0) return undefined;
  return { projectId, id };
}

export function partitionWorkItemIds(workItemIds) {
  const batches = [];
  for (let offset = 0; offset < workItemIds.length; offset += MAX_BATCH_SIZE) {
    batches.push(workItemIds.slice(offset, offset + MAX_BATCH_SIZE));
  }
  return batches;
}

export async function collectAzureBacklog({
  organization,
  project,
  team,
  backlogId,
  invoke,
  observedAt,
  includeSignals = observedAt !== undefined,
}) {
  if (typeof invoke !== "function") {
    throw incomplete("a scoped Azure request adapter is required");
  }
  if (typeof includeSignals !== "boolean") throw incomplete("invalid signal enrichment selection");

  const scope = {
    organization: explicitOrganization(organization),
    project,
    team,
    backlogId,
  };
  const encodedProject = encodeSegment(project, "project");
  const encodedTeam = encodeSegment(team, "team");
  const encodedBacklog = encodeSegment(backlogId, "backlog");
  const backlogLevelsPath = `/${encodedProject}/${encodedTeam}/_apis/work/backlogs`;
  const backlogItemsPath = `${backlogLevelsPath}/${encodedBacklog}/workItems`;
  const projectPath = `/_apis/projects/${encodedProject}`;
  const workItemBatchPath = `/${encodedProject}/_apis/wit/workitemsbatch`;
  const allowedRoutes = new Set([
    `GET ${backlogLevelsPath}`,
    `GET ${backlogItemsPath}`,
    `GET ${projectPath}`,
    `POST ${workItemBatchPath}`,
  ]);

  const request = async (method, path, body) => {
    if (!allowedRoutes.has(`${method} ${path}`)) {
      throw incomplete("a request did not match the scoped read allowlist");
    }
    return invoke({
      method,
      path,
      ...scope,
      apiVersion: API_VERSION,
      ...(body ? { body } : {}),
    });
  };

  try {
    const backlogResponse = await request("GET", backlogLevelsPath);
    const backlogs = requireArray(backlogResponse, "value", "backlog levels");
    const matchingBacklogs = backlogs.filter(
      (backlog) => backlog?.id === backlogId,
    );
    if (matchingBacklogs.length !== 1) {
      throw incomplete("the selected backlog level was not uniquely listed");
    }
    const workItemCountLimit = matchingBacklogs[0].workItemCountLimit;
    if (
      !Number.isSafeInteger(workItemCountLimit) ||
      workItemCountLimit <= 0
    ) {
      throw incomplete("the selected backlog work-item limit is unknown");
    }

    const backlogItemsResponse = await request("GET", backlogItemsPath);
    const references = requireArray(
      backlogItemsResponse,
      "workItems",
      "backlog work items",
    );
    if (references.length >= workItemCountLimit) {
      throw incomplete("the selected backlog reached its work-item limit");
    }

    const workItemIds = references.map((reference) => reference?.target?.id);
    if (
      workItemIds.some(
        (id) => !Number.isSafeInteger(id) || id <= 0,
      ) ||
      new Set(workItemIds).size !== workItemIds.length
    ) {
      throw incomplete("the backlog returned invalid or duplicate work-item IDs");
    }

    const detailsById = new Map();
    for (const batch of partitionWorkItemIds(workItemIds)) {
      const batchResponse = await request("POST", workItemBatchPath, {
        ids: batch,
        errorPolicy: "Fail",
        "$expand": "Relations",
      });
      const details = requireArray(batchResponse, "value", "work-item batch");
      const returnedIds = details.map((item) => item?.id);
      if (
        returnedIds.some((id) => !Number.isSafeInteger(id)) ||
        new Set(returnedIds).size !== returnedIds.length ||
        returnedIds.length !== batch.length ||
        returnedIds.some((id) => !batch.includes(id))
      ) {
        throw incomplete("a detail batch did not return exactly the requested IDs");
      }
      for (const item of details) detailsById.set(item.id, item);
    }

    const workItems = workItemIds.map((id) => {
      const item = detailsById.get(id);
      if (!item) throw incomplete("a selected work item is missing");
      requireWorkItemType(item);
      requireWorkItemState(item);
      return item;
    });
    const relatedTargets = workItems.flatMap((item) =>
      (item.relations ?? [])
        .map((relation) =>
          relatedWorkItemTarget(relation, scope.organization),
        )
        .filter((target) => target !== undefined),
    );
    const projectResponse =
      relatedTargets.length === 0
        ? undefined
        : await request("GET", projectPath);
    const projectId = projectResponse?.id;
    if (
      relatedTargets.length > 0 &&
      (typeof projectId !== "string" ||
        !AZURE_PROJECT_ID_PATTERN.test(projectId))
    ) {
      throw incomplete("the selected project ID is invalid");
    }
    const relatedWorkItemIds = [
      ...new Set(
        relatedTargets
          .filter(
            (target) =>
              target.projectId.toLowerCase() === projectId?.toLowerCase(),
          )
          .map((target) => target.id),
      ),
    ].filter((id) => !detailsById.has(id));

    for (const batch of partitionWorkItemIds(relatedWorkItemIds)) {
      const batchResponse = await request("POST", workItemBatchPath, {
        ids: batch,
        fields: RELATED_ITEM_FIELDS,
        errorPolicy: "Fail",
      });
      const details = requireArray(
        batchResponse,
        "value",
        "related work-item batch",
      );
      const returnedIds = details.map((item) => item?.id);
      if (
        returnedIds.some((id) => !Number.isSafeInteger(id)) ||
        new Set(returnedIds).size !== returnedIds.length ||
        returnedIds.length !== batch.length ||
        returnedIds.some((id) => !batch.includes(id))
      ) {
        throw incomplete("a related-item batch did not return exactly the requested IDs");
      }
      for (const item of details) detailsById.set(item.id, item);
    }

    const inventoryItems = workItems.map((item) => ({
      ...item,
      ...(item.relations
        ? {
            relations: item.relations.map((relation) => {
              const target = relatedWorkItemTarget(
                relation,
                scope.organization,
              );
              if (
                !target ||
                target.projectId.toLowerCase() !== projectId?.toLowerCase()
              ) {
                return relation;
              }
              const relatedItem = detailsById.get(target.id);
              if (!relatedItem) return relation;

              return {
                ...relation,
                relatedItem: {
                  id: relatedItem.id,
                  type: requireWorkItemType(relatedItem),
                  state: requireWorkItemState(relatedItem),
                  title: requireWorkItemTitle(relatedItem),
                },
              };
            }),
          }
        : {}),
    }));

    if (includeSignals) {
      const observation = observedAt ?? new Date().toISOString();
      const fieldsPath = `/${encodedProject}/_apis/wit/fields`;
      const iterationsPath = `/${encodedProject}/${encodedTeam}/_apis/work/teamsettings/iterations`;
      const signalRequest = (path, query) => invoke({
        ...scope, method: "GET", path,
        apiVersion: query ? "7.1-preview.4" : API_VERSION,
        ...(query ? { query } : {}),
      });
      const optionalRead = async (path, nextAction) => {
        try {
          return { status: "complete", response: await signalRequest(path) };
        } catch (error) {
          return optionalReadGap(error, nextAction);
        }
      };
      let selectedProjectId = projectId;
      if (!selectedProjectId && workItems.length) {
        const projectRead = await optionalRead(projectPath, "Retry the selected project's identity read.");
        const id = projectRead.response?.id;
        if (typeof id === "string" && AZURE_PROJECT_ID_PATTERN.test(id)) selectedProjectId = id;
      }
      const metadataRead = await optionalRead(fieldsPath, "Request access to project field metadata, then retry.");
      const fieldMetadata = metadataRead.status === "complete"
        ? readAzureFieldMetadata(metadataRead.response) : metadataRead;
      const iterations = await optionalRead(iterationsPath, "Request access to the selected team's iterations, then retry.");
      const parentFields = parentProjection(fieldMetadata);
      const parentReads = new Map();
      const parentsByItem = new Map();
      for (const item of workItems) {
        const parentRelations = (item.relations ?? []).filter((relation) =>
          relation.rel === "System.LinkTypes.Hierarchy-Reverse"
        );
        const sameProjectParents = [...new Set(parentRelations
          .map((relation) => relatedWorkItemTarget(relation, scope.organization))
          .filter((target) => target?.projectId.toLowerCase() === projectId?.toLowerCase())
          .map((target) => target.id))];
        if (sameProjectParents.length !== 1) {
          parentsByItem.set(item.id, {
            status: parentRelations.length ? "partial" : "absent",
            reason: parentRelations.length ? "parent-scope-unresolved" : "no-direct-parent",
            nextAction: parentRelations.length ? "Confirm one direct parent in the selected project." : "No direct parent to read.",
          });
          continue;
        }
        const parentId = sameProjectParents[0];
        parentsByItem.set(item.id, parentId);
        if (workItemIds.includes(parentId)) {
          parentReads.set(parentId, { status: "complete", item: detailsById.get(parentId) });
        } else if (!parentReads.has(parentId)) {
          parentReads.set(parentId, {
            status: "partial", reason: "parent-details-unavailable",
            nextAction: "Retry the direct parent's detail read.",
          });
        }
      }
      const parentIds = [...parentReads.keys()].filter((id) => !workItemIds.includes(id));
      if (parentFields.length > RELATED_ITEM_FIELDS.length) {
        for (const batch of partitionWorkItemIds(parentIds)) {
          let batchResponse;
          try {
            batchResponse = await request("POST", workItemBatchPath, {
              ids: batch, fields: parentFields, errorPolicy: "Fail",
            });
          } catch (error) {
            const unavailable = optionalReadGap(error, "Request read access to the direct parents, then retry.");
            for (const id of batch) parentReads.set(id, unavailable);
            continue;
          }
          const details = batchResponse?.value;
          if (
            !Array.isArray(details) ||
            (batchResponse.count !== undefined && batchResponse.count !== details.length) ||
            new Set(details.map((item) => item?.id)).size !== details.length ||
            details.some((item) => !batch.includes(item?.id))
          ) continue;
          for (const item of details) parentReads.set(item.id, { status: "complete", item });
        }
      }
      const enrichedItems = [];
      for (const item of inventoryItems) {
        const path = `/${encodedProject}/_apis/wit/workItems/${item.id}/comments`;
        const endpoint = `${scope.organization}${path}`;
        const pages = [];
        let bufferedBytes = 0;
        let token;
        let discussion;
        while (true) {
          try {
            const page = await signalRequest(path, {
              "$top": 200, order: "asc", includeDeleted: true,
              ...(token ? { continuationToken: token } : {}),
            });
            bufferedBytes += Buffer.byteLength(JSON.stringify(page) ?? "", "utf8");
            if (bufferedBytes > 20 * 1024 * 1024) {
              discussion = {
                status: "partial", reason: "comment-buffer-limit",
                nextAction: "Retry the full discussion with a smaller service response.", pages,
              };
              break;
            }
            pages.push(page);
          } catch (error) {
            discussion = { ...optionalReadGap(error, "Retry all comment pages for the selected item.", pages.length > 0), pages };
            break;
          }
          const normalized = normalizeAzureDiscussion({
            workItemId: item.id, read: { status: "complete", pages }, endpoint, projectId: selectedProjectId,
          });
          const nextToken = pages.at(-1)?.continuationToken;
          if (normalized.status === "partial" && normalized.reason !== "missing-comment-page") {
            discussion = { ...normalized, pages };
            break;
          }
          if (!nextToken) {
            discussion = { ...normalized, pages };
            break;
          }
          // Bound buffering even if a service returns endless distinct tokens.
          if (pages.length >= 1000) {
            discussion = {
              status: "partial", reason: "comment-page-limit",
              nextAction: "Check the service's continuation sequence, then retry the full discussion.", pages,
            };
            break;
          }
          token = nextToken;
        }
        const parent = parentsByItem.get(item.id);
        enrichedItems.push({
          ...item,
          signals: normalizeAzureSignals({
            item, observedAt: observation, discussion, fieldMetadata, iterations,
            parent: typeof parent === "number" ? parentReads.get(parent) : parent,
          }),
        });
      }
      return { complete: true, observedAt: observation, items: enrichedItems };
    }
    return {
      complete: true,
      items: inventoryItems,
    };
  } catch (error) {
    if (error instanceof IncompleteAzureInventoryError || error instanceof AzureReadError) throw error;
    throw incomplete("an Azure read failed");
  }
}
