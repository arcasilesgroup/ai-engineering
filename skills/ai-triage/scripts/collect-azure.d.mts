import type { AzureSignals } from "./azure-signals.mjs";

export type AzureRecentComments = {
  totalCount?: number;
  items: Array<{
    id: number;
    text: string;
    createdDate: string;
  }>;
  status?: "complete" | "absent" | "partial" | "inaccessible";
  reason?: string;
  nextAction?: string;
};

export type AzureWorkItem = {
  id: number;
  rev?: number;
  fields: Record<string, unknown>;
  signals?: AzureSignals;
  comments?: AzureRecentComments;
  relations?: Array<{
    rel: string;
    url: string;
    relatedItem?: {
      id: number;
      type: string;
      state: string;
      title: string;
      comments?: AzureRecentComments;
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
  apiVersion: "7.1" | "7.1-preview.4";
  query?: Record<string, string | number | boolean>;
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
  includeSignals?: boolean;
  observedAt?: string;
  invoke: (request: AzureInvokeRequest) => Promise<unknown>;
};

export type AzureCliRun = (args: string[]) => Promise<string>;

export type CreateAzureDevOpsInvokerInput = Omit<
  CollectAzureBacklogInput,
  "invoke" | "includeSignals" | "observedAt"
> & {
  run?: AzureCliRun;
};

export type AzureInventory = {
  complete: true;
  observedAt?: string;
  items: AzureWorkItem[];
};

export function partitionWorkItemIds(workItemIds: number[]): number[][];

export function createAzureDevOpsInvoker(
  input: CreateAzureDevOpsInvokerInput,
): CollectAzureBacklogInput["invoke"];

export function collectAzureBacklog(
  input: CollectAzureBacklogInput,
): Promise<AzureInventory>;
