const API_VERSION = "7.1";
const MAX_BATCH_SIZE = 200;
const NONTERMINAL_CATEGORIES = new Set([
  "Proposed",
  "InProgress",
  "Resolved",
]);
const STATE_CATEGORIES = new Set([
  ...NONTERMINAL_CATEGORIES,
  "Completed",
  "Removed",
]);

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
    throw incomplete("a work item has no type metadata");
  }
  return workItemType;
}

function requireWorkItemState(item) {
  const state = item?.fields?.["System.State"];
  if (typeof state !== "string" || !state) {
    throw incomplete("a work item has no state metadata");
  }
  return state;
}

function stateKey(workItemType, state) {
  return `${workItemType}\u0000${state}`;
}

export function filterNonterminalWorkItems(workItems, stateMetadata) {
  const categoriesByState = new Map();
  for (const metadata of stateMetadata) {
    if (
      typeof metadata.workItemType !== "string" ||
      typeof metadata.name !== "string" ||
      !metadata.name
    ) {
      throw incomplete("a work-item state is missing metadata");
    }
    const category = metadata.stateCategory ?? metadata.category;
    if (!STATE_CATEGORIES.has(category)) {
      throw incomplete("a work-item state has an unknown category");
    }
    const key = stateKey(metadata.workItemType, metadata.name);
    if (categoriesByState.has(key)) {
      throw incomplete("work-item state metadata is ambiguous");
    }
    categoriesByState.set(key, category);
  }

  return workItems.filter((item) => {
    const category = categoriesByState.get(
      stateKey(requireWorkItemType(item), requireWorkItemState(item)),
    );
    if (category === undefined) {
      throw incomplete("a work-item state has no category metadata");
    }
    return NONTERMINAL_CATEGORIES.has(category);
  });
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
  const workItemTypesPath = `/${encodedProject}/_apis/wit/workitemtypes`;
  const workItemBatchPath = `/${encodedProject}/_apis/wit/workitemsbatch`;
  const allowedRoutes = new Set([
    `GET ${backlogLevelsPath}`,
    `GET ${backlogItemsPath}`,
    `GET ${workItemTypesPath}`,
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

    const workItemIds = references.map((reference) => reference?.id);
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

    const workItems = workItemIds.map((id) => detailsById.get(id));
    const typesResponse = await request("GET", workItemTypesPath);
    const workItemTypes = requireArray(
      typesResponse,
      "value",
      "work-item types",
    );
    const availableTypes = new Set(
      workItemTypes.map((type) => type?.name).filter((name) => typeof name === "string"),
    );
    const selectedTypes = [...new Set(workItems.map(requireWorkItemType))];
    const stateMetadata = [];

    for (const workItemType of selectedTypes) {
      if (!availableTypes.has(workItemType)) {
        throw incomplete("a selected work-item type is not listed");
      }
      const encodedType = encodeSegment(workItemType, "work-item type");
      const statePath = `${workItemTypesPath}/${encodedType}/states`;
      allowedRoutes.add(`GET ${statePath}`);
      const stateResponse = await request("GET", statePath);
      const states = requireArray(stateResponse, "value", "work-item states");
      stateMetadata.push(
        ...states.map((state) => ({
          workItemType,
          name: state?.name,
          stateCategory: state?.stateCategory ?? state?.category,
        })),
      );
    }

    return {
      complete: true,
      items: filterNonterminalWorkItems(workItems, stateMetadata),
    };
  } catch (error) {
    if (error instanceof IncompleteAzureInventoryError) throw error;
    throw incomplete("an Azure read failed");
  }
}
