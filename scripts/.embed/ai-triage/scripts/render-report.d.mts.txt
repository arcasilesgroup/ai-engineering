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
