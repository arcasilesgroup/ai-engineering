export type AmbiguousField =
  | "provider"
  | "project"
  | "team"
  | "board"
  | "backlog";

export type TargetSelection = {
  provider?: string;
  organization?: string;
  project?: string;
  team?: string;
  board?: string;
  backlog?: string;
  backlogLevel?: string;
};

export type DiscoveredBoard = {
  organization: string;
  project: string;
  team: string;
  board?: string;
  backlogLevel: string;
};

export type ResolveTargetInput = {
  explicitUrl?: string;
  url?: string;
  remotes?: string[];
  discoveredBoards?: DiscoveredBoard[];
  selection?: TargetSelection;
  [key: string]: unknown;
};

export type AzureReadScope = {
  provider: "azure-devops";
  organization: string;
  project: string;
  team: string;
  board: string;
  backlog: string;
};

export type TargetResolution =
  | { status: "unsupported"; reason: string }
  | { status: "needs-answer"; field: AmbiguousField }
  | {
      status: "ready";
      provider: "github";
      owner: string;
      repository: string;
    }
  | {
      status: "ready";
      provider: "azure-devops";
      organization: string;
      project: string;
      team: string;
      board?: string;
      backlogLevel: string;
      backlog?: string;
      missingBoard?: boolean;
    };

export function resolveTarget(
  input?: ResolveTargetInput,
): TargetResolution;

export function resolveTargetAndRead(
  input?: ResolveTargetInput,
  read?: (scope: AzureReadScope) => unknown | Promise<unknown>,
): Promise<
  TargetResolution | { status: "read"; target: AzureReadScope }
>;
