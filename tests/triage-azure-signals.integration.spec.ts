import { describe, expect, test } from "bun:test";
import {
  collectAzureBacklog,
  createAzureDevOpsInvoker,
  type AzureInvokeRequest,
  type AzureWorkItem,
} from "../skills/ai-triage/scripts/collect-azure.mjs";
import { writeAzureTriageReport } from "../skills/ai-triage/scripts/render-report.mjs";
import { resolveTargetAndRead } from "../skills/ai-triage/scripts/resolve-target.mjs";

const scope = {
  organization: "https://dev.azure.com/synthetic-org",
  project: "synthetic-project",
  team: "synthetic-team",
  backlogId: "stories",
};
const observedAt = "2026-10-08T12:00:00Z";
const projectId = "fa918c8b-73ef-43d7-8f62-f664bae82720";
const otherProjectId = "ea918c8b-73ef-43d7-8f62-f664bae82720";
const projectPath = `/_apis/projects/${scope.project}`;
const backlogPath = `/${scope.project}/${scope.team}/_apis/work/backlogs`;
const membershipPath = `${backlogPath}/${scope.backlogId}/workItems`;
const batchPath = `/${scope.project}/_apis/wit/workitemsbatch`;
const fieldsPath = `/${scope.project}/_apis/wit/fields`;
const iterationsPath = `/${scope.project}/${scope.team}/_apis/work/teamsettings/iterations`;
const relatedFields = ["System.WorkItemType", "System.State", "System.Title"];
const parentFields = [
  ...relatedFields,
  "Microsoft.VSTS.Common.Priority",
  "Microsoft.VSTS.Common.Severity",
  "System.CreatedDate",
  "System.ChangedDate",
  "Microsoft.VSTS.Scheduling.DueDate",
  "Microsoft.VSTS.Scheduling.TargetDate",
];
const fieldMetadata = [
  ["System.WorkItemType", "string"],
  ["System.State", "string"],
  ["System.Title", "string"],
  ["System.CreatedDate", "dateTime"],
  ["System.ChangedDate", "dateTime"],
  ["Microsoft.VSTS.Common.Priority", "integer"],
  ["Microsoft.VSTS.Common.Severity", "string"],
  ["Microsoft.VSTS.Scheduling.DueDate", "dateTime"],
  ["Microsoft.VSTS.Scheduling.TargetDate", "dateTime"],
  ["Custom.DeliveryDate", "dateTime"],
].map(([referenceName, type]) => ({ referenceName, type, name: referenceName }));
const iteration = {
  id: "5ca918c8-73ef-43d7-8f62-f664bae82720",
  name: "Sprint 7",
  path: "Synthetic Project\\Sprint 7",
  attributes: {
    startDate: "2026-10-01T00:00:00Z",
    finishDate: "2026-10-15T00:00:00Z",
    timeFrame: "current",
  },
};

type SignalRequest = Omit<AzureInvokeRequest, "apiVersion"> & {
  apiVersion: string;
  query?: Record<string, string | number | boolean>;
};
type Comment = {
  id?: number;
  commentId?: number;
  workItemId: number;
  version: number;
  text: string;
  createdDate: string;
  modifiedDate: string;
  isDeleted?: boolean;
  createdBy?: { displayName: string; uniqueName: string };
  modifiedBy?: { displayName: string };
  mentions?: unknown[];
  reactions?: unknown[];
};
type CommentPage = {
  count: number;
  totalCount: number;
  comments: Comment[];
  continuationToken?: string;
  nextPage?: string;
};
type FixtureOptions = {
  items?: AzureWorkItem[];
  relatives?: AzureWorkItem[];
  pages?: unknown[];
  limit?: number | null;
  fields?: unknown;
  iterations?: unknown;
  failRequest?: (request: SignalRequest) => Error | undefined;
  batchResponse?: (
    request: SignalRequest,
    items: AzureWorkItem[],
  ) => AzureWorkItem[];
};

function commentsPath(id: number): string {
  return `/${scope.project}/_apis/wit/workItems/${id}/comments`;
}

function makeItem(
  id: number,
  fields: Record<string, unknown> = {},
  relations: NonNullable<AzureWorkItem["relations"]> = [],
): AzureWorkItem {
  const item = {
    id,
    rev: 7,
    fields: {
      "System.WorkItemType": "Story",
      "System.State": "Ready for product review",
      "System.Title": `Synthetic work item ${id}`,
      "System.CreatedDate": "2026-09-08T12:00:00Z",
      "System.ChangedDate": "2026-10-06T12:00:00Z",
      "System.IterationPath": iteration.path,
      "System.IterationId": 17,
      "Microsoft.VSTS.Common.Priority": 2,
      "Microsoft.VSTS.Common.Severity": "3 - Medium",
      "Microsoft.VSTS.Scheduling.DueDate": "2026-10-09T00:00:00Z",
      "Microsoft.VSTS.Scheduling.TargetDate": "2026-10-12T00:00:00Z",
      "Custom.DeliveryDate": "2026-10-08T00:00:00Z",
      ...fields,
    },
    relations,
  };
  return item;
}

function hierarchy(
  id: number,
  direction = "Reverse",
  relatedProjectId = projectId,
): NonNullable<AzureWorkItem["relations"]>[number] {
  return {
    rel: `System.LinkTypes.Hierarchy-${direction}`,
    url: `${scope.organization}/${relatedProjectId}/_apis/wit/workItems/${id}`,
  };
}

function makeComment(id: number, workItemId = 101): Comment {
  return {
    id,
    workItemId,
    version: 2,
    text: `Synthetic discussion ${id}`,
    createdDate: "2026-10-06T10:00:00Z",
    modifiedDate: "2026-10-07T10:00:00Z",
    createdBy: {
      displayName: "Synthetic identity marker",
      uniqueName: "synthetic-private-identity-marker",
    },
    modifiedBy: { displayName: "Synthetic identity marker" },
    mentions: [{ artifactId: "synthetic-mention-marker" }],
    reactions: [{ type: "synthetic-reaction-marker" }],
  };
}

function makePage(
  comments: Comment[],
  totalCount = comments.length,
  continuationToken?: string,
): CommentPage {
  return {
    count: comments.length,
    totalCount,
    comments,
    ...(continuationToken
      ? {
          continuationToken,
          nextPage: `${scope.organization}${commentsPath(101)}?${new URLSearchParams({
            "api-version": "7.1-preview.4",
            continuationToken,
          })}`,
        }
      : {}),
  };
}

function createFixture(options: FixtureOptions = {}) {
  const calls: SignalRequest[] = [];
  const cliCalls: string[][] = [];
  const items = options.items ?? [makeItem(101)];
  const relatives = options.relatives ?? [];
  const itemsById = new Map([...items, ...relatives].map((item) => [item.id, item]));
  const pages = options.pages ?? [makePage([])];
  let pageIndex = 0;

  const invoke = async (request: SignalRequest): Promise<unknown> => {
    calls.push(request);
    const failure = options.failRequest?.(request);
    if (failure) throw failure;
    if (request.path === backlogPath) {
      return {
        count: 1,
        value: [{
          id: scope.backlogId,
          ...(options.limit === null
            ? {}
            : { workItemCountLimit: options.limit ?? 1000 }),
        }],
      };
    }
    if (request.path === membershipPath) {
      return {
        workItems: items.map(({ id }) => ({
          target: { id, url: `${scope.organization}/${projectId}/_apis/wit/workItems/${id}` },
        })),
      };
    }
    if (request.path === projectPath) return { id: projectId };
    if (request.path === batchPath) {
      const selectedDetails = (request.body?.ids ?? []).flatMap((id) => {
        const item = itemsById.get(id);
        if (!item) return [];
        const fields = request.body?.fields;
        if (!fields) return [item];
        return [{
          id,
          rev: 7,
          fields: Object.fromEntries(
            fields.filter((field) => field in item.fields)
              .map((field) => [field, item.fields[field]]),
          ),
        }];
      });
      return {
        count: selectedDetails.length,
        value: options.batchResponse?.(request, selectedDetails) ?? selectedDetails,
      };
    }
    if (request.path === fieldsPath) {
      return options.fields ?? { count: fieldMetadata.length, value: fieldMetadata };
    }
    if (request.path === iterationsPath) {
      return options.iterations ?? { count: 1, value: [iteration] };
    }
    if (items.some(({ id }) => request.path === commentsPath(id))) {
      if (request.path !== commentsPath(101)) return makePage([]);
      const page = pages[pageIndex++];
      if (page === undefined) throw cliFailure("ERROR: Service Unavailable");
      return page;
    }
    throw new Error("Unexpected synthetic scoped read");
  };

  const run = async (args: string[]): Promise<string> => {
    cliCalls.push(args);
    const urlArgument = args[args.indexOf("--url") + 1];
    const method = args[args.indexOf("--method") + 1];
    if (!urlArgument || (method !== "get" && method !== "post")) {
      throw new Error("Invalid synthetic az argument array");
    }
    const url = new URL(urlArgument);
    const bodyIndex = args.indexOf("--body");
    const body = bodyIndex < 0 ? undefined : args[bodyIndex + 1];
    const apiVersion = url.searchParams.get("api-version");
    if (!apiVersion) throw new Error("Synthetic request lacks an API version");
    url.searchParams.delete("api-version");
    return JSON.stringify(await invoke({
      ...scope,
      method: method === "get" ? "GET" : "POST",
      path: url.pathname.slice("/synthetic-org".length),
      apiVersion,
      ...(url.searchParams.size ? { query: Object.fromEntries(url.searchParams) } : {}),
      ...(body === undefined ? {} : { body: JSON.parse(body) }),
    }));
  };

  return {
    calls,
    cliCalls,
    invoke,
    run,
    collect: (isCli = false) => {
      const input = {
        ...scope,
        observedAt,
        invoke: isCli ? createAzureDevOpsInvoker({ ...scope, run }) : invoke,
      };
      return collectAzureBacklog(input);
    },
  };
}

function cliFailure(stderr: string, code: string | number = 1): Error {
  return Object.assign(new Error("Synthetic az process failed"), { stderr, code });
}

function expectCommentCoverage(
  item: AzureWorkItem | undefined,
  status: string,
  totalCount?: number,
  reason?: string,
): void {
  expect(item).toMatchObject({
    signals: {
      discussion: {
        status,
        ...(totalCount === undefined ? {} : { totalCount }),
        ...(status === "complete" || status === "absent"
          ? {}
          : {
              reason: reason ?? expect.stringMatching(/\S/),
              nextAction: expect.stringMatching(/\S/),
            }),
      },
      coverage: status === "partial" || status === "inaccessible"
        ? "limited"
        : "sufficient",
    },
  });
}

describe("Azure signal adapter read allowlist (A1)", () => {
  test("passes exact scoped versions and encoded opaque continuation values to bare az rest", async () => {
    const token = "opaque +/&?api-version=1#segment";
    const fixture = createFixture({
      pages: [
        makePage([makeComment(1)], 2, token),
        makePage([makeComment(2)], 2),
      ],
    });
    await fixture.collect(true);
    const commentCalls = fixture.cliCalls.filter((args) =>
      args.some((argument) => argument.includes("/comments?")),
    );
    expect(commentCalls).toHaveLength(2);
    const urls = commentCalls.map((args) => {
      const argument = args[args.indexOf("--url") + 1];
      if (!argument) throw new Error("Missing synthetic CLI URL");
      return new URL(argument);
    });
    for (const [index, args] of commentCalls.entries()) {
      const url = urls[index];
      if (!url) throw new Error("Missing synthetic parsed URL");
      expect(args).toEqual([
        "rest", "--method", "get", "--url", url.href,
        "--resource", "499b84ac-1321-427f-aa17-267ca6975798",
        "--only-show-errors", "--output", "json",
      ]);
      expect(url.origin + url.pathname).toBe(`${scope.organization}${commentsPath(101)}`);
      expect(Object.fromEntries(url.searchParams)).toEqual({
        "api-version": "7.1-preview.4",
        "$top": "200",
        order: "asc",
        includeDeleted: "true",
        ...(index === 1 ? { continuationToken: token } : {}),
      });
    }
    expect(urls[1]?.href).toContain(`continuationToken=${encodeURIComponent(token).replace(/%20/g, "+")}`);
    expect(fixture.calls.filter(({ path }) => path === fieldsPath)).toEqual([
      { ...scope, method: "GET", path: fieldsPath, apiVersion: "7.1" },
    ]);
    expect(fixture.calls.filter(({ path }) => path === iterationsPath)).toEqual([
      { ...scope, method: "GET", path: iterationsPath, apiVersion: "7.1" },
    ]);
  });

  const unsafeRequests = [
    { name: "organization scope escape", organization: "https://dev.azure.com/another-org" },
    { name: "project scope escape", project: "another-project" },
    { name: "team scope escape", team: "another-team" },
    { name: "backlog scope escape", backlogId: "features" },
    { name: "unselected comment ID", path: commentsPath(901), apiVersion: "7.1-preview.4" },
    { name: "cross-project fields", path: "/another-project/_apis/wit/fields" },
    { name: "cross-team iterations", path: `/${scope.project}/another-team/_apis/work/teamsettings/iterations` },
    { name: "wrong fields version", path: fieldsPath, apiVersion: "7.1-preview.4" },
    { name: "wrong comments version", path: commentsPath(101) },
    { name: "raw nextPage URL", path: `${scope.organization}${commentsPath(101)}` },
    { name: "GET body", path: membershipPath, body: { ids: [101], errorPolicy: "Fail" } },
    { name: "arbitrary comment query", path: commentsPath(101), apiVersion: "7.1-preview.4", query: { expand: "all" } },
    { name: "comment version query override", path: commentsPath(101), apiVersion: "7.1-preview.4", query: { "api-version": "1" } },
    { name: "iteration timeframe fallback", path: iterationsPath, query: { "$timeframe": "Current" } },
    { name: "arbitrary field query", path: fieldsPath, query: { fields: "Custom.SecretDate" } },
    { name: "raw URL override", path: membershipPath, url: "https://example.invalid/private" },
    { name: "mutation method", path: membershipPath, method: "DELETE" },
    { name: "mutation route", method: "POST", path: `/${scope.project}/_apis/wit/workItems/101` },
    { name: "oversize inventory batch", method: "POST", path: batchPath, body: { ids: Array.from({ length: 201 }, (_, index) => index + 1), errorPolicy: "Fail", "$expand": "Relations" } },
    { name: "duplicate batch IDs", method: "POST", path: batchPath, body: { ids: [101, 101], errorPolicy: "Fail", "$expand": "Relations" } },
    { name: "invalid batch IDs", method: "POST", path: batchPath, body: { ids: [0, -1, 1.5], errorPolicy: "Fail", "$expand": "Relations" } },
    { name: "unsafe batch keys", method: "POST", path: batchPath, body: { ids: [101], errorPolicy: "Fail", "$expand": "Relations", bypassRules: true } },
    { name: "custom projection", method: "POST", path: batchPath, body: { ids: [901], errorPolicy: "Fail", fields: ["Custom.DeliveryDate"] } },
  ];
  test.each(unsafeRequests)("rejects $name before CLI execution", async ({ name: _name, ...overrides }) => {
    const calls: string[][] = [];
    const invoke = createAzureDevOpsInvoker({
      ...scope,
      run: async (args) => {
        calls.push(args);
        return JSON.stringify({ workItems: [{ target: { id: 101 } }] });
      },
    });
    await invoke({ ...scope, method: "GET", path: membershipPath, apiVersion: "7.1" });
    calls.length = 0;
    const request: AzureInvokeRequest = {
      ...scope, method: "GET", path: membershipPath, apiVersion: "7.1",
    };
    const failure = await invoke(Object.assign(request, overrides)).then(
      () => undefined,
      (error: unknown) => error,
    );
    expect(failure).toBeInstanceOf(Error);
    expect(calls).toEqual([]);
  });
});

describe("Azure comment pagination and provenance (A2)", () => {
  test("reads two full pages plus terminal tombstone and reconciles all 401 declared comments", async () => {
    const comments = Array.from({ length: 400 }, (_, index) => makeComment(index + 1));
    const tombstone = { ...makeComment(401), text: "deleted-private-body-marker", isDeleted: true };
    const fixture = createFixture({
      pages: [
        makePage(comments.slice(0, 200), 401, "page +/2"),
        makePage(comments.slice(200).map((comment) => {
          if (comment.id !== 400) return comment;
          const { id, ...exampleComment } = comment;
          return { ...exampleComment, commentId: id };
        }), 401, "page ?&3"),
        makePage([tombstone], 401),
      ],
    });
    const inventory = await fixture.collect();
    expectCommentCoverage(inventory.items[0], "complete", 401);
    expect(inventory).toMatchObject({ complete: true, observedAt });
    expect(inventory.items[0]).toHaveProperty(
      "signals.discussion.comments",
      [
            ...comments.map(({ id, workItemId, version, text, createdDate, modifiedDate }) => ({
              id, workItemId, version, text, createdDate, modifiedDate,
              isDeleted: false,
              sourceId: `comment:101:${id}:v2`,
            })),
            {
              id: 401, workItemId: 101, version: 2, isDeleted: true,
              createdDate: tombstone.createdDate, modifiedDate: tombstone.modifiedDate,
            },
      ],
    );
    expect(inventory.items[0]).not.toMatchObject({
      signals: { sources: expect.arrayContaining([expect.objectContaining({ id: "comment:101:401:v2" })]) },
    });
    const requests = fixture.calls.filter(({ path }) => path === commentsPath(101));
    expect(requests).toEqual([
      { ...scope, method: "GET", path: commentsPath(101), apiVersion: "7.1-preview.4", query: { "$top": 200, order: "asc", includeDeleted: true } },
      { ...scope, method: "GET", path: commentsPath(101), apiVersion: "7.1-preview.4", query: { "$top": 200, order: "asc", includeDeleted: true, continuationToken: "page +/2" } },
      { ...scope, method: "GET", path: commentsPath(101), apiVersion: "7.1-preview.4", query: { "$top": 200, order: "asc", includeDeleted: true, continuationToken: "page ?&3" } },
    ]);
    const normalized = JSON.stringify(inventory);
    for (const marker of ["deleted-private-body-marker", "synthetic-private-identity-marker", "Synthetic identity marker", "synthetic-mention-marker", "synthetic-reaction-marker"]) {
      expect(normalized).not.toContain(marker);
    }
  });

  test("keeps a terminal zero-comment response explicitly absent with a proven zero count", async () => {
    const fixture = createFixture();
    const inventory = await fixture.collect();
    expectCommentCoverage(inventory.items[0], "absent", 0);
    expect(inventory.items[0]).toMatchObject({ signals: { discussion: { comments: [] } } });
    expect(fixture.calls.filter(({ path }) => path === commentsPath(101))).toHaveLength(1);
  });

  test.each([false, true])("accepts verified project-GUID pagination with a parent present: %s", async (hasParent) => {
    const token = "second +/&";
    const fixture = createFixture({
      items: [makeItem(101, {}, hasParent ? [hierarchy(901)] : [])],
      relatives: hasParent ? [makeItem(901)] : [],
      pages: [
        {
          ...makePage([makeComment(1)], 2, token),
          nextPage: `${scope.organization}/${projectId.toUpperCase()}/_apis/wit/workItems/101/comments?${new URLSearchParams({
            "api-version": "7.1-preview.4", continuationToken: token, ignored: "never-executed",
          })}`,
        },
        makePage([makeComment(2)], 2),
      ],
    });
    const inventory = await fixture.collect(true);
    expectCommentCoverage(inventory.items[0], "complete", 2);
    expect(inventory.items[0]?.signals?.discussion.comments.map(({ id }) => id)).toEqual([1, 2]);
    expect(fixture.calls.filter(({ path }) => path === projectPath)).toHaveLength(1);
    const commentCalls = fixture.calls.filter(({ path }) => path.endsWith("/comments"));
    expect(commentCalls.map(({ path }) => path)).toEqual([commentsPath(101), commentsPath(101)]);
    expect(commentCalls[1]?.query).toEqual({
      "$top": "200", order: "asc", includeDeleted: "true", continuationToken: token,
    });
    expect(fixture.cliCalls.every((args) => !args.join(" ").includes("never-executed"))).toBe(true);
  });

  const incompletePages = [
    { name: "repeated token", reason: "repeated-continuation-token", pages: [makePage([makeComment(1)], 3, "repeat"), makePage([makeComment(2)], 3, "repeat")] },
    { name: "changing totals", reason: "comment-total-drift", pages: [makePage([makeComment(1)], 2, "second"), makePage([makeComment(2)], 3)] },
    { name: "duplicate ID", reason: "duplicate-comment-id", pages: [makePage([makeComment(1)], 2, "second"), makePage([makeComment(1)], 2)] },
    { name: "mislinked work item", reason: "comment-item-mismatch", pages: [makePage([makeComment(1)], 2, "second"), makePage([makeComment(2, 999)], 2)] },
    { name: "inaccurate page count", reason: "comment-count-mismatch", pages: [makePage([makeComment(1)], 2, "second"), { ...makePage([makeComment(2)], 2), count: 0 }] },
    { name: "conflicting ID aliases", reason: "conflicting-comment-id", pages: [makePage([makeComment(1)], 2, "second"), makePage([{ ...makeComment(2), commentId: 3 }], 2)] },
    { name: "invalid version", reason: "invalid-comment-version", pages: [makePage([makeComment(1)], 2, "second"), makePage([{ ...makeComment(2), version: 0 }], 2)] },
    { name: "malformed timestamp", reason: "invalid-comment-date", pages: [makePage([makeComment(1)], 2, "second"), makePage([{ ...makeComment(2), createdDate: "last week" }], 2)] },
    { name: "malformed page envelope", pages: [makePage([makeComment(1)], 2, "second"), { count: 1, totalCount: 2, comments: null }] },
    { name: "missing last page", pages: [makePage([makeComment(1)], 2, "second")] },
    { name: "terminal count mismatch", reason: "missing-comment-page", pages: [makePage([makeComment(1)], 3, "second"), makePage([makeComment(2)], 3)] },
    { name: "nextPage without a token", reason: "contradictory-continuation", pages: [{ ...makePage([makeComment(1)], 2), nextPage: `${scope.organization}${commentsPath(101)}?continuationToken=second` }] },
    { name: "contradictory nextPage token", reason: "contradictory-continuation", pages: [{ ...makePage([makeComment(1)], 2, "second"), nextPage: `${scope.organization}${commentsPath(101)}?continuationToken=other` }] },
    { name: "scope-escaping nextPage", pages: [{ ...makePage([makeComment(1)], 2, "second"), nextPage: "https://example.invalid/another-project/comments?continuationToken=second" }] },
    { name: "different project GUID", reason: "contradictory-continuation", pages: [{ ...makePage([makeComment(1)], 2, "second"), nextPage: `${scope.organization}/${otherProjectId}/_apis/wit/workItems/101/comments?continuationToken=second` }] },
    { name: "different organization with the same GUID", reason: "contradictory-continuation", pages: [{ ...makePage([makeComment(1)], 2, "second"), nextPage: `https://dev.azure.com/other-org/${projectId}/_apis/wit/workItems/101/comments?continuationToken=second` }] },
  ];
  test.each(incompletePages)("marks $name partial rather than absent or complete", async ({ pages, reason }) => {
    const fixture = createFixture({ pages });
    const inventory = await fixture.collect();
    expect(inventory.complete).toBe(true);
    expectCommentCoverage(inventory.items[0], "partial", undefined, reason);
    expect(fixture.calls.filter(({ path }) => path === commentsPath(101)).length).toBeLessThanOrEqual(3);
    expect(fixture.calls.every(({ path }) => !path.startsWith("http"))).toBe(true);
  });
});

describe("Azure membership and scoped cached enrichment (A3–A4)", () => {
  test("preserves exact selected IDs and literal states, never adding related evidence as rows", async () => {
    const items = [
      makeItem(101, { "System.State": "Done in this board" }, [hierarchy(901)]),
      makeItem(102, { "System.State": "Won't fix" }, [hierarchy(902, "Forward")]),
      makeItem(103, { "System.State": "Custom intake state" }),
    ];
    const fixture = createFixture({ items, relatives: [makeItem(901), makeItem(902)] });
    const inventory = await fixture.collect();
    expect(inventory.items.map(({ id }) => id)).toEqual([101, 102, 103]);
    expect(inventory.items.map(({ fields }) => fields["System.State"])).toEqual([
      "Done in this board", "Won't fix", "Custom intake state",
    ]);
    expect(inventory.items.map(({ fields }) => fields["Microsoft.VSTS.Common.Priority"])).toEqual([2, 2, 2]);
    expect(inventory.items[0]).toMatchObject({ signals: expect.any(Object) });
    for (const item of inventory.items) {
      expect(item).toMatchObject({
        signals: {
          observedAt,
          dates: {
            created: { status: "complete", value: "2026-09-08T12:00:00Z", elapsedDays: 30 },
            changed: { status: "complete", value: "2026-10-06T12:00:00Z", elapsedDays: 2 },
          },
          sources: expect.arrayContaining([{
            id: `field:${item.id}:r7:System.CreatedDate`,
            workItemId: item.id,
            revision: 7,
            referenceName: "System.CreatedDate",
            value: "2026-09-08T12:00:00Z",
          }]),
        },
      });
    }
    expect(fixture.calls.filter(({ path }) => path.endsWith("/comments")).map(({ path }) => path)).toEqual([
      commentsPath(101), commentsPath(102), commentsPath(103),
    ]);
  });

  test("reads shared metadata once, reuses selected parents and enriches only distinct direct same-project parents", async () => {
    const items = [
      makeItem(101, {}, [hierarchy(901), hierarchy(902, "Forward"), hierarchy(904, "Reverse", otherProjectId)]),
      makeItem(102, {}, [hierarchy(901)]),
      makeItem(103, {}, [hierarchy(102)]),
    ];
    const relatives = [
      makeItem(901, { "Microsoft.VSTS.Common.Priority": 1 }, [hierarchy(903)]),
      makeItem(902),
      makeItem(903),
      makeItem(904),
    ];
    const fixture = createFixture({ items, relatives });
    const inventory = await fixture.collect();
    expect(fixture.calls.filter(({ path }) => path === fieldsPath)).toHaveLength(1);
    expect(fixture.calls.filter(({ path }) => path === iterationsPath)).toHaveLength(1);
    const projections = fixture.calls.filter(({ body }) => body?.fields);
    expect(projections.map(({ body }) => body)).toEqual([
      { ids: [901, 902], fields: relatedFields, errorPolicy: "Fail" },
      { ids: [901], fields: parentFields, errorPolicy: "Fail" },
    ]);
    expect(fixture.calls.filter(({ body }) => body?.ids.includes(903) || body?.ids.includes(904))).toEqual([]);
    expect(inventory.items[0]).toMatchObject({
      signals: {
        parent: {
          status: "complete",
          workItemId: 901,
          priority: 1,
          delivery: {
            entries: expect.arrayContaining([{
              referenceName: "Microsoft.VSTS.Scheduling.DueDate",
              value: "2026-10-09T00:00:00Z",
              semantics: "due",
              status: "complete",
              sourceId: "field:901:r7:Microsoft.VSTS.Scheduling.DueDate",
            }]),
          },
        },
        iteration: { status: "complete", id: iteration.id, path: iteration.path },
        sources: expect.arrayContaining([{
          id: "field:901:r7:Microsoft.VSTS.Scheduling.DueDate",
          workItemId: 901,
          revision: 7,
          referenceName: "Microsoft.VSTS.Scheduling.DueDate",
          value: "2026-10-09T00:00:00Z",
        }]),
      },
    });
    expect(inventory.items[2]).toMatchObject({
      signals: { parent: { status: "complete", workItemId: 102 } },
    });
    expect(inventory.items.map(({ fields }) => fields["Microsoft.VSTS.Common.Priority"])).toEqual([2, 2, 2]);
  });

  test("partitions 201 distinct optional parents into 200 and 1 without unbounded traversal", async () => {
    const items = Array.from({ length: 201 }, (_, index) =>
      makeItem(index + 101, {}, [hierarchy(index + 1001)]),
    );
    const relatives = Array.from({ length: 201 }, (_, index) => makeItem(index + 1001));
    const fixture = createFixture({ items, relatives });
    const inventory = await fixture.collect();
    expect(inventory.items.map(({ id }) => id)).toEqual(items.map(({ id }) => id));
    const enrichment = fixture.calls.filter(({ body }) =>
      body?.fields?.includes("Microsoft.VSTS.Common.Priority"),
    );
    expect(enrichment.map(({ body }) => body?.ids.length)).toEqual([200, 1]);
    expect(enrichment.flatMap(({ body }) => body?.ids ?? [])).toEqual(relatives.map(({ id }) => id));
    expect(fixture.calls.filter(({ body }) => body).every(({ body }) =>
      body !== undefined && body.ids.length <= 200 && body.errorPolicy === "Fail",
    )).toBe(true);
  });

  test("a missing optional parent retains mandatory hierarchy and marks coverage limited", async () => {
    const fixture = createFixture({
      items: [makeItem(101, {}, [hierarchy(901)])],
      relatives: [makeItem(901)],
      batchResponse: (request, details) =>
        request.body?.fields?.includes("Microsoft.VSTS.Common.Priority") ? [] : details,
    });
    const inventory = await fixture.collect();
    expect(inventory.items[0]).toMatchObject({
      relations: [{ relatedItem: { id: 901, title: "Synthetic work item 901" } }],
      signals: {
        parent: {
          status: "partial",
          reason: "parent-details-unavailable",
          nextAction: expect.stringMatching(/\S/),
        },
        coverage: "limited",
      },
    });
  });

  test("optional parent projections cannot acquire meaning from wrong-type or custom date metadata", async () => {
    const metadata = fieldMetadata.filter(({ referenceName }) =>
      referenceName !== "Microsoft.VSTS.Scheduling.TargetDate",
    ).map((field) => field.referenceName === "Microsoft.VSTS.Scheduling.DueDate"
      ? { ...field, type: "string" }
      : field);
    const fixture = createFixture({
      items: [makeItem(101, {}, [hierarchy(901)])],
      relatives: [makeItem(901)],
      fields: { count: metadata.length, value: metadata },
    });
    const inventory = await fixture.collect();
    const projections = fixture.calls.filter(({ body }) =>
      body?.fields?.includes("Microsoft.VSTS.Common.Priority"),
    );
    expect(projections.map(({ body }) => body)).toEqual([{
      ids: [901],
      fields: parentFields.filter((field) =>
        field !== "Microsoft.VSTS.Scheduling.DueDate" &&
        field !== "Microsoft.VSTS.Scheduling.TargetDate",
      ),
      errorPolicy: "Fail",
    }]);
    expect(inventory.items[0]).toMatchObject({
      signals: {
        delivery: {
          entries: expect.arrayContaining([expect.objectContaining({
            referenceName: "Custom.DeliveryDate",
            value: "2026-10-08T00:00:00Z",
            semantics: "unrecognized",
          })]),
        },
      },
    });
  });

  const inventoryFailures: Array<{ name: string; options: FixtureOptions }> = [
    { name: "unknown membership cap", options: { limit: null } },
    { name: "at-cap membership", options: { limit: 1 } },
    { name: "missing selected detail", options: { batchResponse: () => [] } },
    { name: "missing mandatory related context", options: {
      items: [makeItem(101, {}, [hierarchy(901)])],
      relatives: [makeItem(901)],
      batchResponse: (request: SignalRequest, details: AzureWorkItem[]) =>
        request.body?.fields?.length === 3 ? [] : details,
    } },
    { name: "inventory Unauthorized", options: {
      failRequest: (request: SignalRequest) =>
        request.path === membershipPath ? cliFailure("ERROR: Unauthorized") : undefined,
    } },
  ];
  test.each(inventoryFailures)("stops $name before optional reads or writer invocation and preserves the prior report", async ({ options }) => {
    const fixture = createFixture(options);
    const previousReport = "<html>previous synthetic report</html>";
    let report = previousReport;
    let writeCount = 0;
    const failure = await (async () => {
      const inventory = await fixture.collect();
      await writeAzureTriageReport({
        scope: { ...scope, provider: "azure-devops", backlogName: "Synthetic stories" },
        inventory,
        analyzeItem: async () => ({ status: "UNASSESSED" }),
        writeFile: async (_path, contents) => { report = contents; writeCount++; },
      });
    })().then(
      () => undefined,
      (error: unknown) => error,
    );
    expect(failure).toBeInstanceOf(Error);
    expect(writeCount).toBe(0);
    expect(report).toBe(previousReport);
    expect(fixture.calls.filter(({ path }) =>
      path === fieldsPath || path === iterationsPath || path.endsWith("/comments"),
    )).toEqual([]);
  });
});

describe("Azure optional permission and fatal authentication classification (A5)", () => {
  test.each([
    { name: "project field metadata", path: fieldsPath, signal: "delivery" },
    { name: "selected-team iterations", path: iterationsPath, signal: "iteration" },
  ])("keeps a confirmed Forbidden $name read inaccessible rather than absent", async ({ path, signal }) => {
    const fixture = createFixture({
      failRequest: (request) => request.path === path
        ? cliFailure('ERROR: Forbidden({"message":"synthetic-private-stderr-marker"})')
        : undefined,
    });
    const inventory = await fixture.collect(true);
    expect(inventory.items[0]).toMatchObject({
      signals: {
        [signal]: {
          status: "inaccessible",
          reason: expect.stringMatching(/\S/),
          nextAction: expect.stringMatching(/\S/),
        },
        coverage: "limited",
      },
    });
    expect(JSON.stringify(inventory)).not.toContain("synthetic-private-stderr-marker");
  });

  test("classifies only an anchored optional Forbidden reason and never retains raw diagnostics", async () => {
    const marker = "synthetic-private-stderr-marker";
    const fixture = createFixture({
      failRequest: (request) => request.path === commentsPath(101)
        ? cliFailure(`ERROR: Forbidden({"message":"${marker}","createdBy":"synthetic-identity-marker"})`)
        : undefined,
    });
    const inventory = await fixture.collect(true);
    expectCommentCoverage(inventory.items[0], "inaccessible");
    expect(inventory.items[0]).toMatchObject({
      signals: { discussion: { reason: "permission-denied" } },
    });
    expect(JSON.stringify(inventory)).not.toContain(marker);
    expect(JSON.stringify(inventory)).not.toContain("synthetic-identity-marker");
  });

  test.each([
    { name: "429", failure: cliFailure("ERROR: Too Many Requests") },
    { name: "500", failure: cliFailure("ERROR: Internal Server Error") },
    { name: "503", failure: cliFailure("ERROR: Service Unavailable") },
    { name: "buffer interruption", failure: cliFailure("", "ERR_CHILD_PROCESS_STDIO_MAXBUFFER") },
    { name: "timeout interruption", failure: cliFailure("", "ETIMEDOUT") },
  ])("keeps a $name interrupted second page partial with earlier evidence", async ({ failure }) => {
    let commentReads = 0;
    const fixture = createFixture({
      pages: [makePage([makeComment(1)], 2, "second")],
      failRequest: (request) => {
        if (request.path !== commentsPath(101)) return undefined;
        commentReads++;
        return commentReads === 2 ? failure : undefined;
      },
    });
    const inventory = await fixture.collect(true);
    expectCommentCoverage(inventory.items[0], "partial");
    expect(inventory.items[0]).toMatchObject({
      signals: { discussion: { comments: [expect.objectContaining({ id: 1, text: "Synthetic discussion 1" })] } },
    });
    expect(commentReads).toBe(2);
  });

  test.each([
    "ERROR: Unauthorized",
    "ERROR: Please run 'az login' to setup account.",
    'ERROR: Bad Request({"message":"Forbidden"})',
    "ERROR: unknown-prefix Forbidden",
    '{"message":"Forbidden","status":403}',
    "ERROR: synthetic-private-stderr-marker",
  ])("keeps an unrecognized or authentication failure fatal on optional reads: %s", async (stderr) => {
    const fixture = createFixture({
      failRequest: (request) =>
        request.path === commentsPath(101) ? cliFailure(stderr) : undefined,
    });
    const outcome = fixture.collect(true).then(
      () => "unexpected success",
      (error: unknown) => error,
    );
    const failure = await outcome;
    expect(failure).toBeInstanceOf(Error);
    expect(String(failure)).not.toContain(stderr);
  });
});

describe("Azure enriched inventory compatibility (A6)", () => {
  test("writes every enriched UNASSESSED member once in inventory order", async () => {
    const fixture = createFixture({
      items: [
        makeItem(101, { "Microsoft.VSTS.Common.Priority": 3 }),
        makeItem(102, { "Microsoft.VSTS.Common.Priority": 1 }),
        makeItem(103, { "Microsoft.VSTS.Common.Priority": 2 }),
      ],
    });
    const inventory = await fixture.collect();
    expect(inventory.items.map(({ id }) => id)).toEqual([101, 102, 103]);
    expect(inventory.items[0]).toMatchObject({ signals: expect.any(Object) });
    let report = "";
    const analyzed: number[] = [];
    await writeAzureTriageReport({
      scope: { ...scope, provider: "azure-devops", backlogName: "Synthetic stories" },
      inventory,
      analyzeItem: async (item: AzureWorkItem) => {
        analyzed.push(item.id);
        return { status: "UNASSESSED" };
      },
      writeFile: async (_path, contents) => { report = contents; },
    });
    expect(analyzed.sort((first, second) => first - second)).toEqual([101, 102, 103]);
    expect([...report.matchAll(/<details class="item" id="i(\d+)"/g)].map((match) => Number(match[1]))).toEqual([101, 102, 103]);
    expect(report).toContain("Priority 3");
  });

  test("resolver ambiguity makes zero inventory or new evidence reads", async () => {
    const fixture = createFixture();
    const result = await resolveTargetAndRead({
      remotes: [
        "https://dev.azure.com/synthetic-org/synthetic-project/_git/synthetic-repo",
      ],
    }, async () => fixture.collect());
    expect(result).toEqual({ status: "needs-answer", field: "team" });
    expect(fixture.calls).toEqual([]);
    expect(fixture.cliCalls).toEqual([]);
  });
});
