export type AzureSignalStatus = "complete" | "absent" | "partial" | "inaccessible";
export type AzureSignalCoverage = {
  status: AzureSignalStatus;
  reason?: string;
  nextAction?: string;
};
export type AzureSignalItem = {
  id: number;
  rev?: number;
  fields: Record<string, unknown>;
};
export type AzureSignalRead = AzureSignalCoverage & {
  pages?: unknown[];
  fields?: unknown[];
  response?: unknown;
  item?: AzureSignalItem;
};
export type AzureComment = {
  id: number;
  workItemId: number;
  version: number;
  text?: string;
  createdDate: string;
  modifiedDate: string;
  isDeleted: boolean;
  sourceId?: string;
};
export type AzureDiscussion = AzureSignalCoverage & {
  totalCount?: number;
  comments: AzureComment[];
};
export type AzureFieldSignal = AzureSignalCoverage & {
  value?: unknown;
  sourceId?: string;
};
export type AzureDateSignal = AzureFieldSignal & {
  elapsedDays?: number;
};
export type AzureDates = { created: AzureDateSignal; changed: AzureDateSignal };
export type AzureDeliveryEntry = AzureSignalCoverage & {
  referenceName: string;
  value?: unknown;
  semantics: "due" | "forecast" | "unrecognized";
  sourceId?: string;
};
export type AzureDelivery = AzureSignalCoverage & { entries: AzureDeliveryEntry[] };
export type AzureIterationSignal = AzureSignalCoverage & {
  id?: string;
  path?: string;
  name?: string;
  startDate?: string;
  finishDate?: string;
  timeFrame?: string;
  sourceId?: string;
  calendarPosition?: string;
  deadline?: never;
};
export type AzureParentSignal = AzureSignalCoverage & {
  workItemId?: number;
  priority?: number;
  severity?: string;
  importance?: { priority: AzureFieldSignal; severity: AzureFieldSignal };
  dates?: AzureDates;
  delivery: AzureDelivery;
  isBlockingDelivery?: never;
  inheritedUrgency?: never;
};
export type AzureSource = {
  id: string;
  workItemId: number;
  revision?: number;
  referenceName?: string;
  value?: unknown;
  commentId?: number;
  version?: number;
  text?: string;
  createdDate?: string;
  modifiedDate?: string;
  iterationId?: string;
  path?: string;
  name?: string;
  startDate?: string | null;
  finishDate?: string | null;
  timeFrame?: string;
};
export type AzureSignals = {
  observedAt: string;
  discussion: AzureDiscussion;
  dates: AzureDates;
  delivery: AzureDelivery;
  iteration: AzureIterationSignal;
  parent: AzureParentSignal;
  sources: AzureSource[];
  coverage: "sufficient" | "limited" | "not-assessable";
};
export function readAzureFieldMetadata(response: unknown): AzureSignalRead;
export function normalizeAzureDiscussion(input: {
  workItemId: number;
  read: AzureSignalRead;
  endpoint?: string;
  projectId?: string;
}): AzureDiscussion;
export function normalizeAzureSignals(input: {
  item: AzureSignalItem;
  observedAt: string;
  discussion: AzureSignalRead;
  fieldMetadata: AzureSignalRead;
  iterations: AzureSignalRead;
  parent: AzureSignalRead;
}): AzureSignals;
