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

export function writeAzureTriageReport<T extends { id: number }>(
  input: AzureTriageReportInput<T>,
): Promise<void>;
