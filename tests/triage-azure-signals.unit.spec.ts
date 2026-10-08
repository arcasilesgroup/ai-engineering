import { describe, expect, test } from "bun:test";
import { normalizeAzureDiscussion, normalizeAzureSignals } from "../skills/ai-triage/scripts/azure-signals.mjs";

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
