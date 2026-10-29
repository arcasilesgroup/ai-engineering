import { describe, expect, test } from "bun:test";
import { normalizeAzureDiscussion, normalizeAzureSignals } from "../packs/triage/scripts/azure-signals.mjs";
import * as azureRecommendationApi from "../packs/triage/scripts/azure-signals.mjs";

type WorkItemFixture = {
  id: number;
  rev: number;
  fields: Record<string, unknown>;
};

type ReadFixture = {
  status: "complete" | "absent" | "partial" | "inaccessible";
  pages?: unknown[];
  fields?: unknown[];
  response?: unknown;
  item?: WorkItemFixture;
  reason?: string;
  nextAction?: string;
};

type SignalFixture = {
  item: WorkItemFixture;
  observedAt: string;
  discussion: ReadFixture;
  fieldMetadata: ReadFixture;
  iterations: ReadFixture;
  parent: ReadFixture;
};

const observedAt = "2026-10-08T00:00:00Z";
const dueReference = "Microsoft.VSTS.Scheduling.DueDate";
const targetReference = "Microsoft.VSTS.Scheduling.TargetDate";
const iterationPath = "Example\\Release\\Sprint 1";
const fieldMetadata = [
  { referenceName: "Microsoft.VSTS.Common.Priority", type: "integer" },
  { referenceName: "Microsoft.VSTS.Common.Severity", type: "string" },
  { referenceName: dueReference, name: "Delivery", type: "dateTime" },
  { referenceName: targetReference, name: "Forecast", type: "dateTime" },
  { referenceName: "Custom.DeliveryDate", name: "Due Date", type: "dateTime" },
  { referenceName: "Microsoft.VSTS.Scheduling.StartDate", type: "dateTime" },
  { referenceName: "Microsoft.VSTS.Scheduling.FinishDate", type: "dateTime" },
];
const iteration = {
  id: "11111111-1111-4111-8111-111111111111",
  name: "Sprint 1",
  path: iterationPath,
  attributes: {
    startDate: "2026-10-01T00:00:00Z",
    finishDate: "2026-10-08T00:00:00Z",
    timeFrame: "current",
  },
};

function signalFixture(overrides: Partial<SignalFixture> = {}): SignalFixture {
  return {
    item: {
      id: 202,
      rev: 3,
      fields: {
        "System.CreatedDate": "2026-09-08T00:00:00Z",
        "System.ChangedDate": "2026-10-07T00:00:00Z",
        "System.IterationPath": iterationPath,
        "System.IterationId": 17,
        "Microsoft.VSTS.Common.Priority": 3,
        "Microsoft.VSTS.Common.Severity": "3 - Medium",
        [dueReference]: "2026-10-09T00:00:00Z",
        [targetReference]: "2026-10-12T00:00:00Z",
      },
    },
    observedAt,
    discussion: {
      status: "complete",
      pages: [{ count: 0, totalCount: 0, comments: [] }],
    },
    fieldMetadata: { status: "complete", fields: fieldMetadata },
    iterations: { status: "complete", response: { value: [iteration] } },
    parent: { status: "absent" },
    ...overrides,
  };
}

function commentFixture(overrides: Record<string, unknown> = {}) {
  return {
    id: 7,
    workItemId: 202,
    version: 2,
    text: "The synthetic dependency needs review.",
    createdDate: "2026-10-06T12:00:00Z",
    modifiedDate: "2026-10-07T12:00:00Z",
    isDeleted: false,
    ...overrides,
  };
}

function normalizeDiscussion(pages: unknown[]) {
  return normalizeAzureSignals(
    signalFixture({ discussion: { status: "complete", pages } }),
  );
}

function expectGap(
  signal: { status: string; reason?: string; nextAction?: string },
  status: string,
  reason: string,
) {
  expect(signal.status).toBe(status);
  expect(signal.reason).toBe(reason);
  expect(signal.nextAction).toEqual(expect.any(String));
  expect(signal.nextAction?.trim().length).toBeGreaterThan(0);
}

describe("U1 discussion normalization and coverage", () => {
  test("preserves linked comments across opaque tokens, reconciles tombstones, and drops identities", () => {
    const token = "opaque+/=&?api-version=999#token";
    const comment = commentFixture({
      commentId: 7,
      createdBy: { displayName: "Synthetic author" },
      modifiedBy: { id: "synthetic-identity" },
      mentions: [{ displayName: "Synthetic mention" }],
      reactions: [{ type: "like" }],
      renderedText: "<script>synthetic markup</script>",
    });
    const deleted = commentFixture({
      id: 8,
      isDeleted: true,
      text: "Deleted body must not survive.",
    });
    const { id: exampleId, ...exampleComment } = commentFixture({ id: 9 });
    const signals = normalizeDiscussion([
      {
        count: 2,
        totalCount: 3,
        comments: [comment, deleted],
        continuationToken: token,
        nextPage: "https://dev.azure.com/example/project/_apis/wit/workItems/202/comments",
      },
      {
        count: 1,
        totalCount: 3,
        comments: [{ ...exampleComment, commentId: exampleId }],
      },
    ]);

    expect(signals.discussion.status).toBe("complete");
    expect(signals.discussion.totalCount).toBe(3);
    expect(signals.discussion.comments).toEqual([
      {
        id: 7, workItemId: 202, version: 2,
        text: "The synthetic dependency needs review.",
        createdDate: "2026-10-06T12:00:00Z",
        modifiedDate: "2026-10-07T12:00:00Z",
        isDeleted: false, sourceId: "comment:202:7:v2",
      },
      {
        id: 8, workItemId: 202, version: 2,
        createdDate: "2026-10-06T12:00:00Z",
        modifiedDate: "2026-10-07T12:00:00Z",
        isDeleted: true,
      },
      {
        id: 9, workItemId: 202, version: 2,
        text: "The synthetic dependency needs review.",
        createdDate: "2026-10-06T12:00:00Z",
        modifiedDate: "2026-10-07T12:00:00Z",
        isDeleted: false, sourceId: "comment:202:9:v2",
      },
    ]);
    expect(signals.sources.find((source: { id: string }) => source.id === "comment:202:7:v2")).toMatchObject({
      workItemId: 202, commentId: 7, version: 2,
      text: comment.text, createdDate: comment.createdDate, modifiedDate: comment.modifiedDate,
    });
    expect(signals.sources.some((source: { id: string }) => source.id === "comment:202:8:v2")).toBe(false);
    const serialized = JSON.stringify(signals);
    for (const discarded of [
      "Synthetic author", "synthetic-identity", "Synthetic mention",
      "reactions", "renderedText", "Deleted body must not survive.",
    ]) {
      expect(serialized).not.toContain(discarded);
    }
    expect(signals.coverage).toBe("sufficient");
  });

  test("a reconciled terminal zero is known absence, not an unread discussion", () => {
    const signals = normalizeDiscussion([{ count: 0, totalCount: 0, comments: [] }]);
    expect(signals.discussion).toMatchObject({ status: "absent", totalCount: 0, comments: [] });
    expect(signals.coverage).toBe("sufficient");
  });

  test.each([undefined, "ea918c8b-73ef-43d7-8f62-f664bae82720", "unverified-project"])("denies a GUID alias without matching established project identity %s", (projectId) => {
    const discussion = normalizeAzureDiscussion({
      workItemId: 202, ...(projectId ? { projectId } : {}),
      endpoint: "https://dev.azure.com/example/Named%20Project/_apis/wit/workItems/202/comments",
      read: {
        status: "complete",
        pages: [{
          count: 1, totalCount: 2, comments: [commentFixture()], continuationToken: "second",
          nextPage: "https://dev.azure.com/example/fa918c8b-73ef-43d7-8f62-f664bae82720/_apis/wit/workItems/202/comments?continuationToken=second",
        }],
      },
    });
    expectGap(discussion, "partial", "contradictory-continuation");
    expect(discussion.comments.map(({ id }) => id)).toEqual([7]);
  });

  test.each([
    [{ commentId: 8 }, "conflicting-comment-id"],
    [{ id: 0 }, "invalid-comment-id"],
    [{ id: 1.5 }, "invalid-comment-id"],
    [{ workItemId: 203 }, "comment-item-mismatch"],
    [{ version: 0 }, "invalid-comment-version"],
    [{ text: null }, "invalid-comment-text"],
    [{ createdDate: "2026-02-30T00:00:00Z" }, "invalid-comment-date"],
    [{ modifiedDate: "2026-10-07T12:00:00" }, "invalid-comment-date"],
    [{ modifiedDate: "2026-10-05T12:00:00Z" }, "inconsistent-comment-dates"],
  ])("rejects a malformed comment %j", (overrides, reason) => {
    const signals = normalizeDiscussion([
      { count: 1, totalCount: 1, comments: [commentFixture(overrides)] },
    ]);
    expectGap(signals.discussion, "partial", reason);
    expect(signals.discussion.comments).toEqual([]);
    expect(signals.coverage).toBe("limited");
  });

  test.each([
    [[{ count: 2, totalCount: 2, comments: [commentFixture()] }], "comment-count-mismatch"],
    [[{ count: 1, totalCount: 2, comments: [commentFixture()] }], "missing-comment-page"],
    [[{ count: 2, totalCount: 2, comments: [commentFixture(), commentFixture()] }], "duplicate-comment-id"],
    [[{ count: 1, totalCount: 1, comments: [commentFixture()], nextPage: "https://example.invalid/page" }], "contradictory-continuation"],
    [[
      { count: 1, totalCount: 2, comments: [commentFixture()], continuationToken: "next" },
      { count: 1, totalCount: 3, comments: [commentFixture({ id: 8 })] },
    ], "comment-total-drift"],
    [[
      { count: 1, totalCount: 3, comments: [commentFixture()], continuationToken: "repeat" },
      { count: 1, totalCount: 3, comments: [commentFixture({ id: 8 })], continuationToken: "repeat" },
    ], "repeated-continuation-token"],
  ])("does not certify an incoherent page sequence %j", (pages, reason) => {
    const signals = normalizeDiscussion(pages);
    expectGap(signals.discussion, "partial", reason);
    expect(signals.coverage).toBe("limited");
  });

  test.each(["partial", "inaccessible"] as const)("keeps a confirmed %s read separate from absence", (status) => {
    const signals = normalizeAzureSignals(signalFixture({
      discussion: {
        status, reason: "discussion-unavailable",
        nextAction: "Retry the selected item's comment read.",
        pages: status === "partial"
          ? [{ count: 1, totalCount: 2, comments: [commentFixture()], continuationToken: "next" }]
          : [],
      },
    }));
    expectGap(signals.discussion, status, "discussion-unavailable");
    expect(signals.discussion.comments.length).toBe(status === "partial" ? 1 : 0);
    expect(signals.dates.created.elapsedDays).toBe(30);
    expect(signals.coverage).toBe("limited");
  });
});

describe("U2 one observed clock and honest elapsed-day signals", () => {
  test.each([
    ["2026-10-08T00:00:00Z", "2026-10-07T00:00:01Z", 0],
    ["2026-10-08T00:00:00Z", "2026-10-07T00:00:00Z", 1],
    ["2026-10-08T00:00:00Z", "2026-10-07T02:00:00+02:00", 1],
    ["2024-03-01T00:00:00Z", "2024-02-28T00:00:00Z", 2],
    ["2026-03-30T00:00:00+02:00", "2026-03-29T00:00:00+01:00", 0],
    ["2026-10-26T00:00:00+01:00", "2026-10-25T00:00:00+02:00", 1],
  ])("uses elapsed instants %s minus %s", (clock, timestamp, elapsedDays) => {
    const input = signalFixture({ observedAt: clock });
    input.item.fields["System.CreatedDate"] = timestamp;
    input.item.fields["System.ChangedDate"] = timestamp;
    const signals = normalizeAzureSignals(input);
    expect(signals.observedAt).toBe(clock);
    for (const date of [signals.dates.created, signals.dates.changed]) {
      expect(date).toMatchObject({ status: "complete", value: timestamp, elapsedDays });
    }
    expect(signals.sources.find((source: { id: string }) => source.id === "field:202:r3:System.CreatedDate")).toEqual({
      id: "field:202:r3:System.CreatedDate",
      workItemId: 202, revision: 3, referenceName: "System.CreatedDate", value: timestamp,
    });
  });

  test.each([
    [undefined, "absent", "not-returned"],
    [null, "absent", "unset"],
    ["not a date", "partial", "invalid-date"],
    ["2026-02-30T00:00:00Z", "partial", "invalid-date"],
    ["2026-10-07", "partial", "invalid-date"],
    ["2026-10-07T00:00:00", "partial", "invalid-date"],
    ["2026-10-09T00:00:00Z", "partial", "future-date"],
  ])("does not turn %j into an age", (timestamp, status, reason) => {
    const input = signalFixture();
    input.item.fields["System.CreatedDate"] = timestamp;
    input.item.fields["System.ChangedDate"] = timestamp;
    const signals = normalizeAzureSignals(input);
    for (const date of [signals.dates.created, signals.dates.changed]) {
      expectGap(date, status, reason);
      expect(date.elapsedDays).toBeUndefined();
    }
    expect(signals.coverage).toBe("limited");
    expect(JSON.stringify(signals)).not.toContain("continuously");
  });

  test("changed-before-created stays inconsistent rather than becoming a valid idle period", () => {
    const input = signalFixture();
    input.item.fields["System.ChangedDate"] = "2026-09-07T00:00:00Z";
    const signals = normalizeAzureSignals(input);
    expectGap(signals.dates.changed, "partial", "changed-before-created");
    expect(signals.dates.changed.elapsedDays).toBeUndefined();
    expect(signals.dates.created.elapsedDays).toBe(30);
  });

  test("an invalid observation clock fails closed", () => {
    expect(() => normalizeAzureSignals(signalFixture({ observedAt: "2026-10-08" }))).toThrow(/observation/i);
  });
});

describe("U3 documented delivery fields and unrecognized custom context", () => {
  test("preserves conflicting due/forecast values and raw revision-linked sources", () => {
    const input = signalFixture();
    const signals = normalizeAzureSignals(input);
    expect(signals.delivery.status).toBe("complete");
    expect(signals.delivery.entries).toEqual([
      {
        referenceName: dueReference, value: "2026-10-09T00:00:00Z",
        semantics: "due", status: "complete",
        sourceId: `field:202:r3:${dueReference}`,
      },
      {
        referenceName: targetReference, value: "2026-10-12T00:00:00Z",
        semantics: "forecast", status: "complete",
        sourceId: `field:202:r3:${targetReference}`,
      },
    ]);
    expect(signals.sources.find((source: { id: string }) => source.id === `field:202:r3:${dueReference}`)).toEqual({
      id: `field:202:r3:${dueReference}`,
      workItemId: 202, revision: 3, referenceName: dueReference, value: "2026-10-09T00:00:00Z",
    });
    expect(input.item.fields["Microsoft.VSTS.Common.Priority"]).toBe(3);
    expect(input.item.fields["Microsoft.VSTS.Common.Severity"]).toBe("3 - Medium");
  });

  test("custom lookalikes and start/finish remain context, never delivery promises", () => {
    const input = signalFixture();
    input.item.fields["Custom.DeliveryDate"] = "2026-10-09T00:00:00Z";
    input.item.fields["Microsoft.VSTS.Scheduling.StartDate"] = "2026-10-01T00:00:00Z";
    input.item.fields["Microsoft.VSTS.Scheduling.FinishDate"] = "2026-10-09T00:00:00Z";
    const signals = normalizeAzureSignals(input);
    for (const referenceName of [
      "Custom.DeliveryDate",
      "Microsoft.VSTS.Scheduling.StartDate",
      "Microsoft.VSTS.Scheduling.FinishDate",
    ]) {
      expect(signals.delivery.entries.find((entry: { referenceName: string }) => entry.referenceName === referenceName)).toMatchObject({
        referenceName, value: input.item.fields[referenceName], semantics: "unrecognized",
        sourceId: `field:202:r3:${referenceName}`,
      });
    }
  });

  test.each([
    [[], "absent", "unsupported-field"],
    [[{ referenceName: dueReference, type: "string" }], "partial", "wrong-field-type"],
  ])("does not recognize due semantics from metadata %j", (fields, status, reason) => {
    const signals = normalizeAzureSignals(signalFixture({ fieldMetadata: { status: "complete", fields } }));
    const due = signals.delivery.entries.find((entry: { referenceName: string }) => entry.referenceName === dueReference);
    if (!due) throw new Error("Returned due context must remain visible.");
    expectGap(due, status, reason);
    expect(due.semantics).toBe("unrecognized");
    expect(due.value).toBe("2026-10-09T00:00:00Z");
  });

  test.each([
    [undefined, "absent", "not-returned"],
    [null, "absent", "unset"],
    ["2026-02-30T00:00:00Z", "partial", "invalid-date"],
  ])("keeps missing, unset and invalid delivery values distinct: %j", (value, status, reason) => {
    const input = signalFixture();
    input.item.fields[dueReference] = value;
    const signals = normalizeAzureSignals(input);
    const due = signals.delivery.entries.find((entry: { referenceName: string }) => entry.referenceName === dueReference);
    if (!due) throw new Error("A recognized field must expose its coverage.");
    expectGap(due, status, reason);
  });

  test("unavailable metadata preserves returned context without granting date meaning", () => {
    const signals = normalizeAzureSignals(signalFixture({
      fieldMetadata: {
        status: "inaccessible", reason: "field-metadata-unavailable",
        nextAction: "Request read access to project field metadata.",
      },
    }));
    expectGap(signals.delivery, "inaccessible", "field-metadata-unavailable");
    expect(signals.delivery.entries.find((entry: { referenceName: string }) => entry.referenceName === dueReference)).toMatchObject({
      referenceName: dueReference, value: "2026-10-09T00:00:00Z", semantics: "unrecognized",
    });
    expect(signals.coverage).toBe("limited");
  });

  test.each(["inaccessible", "partial"] as const)("retains raw custom context and sources with %s metadata", (status) => {
    const input = signalFixture({
      fieldMetadata: { status, reason: "field-metadata-unavailable", nextAction: "Retry project field metadata." },
    });
    input.item.fields["Custom.DeliveryDate"] = "2026-10-11T00:00:00Z";
    input.item.fields["Custom.UnknownField"] = "Unverified context";
    const signals = normalizeAzureSignals(input);
    for (const referenceName of ["Custom.DeliveryDate", "Custom.UnknownField"]) {
      const entry = signals.delivery.entries.find((candidate) => candidate.referenceName === referenceName);
      if (!entry) throw new Error("Returned unrecognized custom context must survive metadata failures.");
      expectGap(entry, status, "field-metadata-unavailable");
      expect(entry).toMatchObject({
        referenceName, value: input.item.fields[referenceName], semantics: "unrecognized",
        sourceId: `field:202:r3:${referenceName}`,
      });
      const sourceId = `field:202:r3:${referenceName}`;
      expect(signals.sources.find((source) => source.id === entry.sourceId)).toEqual({
        id: sourceId, workItemId: 202, revision: 3,
        referenceName, value: input.item.fields[referenceName],
      });
    }
    expect(signals.coverage).toBe("limited");
  });
});

describe("U4 exact selected-team iteration and parent context", () => {
  test.each(["value", "values"])("accepts the explicit %s envelope and inclusive UTC sprint end", (envelope) => {
    const signals = normalizeAzureSignals(signalFixture({
      observedAt: "2026-10-08T23:59:59-00:00",
      iterations: { status: "complete", response: { [envelope]: [iteration] } },
    }));
    expect(signals.iteration).toMatchObject({
      status: "complete", id: iteration.id, path: iterationPath, name: "Sprint 1",
      startDate: "2026-10-01", finishDate: "2026-10-08", timeFrame: "current",
      calendarPosition: "within",
    });
    expect(signals.iteration.deadline).toBeUndefined();
  });

  test.each([
    ["2026-09-30T23:59:59Z", "before"],
    ["2026-10-01T00:00:00Z", "within"],
    ["2026-10-09T00:00:00Z", "after"],
    ["2026-10-09T01:00:00+02:00", "within"],
  ])("compares UTC calendar days at %s", (clock, position) => {
    const input = signalFixture({ observedAt: clock });
    input.item.fields["System.CreatedDate"] = "2026-09-01T00:00:00Z";
    input.item.fields["System.ChangedDate"] = "2026-09-02T00:00:00Z";
    expect(normalizeAzureSignals(input).iteration.calendarPosition).toBe(position);
  });

  test.each([
    [{ value: [{ ...iteration, path: "Example\\Other\\Sprint 1" }] }, "absent", "iteration-path-unmatched"],
    [{ value: [iteration, { ...iteration, id: "second-id" }] }, "partial", "duplicate-iteration-path"],
    [{ value: [iteration], values: [] }, "partial", "conflicting-iteration-envelope"],
    [{ iterations: [iteration] }, "partial", "invalid-iteration-envelope"],
    [{ value: [{ ...iteration, attributes: { startDate: null, finishDate: null } }] }, "absent", "iteration-dates-unset"],
    [{ value: [{ ...iteration, attributes: { startDate: "2026-02-30T00:00:00Z", finishDate: "2026-10-08T00:00:00Z" } }] }, "partial", "invalid-iteration-dates"],
    [{ value: [{ ...iteration, attributes: { startDate: "2026-10-01T01:00:00Z", finishDate: "2026-10-08T00:00:00Z" } }] }, "partial", "invalid-iteration-dates"],
    [{ value: [{ ...iteration, attributes: { startDate: "2026-10-09T00:00:00Z", finishDate: "2026-10-08T00:00:00Z" } }] }, "partial", "reversed-iteration-range"],
  ])("does not invent a deadline for %j", (response, status, reason) => {
    const signals = normalizeAzureSignals(signalFixture({
      iterations: { status: "complete", response },
    }));
    expectGap(signals.iteration, status, reason);
    expect(signals.iteration.calendarPosition).toBeUndefined();
    expect(signals.iteration.deadline).toBeUndefined();
    expect(signals.coverage).toBe("limited");
  });

  test.each(["Priority", "Severity"])("a missing parent %s cannot hide behind the other valid importance field", (name) => {
    const input = signalFixture();
    const parentItem = { ...structuredClone(input.item), id: 101, rev: 4 };
    delete parentItem.fields[`Microsoft.VSTS.Common.${name}`];
    input.parent = { status: "complete", item: parentItem };
    const signals = normalizeAzureSignals(input);
    expectGap(signals.parent, "partial", "not-returned");
    expect(signals.parent.priority).toBe(name === "Priority" ? undefined : 3);
    expect(signals.parent.severity).toBe(name === "Severity" ? undefined : "3 - Medium");
    expect(signals.parent.delivery.status).toBe("complete");
    expect(signals.coverage).toBe("limited");
  });

  test("fully validated parent importance and dates allow sufficient coverage", () => {
    const input = signalFixture();
    input.parent = { status: "complete", item: { ...input.item, id: 101, rev: 4 } };
    const signals = normalizeAzureSignals(input);
    expect(signals.parent).toMatchObject({
      status: "complete", priority: 3, severity: "3 - Medium",
      importance: {
        priority: { status: "complete", sourceId: "field:101:r4:Microsoft.VSTS.Common.Priority" },
        severity: { status: "complete", sourceId: "field:101:r4:Microsoft.VSTS.Common.Severity" },
      },
    });
    expect(signals.coverage).toBe("sufficient");
  });

  test("an iteration ID or current sprint is never a fallback for a missing exact path", () => {
    const input = signalFixture();
    delete input.item.fields["System.IterationPath"];
    input.item.fields["System.IterationId"] = iteration.id;
    const signals = normalizeAzureSignals(input);
    expectGap(signals.iteration, "absent", "iteration-path-not-returned");
    expect(signals.iteration.id).toBeUndefined();
  });

  test("denied iteration reads retain a concrete next action without exposing stderr", () => {
    const signals = normalizeAzureSignals(signalFixture({
      iterations: {
        status: "inaccessible", reason: "iteration-read-forbidden",
        nextAction: "Request access to the selected team's iterations.",
      },
    }));
    expectGap(signals.iteration, "inaccessible", "iteration-read-forbidden");
    expect(signals.iteration.calendarPosition).toBeUndefined();
    expect(signals.coverage).toBe("limited");
  });

  test("parent priority and dates remain separately linked context, without child inheritance", () => {
    const input = signalFixture({
      parent: {
        status: "complete",
        item: {
          id: 101, rev: 4,
          fields: {
            "Microsoft.VSTS.Common.Priority": 1,
            "Microsoft.VSTS.Common.Severity": "1 - Critical",
            "System.CreatedDate": "2026-08-01T00:00:00Z",
            "System.ChangedDate": "2026-10-06T00:00:00Z",
            [dueReference]: "2026-10-08T00:00:00Z",
          },
        },
      },
    });
    const originalItem = structuredClone(input.item);
    const signals = normalizeAzureSignals(input);
    expect(input.item).toEqual(originalItem);
    expect(signals.parent).toMatchObject({
      status: "complete", workItemId: 101, priority: 1, severity: "1 - Critical",
    });
    expect(signals.parent.delivery.entries.find((entry: { referenceName: string }) => entry.referenceName === dueReference)).toMatchObject({
      value: "2026-10-08T00:00:00Z", sourceId: `field:101:r4:${dueReference}`,
    });
    expect(signals.sources.find((source: { id: string }) => source.id === `field:101:r4:${dueReference}`)).toMatchObject({
      workItemId: 101, revision: 4, referenceName: dueReference, value: "2026-10-08T00:00:00Z",
    });
    expect(signals.delivery.entries.find((entry: { referenceName: string }) => entry.referenceName === dueReference)?.value).toBe("2026-10-09T00:00:00Z");
    expect(signals.parent.isBlockingDelivery).toBeUndefined();
    expect(signals.parent.inheritedUrgency).toBeUndefined();
  });

  test("missing optional parent enrichment is limited, not a fabricated parent absence", () => {
    const signals = normalizeAzureSignals(signalFixture({
      parent: {
        status: "partial", reason: "parent-details-unavailable",
        nextAction: "Retry the direct parent's detail read.",
      },
    }));
    expectGap(signals.parent, "partial", "parent-details-unavailable");
    expect(signals.coverage).toBe("limited");
  });

  test.each([
    [undefined, undefined, "not-returned", "not-returned"],
    [null, "", "unset", "unset"],
    ["invalid-priority", 3, "invalid-value", "invalid-value"],
    [1.5, " ", "invalid-value", "invalid-value"],
  ])("missing or malformed parent importance %j / %j retains dates without sufficient coverage", (priority, severity, priorityReason, severityReason) => {
    const input = signalFixture();
    const parentItem: WorkItemFixture = {
      id: 101, rev: 4,
      fields: {
        ...input.item.fields,
        "Microsoft.VSTS.Common.Priority": priority,
        "Microsoft.VSTS.Common.Severity": severity,
      },
    };
    input.parent = { status: "complete", item: parentItem };
    const signals = normalizeAzureSignals(input);
    expectGap(signals.parent, "partial", priorityReason);
    expect(signals.parent.priority).toBeUndefined();
    expect(signals.parent.severity).toBeUndefined();
    expect(signals.parent).toMatchObject({
      workItemId: 101,
      importance: {
        priority: { status: priorityReason === "invalid-value" ? "partial" : "absent", reason: priorityReason, nextAction: expect.stringMatching(/\S/) },
        severity: { status: severityReason === "invalid-value" ? "partial" : "absent", reason: severityReason, nextAction: expect.stringMatching(/\S/) },
      },
      dates: { created: { status: "complete", elapsedDays: 30 }, changed: { status: "complete", elapsedDays: 1 } },
      delivery: { status: "complete" },
    });
    for (const referenceName of ["Microsoft.VSTS.Common.Priority", "Microsoft.VSTS.Common.Severity"]) {
      const value = parentItem.fields[referenceName];
      const source = signals.sources.find((candidate) => candidate.id === `field:101:r4:${referenceName}`);
      if (value === undefined) expect(source).toBeUndefined();
      else expect(source).toEqual({ id: `field:101:r4:${referenceName}`, workItemId: 101, revision: 4, referenceName, value });
    }
    expect(signals.coverage).toBe("limited");
  });

  test.each([
    [{ status: "inaccessible", reason: "metadata-unavailable", nextAction: "Retry project field metadata." }, "metadata-unavailable"],
    [{ status: "complete", fields: fieldMetadata.filter((field) => field.referenceName !== "Microsoft.VSTS.Common.Priority") }, "unsupported-field"],
    [{ status: "complete", fields: fieldMetadata.map((field) => field.referenceName === "Microsoft.VSTS.Common.Priority" ? { ...field, type: "string" } : field) }, "wrong-field-type"],
  ])("does not validate parent importance against unusable metadata %j", (metadata, reason) => {
    const input = signalFixture({ fieldMetadata: metadata as ReadFixture });
    input.parent = { status: "complete", item: { ...input.item, id: 101, rev: 4 } };
    const signals = normalizeAzureSignals(input);
    expectGap(signals.parent, "partial", reason);
    expect(signals.parent.priority).toBeUndefined();
    expect(signals.parent.dates?.created.elapsedDays).toBe(30);
    expect(signals.coverage).toBe("limited");
  });

  test("entirely unread evidence is not assessable, never an empty sufficient assessment", () => {
    const input = signalFixture({
      item: { id: 202, rev: 3, fields: {} },
      discussion: { status: "inaccessible", reason: "discussion-unavailable", nextAction: "Read comments." },
      fieldMetadata: { status: "inaccessible", reason: "metadata-unavailable", nextAction: "Read field metadata." },
      iterations: { status: "inaccessible", reason: "iterations-unavailable", nextAction: "Read team iterations." },
      parent: { status: "inaccessible", reason: "parent-unavailable", nextAction: "Read the direct parent." },
    });
    expect(normalizeAzureSignals(input).coverage).toBe("not-assessable");
  });
});

function recommendationFixture(
  fields: Record<string, unknown> = {},
  comments: ReturnType<typeof commentFixture>[] = [],
  reads: Pick<Partial<SignalFixture>, "discussion" | "parent" | "iterations"> = {},
) {
  const input = signalFixture({
    discussion: {
      status: "complete",
      pages: [{ count: comments.length, totalCount: comments.length, comments }],
    },
    ...reads,
  });
  input.item.fields = {
    "System.Title": "Synthetic outstanding work",
    "System.State": "Ready for investigation",
    "System.CreatedDate": "2026-09-01T00:00:00Z",
    "System.ChangedDate": "2026-10-07T00:00:00Z",
    "System.IterationPath": iterationPath,
    "Microsoft.VSTS.Common.Priority": 3,
    "Microsoft.VSTS.Common.Severity": "3 - Medium",
    ...fields,
  };
  return { ...input.item, signals: normalizeAzureSignals(input) };
}

function claimFixture(
  type: string,
  comment: ReturnType<typeof commentFixture>,
  overrides: Record<string, unknown> = {},
) {
  return {
    type,
    sourceIds: [`comment:202:${comment.id}:v${comment.version}`],
    excerpt: comment.text,
    provenance: "team-reported",
    ...overrides,
  };
}

function assessedFixture(claims: unknown[] = []) {
  return {
    status: "ASSESSED",
    summary: "Synthetic explanation of the remaining work.",
    claims,
  };
}

function commitmentFixture(
  date = "2026-10-09T00:00:00Z",
  referenceName = dueReference,
  isOutstanding = true,
) {
  const comment = commentFixture({
    text: isOutstanding
      ? `The package remains outstanding for the ${date} commitment.`
      : `The package for the ${date} commitment has been delivered.`,
  });
  const item = recommendationFixture({ [referenceName]: date }, [comment]);
  const claim = claimFixture("commitment", comment, {
    sourceIds: [`field:202:r3:${referenceName}`, "comment:202:7:v2"],
    date,
    isOutstanding,
  });
  return { item, claim, analysis: assessedFixture([claim]) };
}

describe("U5 source-referenced claims fail closed", () => {
  test("accepts exact current item evidence without upgrading team reports to code verification", () => {
    const { item, claim, analysis } = commitmentFixture();
    expect(azureRecommendationApi.validateAzureClaims(item, analysis)).toEqual([claim]);
    expect(analysis.claims).toEqual([claim]);
  });

  test.each([
    ["missing references", { sourceIds: [] }],
    ["unknown source", { sourceIds: ["comment:202:999:v2"] }],
    ["cross-item source", { sourceIds: ["comment:203:7:v2"] }],
    ["old comment version", { sourceIds: ["comment:202:7:v1"] }],
    ["unsupported type", { type: "priority-override" }],
    ["invented quotation", { excerpt: "A quotation that the source never contained." }],
    ["mismatched date", { date: "2026-10-10T00:00:00Z" }],
    ["unsupported provenance", { provenance: "model-verified" }],
    ["ordinary HTTPS is not code verification", {
      provenance: "code-verified",
      url: "https://dev.azure.com/example/project/_workitems/edit/202",
    }],
  ])("rejects %s before a recommendation", (_reason, overrides) => {
    const { item, claim } = commitmentFixture();
    expect(azureRecommendationApi.validateAzureClaims(item, assessedFixture([claim]))).toEqual([claim]);
    const analysis = assessedFixture([{ ...claim, ...overrides }]);
    expect(() => azureRecommendationApi.validateAzureClaims(item, analysis)).toThrow();
    expect(() => azureRecommendationApi.buildAzureRecommendation(item, analysis)).toThrow();
  });

  test("field values and the actual direct parent must match, not merely use existing IDs", () => {
    const parent = signalFixture().item;
    parent.id = 101;
    parent.rev = 4;
    const comment = commentFixture({ text: "Item #202 is required for parent #101's delivery." });
    const item = recommendationFixture({}, [comment], { parent: { status: "complete", item: parent } });
    const dependency = claimFixture("parent-dependency", comment, {
      parentId: 999, sourceIds: ["comment:202:7:v2", `field:101:r4:${dueReference}`],
      date: "2026-10-09T00:00:00Z", isOutstanding: true,
    });
    expect(azureRecommendationApi.validateAzureClaims(item, assessedFixture([
      { ...dependency, parentId: 101 },
    ]))).toEqual([{ ...dependency, parentId: 101 }]);
    expect(() => azureRecommendationApi.validateAzureClaims(item, assessedFixture([dependency]))).toThrow();
    const context = {
      type: "context", sourceIds: ["field:202:r3:Microsoft.VSTS.Common.Priority"],
      value: 1, provenance: "team-reported",
    };
    expect(azureRecommendationApi.validateAzureClaims(item, assessedFixture([
      { ...context, value: 3 },
    ]))).toEqual([{ ...context, value: 3 }]);
    expect(() => azureRecommendationApi.validateAzureClaims(item, assessedFixture([context]))).toThrow();
    item.signals.sources.push({
      id: "field:203:r3:Microsoft.VSTS.Common.Priority", workItemId: 203,
      revision: 3, referenceName: "Microsoft.VSTS.Common.Priority", value: 3,
    });
    expect(() => azureRecommendationApi.validateAzureClaims(item, assessedFixture([{
      ...context, value: 3, sourceIds: ["field:203:r3:Microsoft.VSTS.Common.Priority"],
    }]))).toThrow();
  });

  test("a missing or invalid assessment remains fatal instead of synthesizing UNASSESSED", () => {
    const item = recommendationFixture();
    expect(azureRecommendationApi.buildAzureRecommendation(item, assessedFixture()).orderGroup).toBe("native");
    for (const analysis of [undefined, null, {}, { status: "ASSESSED", summary: "" }]) {
      expect(() => azureRecommendationApi.buildAzureRecommendation(item, analysis)).toThrow();
    }
  });
});

describe("U6 current reasons change the group, never native urgency", () => {
  test.each([
    [3, "3 - Medium", "P2"],
    [3, "4 - Low", "P3"],
    [1, "3 - Medium", "P1"],
    [4, "1 - Critical", "P0"],
    [undefined, undefined, "P5"],
  ])("preserves the strongest native band for Priority %j / Severity %j", (priority, severity, nativePriority) => {
    const item = recommendationFixture({
      "Microsoft.VSTS.Common.Priority": priority,
      "Microsoft.VSTS.Common.Severity": severity,
    });
    expect(azureRecommendationApi.buildAzureRecommendation(item, assessedFixture()).nativePriority).toBe(nativePriority);
  });

  test("missing delivery dates limit coverage without discarding usable critical evidence", () => {
    const item = recommendationFixture({ "Microsoft.VSTS.Common.Severity": "1 - Critical" });
    for (const referenceName of [dueReference, targetReference]) {
      const entry = item.signals.delivery.entries.find((candidate) => candidate.referenceName === referenceName);
      if (!entry) throw new Error(`Missing delivery signal ${referenceName}`);
      expectGap(entry, "absent", "not-returned");
    }
    expect(azureRecommendationApi.buildAzureRecommendation(item, assessedFixture())).toMatchObject({
      kind: "critical-risk", orderGroup: "critical", coverage: "limited",
    });
    const complete = recommendationFixture({
      ...item.fields,
      [dueReference]: "2026-10-30T00:00:00Z",
      [targetReference]: "2026-10-30T00:00:00Z",
    });
    expect(azureRecommendationApi.buildAzureRecommendation(complete, assessedFixture())).toMatchObject({
      kind: "critical-risk", orderGroup: "critical", coverage: "sufficient",
    });
  });

  test("scenario: critical risk stays ahead of tomorrow's lower-risk commitment with both facts intact", () => {
    const criticalItem = recommendationFixture({ "Microsoft.VSTS.Common.Severity": "1 - Critical" });
    const { item, analysis } = commitmentFixture();
    const originalCritical = structuredClone(criticalItem);
    const originalDelivery = structuredClone(item);
    const critical = azureRecommendationApi.buildAzureRecommendation(criticalItem, assessedFixture());
    const delivery = azureRecommendationApi.buildAzureRecommendation(item, { ...analysis, priority: "P0" });
    expect(critical).toMatchObject({
      kind: "critical-risk", orderGroup: "critical", nativePriority: "P0",
      recommendation: "Address critical risk.", coverage: "limited",
      nextAction: "Validate the critical risk reported for item #202 before shipping.",
    });
    expect(critical.sourceIds).toContain("field:202:r3:Microsoft.VSTS.Common.Severity");
    expect(critical.whyNow).toContain("Microsoft.VSTS.Common.Severity");
    expect(critical.whyNow).toContain("1 - Critical");
    expect(delivery).toMatchObject({
      kind: "meet-commitment", orderGroup: "attention", nativePriority: "P2",
      recommendation: "Meet the commitment.", coverage: "limited",
      nextAction: "Complete the outstanding work for item #202 or confirm a revised delivery date.",
    });
    expect(delivery.sourceIds).toEqual([`field:202:r3:${dueReference}`, "comment:202:7:v2"]);
    for (const fact of [dueReference, "2026-10-09", "#7", "v2", "2026-10-07T12:00:00Z"]) {
      expect(delivery.whyNow).toContain(fact);
    }
    expect(criticalItem).toEqual(originalCritical);
    expect(item).toEqual(originalDelivery);
  });

  test.each([
    ["2026-10-07T23:59:59Z", "attention"],
    ["2026-10-08T23:59:59Z", "attention"],
    ["2026-10-15T23:59:59Z", "attention"],
    ["2026-10-16T00:30:00+02:00", "attention"],
    ["2026-10-16T00:00:00Z", "native"],
  ])("uses overdue/today/seven UTC calendar days for %s", (date, orderGroup) => {
    const { item, analysis } = commitmentFixture(date);
    expect(azureRecommendationApi.buildAzureRecommendation(item, analysis)).toMatchObject({
      orderGroup, nativePriority: "P2",
      kind: orderGroup === "attention" ? "meet-commitment" : "keep-native-order",
    });
  });

  test("explicit unresolved blockers and current commitments share one native-ranked attention group", () => {
    const comment = commentFixture({ text: "Release remains blocked by dependency alpha." });
    const blockerItem = recommendationFixture({ "Microsoft.VSTS.Common.Priority": 2 }, [comment]);
    const blocker = azureRecommendationApi.buildAzureRecommendation(
      blockerItem, assessedFixture([claimFixture("blocker", comment, { issueId: "dependency-alpha" })]),
    );
    const { item, analysis } = commitmentFixture();
    const delivery = azureRecommendationApi.buildAzureRecommendation(item, analysis);
    expect(blocker).toMatchObject({
      kind: "unblock", orderGroup: "attention", nativePriority: "P2",
      recommendation: "Unblock the work.",
      nextAction: "Resolve blocker dependency-alpha for item #202.",
    });
    expect(blocker.sourceIds).toEqual(["comment:202:7:v2"]);
    expect(blocker.whyNow).toContain("dependency-alpha");
    expect(blocker.whyNow).toContain("#7");
    expect(blocker.whyNow).toContain("v2");
    expect(delivery).toMatchObject({ orderGroup: blocker.orderGroup, nativePriority: "P2" });
  });

  test("a due field alone, fulfilled commitment, and forecast alone cannot promote", () => {
    const dueOnly = recommendationFixture({ [dueReference]: "2026-10-09T00:00:00Z" });
    const dueRecommendation = azureRecommendationApi.buildAzureRecommendation(dueOnly, assessedFixture());
    expect(dueRecommendation).toMatchObject({
      kind: "confirm-evidence", orderGroup: "native", nativePriority: "P2",
      recommendation: "Clarify the current commitment.",
      nextAction: "Confirm whether item #202 still has outstanding work for the recorded delivery date.",
    });
    expect(dueRecommendation.whyNow).toContain(dueReference);
    expect(dueRecommendation.whyNow).toContain("2026-10-09");
    const fulfilled = commitmentFixture("2026-10-09T00:00:00Z", dueReference, false);
    expect(azureRecommendationApi.buildAzureRecommendation(fulfilled.item, fulfilled.analysis)).toMatchObject({
      orderGroup: "native", nativePriority: "P2",
    });
    const forecast = commitmentFixture("2026-10-09T00:00:00Z", targetReference);
    expect(azureRecommendationApi.buildAzureRecommendation(forecast.item, assessedFixture())).toMatchObject({
      orderGroup: "native", nativePriority: "P2",
    });
    expect(azureRecommendationApi.buildAzureRecommendation(forecast.item, forecast.analysis)).toMatchObject({
      kind: "meet-commitment", orderGroup: "attention", nativePriority: "P2",
    });
    expect(azureRecommendationApi.buildAzureRecommendation(recommendationFixture(), assessedFixture())).toMatchObject({
      kind: "keep-native-order", orderGroup: "native", nativePriority: "P2",
    });
  });

  test("distinct due and forecast dates remain a visible conflict, not a silently chosen promise", () => {
    const { item, analysis } = commitmentFixture();
    const dueComment = commentFixture({ text: "The package remains outstanding for the 2026-10-09T00:00:00Z commitment." });
    const targetComment = commentFixture({
      id: 8, version: 1,
      text: "The package is also currently committed for delivery on 2026-10-12.",
    });
    const conflicting = recommendationFixture({
      ...item.fields, [targetReference]: "2026-10-12T00:00:00Z",
    }, [dueComment, targetComment]);
    const targetClaim = claimFixture("commitment", targetComment, {
      sourceIds: [`field:202:r3:${targetReference}`, "comment:202:8:v1"],
      date: "2026-10-12T00:00:00Z", isOutstanding: true,
    });
    const recommendation = azureRecommendationApi.buildAzureRecommendation(conflicting, {
      ...analysis, claims: [...analysis.claims, targetClaim],
    });
    expect(recommendation.orderGroup).toBe("native");
    expect(recommendation.kind).toBe("confirm-evidence");
    for (const fact of [dueReference, targetReference, "2026-10-09", "2026-10-12"]) {
      expect(recommendation.whyNow).toContain(fact);
    }
    expect(recommendation.nextAction).toBe("Confirm the current delivery date for item #202.");
  });
});

describe("U7 age, activity, hierarchy and sprint are not urgency", () => {
  test("scenario: an old busy ticket gets 30-day relevance review without promotion", () => {
    const comments = Array.from({ length: 12 }, (_, index) => commentFixture({ id: index + 1 }));
    const item = recommendationFixture({ "System.ChangedDate": "2026-09-08T00:00:00Z" }, comments);
    const recommendation = azureRecommendationApi.buildAzureRecommendation(item, assessedFixture());
    expect(recommendation).toMatchObject({
      kind: "review-relevance", orderGroup: "native", nativePriority: "P2",
      recommendation: "Review relevance.",
      nextAction: "Confirm whether item #202 still belongs in the backlog.",
      sourceIds: ["field:202:r3:System.ChangedDate"],
    });
    expect(recommendation.whyNow).toContain("System.ChangedDate");
    expect(recommendation.whyNow).toContain("30");
    const recent = recommendationFixture({ "System.ChangedDate": "2026-09-08T00:00:01Z" }, comments);
    expect(azureRecommendationApi.buildAzureRecommendation(recent, assessedFixture())).toMatchObject({
      kind: "keep-native-order", orderGroup: "native",
    });
    expect(azureRecommendationApi.buildAzureRecommendation(recommendationFixture({}, comments), assessedFixture())).toMatchObject({
      kind: "keep-native-order", orderGroup: "native",
    });
  });

  test("scenario: priority-1 parent dates matter only with matching outstanding dependency and commitment", () => {
    const parent = {
      id: 101, rev: 4,
      fields: {
        ...recommendationFixture().fields,
        "Microsoft.VSTS.Common.Priority": 1,
        [dueReference]: "2026-10-09T00:00:00Z",
      },
    };
    const comment = commentFixture({
      text: "Item #202 remains required for parent #101's current delivery commitment on 2026-10-09.",
    });
    const item = recommendationFixture({}, [comment], { parent: { status: "complete", item: parent } });
    expect(azureRecommendationApi.buildAzureRecommendation(item, assessedFixture())).toMatchObject({
      kind: "keep-native-order", orderGroup: "native", nativePriority: "P2",
    });
    const sourceIds = ["comment:202:7:v2", `field:101:r4:${dueReference}`];
    const dependency = claimFixture("parent-dependency", comment, {
      parentId: 101, sourceIds, isOutstanding: true,
    });
    const commitment = claimFixture("commitment", comment, {
      parentId: 101, sourceIds, date: "2026-10-09T00:00:00Z", isOutstanding: true,
    });
    expect(azureRecommendationApi.buildAzureRecommendation(item, assessedFixture([dependency]))).toMatchObject({
      orderGroup: "native", nativePriority: "P2",
    });
    const recommendation = azureRecommendationApi.buildAzureRecommendation(item, assessedFixture([dependency, commitment]));
    expect(recommendation).toMatchObject({
      kind: "meet-commitment", orderGroup: "attention", nativePriority: "P2",
    });
    expect(recommendation.sourceIds).toEqual(expect.arrayContaining(sourceIds));
    expect(recommendation.whyNow).toContain("#101");
    expect(recommendation.whyNow).toContain("2026-10-09");
    expect(item.fields["Microsoft.VSTS.Common.Priority"]).toBe(3);
  });

  test("scenario: expired sprint suggests planning review, not overdue delivery or state-derived urgency", () => {
    const expired = {
      ...iteration,
      attributes: { ...iteration.attributes, finishDate: "2026-10-07T00:00:00Z", timeFrame: "past" },
    };
    for (const state of ["Ready for investigation", "Blocked", "Closed", "Urgent"]) {
      const item = recommendationFixture({ "System.State": state }, [], {
        iterations: { status: "complete", response: { value: [expired] } },
      });
      const recommendation = azureRecommendationApi.buildAzureRecommendation(item, assessedFixture());
      expect(recommendation).toMatchObject({
        kind: "update-planning", orderGroup: "native", nativePriority: "P2",
        recommendation: "Update planning.",
        nextAction: "Confirm the current iteration for item #202.",
      });
      expect(recommendation.whyNow).toContain(iterationPath);
      expect(recommendation.whyNow).toContain("2026-10-07");
      expect(recommendation.whyNow).not.toMatch(/overdue delivery|missed delivery|unresolved blocker/i);
      expect(item.fields["System.State"]).toBe(state);
    }
  });
});

describe("U8 chronology, conflicts and limited evidence", () => {
  test.each(["blocker", "commitment"])("an older-created edited %s counterclaim retains both sources without promotion", (type) => {
    const report = commentFixture({
      id: 21, version: 1, text: "The October 9 package is outstanding, blocked by dependency alpha.",
      createdDate: "2026-10-06T10:00:00Z", modifiedDate: "2026-10-06T10:00:00Z",
    });
    for (const createdDate of ["2026-10-05T10:00:00Z", report.createdDate]) {
      const update = commentFixture({
        id: 22, version: 2, text: "Dependency alpha is resolved; the October 9 package is delivered.",
        createdDate, modifiedDate: "2026-10-07T10:00:00Z",
      });
      const item = recommendationFixture({ [dueReference]: "2026-10-09T00:00:00Z" }, [update, report]);
      const fieldSourceId = `field:202:r3:${dueReference}`;
      const claims = [report, update].map((comment, index) => claimFixture(
        type === "blocker" && index === 1 ? "blocker-resolved" : type,
        comment,
        {
          issueId: "dependency-alpha",
          ...(type === "commitment" ? {
            date: "2026-10-09T00:00:00Z", isOutstanding: index === 0,
            sourceIds: [fieldSourceId, `comment:202:${comment.id}:v${comment.version}`],
          } : {}),
        },
      ));
      expect(azureRecommendationApi.validateAzureClaims(item, assessedFixture(claims))).toEqual(claims);
      const recommendation = azureRecommendationApi.buildAzureRecommendation(item, assessedFixture(claims));
      expect(recommendation).toMatchObject({ kind: "confirm-evidence", orderGroup: "native" });
      expect(recommendation.sourceIds).toEqual(expect.arrayContaining(["comment:202:21:v1", "comment:202:22:v2"]));
      for (const fact of ["#21", "#22", createdDate, update.modifiedDate]) {
        expect(recommendation.whyNow).toContain(fact);
      }
    }
  });

  test("commitment counterclaims pair by issue identity, not a shared calendar date", () => {
    const report = commentFixture({
      id: 21, version: 1, text: "Package alpha remains unfinished for October 9.",
      createdDate: "2026-10-06T10:00:00Z", modifiedDate: "2026-10-06T10:00:00Z",
    });
    const update = commentFixture({
      id: 22, version: 1, text: "Package beta is delivered for October 9.",
      createdDate: "2026-10-07T10:00:00Z", modifiedDate: "2026-10-07T10:00:00Z",
    });
    const item = recommendationFixture({ [dueReference]: "2026-10-09T00:00:00Z" }, [report, update]);
    const claims = [report, update].map((comment, index) => claimFixture("commitment", comment, {
      issueId: index === 0 ? "package-alpha" : "package-beta", isOutstanding: index === 0,
      date: "2026-10-09T00:00:00Z",
      sourceIds: [`field:202:r3:${dueReference}`, `comment:202:${comment.id}:v1`],
    }));
    const recommendation = azureRecommendationApi.buildAzureRecommendation(item, assessedFixture(claims));
    expect(recommendation).toMatchObject({ kind: "meet-commitment", orderGroup: "attention" });
    expect(recommendation.sourceIds).toEqual([`field:202:r3:${dueReference}`, "comment:202:21:v1"]);
    const edited = { ...report, modifiedDate: "2026-10-07T18:00:00Z" };
    const conflictedItem = recommendationFixture(item.fields, [edited, update]);
    const matchingClaims = [claims[0], { ...claims[1], issueId: "package-alpha" }];
    expect(azureRecommendationApi.buildAzureRecommendation(conflictedItem, assessedFixture(matchingClaims))).toMatchObject({
      kind: "confirm-evidence", orderGroup: "native",
      sourceIds: expect.arrayContaining(["comment:202:21:v1", "comment:202:22:v1"]),
    });
  });

  test.each([
    { status: "current", isOutstanding: true, createdDate: "2026-10-07T10:00:00Z", modifiedDate: "2026-10-07T10:00:00Z" },
    { status: "withdrawn", isOutstanding: false, createdDate: "2026-10-07T10:00:00Z", modifiedDate: "2026-10-07T10:00:00Z" },
    { status: "unknown", isOutstanding: undefined, createdDate: "2026-10-07T10:00:00Z", modifiedDate: "2026-10-07T10:00:00Z" },
    { status: "edited withdrawal", isOutstanding: false, createdDate: "2026-10-05T10:00:00Z", modifiedDate: "2026-10-07T10:00:00Z" },
  ])("parent dependency $status reconciles separate comments and cites the admission evidence", ({ status, isOutstanding, createdDate, modifiedDate }) => {
    const parent = { ...signalFixture().item, id: 901, rev: 2 };
    const dependency = commentFixture({
      id: 25, version: 1, text: "Child #202 is required for parent #901 delivery.",
      createdDate: "2026-10-06T10:00:00Z", modifiedDate: "2026-10-06T10:00:00Z",
    });
    const update = commentFixture({
      id: 26, version: 1,
      text: isOutstanding === true ? "Child #202 is still required for parent #901 delivery."
        : isOutstanding === false ? "Child #202 is no longer required for parent #901 delivery."
        : "Whether child #202 is required for parent #901 delivery is unknown.",
      createdDate, modifiedDate,
    });
    const commitment = commentFixture({
      id: 27, version: 1, text: "Parent #901 delivery remains unfinished for October 9.",
      createdDate: "2026-10-07T20:00:00Z", modifiedDate: "2026-10-07T20:00:00Z",
    });
    const item = recommendationFixture({}, [commitment, update, dependency], { parent: { status: "complete", item: parent } });
    const fieldSourceId = `field:901:r2:${dueReference}`;
    const claims = [dependency, update, commitment].map((comment, index) => claimFixture(
      index === 2 ? "commitment" : "parent-dependency", comment, {
        parentId: 901, issueId: "parent-package",
        sourceIds: [fieldSourceId, `comment:202:${comment.id}:v1`],
        ...(index === 2 ? { date: "2026-10-09T00:00:00Z" } : {}),
        ...(index === 1 && isOutstanding === undefined ? {} : {
          isOutstanding: index === 1 ? isOutstanding : true,
        }),
      },
    ));
    expect(azureRecommendationApi.validateAzureClaims(item, assessedFixture(claims))).toEqual(claims);
    const recommendation = azureRecommendationApi.buildAzureRecommendation(item, assessedFixture(claims));
    expect(recommendation.orderGroup).toBe(status === "current" ? "attention" : "native");
    expect(recommendation.sourceIds).toEqual(expect.arrayContaining([fieldSourceId, "comment:202:25:v1", "comment:202:26:v1"]));
    expect(recommendation.whyNow).toContain("#25");
    expect(recommendation.whyNow).toContain("#26");
    if (status === "current") {
      expect(recommendation.kind).toBe("meet-commitment");
      expect(recommendation.sourceIds).toContain("comment:202:27:v1");
    }
    if (status === "edited withdrawal" || status === "unknown") expect(recommendation.kind).toBe("confirm-evidence");
  });

  test.each([
    { hasHistoricalDependency: true, unknownModifiedDate: "2026-10-07T10:00:00Z", hasCurrentUncertainty: false },
    { hasHistoricalDependency: false, unknownModifiedDate: "2026-10-07T10:00:00Z", hasCurrentUncertainty: false },
    { hasHistoricalDependency: true, unknownModifiedDate: "2026-10-07T11:00:00Z", hasCurrentUncertainty: false },
    { hasHistoricalDependency: false, unknownModifiedDate: "2026-10-07T11:00:00Z", hasCurrentUncertainty: false },
    { hasHistoricalDependency: true, unknownModifiedDate: "2026-10-08T08:30:00Z", hasCurrentUncertainty: true },
    { hasHistoricalDependency: false, unknownModifiedDate: "2026-10-08T08:30:00Z", hasCurrentUncertainty: true },
  ])("renewed dependency confirmation reconciles uncertainty (history=$hasHistoricalDependency, modified=$unknownModifiedDate)", ({ hasHistoricalDependency, unknownModifiedDate, hasCurrentUncertainty }) => {
    const dependency = commentFixture({
      id: 25, version: 1, text: "Child #202 is required for parent #901 package alpha delivery on October 9.",
      createdDate: "2026-10-06T10:00:00Z", modifiedDate: "2026-10-06T10:00:00Z",
    });
    const uncertainty = commentFixture({
      id: 26, version: unknownModifiedDate === "2026-10-07T10:00:00Z" ? 1 : 2,
      text: "Whether child #202 is still required for parent #901 package alpha is unknown.",
      createdDate: "2026-10-07T10:00:00Z",
      modifiedDate: unknownModifiedDate,
    });
    const confirmation = commentFixture({
      id: 28, version: 1, text: "Confirmed October 8: child #202 is still required for parent #901 package alpha delivery on October 9.",
      createdDate: "2026-10-08T08:00:00Z", modifiedDate: "2026-10-08T08:00:00Z",
    });
    const commitment = commentFixture({
      id: 27, version: 1, text: "Parent #901 package alpha remains unfinished and committed for October 9.",
      createdDate: "2026-10-08T09:00:00Z", modifiedDate: "2026-10-08T09:00:00Z",
    });
    const comments = [...(hasHistoricalDependency ? [dependency] : []), uncertainty, confirmation, commitment];
    const input = signalFixture({
      observedAt: "2026-10-08T10:00:00Z",
      discussion: { status: "complete", pages: [{ count: comments.length, totalCount: comments.length, comments }] },
      parent: { status: "complete", item: { ...signalFixture().item, id: 901, rev: 2 } },
    });
    input.item.rev = 6;
    input.item.fields["Microsoft.VSTS.Common.Severity"] = "4 - Low";
    const item = { ...input.item, signals: normalizeAzureSignals(input) };
    const fieldSourceId = `field:901:r2:${dueReference}`;
    const claims = comments.map((comment) => claimFixture(
      comment.id === 27 ? "commitment" : "parent-dependency", comment, {
        parentId: 901, issueId: "package-alpha",
        sourceIds: [fieldSourceId, `comment:202:${comment.id}:v${comment.version}`],
        ...(comment.id === 27 ? { date: "2026-10-09T00:00:00Z" } : {}),
        ...(comment.id === 26 ? {} : { isOutstanding: true }),
      },
    ));
    expect(item.signals.coverage).toBe("sufficient");
    expect(azureRecommendationApi.validateAzureClaims(item, assessedFixture(claims))).toEqual(claims);
    const recommendation = azureRecommendationApi.buildAzureRecommendation(item, assessedFixture(claims));
    expect(recommendation.kind).toBe(hasCurrentUncertainty ? "confirm-evidence" : "meet-commitment");
    expect(recommendation.orderGroup).toBe(hasCurrentUncertainty ? "native" : "attention");
    expect(recommendation.nativePriority).toBe("P3");
    expect(recommendation.sourceIds).toEqual(expect.arrayContaining([
      fieldSourceId, "comment:202:28:v1", "comment:202:27:v1",
    ]));
    for (const fact of ["#28 v1", "#27 v1", "#901"]) expect(recommendation.whyNow).toContain(fact);
    expect(recommendation.sourceIds).not.toContain("comment:202:25:v1");
    expect(recommendation.whyNow).not.toContain("#25");
    if (hasCurrentUncertainty) {
      expect(recommendation.sourceIds).toContain("comment:202:26:v2");
      expect(recommendation.sourceIds).toHaveLength(4);
      expect(recommendation.whyNow).toContain(unknownModifiedDate);
    } else {
      expect(recommendation.sourceIds).toEqual([fieldSourceId, "comment:202:27:v1", "comment:202:28:v1"]);
      for (const obsolete of ["#25", "#26", "withdrawal"]) expect(recommendation.whyNow).not.toContain(obsolete);
    }
  });

  test("sharing a parent date is not identity for separate dependency and commitment claims", () => {
    const parent = { ...signalFixture().item, id: 901, rev: 2 };
    const dependency = commentFixture({
      id: 25, version: 1, text: "Child #202 is required for parent #901 package alpha.",
      createdDate: "2026-10-06T10:00:00Z", modifiedDate: "2026-10-06T10:00:00Z",
    });
    const commitment = commentFixture({
      id: 27, version: 1, text: "Parent #901 package beta remains unfinished for October 9.",
      createdDate: "2026-10-07T10:00:00Z", modifiedDate: "2026-10-07T10:00:00Z",
    });
    const item = recommendationFixture({}, [dependency, commitment], { parent: { status: "complete", item: parent } });
    const claims = [dependency, commitment].map((comment, index) => claimFixture(
      index === 0 ? "parent-dependency" : "commitment", comment, {
        parentId: 901, issueId: index === 0 ? "package-alpha" : "package-beta", isOutstanding: true,
        sourceIds: [`field:901:r2:${dueReference}`, `comment:202:${comment.id}:v1`],
        ...(index === 1 ? { date: "2026-10-09T00:00:00Z" } : {}),
      },
    ));
    const recommendation = azureRecommendationApi.buildAzureRecommendation(item, assessedFixture(claims));
    expect(recommendation.orderGroup).toBe("native");
    expect(recommendation.kind).not.toBe("meet-commitment");
  });

  test("an unedited earlier counterclaim cannot withdraw a newer explicit report", () => {
    const resolved = commentFixture({
      id: 21, version: 1, text: "Package alpha is delivered and its blocker is resolved.",
      createdDate: "2026-10-05T10:00:00Z", modifiedDate: "2026-10-05T10:00:00Z",
    });
    const outstanding = commentFixture({
      id: 22, version: 1, text: "Package alpha is blocked again and unfinished for October 9.",
      createdDate: "2026-10-06T10:00:00Z", modifiedDate: "2026-10-06T10:00:00Z",
    });
    const item = recommendationFixture({ [dueReference]: "2026-10-09T00:00:00Z" }, [outstanding, resolved]);
    for (const type of ["blocker", "commitment"]) {
      const claims = [resolved, outstanding].map((comment, index) => claimFixture(
        type === "blocker" && index === 0 ? "blocker-resolved" : type, comment, {
          issueId: "package-alpha",
          ...(type === "commitment" ? {
            date: "2026-10-09T00:00:00Z", isOutstanding: index === 1,
            sourceIds: [`field:202:r3:${dueReference}`, `comment:202:${comment.id}:v1`],
          } : {}),
        },
      ));
      const recommendation = azureRecommendationApi.buildAzureRecommendation(item, assessedFixture(claims));
      expect(recommendation.orderGroup).toBe("attention");
      expect(recommendation.sourceIds).toContain("comment:202:22:v1");
      expect(recommendation.sourceIds).not.toContain("comment:202:21:v1");
    }
  });

  test.each(["unknown", "unpaired", "edited outstanding"])("a parent's %s child dependency requires clarification", (status) => {
    const parent = { ...signalFixture().item, id: 901, rev: 2 };
    const dependency = commentFixture({
      id: 25, version: 1,
      text: status === "unknown" ? "Whether child #202 is required for parent #901 is unknown."
        : "Child #202 is required for parent #901 package alpha.",
      createdDate: "2026-10-06T10:00:00Z",
      modifiedDate: status === "edited outstanding" ? "2026-10-07T20:00:00Z" : "2026-10-06T10:00:00Z",
    });
    const withdrawal = commentFixture({
      id: 26, version: 1, text: "Child #202 is no longer required for parent #901 package alpha.",
      createdDate: "2026-10-07T10:00:00Z", modifiedDate: "2026-10-07T10:00:00Z",
    });
    const commitment = commentFixture({
      id: 27, version: 1, text: "Parent #901 package alpha remains unfinished for October 9.",
      createdDate: "2026-10-07T21:00:00Z", modifiedDate: "2026-10-07T21:00:00Z",
    });
    const comments = status === "edited outstanding" ? [dependency, withdrawal, commitment] : [dependency, commitment];
    const item = recommendationFixture({}, comments, { parent: { status: "complete", item: parent } });
    const claims = comments.map((comment) => claimFixture(comment.id === 27 ? "commitment" : "parent-dependency", comment, {
      parentId: 901,
      ...(status === "unpaired" ? {} : { issueId: "package-alpha" }),
      sourceIds: [`field:901:r2:${dueReference}`, `comment:202:${comment.id}:v1`],
      ...(comment.id === 27 ? { date: "2026-10-09T00:00:00Z" } : {}),
      ...(status === "unknown" && comment.id === 25 ? {} : { isOutstanding: comment.id !== 26 }),
    }));
    const recommendation = azureRecommendationApi.buildAzureRecommendation(item, assessedFixture(claims));
    expect(recommendation).toMatchObject({ kind: "confirm-evidence", orderGroup: "native" });
    expect(recommendation.sourceIds).toEqual(expect.arrayContaining(["comment:202:25:v1", "comment:202:27:v1"]));
    if (status === "edited outstanding") expect(recommendation.sourceIds).toContain("comment:202:26:v1");
  });

  test("scenario: only a later explicit resolution of the same blocker removes attention", () => {
    const blocker = commentFixture({
      text: "Release is blocked by dependency alpha.",
      createdDate: "2026-10-05T12:00:00Z", modifiedDate: "2026-10-05T12:00:00Z",
    });
    const resolution = commentFixture({
      id: 8, version: 1, text: "Dependency alpha has been resolved.",
      createdDate: "2026-10-07T12:00:00Z", modifiedDate: "2026-10-07T12:00:00Z",
    });
    const item = recommendationFixture({}, [resolution, blocker]);
    const blockerClaim = claimFixture("blocker", blocker, { issueId: "dependency-alpha" });
    const resolutionClaim = claimFixture("blocker-resolved", resolution, { issueId: "dependency-alpha" });
    const resolved = azureRecommendationApi.buildAzureRecommendation(item, assessedFixture([resolutionClaim, blockerClaim]));
    expect(resolved).toMatchObject({
      kind: "keep-native-order", orderGroup: "native", nativePriority: "P2",
      recommendation: "Keep native order.",
      nextAction: "Continue item #202 in native Azure priority order.",
    });
    expect(resolved.sourceIds).toEqual(expect.arrayContaining(["comment:202:7:v2", "comment:202:8:v1"]));
    expect(resolved.whyNow).toContain("resolved");
    expect(resolved.whyNow).toContain("#8");
    expect(resolved.whyNow).toContain("dependency-alpha");
    const unrelatedResolution = commentFixture({
      ...resolution, text: "Dependency beta has been resolved.",
    });
    const unrelatedItem = recommendationFixture({}, [blocker, unrelatedResolution]);
    const unrelated = claimFixture("blocker-resolved", unrelatedResolution, { issueId: "dependency-beta" });
    expect(azureRecommendationApi.buildAzureRecommendation(unrelatedItem, assessedFixture([blockerClaim, unrelated]))).toMatchObject({
      kind: "unblock", orderGroup: "attention",
    });
  });

  test("an edited old blocker conflicting with a later resolution requires clarification, not fabricated urgency", () => {
    const edited = commentFixture({
      text: "Release is blocked again by dependency alpha.",
      createdDate: "2026-10-05T12:00:00Z", modifiedDate: "2026-10-07T18:00:00Z",
    });
    const resolution = commentFixture({
      id: 8, version: 1, text: "Dependency alpha has been resolved.",
      createdDate: "2026-10-07T12:00:00Z", modifiedDate: "2026-10-07T12:00:00Z",
    });
    const item = recommendationFixture({}, [edited, resolution]);
    const recommendation = azureRecommendationApi.buildAzureRecommendation(item, assessedFixture([
      claimFixture("blocker", edited, { issueId: "dependency-alpha" }),
      claimFixture("blocker-resolved", resolution, { issueId: "dependency-alpha" }),
    ]));
    expect(recommendation).toMatchObject({
      kind: "confirm-evidence", orderGroup: "native", nativePriority: "P2",
      nextAction: "Clarify the conflicting blocker reports for item #202.",
    });
    for (const fact of ["#7", "#8", "2026-10-07T18:00:00Z", "2026-10-07T12:00:00Z"]) {
      expect(recommendation.whyNow).toContain(fact);
    }
  });

  test("partial chronology cannot prove a current blocker, commitment or no blockers; critical fields remain usable", () => {
    const comment = commentFixture({ text: "Release is blocked by dependency alpha." });
    const discussion: ReadFixture = {
      status: "partial", reason: "remaining-comments-unavailable",
      nextAction: "Fetch the remaining comments for item #202.",
      pages: [{ count: 1, totalCount: 2, comments: [comment], continuationToken: "next-page" }],
    };
    const item = recommendationFixture({}, [comment], { discussion });
    const claims = assessedFixture([claimFixture("blocker", comment, { issueId: "dependency-alpha" })]);
    const recommendation = azureRecommendationApi.buildAzureRecommendation(item, claims);
    expect(recommendation).toMatchObject({
      kind: "confirm-evidence", orderGroup: "native", coverage: "limited",
      nextAction: discussion.nextAction,
    });
    expect(recommendation.whyNow).toContain("remaining-comments-unavailable");
    expect(recommendation.whyNow).not.toMatch(/no blockers|unresolved blocker/i);
    const critical = recommendationFixture({ "Microsoft.VSTS.Common.Severity": "1 - Critical" }, [comment], { discussion });
    expect(azureRecommendationApi.buildAzureRecommendation(critical, claims)).toMatchObject({
      kind: "critical-risk", orderGroup: "critical", nativePriority: "P0", coverage: "limited",
    });
    const commitment = commitmentFixture();
    const partialCommitment = recommendationFixture(commitment.item.fields, [], {
      discussion: {
        ...discussion,
        pages: [{ count: 1, totalCount: 2, comments: [commentFixture({
          text: "The package remains outstanding for the 2026-10-09T00:00:00Z commitment.",
        })], continuationToken: "next-page" }],
      },
    });
    expect(azureRecommendationApi.buildAzureRecommendation(partialCommitment, commitment.analysis)).toMatchObject({
      kind: "confirm-evidence", orderGroup: "native", coverage: "limited",
      nextAction: discussion.nextAction,
    });
  });

  test("explicit UNASSESSED remains last and not assessable, even with native critical fields", () => {
    const item = recommendationFixture({ "Microsoft.VSTS.Common.Severity": "1 - Critical" });
    expect(azureRecommendationApi.buildAzureRecommendation(item, { status: "UNASSESSED" })).toMatchObject({
      kind: "not-assessable", orderGroup: "unassessed", nativePriority: "P0",
      recommendation: "Not assessable.", coverage: "not-assessable",
      nextAction: "Assess the evidence for item #202 before recommending work.",
      sourceIds: [],
    });
  });
});
