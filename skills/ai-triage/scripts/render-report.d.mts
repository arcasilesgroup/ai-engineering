export type AzureTriageScope = {
  provider: "azure-devops";
  organization: string;
  project: string;
  team: string;
  backlogId: string;
  backlogName: string;
};

export type AzureTriageReportInput<T extends { id: number }> = {
  scope: AzureTriageScope;
  inventory: unknown;
  analyzeItem: (item: T) => unknown | Promise<unknown>;
  writeFile?: (path: string, contents: string) => void | Promise<void>;
};

export function escapeHtml(value: string): string;
export function sanitizeEvidenceUrl(value: unknown): string | null;
export function renderAnalysis(value: string): string;
export function azurePriority(item: { fields: Record<string, unknown> }): string;

export type TriageHierarchyNode = {
  label: string;
  url: string | null;
  type?: string;
  title?: string;
  state?: string;
};

export function renderHierarchy(input: {
  current: TriageHierarchyNode;
  parents?: TriageHierarchyNode[];
  children?: TriageHierarchyNode[];
}): string;

export function atomicWriteReport(
  path: string,
  contents: string,
  operations?: {
    writeTemporaryFile?: (
      handle: { writeFile(contents: string, encoding: "utf8"): Promise<void> },
      contents: string,
      temporaryPath: string,
    ) => Promise<void>;
    beforeReplace?: (temporaryPath: string, path: string) => Promise<void>;
  },
): Promise<void>;

export function writeAzureTriageReport<T extends { id: number }>(
  input: AzureTriageReportInput<T>,
): Promise<void>;
export type { AzureAssessment, AzureClaim, AzureRecommendation } from "./azure-signals.mjs";
