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
      {
        id: 105,
        fields: {
          "System.WorkItemType": "Feature",
          "System.State": "Ready for validation",
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
      {
        workItemType: "Feature",
        name: "Ready for validation",
        stateCategory: "Resolved",
      },
    ];

    expect(filterNonterminalWorkItems(workItems, stateMetadata)).toEqual([
      workItems[2],
      workItems[3],
      workItems[4],
    ]);
  });

  test("fails closed when a work-item state has an unknown category", () => {
    const workItems = [
      { id: 101, fields: { "System.WorkItemType": "Story", "System.State": "Active" } },
      { id: 102, fields: { "System.WorkItemType": "Story", "System.State": "Custom" } },
    ];
    const stateMetadata = [
      { workItemType: "Story", name: "Active", stateCategory: "InProgress" },
      { workItemType: "Story", name: "Custom", stateCategory: "FutureCategory" },
    ];

    expect(() => filterNonterminalWorkItems(workItems, stateMetadata)).toThrow();
  });

  test("fails closed when a work-item state category is missing", () => {
    const workItems = [
      { id: 101, fields: { "System.WorkItemType": "Story", "System.State": "Active" } },
      { id: 102, fields: { "System.WorkItemType": "Story", "System.State": "Unknown" } },
    ];
    const stateMetadata = [
      { workItemType: "Story", name: "Active", stateCategory: "InProgress" },
      { workItemType: "Story", name: "Unknown" },
    ];

    expect(() => filterNonterminalWorkItems(workItems, stateMetadata)).toThrow();
    expect(() => filterNonterminalWorkItems(workItems, [stateMetadata[0]])).toThrow();
  });
});

describe("partitionWorkItemIds", () => {
  test("returns no batches for an empty inventory", () => {
    expect(partitionWorkItemIds([])).toEqual([]);
  });

  test("keeps exactly 200 IDs in one batch", () => {
    const workItemIds = Array.from({ length: 200 }, (_, index) => index + 1);

    expect(partitionWorkItemIds(workItemIds)).toEqual([workItemIds]);
  });

  test("splits 201 IDs into ordered batches", () => {
    const workItemIds = Array.from({ length: 201 }, (_, index) => index + 1);
    const batches = partitionWorkItemIds(workItemIds);

    expect(batches).toEqual([workItemIds.slice(0, 200), workItemIds.slice(200)]);
    expect(batches.flat()).toEqual(workItemIds);
  });

  test("keeps each ID once and preserves order across multiple batches", () => {
    const workItemIds = Array.from({ length: 405 }, (_, index) => index + 1);
    const batches = partitionWorkItemIds(workItemIds);

    expect(batches).toEqual([
      workItemIds.slice(0, 200),
      workItemIds.slice(200, 400),
      workItemIds.slice(400),
    ]);
    expect(batches.every((batch) => batch.length <= 200)).toBe(true);
    expect(batches.flat()).toEqual(workItemIds);
    expect(new Set(batches.flat()).size).toBe(workItemIds.length);
  });
});
