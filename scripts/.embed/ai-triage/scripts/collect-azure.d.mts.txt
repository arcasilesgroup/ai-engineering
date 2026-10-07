export type AzureWorkItem = {
  id: number;
  fields: Record<string, unknown>;
  relations?: Array<{ rel: string; url: string }>;
};

export type AzureStateMetadata = {
  workItemType: string;
  name: string;
  stateCategory?: string;
  category?: string;
};

export type AzureInvokeRequest = {
  method: "GET" | "POST";
  path: string;
  organization: string;
  project: string;
  team: string;
  backlogId: string;
  apiVersion: "7.1";
  body?: {
    ids: number[];
    errorPolicy: "Fail";
  };
};

export type CollectAzureBacklogInput = {
  organization: string;
  project: string;
  team: string;
  backlogId: string;
  invoke: (request: AzureInvokeRequest) => Promise<unknown>;
};

export type AzureInventory = {
  complete: true;
  items: AzureWorkItem[];
};

export function filterNonterminalWorkItems<T extends AzureWorkItem>(
  workItems: T[],
  stateMetadata: AzureStateMetadata[],
): T[];

export function partitionWorkItemIds(workItemIds: number[]): number[][];

export function collectAzureBacklog(
  input: CollectAzureBacklogInput,
): Promise<AzureInventory>;
