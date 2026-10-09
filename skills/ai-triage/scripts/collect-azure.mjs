import { execFile } from "node:child_process";
import { promisify } from "node:util";

const API_VERSION = "7.1";
const COMMENTS_API_VERSION = "7.1-preview.4";
const AZURE_DEVOPS_RESOURCE = "499b84ac-1321-427f-aa17-267ca6975798";
const AZURE_PROJECT_ID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const MAX_BATCH_SIZE = 200;
const MAX_COMMENT_READS = 5;
const RECENT_COMMENT_LIMIT = 5;
const RELATED_ITEM_FIELDS = [
  "System.WorkItemType",
  "System.State",
  "System.Title",
];

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
    /[\u0000-\u001f\u007f]/.test(value)
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

function commentWorkItemId(path, encodedProject) {
  const prefix = `/${encodedProject}/_apis/wit/workItems/`;
  if (!path.startsWith(prefix)) return undefined;
  const match = path.slice(prefix.length).match(/^(\d+)\/comments$/);
  const id = Number(match?.[1]);
  return Number.isSafeInteger(id) && id > 0 ? id : undefined;
}

const execFileAsync = promisify(execFile);

async function executeAz(args) {
  const { stdout } = await execFileAsync("az", args, {
    encoding: "utf8",
    maxBuffer: 20 * 1024 * 1024,
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

  return async (request) => {
    const commentId = commentWorkItemId(request.path, encodedProject);
    if (
      request.organization !== selectedScope.organization ||
      request.project !== selectedScope.project ||
      request.team !== selectedScope.team ||
      request.backlogId !== selectedScope.backlogId ||
      request.apiVersion !==
        (commentId === undefined ? API_VERSION : COMMENTS_API_VERSION)
    ) {
      throw incomplete("an Azure request escaped the selected scope");
    }

    const isAllowedGet =
      request.method === "GET" &&
      (request.path === backlogLevelsPath ||
        request.path === backlogItemsPath ||
        request.path === projectPath);
    const isAllowedCommentRead =
      request.method === "GET" &&
      commentId !== undefined &&
      request.apiVersion === COMMENTS_API_VERSION &&
      request.query?.["$top"] === RECENT_COMMENT_LIMIT &&
      request.query.order === "desc" &&
      Object.keys(request.query).length === 2;
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
    const isAllowedBatch = isInventoryBatch || isRelatedContextBatch;
    if (!isAllowedGet && !isAllowedBatch && !isAllowedCommentRead) {
      throw incomplete("an Azure request did not match the read allowlist");
    }

    const args = [
      "rest",
      "--method",
      request.method.toLowerCase(),
      "--url",
      `${selectedScope.organization}${request.path}?${
        isAllowedCommentRead
          ? `$top=${RECENT_COMMENT_LIMIT}&order=desc&api-version=${COMMENTS_API_VERSION}`
          : `api-version=${API_VERSION}`
      }`,
      "--resource",
      AZURE_DEVOPS_RESOURCE,
      "--only-show-errors",
      "--output",
      "json",
    ];
    if (isAllowedBatch) {
      args.push("--body", JSON.stringify(request.body));
    }

    const output = await run(args);
    return JSON.parse(output);
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
}) {
  if (typeof invoke !== "function") {
    throw incomplete("a scoped Azure request adapter is required");
  }

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
    const isCommentRead =
      method === "GET" &&
      commentWorkItemId(path, encodedProject) !== undefined;
    if (!allowedRoutes.has(`${method} ${path}`) && !isCommentRead) {
      throw incomplete("a request did not match the scoped read allowlist");
    }
    return invoke({
      method,
      path,
      ...scope,
      apiVersion: isCommentRead ? COMMENTS_API_VERSION : API_VERSION,
      ...(isCommentRead
        ? { query: { "$top": RECENT_COMMENT_LIMIT, order: "desc" } }
        : {}),
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

    const commentIds = [...detailsById.keys()];
    const commentsById = new Map();
    let nextCommentIndex = 0;
    const readComments = async () => {
      while (nextCommentIndex < commentIds.length) {
        const workItemId = commentIds[nextCommentIndex++];
        if (workItemId === undefined) {
          throw incomplete("the related-comment inventory changed during collection");
        }
        const response = await request(
          "GET",
          `/${encodedProject}/_apis/wit/workItems/${workItemId}/comments`,
        );
        const comments = requireArray(response, "comments", "work-item comments");
        if (
          !Number.isSafeInteger(response?.totalCount) ||
          response.totalCount < comments.length ||
          comments.length > RECENT_COMMENT_LIMIT
        ) {
          throw incomplete("invalid work-item comments response");
        }
        commentsById.set(workItemId, {
          totalCount: response.totalCount,
          items: comments.map((comment) => {
            const createdDate = comment?.createdDate;
            if (
              comment?.workItemId !== workItemId ||
              !Number.isSafeInteger(comment.commentId) ||
              comment.commentId <= 0 ||
              typeof comment.text !== "string" ||
              typeof createdDate !== "string" ||
              !Number.isFinite(Date.parse(createdDate))
            ) {
              throw incomplete("invalid work-item comment");
            }
            return {
              id: comment.commentId,
              text: comment.text,
              createdDate,
            };
          }),
        });
      }
    };
    await Promise.all(
      Array.from(
        { length: Math.min(MAX_COMMENT_READS, commentIds.length) },
        () => readComments(),
      ),
    );

    const inventoryItems = workItems.map((item) => ({
      ...item,
      comments: commentsById.get(item.id),
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
                  comments: commentsById.get(relatedItem.id),
                },
              };
            }),
          }
        : {}),
    }));

    return {
      complete: true,
      items: inventoryItems,
    };
  } catch (error) {
    if (error instanceof IncompleteAzureInventoryError) throw error;
    throw incomplete("an Azure read failed");
  }
}
