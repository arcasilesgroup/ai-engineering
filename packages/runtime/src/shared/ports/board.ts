import type { Result } from "../kernel/result.ts";

/**
 * BoardPort — driven port for work item state synchronization.
 *
 * Adapters: GitHub Projects v2, Azure DevOps, Linear, Jira.
 * Fail-open by design: never blocks the calling workflow.
 */
export interface WorkItem {
  readonly id: string;
  readonly title: string;
  readonly state: WorkItemState;
  readonly url: string;
}

export type WorkItemState =
  | "triage"
  | "backlog"
  | "ready"
  | "in_progress"
  | "in_review"
  | "done";

export class BoardError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "BoardError";
  }
}

export interface BoardPort {
  fetch(itemId: string): Promise<Result<WorkItem, BoardError>>;
  transition(
    itemId: string,
    to: WorkItemState,
  ): Promise<Result<void, BoardError>>;
}
