import { describe, expect, test } from "bun:test";
import { partitionWorkItemIds } from "../skills/ai-triage/scripts/collect-azure.mjs";

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
