import { describe, expect, test } from "bun:test";
import {
  filterNonterminalWorkItems,
  partitionWorkItemIds,
} from "../skills/ai-triage/scripts/collect-azure.mjs";

describe("Azure work-item collection helpers", () => {
  test("uses each work-item type's state category instead of its display name", () => {
    const workItems = [
      {
        id: 101,
        fields: {
          "System.WorkItemType": "Story",
          "System.State": "Verified by reviewers",
        },
      },
      {
        id: 102,
        fields: {
          "System.WorkItemType": "Issue",
          "System.State": "Dropped from scope",
        },
      },
      {
        id: 103,
        fields: {
          "System.WorkItemType": "Task",
          "System.State": "Completed",
        },
      },
      {
        id: 104,
        fields: {
          "System.WorkItemType": "Issue",
          "System.State": "Verified by reviewers",
        },
      },
    ];
    const stateMetadata = [
      {
        workItemType: "Story",
        name: "Verified by reviewers",
        stateCategory: "Completed",
      },
      {
        workItemType: "Issue",
        name: "Dropped from scope",
        stateCategory: "Removed",
      },
      {
        workItemType: "Task",
        name: "Completed",
        stateCategory: "InProgress",
      },
      {
        workItemType: "Issue",
        name: "Verified by reviewers",
        stateCategory: "Proposed",
      },
    ];

    expect(filterNonterminalWorkItems(workItems, stateMetadata)).toEqual([
      workItems[2],
      workItems[3],
    ]);
  });

  test("partitions fetched work-item IDs into complete batches of at most 200", () => {
    const workItemIds = Array.from({ length: 405 }, (_, index) => index + 1);
    const batches = partitionWorkItemIds(workItemIds);

    expect(batches).toEqual([
      workItemIds.slice(0, 200),
      workItemIds.slice(200, 400),
      workItemIds.slice(400),
    ]);
    expect(batches.every((batch) => batch.length <= 200)).toBe(true);
  });
});
