export type AzureWorkItem = {
  id: number;
  fields: Record<string, unknown>;
  relations?: Array<{
    rel: string;
    url: string;
    relatedItem?: {
      id: number;
      type: string;
      state: string;
      title: string;
    };
  }>;
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
    "$expand"?: "Relations";
    fields?: string[];
  };
};

export type CollectAzureBacklogInput = {
  organization: string;
  project: string;
  team: string;
  backlogId: string;
  invoke: (request: AzureInvokeRequest) => Promise<unknown>;
};

export type AzureCliRun = (args: string[]) => Promise<string>;

export type CreateAzureDevOpsInvokerInput = Omit<
  CollectAzureBacklogInput,
  "invoke"
> & {
  run?: AzureCliRun;
};

export type AzureInventory = {
  complete: true;
  items: AzureWorkItem[];
};

export function partitionWorkItemIds(workItemIds: number[]): number[][];

export function createAzureDevOpsInvoker(
  input: CreateAzureDevOpsInvokerInput,
): CollectAzureBacklogInput["invoke"];

export function collectAzureBacklog(
  input: CollectAzureBacklogInput,
): Promise<AzureInventory>;
