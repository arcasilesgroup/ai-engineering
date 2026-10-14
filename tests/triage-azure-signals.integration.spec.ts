import { randomUUID } from "node:crypto";
import { mkdir, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { describe, expect, test } from "bun:test";
import {
  collectAzureBacklog,
  createAzureDevOpsInvoker,
  type AzureInvokeRequest,
  type AzureWorkItem,
} from "../skills/ai-triage/scripts/collect-azure.mjs";
import {
  atomicWriteReport,
  writeAzureTriageReport,
} from "../skills/ai-triage/scripts/render-report.mjs";
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
  pagesByItem?: Record<number, unknown[]>;
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
  const pageIndices = new Map<number, number>();

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
    const recentItem = [...items, ...relatives].find(({ id }) =>
      request.path === commentsPath(id) && Number(request.query?.["$top"]) === 5
    );
    if (recentItem) {
      const recentPages = options.pagesByItem?.[recentItem.id] ??
        (recentItem.id === 101 ? pages : [makePage([])]);
      const comments = recentPages.flatMap((page) =>
        (page as CommentPage).comments ?? []
      ).filter((comment) => !comment.isDeleted).sort((first, second) =>
        Date.parse(second.createdDate) - Date.parse(first.createdDate) ||
        (second.id ?? second.commentId ?? 0) - (first.id ?? first.commentId ?? 0)
      );
      return {
        count: Math.min(comments.length, 5),
        totalCount: (recentPages.at(-1) as CommentPage | undefined)?.totalCount ?? comments.length,
        comments: comments.slice(0, 5),
      };
    }
    if (items.some(({ id }) => request.path === commentsPath(id))) {
      const selectedItem = items.find(({ id }) => request.path === commentsPath(id));
      const selectedPages = selectedItem && options.pagesByItem?.[selectedItem.id];
      if (selectedItem && selectedPages) {
        const index = pageIndices.get(selectedItem.id) ?? 0;
        pageIndices.set(selectedItem.id, index + 1);
        const page = selectedPages[index];
        if (page === undefined) throw cliFailure("ERROR: Service Unavailable");
        return page;
      }
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
    collect: (isCli = false, includeSignals = true) => {
      const input = {
        ...scope,
        observedAt,
        includeSignals,
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
    expect(commentCalls.map(({ path }) => path)).toEqual([
      ...(hasParent ? [commentsPath(901)] : []),
      commentsPath(101), commentsPath(101),
    ]);
    expect(commentCalls.at(-1)?.query).toEqual({
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
      commentsPath(901), commentsPath(902),
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
    expect(commentReads).toBe(3);
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
  test.each([false, true])("integrates recent hierarchy context without replacing full grounded discussion (signals=%s)", async (includeSignals) => {
    const comments = [
      datedComment(1, 101, "Package alpha is blocked.", "2026-10-01T10:00:00Z"),
      datedComment(2, 101, "Package alpha is resolved.", "2026-10-02T10:00:00Z"),
      ...Array.from({ length: 5 }, (_, index) =>
        datedComment(index + 3, 101, `Unrelated context ${index + 3}.`, "2026-10-03T10:00:00Z")
      ),
    ];
    const parentComment = datedComment(91, 901, "<script>syntheticAttack()</script> token=synthetic-comment-secret", "2026-10-04T10:00:00Z");
    const fixture = createFixture({
      items: [makeItem(101, {}, [hierarchy(901), hierarchy(902, "Forward"), hierarchy(903, "Reverse", otherProjectId)])],
      relatives: [makeItem(901), makeItem(902), makeItem(903)],
      pagesByItem: {
        101: [makePage(comments.slice(0, 2), 7, "next"), makePage(comments.slice(2), 7)],
        901: [makePage([parentComment])],
      },
    });
    const inventory = await fixture.collect(true, includeSignals);
    expect(inventory.items.map(({ id }) => id)).toEqual([101]);
    expect(inventory.items[0]?.comments?.items.map(({ id }) => id)).toEqual([7, 6, 5, 4, 3]);
    expect(inventory.items[0]?.relations?.[0]?.relatedItem?.comments?.items).toEqual([
      { id: 91, text: parentComment.text, createdDate: parentComment.createdDate },
    ]);
    expect(fixture.calls.filter(({ path }) => path === commentsPath(903))).toEqual([]);
    const selectedReads = fixture.calls.filter(({ path }) => path === commentsPath(101));
    expect(selectedReads.map(({ query }) => query)).toEqual(includeSignals ? [
      { "$top": "200", order: "asc", includeDeleted: "true" },
      { "$top": "200", order: "asc", includeDeleted: "true", continuationToken: "next" },
    ] : [{ "$top": "5", order: "desc" }]);
    if (includeSignals) {
      expect(inventory.items[0]?.signals?.discussion.comments.map(({ id }) => id)).toEqual([1, 2, 3, 4, 5, 6, 7]);
    } else {
      expect(inventory.items[0]?.signals).toBeUndefined();
      expect(fixture.calls.filter(({ path }) => path === fieldsPath || path === iterationsPath)).toEqual([]);
    }
    let report = "";
    await writeAzureTriageReport({
      scope: reportScope, inventory,
      analyzeItem: async () => ({
        status: "ASSESSED", summary: "Synthetic integration.",
        whyNow: "MODEL_TIMING_MARKER", confidence: "HIGH", confidenceBasis: "MODEL_CONFIDENCE_MARKER",
        claims: includeSignals ? [
          { type: "blocker", sourceIds: ["comment:101:1:v1"], excerpt: comments[0]?.text, issueId: "package-alpha", provenance: "team-reported" },
          { type: "blocker-resolved", sourceIds: ["comment:101:2:v1"], excerpt: comments[1]?.text, issueId: "package-alpha", provenance: "team-reported" },
        ] : [],
      }),
      writeFile: async (_path, contents) => { report = contents; },
    });
    expect(report).toContain("Latest 5 of 7");
    expect(report).toContain("&lt;script&gt;syntheticAttack()&lt;/script&gt; [redacted]");
    expect(report).not.toContain("synthetic-comment-secret");
    expect(rankedIds(report)).toEqual([101]);
    if (includeSignals) {
      expect(signalRow(itemMarkup(report, 101), "Why now")).toMatch(/#2 v1|resolv/i);
      expect(signalRow(itemMarkup(report, 101), "Confidence")).toMatch(/HIGH|MEDIUM|LOW/);
      expect(report).not.toContain("MODEL_TIMING_MARKER");
      expect(report).not.toContain("MODEL_CONFIDENCE_MARKER");
      expect(signalRow(itemMarkup(report, 101), "Recommendation")).not.toContain("Unblock the work.");
    } else {
      expect(signalRow(itemMarkup(report, 101), "Why now")).toContain("MODEL_TIMING_MARKER");
      expect(signalRow(itemMarkup(report, 101), "Confidence")).toContain("MODEL_CONFIDENCE_MARKER");
    }
  });

  test("uses the fixed latest-five window when selected chronology is partial", async () => {
    const oldComments = [
      makeComment(1, 101),
      makeComment(2, 101),
    ];
    const recentComments = Array.from({ length: 5 }, (_, index) =>
      makeComment(index + 3, 101)
    );
    const fixture = createFixture({
      pagesByItem: {
        101: [
          makePage(oldComments, 7, "next"),
          makePage(recentComments, 7),
        ],
      },
      failRequest: (request) => request.query?.continuationToken
        ? cliFailure("ERROR: Service Unavailable") : undefined,
    });

    const inventory = await fixture.collect(true);

    expectCommentCoverage(inventory.items[0], "partial", 7);
    expect(inventory.items[0]?.comments).toMatchObject({
      status: "partial",
      reason: "recent-comment-window",
      totalCount: 7,
      items: [{ id: 7 }, { id: 6 }, { id: 5 }, { id: 4 }, { id: 3 }],
    });
    expect(fixture.calls.filter(({ path }) => path === commentsPath(101)).map(({ query }) => query)).toEqual([
      { "$top": "200", order: "asc", includeDeleted: "true" },
      { "$top": "200", order: "asc", includeDeleted: "true", continuationToken: "next" },
      { "$top": "5", order: "desc" },
    ]);
  });

  test("optional recent hierarchy failures remain gaps, not absent discussion", async () => {
    const fixture = createFixture({
      items: [makeItem(101, {}, [hierarchy(901)])],
      relatives: [makeItem(901)],
      failRequest: (request) => request.path === commentsPath(901)
        ? cliFailure("ERROR: Forbidden") : undefined,
    });
    const inventory = await fixture.collect(true);
    expectCommentCoverage(inventory.items[0], "absent", 0);
    expect({ ...inventory.items[0]?.relations?.[0]?.relatedItem?.comments }).toMatchObject({
      status: "inaccessible", reason: "permission-denied", nextAction: expect.stringMatching(/\S/),
    });
    let report = "";
    await writeAzureTriageReport({
      scope: reportScope, inventory,
      analyzeItem: async () => ({ status: "ASSESSED", summary: "Context unavailable.", claims: [] }),
      writeFile: async (_path, contents) => { report = contents; },
    });
    expect(signalRow(itemMarkup(report, 101), "Recent comments")).toMatch(/inaccessible.*permission-denied/i);
    expect(report).not.toMatch(/no blockers|no unresolved blockers/i);
  });

  test.each([false, true])("bounds recent comment reads to five in flight (signals=%s)", async (includeSignals) => {
    const fixture = createFixture({
      items: Array.from({ length: 12 }, (_, index) =>
        makeItem(index + 101, {}, [hierarchy(index + 901)])
      ),
      relatives: Array.from({ length: 12 }, (_, index) => makeItem(index + 901)),
    });
    let activeReads = 0;
    let maxActiveReads = 0;
    const invoke = createAzureDevOpsInvoker({
      ...scope,
      run: async (args) => {
        const url = new URL(args[args.indexOf("--url") + 1] ?? "");
        if (url.searchParams.get("$top") !== "5") return fixture.run(args);
        activeReads++;
        maxActiveReads = Math.max(maxActiveReads, activeReads);
        await new Promise((resolve) => setTimeout(resolve, 1));
        try {
          return await fixture.run(args);
        } finally {
          activeReads--;
        }
      },
    });
    const inventory = await collectAzureBacklog({ ...scope, observedAt, includeSignals, invoke });
    expect(inventory.items).toHaveLength(12);
    expect(maxActiveReads).toBe(5);
    expect(activeReads).toBe(0);
    const recentReads = fixture.calls.filter(({ query }) => Number(query?.["$top"]) === 5);
    expect(recentReads).toHaveLength(includeSignals ? 12 : 24);
    expect(new Set(recentReads.map(({ path }) => path)).size).toBe(recentReads.length);
  });

  test("writes every enriched UNASSESSED member once in inventory order", async () => {
    const fixture = createFixture({
      items: [
        makeItem(101, { "Microsoft.VSTS.Common.Priority": 3 }),
        makeItem(102, { "Microsoft.VSTS.Common.Priority": 1 }),
        makeItem(103, { "Microsoft.VSTS.Common.Priority": 2 }),
      ],
    });
    const inventory = await fixture.collect();
    const inventoryBeforeReport = structuredClone(inventory);
    expect(inventory.items.map(({ id }) => id)).toEqual([101, 102, 103]);
    expect(structuredClone(inventory.items[0])).toMatchObject({ signals: expect.any(Object) });
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
    expect(inventory).toEqual(inventoryBeforeReport);
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

type GroundedClaim = {
  type: "blocker" | "blocker-resolved" | "commitment" | "parent-dependency" | "context";
  sourceIds: string[];
  provenance: "team-reported" | "code-verified";
  excerpt?: string;
  value?: unknown;
  issueId?: string;
  date?: string;
  parentId?: number;
  isOutstanding?: boolean;
  url?: string;
};

const reportScope = {
  ...scope, provider: "azure-devops" as const, backlogName: "Synthetic stories",
};
const previousReport = Buffer.from("<html>Previous synthetic report ✓</html>\n");
const dueReference = "Microsoft.VSTS.Scheduling.DueDate";
const deliveryExcerpt = "Delivery package remains outstanding for 2026-10-09.";
const blockerExcerpt = "Blocked on package format.";
const resolutionExcerpt = "Package format is settled; that blocker is resolved.";
const expiredIteration = {
  ...iteration,
  id: "expired-synthetic-iteration",
  name: "Previous sprint",
  path: "Synthetic Project\\Previous sprint",
  attributes: {
    startDate: "2026-09-15T00:00:00Z",
    finishDate: "2026-10-01T00:00:00Z",
    timeFrame: "past",
  },
};

function fieldId(id: number, referenceName: string): string {
  return `field:${id}:r7:${referenceName}`;
}

function datedComment(id: number, workItemId: number, text: string, date: string): Comment {
  return { ...makeComment(id, workItemId), version: 1, text, createdDate: date, modifiedDate: date };
}

function recommendationFixture(overrides: FixtureOptions = {}) {
  const { pagesByItem, ...fixtureOverrides } = overrides;
  const ordinaryFields = {
    [dueReference]: "2026-10-30T00:00:00Z",
    "Microsoft.VSTS.Scheduling.TargetDate": "2026-10-30T00:00:00Z",
  };
  return createFixture({
    items: [
      makeItem(203, {
        ...ordinaryFields,
        "System.Title": "Review old package request",
        "System.CreatedDate": "2026-07-01T12:00:00Z",
        "System.ChangedDate": "2026-08-20T12:00:00Z",
      }),
      makeItem(204, {
        ...ordinaryFields,
        "System.Title": "Child planning task",
        "System.IterationPath": expiredIteration.path,
        "Microsoft.VSTS.Common.Priority": 4,
        "Microsoft.VSTS.Common.Severity": "4 - Low",
      }, [hierarchy(901)]),
      makeItem(202, {
        ...ordinaryFields,
        "System.Title": "Prepare delivery package",
        "Microsoft.VSTS.Common.Priority": 3,
        "Microsoft.VSTS.Common.Severity": "4 - Low",
        [dueReference]: "2026-10-09T00:00:00Z",
        "Microsoft.VSTS.Scheduling.TargetDate": "2026-10-09T00:00:00Z",
      }),
      makeItem(201, {
        ...ordinaryFields,
        "System.WorkItemType": "Bug",
        "System.Title": "Investigate critical write loss",
        "Microsoft.VSTS.Common.Priority": 1,
        "Microsoft.VSTS.Common.Severity": "1 - Critical",
      }),
      makeItem(205, {
        ...ordinaryFields,
        "System.Title": "Ordinary native-order task",
        "Microsoft.VSTS.Common.Priority": 4,
        "Microsoft.VSTS.Common.Severity": "4 - Low",
      }),
      makeItem(206, {
        ...ordinaryFields,
        "System.Title": "Unassessed synthetic task",
        "Microsoft.VSTS.Common.Priority": 1,
      }),
    ],
    relatives: [makeItem(901, {
      "System.Title": "Priority-one parent context",
      "System.WorkItemType": "Feature",
      "Microsoft.VSTS.Common.Priority": 1,
      "Microsoft.VSTS.Common.Severity": "2 - High",
    })],
    iterations: { count: 2, value: [iteration, expiredIteration] },
    pagesByItem: {
      202: [makePage([datedComment(21, 202, deliveryExcerpt, "2026-10-08T10:00:00Z")])],
      203: [makePage([
        datedComment(31, 203, blockerExcerpt, "2026-08-10T12:00:00Z"),
        datedComment(32, 203, resolutionExcerpt, "2026-08-20T12:00:00Z"),
        datedComment(33, 203, "Format discussion recorded for reference.", "2026-08-20T12:00:00Z"),
      ])],
      ...pagesByItem,
    },
    ...fixtureOverrides,
  });
}

function groundedAnalysis(item: AzureWorkItem) {
  const claims: GroundedClaim[] = [];
  if (item.id === 202) {
    claims.push({
      type: "commitment", provenance: "team-reported", isOutstanding: true,
      sourceIds: [fieldId(202, dueReference), "comment:202:21:v1"],
      excerpt: deliveryExcerpt, value: "2026-10-09T00:00:00Z", date: "2026-10-09T00:00:00Z",
    });
  }
  if (item.id === 203) {
    claims.push(
      {
        type: "blocker", provenance: "team-reported", issueId: "package-format",
        sourceIds: ["comment:203:31:v1"], excerpt: blockerExcerpt,
      },
      {
        type: "blocker-resolved", provenance: "team-reported", issueId: "package-format",
        sourceIds: ["comment:203:32:v1"], excerpt: resolutionExcerpt,
      },
    );
  }
  if (item.id === 204) {
    claims.push({
      type: "context", provenance: "team-reported", parentId: 901,
      sourceIds: [fieldId(901, "Microsoft.VSTS.Common.Priority")], value: 1,
    });
  }
  return {
    status: item.id === 206 ? "UNASSESSED" : "ASSESSED",
    priority: "P0", summary: `Analysis-only marker for ${item.id}.`,
    claims, evidence: [],
  };
}

function itemMarkup(report: string, id: number): string {
  const markup = report.match(new RegExp(`<details\\b[^>]*\\bid="i${id}"[^>]*>[\\s\\S]*?<\\/details>`))?.[0];
  if (!markup) throw new Error(`Missing report item ${id}`);
  return markup;
}

function signalRow(markup: string, label: string): string {
  const row = markup.match(new RegExp(
    `<span class="ilbl">${label}<\\/span>([\\s\\S]*?)(?=<div class="kv"|<\\/details>)`,
  ))?.[1];
  if (!row) throw new Error(`Missing rendered ${label} row`);
  return row;
}

function rankedIds(report: string): number[] {
  return [...report.matchAll(/<details\b[^>]*\bid="i(\d+)"/g)].map((match) => Number(match[1]));
}

async function renderSignalFixture(fixture: ReturnType<typeof createFixture>) {
  const inventory = await fixture.collect();
  let report = "";
  const analyzedIds: number[] = [];
  let activeAnalyses = 0;
  let maxActiveAnalyses = 0;
  let writeCount = 0;
  await writeAzureTriageReport({
    scope: reportScope, inventory,
    analyzeItem: async (item: AzureWorkItem) => {
      analyzedIds.push(item.id);
      activeAnalyses++;
      maxActiveAnalyses = Math.max(maxActiveAnalyses, activeAnalyses);
      await new Promise((resolve) => setTimeout(resolve, 1));
      activeAnalyses--;
      return groundedAnalysis(item);
    },
    writeFile: async (_path, contents) => {
      expect(activeAnalyses).toBe(0);
      expect(analyzedIds).toHaveLength(inventory.items.length);
      writeCount++;
      report = contents;
    },
  });
  return { report, inventory, analyzedIds, maxActiveAnalyses, writeCount };
}

describe("Evidence-led Azure collect → analyze → report (A7)", () => {
  test.each(["blocker", "commitment"])("edited older %s counterclaims publish clarification in native order", async (type) => {
    const reportComment = datedComment(21, 202, "Package alpha remains blocked and unfinished for October 9.", "2026-10-06T10:00:00Z");
    const update = {
      ...datedComment(22, 202, "Package alpha is delivered and its dependency is resolved.", "2026-10-05T10:00:00Z"),
      version: 2, modifiedDate: "2026-10-07T10:00:00Z",
    };
    const fixture = createFixture({
      items: [
        makeItem(203, { "Microsoft.VSTS.Common.Priority": 1, "Microsoft.VSTS.Common.Severity": "4 - Low" }),
        makeItem(202, { "Microsoft.VSTS.Common.Priority": 3, "Microsoft.VSTS.Common.Severity": "4 - Low", [dueReference]: "2026-10-09T00:00:00Z" }),
      ],
      pagesByItem: { 202: [makePage([update, reportComment])] },
    });
    const inventory = await fixture.collect();
    let report = "";
    let writeCount = 0;
    await writeAzureTriageReport({
      scope: reportScope, inventory,
      analyzeItem: async (item: AzureWorkItem) => ({
        status: "ASSESSED", summary: "Synthetic edited chronology.", evidence: [],
        claims: item.id !== 202 ? [] : [reportComment, update].map((comment, index) => ({
          type: type === "blocker" && index === 1 ? "blocker-resolved" : type,
          provenance: "team-reported", issueId: "package-alpha", excerpt: comment.text,
          sourceIds: [...(type === "commitment" ? [fieldId(202, dueReference)] : []), `comment:202:${comment.id}:v${comment.version}`],
          ...(type === "commitment" ? { date: "2026-10-09T00:00:00Z", isOutstanding: index === 0 } : {}),
        })),
      }),
      writeFile: async (_path, contents) => { writeCount++; report = contents; },
    });
    expect(writeCount).toBe(1);
    expect(rankedIds(report)).toEqual([203, 202]);
    const markup = itemMarkup(report, 202);
    expect(signalRow(markup, "Recommendation")).toContain("Clarify");
    for (const fact of ["#21 v1", "#22 v2", "2026-10-07T10:00:00Z"]) {
      expect(signalRow(markup, "Why now")).toContain(fact);
    }
  });

  test.each([
    { status: "current", isOutstanding: true, createdDate: "2026-10-07T10:00:00Z", modifiedDate: "2026-10-07T10:00:00Z" },
    { status: "withdrawn", isOutstanding: false, createdDate: "2026-10-07T10:00:00Z", modifiedDate: "2026-10-07T10:00:00Z" },
    { status: "unknown", isOutstanding: undefined, createdDate: "2026-10-07T10:00:00Z", modifiedDate: "2026-10-07T10:00:00Z" },
    { status: "edited withdrawal", isOutstanding: false, createdDate: "2026-10-05T10:00:00Z", modifiedDate: "2026-10-07T10:00:00Z" },
  ])("parent dependency $status is reconciled before actual writer ranking", async ({ status, isOutstanding, createdDate, modifiedDate }) => {
    const dependency = datedComment(25, 202, "Child #202 is required for parent #901 package alpha.", "2026-10-06T10:00:00Z");
    const update = {
      ...datedComment(26, 202, isOutstanding === true ? "Child #202 is still required for parent #901 package alpha."
        : isOutstanding === false ? "Child #202 is no longer required for parent #901 package alpha."
        : "The dependency of parent #901 on child #202 is unknown.", createdDate),
      modifiedDate,
    };
    const commitment = datedComment(27, 202, "Parent #901 package alpha remains unfinished for October 9.", "2026-10-08T09:00:00Z");
    const fixture = createFixture({
      items: [
        makeItem(203, { "Microsoft.VSTS.Common.Priority": 1, "Microsoft.VSTS.Common.Severity": "4 - Low" }),
        makeItem(202, { "Microsoft.VSTS.Common.Priority": 3, "Microsoft.VSTS.Common.Severity": "4 - Low" }, [hierarchy(901)]),
      ],
      relatives: [makeItem(901, { "System.WorkItemType": "Feature", [dueReference]: "2026-10-09T00:00:00Z" })],
      pagesByItem: { 202: [makePage([commitment, update, dependency])] },
    });
    const inventory = await fixture.collect();
    let report = "";
    let writeCount = 0;
    await writeAzureTriageReport({
      scope: reportScope, inventory,
      analyzeItem: async (item: AzureWorkItem) => ({
        status: "ASSESSED", summary: "Synthetic parent dependency chronology.", evidence: [],
        claims: item.id !== 202 ? [] : [dependency, update, commitment].map((comment, index) => ({
          type: index === 2 ? "commitment" : "parent-dependency", provenance: "team-reported",
          parentId: 901, issueId: "package-alpha", excerpt: comment.text,
          sourceIds: [fieldId(901, dueReference), `comment:202:${comment.id}:v1`],
          ...(index === 2 ? { date: "2026-10-09T00:00:00Z" } : {}),
          ...(index === 1 && isOutstanding === undefined ? {} : { isOutstanding: index === 1 ? isOutstanding : true }),
        })),
      }),
      writeFile: async (_path, contents) => { writeCount++; report = contents; },
    });
    expect(writeCount).toBe(1);
    expect(rankedIds(report)).toEqual(status === "current" ? [202, 203] : [203, 202]);
    const markup = itemMarkup(report, 202);
    const whyNow = signalRow(markup, "Why now");
    for (const fact of ["#25 v1", "#26 v1", "#901"]) expect(whyNow).toContain(fact);
    if (status === "current") {
      expect(signalRow(markup, "Recommendation")).toContain("Meet the commitment.");
      expect(whyNow).toContain("#27 v1");
    } else {
      expect(signalRow(markup, "Recommendation")).not.toContain("Meet the commitment.");
    }
  });

  test.each([
    { hasHistoricalDependency: true, unknownModifiedDate: "2026-10-07T10:00:00Z", hasCurrentUncertainty: false },
    { hasHistoricalDependency: false, unknownModifiedDate: "2026-10-07T10:00:00Z", hasCurrentUncertainty: false },
    { hasHistoricalDependency: true, unknownModifiedDate: "2026-10-07T11:00:00Z", hasCurrentUncertainty: false },
    { hasHistoricalDependency: false, unknownModifiedDate: "2026-10-07T11:00:00Z", hasCurrentUncertainty: false },
    { hasHistoricalDependency: true, unknownModifiedDate: "2026-10-08T08:30:00Z", hasCurrentUncertainty: true },
    { hasHistoricalDependency: false, unknownModifiedDate: "2026-10-08T08:30:00Z", hasCurrentUncertainty: true },
  ])("renewed dependency confirmation determines actual writer order (history=$hasHistoricalDependency, modified=$unknownModifiedDate)", async ({ hasHistoricalDependency, unknownModifiedDate, hasCurrentUncertainty }) => {
    const dependency = datedComment(25, 202, "Child #202 is required for parent #901 package alpha delivery on October 9.", "2026-10-06T10:00:00Z");
    const uncertainty = {
      ...datedComment(26, 202, "Whether child #202 is still required for parent #901 package alpha is unknown.", "2026-10-07T10:00:00Z"),
      version: unknownModifiedDate === "2026-10-07T10:00:00Z" ? 1 : 2,
      modifiedDate: unknownModifiedDate,
    };
    const confirmation = datedComment(28, 202, "Confirmed October 8: child #202 is still required for parent #901 package alpha delivery on October 9.", "2026-10-08T08:00:00Z");
    const commitment = datedComment(27, 202, "Parent #901 package alpha remains unfinished and committed for October 9.", "2026-10-08T09:00:00Z");
    const comments = [...(hasHistoricalDependency ? [dependency] : []), uncertainty, confirmation, commitment];
    const fixture = createFixture({
      items: [
        makeItem(203, { "Microsoft.VSTS.Common.Priority": 1, "Microsoft.VSTS.Common.Severity": "4 - Low" }),
        makeItem(202, { "Microsoft.VSTS.Common.Priority": 3, "Microsoft.VSTS.Common.Severity": "4 - Low" }, [hierarchy(901)]),
      ],
      relatives: [makeItem(901, { "System.WorkItemType": "Feature", [dueReference]: "2026-10-09T00:00:00Z" })],
      pagesByItem: { 202: [makePage(comments)] },
    });
    const inventory = await fixture.collect();
    expect(inventory.items.find((item) => item.id === 202)?.signals?.coverage).toBe("sufficient");
    let report = "";
    let writeCount = 0;
    await writeAzureTriageReport({
      scope: reportScope, inventory,
      analyzeItem: async (item: AzureWorkItem) => ({
        status: "ASSESSED", summary: "Synthetic renewed parent dependency.", evidence: [],
        claims: item.id !== 202 ? [] : comments.map((comment) => ({
          type: comment.id === 27 ? "commitment" : "parent-dependency", provenance: "team-reported",
          parentId: 901, issueId: "package-alpha", excerpt: comment.text,
          sourceIds: [fieldId(901, dueReference), `comment:202:${comment.id}:v${comment.version}`],
          ...(comment.id === 27 ? { date: "2026-10-09T00:00:00Z" } : {}),
          ...(comment.id === 26 ? {} : { isOutstanding: true }),
        })),
      }),
      writeFile: async (_path, contents) => { writeCount++; report = contents; },
    });
    expect(writeCount).toBe(1);
    expect(rankedIds(report)).toEqual(hasCurrentUncertainty ? [203, 202] : [202, 203]);
    const markup = itemMarkup(report, 202);
    expect(signalRow(markup, "Recommendation")).toContain(hasCurrentUncertainty ? "Clarify the current dependency." : "Meet the commitment.");
    const whyNow = signalRow(markup, "Why now");
    for (const fact of ["#28 v1", "#27 v1", "#901"]) expect(whyNow).toContain(fact);
    expect(whyNow).not.toContain("#25 v1");
    if (hasCurrentUncertainty) {
      expect(whyNow).toContain("#26 v2");
      expect(whyNow).toContain(unknownModifiedDate);
    } else {
      for (const obsolete of ["#26 v1", "#26 v2", "withdrawal"]) expect(whyNow).not.toContain(obsolete);
    }
  });

  test.each([
    { date: "2026-10-07T00:00:00Z", expectedIds: [304, 309, 305, 301, 302, 306, 303, 307, 308], shouldPromote: true },
    { date: "2026-10-08T00:00:00Z", expectedIds: [304, 309, 305, 301, 302, 306, 303, 307, 308], shouldPromote: true },
    { date: "2026-10-15T23:59:59Z", expectedIds: [304, 309, 305, 301, 302, 306, 303, 307, 308], shouldPromote: true },
    { date: "2026-10-16T00:00:00Z", expectedIds: [304, 309, 305, 302, 303, 301, 306, 307, 308], shouldPromote: false },
  ])("critical risk precedes blockers and $date commitments; attention uses only native/stable ties", async ({ date, expectedIds, shouldPromote }) => {
    const commitmentIds = [301, 306];
    const blockerIds = [302, 305];
    const commitmentText = `Delivery remains outstanding for ${date}.`;
    const blockerText = "Delivery is blocked by dependency alpha.";
    const lowFields = { "Microsoft.VSTS.Common.Priority": 3, "Microsoft.VSTS.Common.Severity": "4 - Low" };
    const criticalFields = { "Microsoft.VSTS.Common.Severity": "1 - Critical" };
    const deliveryFields = { ...lowFields, [dueReference]: date, "Microsoft.VSTS.Scheduling.TargetDate": date };
    const inventory = await createFixture({
      items: [
        makeItem(301, deliveryFields),
        makeItem(302, lowFields),
        makeItem(303, { ...lowFields, "Microsoft.VSTS.Common.Priority": 1 }),
        makeItem(304, criticalFields),
        makeItem(305, { ...lowFields, "Microsoft.VSTS.Common.Priority": 2 }),
        makeItem(306, deliveryFields),
        makeItem(307, { "Microsoft.VSTS.Common.Priority": undefined, "Microsoft.VSTS.Common.Severity": undefined }),
        makeItem(308, criticalFields),
        makeItem(309, criticalFields),
      ],
      pagesByItem: Object.fromEntries([...commitmentIds, ...blockerIds].map((id) => [
        id, [makePage([datedComment(1, id, commitmentIds.includes(id) ? commitmentText : blockerText, "2026-10-06T12:00:00Z")])],
      ])),
    }).collect();
    const inventoryBeforeReport = structuredClone(inventory);
    let report = "";
    await writeAzureTriageReport({
      scope: reportScope, inventory,
      analyzeItem: async (item: AzureWorkItem) => {
        if (item.id === 308) return { status: "UNASSESSED" };
        const claims: GroundedClaim[] = commitmentIds.includes(item.id) ? [{
          type: "commitment", provenance: "team-reported", isOutstanding: true,
          sourceIds: [fieldId(item.id, dueReference), `comment:${item.id}:1:v1`],
          excerpt: commitmentText, date,
        }] : blockerIds.includes(item.id) ? [{
          type: "blocker", provenance: "team-reported", issueId: "dependency-alpha",
          sourceIds: [`comment:${item.id}:1:v1`], excerpt: blockerText,
        }] : [];
        return { status: "ASSESSED", priority: "P0", summary: `Ranking fixture ${item.id}.`, claims };
      },
      writeFile: async (_path, contents) => { report = contents; },
    });
    expect(rankedIds(report)).toEqual([...expectedIds]);
    expect(inventory).toEqual(inventoryBeforeReport);
    for (const [id, band] of [[304, "P0"], [309, "P0"], [305, "P2"], [301, "P3"], [302, "P3"], [306, "P3"], [303, "P1"], [307, "P5"]] as const) {
      expect(itemMarkup(report, id)).toContain(`class="band band-${band.toLowerCase()}">${band}</span>`);
    }
    expect(itemMarkup(report, 308)).toContain("UNASSESSED");
    expect(signalRow(itemMarkup(report, 301), "Recommendation")).toContain(shouldPromote ? "Meet the commitment." : "Keep native order.");
    for (const id of blockerIds) {
      expect(signalRow(itemMarkup(report, id), "Recommendation")).toContain("Unblock the work.");
    }
  });

  test("without grounded current reasons enriched ordering exactly matches the legacy native/stable order", async () => {
    const inventory = await recommendationFixture().collect();
    const inventoryBeforeReport = structuredClone(inventory);
    const reports: string[] = [];
    const legacyInventory = {
      ...inventory,
      items: inventory.items.map(({ signals: _signals, ...item }) => item),
    };
    for (const input of [legacyInventory, inventory]) {
      await writeAzureTriageReport({
        scope: reportScope, inventory: input,
        analyzeItem: async (item: AzureWorkItem) => ({
          status: item.id === 206 ? "UNASSESSED" : "ASSESSED",
          priority: "P0", summary: `Native-order fixture ${item.id}.`, claims: [],
        }),
        writeFile: async (_path, contents) => { reports.push(contents); },
      });
    }
    expect(reports).toHaveLength(2);
    for (const report of reports) {
      expect(rankedIds(report)).toEqual([201, 203, 204, 202, 205, 206]);
    }
    expect(inventory).toEqual(inventoryBeforeReport);
  });

  test("keeps native critical first, promotes the current delivery, and leaves old/parent/sprint signals non-urgent", async () => {
    const { report, inventory, analyzedIds, maxActiveAnalyses, writeCount } =
      await renderSignalFixture(recommendationFixture());
    expect(rankedIds(report)).toEqual([201, 202, 203, 204, 205, 206]);
    expect([...analyzedIds].sort((first, second) => first - second)).toEqual([201, 202, 203, 204, 205, 206]);
    expect(maxActiveAnalyses).toBeGreaterThan(1);
    expect(maxActiveAnalyses).toBeLessThanOrEqual(5);
    expect(writeCount).toBe(1);
    expect(inventory.items.map(({ id }) => id)).toEqual([203, 204, 202, 201, 205, 206]);
    expect(inventory.items.find(({ id }) => id === 202)?.signals?.sources).toEqual(
      expect.arrayContaining([
        { id: fieldId(202, dueReference), workItemId: 202, revision: 7, referenceName: dueReference, value: "2026-10-09T00:00:00Z" },
        expect.objectContaining({
          id: "comment:202:21:v1", workItemId: 202, commentId: 21, version: 1,
          text: deliveryExcerpt, createdDate: "2026-10-08T10:00:00Z", modifiedDate: "2026-10-08T10:00:00Z",
        }),
      ]),
    );
    expect(inventory.items.find(({ id }) => id === 204)?.signals).toMatchObject({
      parent: { workItemId: 901, priority: 1 },
      sources: expect.arrayContaining([
        { id: fieldId(901, "Microsoft.VSTS.Common.Priority"), workItemId: 901, revision: 7, referenceName: "Microsoft.VSTS.Common.Priority", value: 1 },
      ]),
    });
    const critical = itemMarkup(report, 201);
    expect(signalRow(critical, "Recommendation")).toContain("Address critical risk.");
    expect(signalRow(critical, "Why now")).toContain("1 - Critical");
    expect(signalRow(critical, "Why now")).toMatch(/#202|commitment/i);
    const delivery = itemMarkup(report, 202);
    expect(delivery).toContain('class="band band-p3">P3</span>');
    expect(signalRow(delivery, "Azure priority")).toContain("Priority 3");
    expect(signalRow(delivery, "Azure priority")).toContain("Severity 4 - Low");
    expect(signalRow(delivery, "Recommendation")).toContain("Meet the commitment.");
    expect(signalRow(delivery, "Why now")).toContain(dueReference);
    expect(signalRow(delivery, "Why now")).toContain("2026-10-09");
    expect(signalRow(delivery, "Why now")).toMatch(/#21 v1/i);
    expect(signalRow(delivery, "Why now")).toMatch(/#201|critical/i);
    expect(signalRow(delivery, "Discussion")).toContain(deliveryExcerpt);
    expect(signalRow(delivery, "Discussion")).toContain("2026-10-08");
    expect(signalRow(delivery, "Discussion")).toMatch(/team-reported/i);
    expect(signalRow(delivery, "Coverage")).toMatch(/sufficient/i);
    const oldRequest = itemMarkup(report, 203);
    expect(signalRow(oldRequest, "Recommendation")).toContain("Review relevance.");
    expect(signalRow(oldRequest, "Why now")).toContain("49");
    expect(signalRow(oldRequest, "Why now")).toContain("System.ChangedDate");
    expect(signalRow(oldRequest, "Why now")).toMatch(/#32 v1/i);
    expect(signalRow(oldRequest, "Why now")).toMatch(/resolv/i);
    expect(signalRow(oldRequest, "Recommendation")).not.toMatch(/unblock|urgent|meet the commitment/i);
    const child = itemMarkup(report, 204);
    expect(signalRow(child, "Parent signals")).toContain("#901");
    expect(signalRow(child, "Parent signals")).toContain("Priority 1");
    expect(signalRow(child, "Iteration / sprint")).toContain("2026-10-01");
    expect(signalRow(child, "Recommendation")).toMatch(/update.*planning|review.*planning/i);
    expect(signalRow(child, "Why now")).toMatch(/planning/i);
    expect(signalRow(child, "Why now")).not.toMatch(/overdue delivery|missed delivery|must deliver/i);
    expect(report.match(/class="tree-row tree-parent"/g)).toHaveLength(1);
    expect(rankedIds(report)).not.toContain(901);
    for (const id of [201, 202, 203, 204, 205]) {
      expect(report.split(`Analysis-only marker for ${id}.`)).toHaveLength(2);
      expect(signalRow(itemMarkup(report, id), "Why now")).not.toContain("Analysis-only marker");
      expect(itemMarkup(report, id)).toContain("Ready for product review");
    }
    expect(report).toContain("6 inventoried");
    expect(report).toMatch(/5 assessed/);
    expect(report).toMatch(/1 (?:explicitly )?UNASSESSED/);
    expect(report).toMatch(/counts sum to 6/);
    expect(report).toContain("<td>Bug</td><td>Ready for product review</td><td>1</td>");
    expect(report).toContain("<td>Story</td><td>Ready for product review</td><td>5</td>");
  });

  test("a later matching resolution removes only its own blocker promotion", async () => {
    const items = [makeItem(101, { "Microsoft.VSTS.Common.Priority": 4, "Microsoft.VSTS.Common.Severity": "4 - Low" }), makeItem(102)];
    for (const issueId of ["package-format", "unrelated-issue"]) {
      const fixture = createFixture({
        items,
        pages: [makePage([
          datedComment(1, 101, blockerExcerpt, "2026-10-06T12:00:00Z"),
          datedComment(2, 101, resolutionExcerpt, "2026-10-07T12:00:00Z"),
        ])],
      });
      const inventory = await fixture.collect();
      let report = "";
      await writeAzureTriageReport({
        scope: reportScope, inventory,
        analyzeItem: async (item: AzureWorkItem) => ({
          status: "ASSESSED", summary: `Resolution fixture ${item.id}.`, evidence: [],
          claims: item.id !== 101 ? [] : [
            { type: "blocker", sourceIds: ["comment:101:1:v1"], excerpt: blockerExcerpt, issueId: "package-format", provenance: "team-reported" },
            { type: "blocker-resolved", sourceIds: ["comment:101:2:v1"], excerpt: resolutionExcerpt, issueId, provenance: "team-reported" },
          ],
        }),
        writeFile: async (_path, contents) => { report = contents; },
      });
      expect(rankedIds(report)).toEqual(issueId === "package-format" ? [102, 101] : [101, 102]);
      const recommendation = signalRow(itemMarkup(report, 101), "Recommendation");
      expect(recommendation).toMatch(issueId === "package-format" ? /keep native order|confirm.*date/i : /unblock/i);
      expect(signalRow(itemMarkup(report, 101), "Why now")).toMatch(issueId === "package-format" ? /#2 v1|resolv/i : /#1 v1/i);
    }
  });
});

describe("Signal coverage and accessible report states (A8, E1–E2 prerequisites)", () => {
  test("the actual writer exposes the five capture regions, accessible disclosure labels, and all evidence rows", async () => {
    const { report } = await renderSignalFixture(recommendationFixture());
    for (const region of ["page-header", "backlog-snapshot", "ranked-work", "type-state-summary", "coverage-method"]) {
      expect(report.match(new RegExp(`data-region="${region}"`, "g"))).toHaveLength(1);
    }
    expect(itemMarkup(report, 202)).toMatch(/<summary\b[^>]*aria-label="Item #202: Prepare delivery package"/);
    for (const label of ["Recommendation", "Why now", "Created / Changed", "Delivery dates", "Discussion", "Iteration / sprint", "Parent signals", "Coverage", "Evidence"]) {
      expect(signalRow(itemMarkup(report, 202), label)).toMatch(/\S/);
    }
    expect([...report.matchAll(/<section\b[^>]*\bid="([^"]+)"/g)].map((match) => match[1])).toEqual(["s01", "s02", "s03", "s04"]);
    expect(signalRow(itemMarkup(report, 206), "Recommendation")).toMatch(/not assessable/i);
    expect(itemMarkup(report, 206)).toContain("UNASSESSED");
    expect(report).not.toMatch(/confidence\s*(?::|=)?\s*\d|guaranteed delivery/i);
  });

  test("partial discussion and inaccessible iterations publish labeled gaps without proving current work or no blockers", async () => {
    const fixture = recommendationFixture({
      pagesByItem: {
        202: [{
          ...makePage([datedComment(21, 202, deliveryExcerpt, "2026-10-08T10:00:00Z")], 2, "second"),
          nextPage: `${scope.organization}${commentsPath(202)}?api-version=7.1-preview.4&continuationToken=second`,
        }],
      },
      failRequest: (request) => request.path === iterationsPath
        ? cliFailure('ERROR: Forbidden({"message":"synthetic-private-diagnostic"})')
        : undefined,
    });
    const { report, inventory } = await renderSignalFixture(fixture);
    expect(rankedIds(report)).toEqual([201, 203, 204, 202, 205, 206]);
    const delivery = itemMarkup(report, 202);
    expect(signalRow(delivery, "Coverage")).toMatch(/limited/i);
    expect(signalRow(delivery, "Discussion")).toMatch(/partial/i);
    expect(signalRow(delivery, "Discussion")).toMatch(/retry|fetch|read|complete/i);
    expect(signalRow(delivery, "Discussion")).toContain(deliveryExcerpt);
    expect(signalRow(delivery, "Iteration / sprint")).toMatch(/inaccessible|permission-denied/i);
    expect(signalRow(delivery, "Iteration / sprint")).toMatch(/retry|access|permission/i);
    expect(signalRow(delivery, "Delivery dates")).toContain("2026-10-09");
    expect(signalRow(delivery, "Recommendation")).toMatch(/confirm/i);
    expect(signalRow(delivery, "Recommendation")).not.toContain("Meet the commitment.");
    expect(report).not.toMatch(/no blockers|no unresolved blockers|synthetic-private-diagnostic/i);
    expect(inventory.complete).toBe(true);
  });

  test("a known independent field commitment remains usable when only iteration access is limited", async () => {
    const fixture = createFixture({
      items: [makeItem(101, { "Microsoft.VSTS.Scheduling.TargetDate": "2026-10-09T00:00:00Z" })],
      pages: [makePage([datedComment(21, 101, deliveryExcerpt, "2026-10-08T10:00:00Z")])],
      failRequest: (request) => request.path === iterationsPath ? cliFailure("ERROR: Forbidden") : undefined,
    });
    const inventory = await fixture.collect();
    let report = "";
    await writeAzureTriageReport({
      scope: reportScope, inventory,
      analyzeItem: async () => ({
        status: "ASSESSED", summary: "Current package work checked independently.", evidence: [],
        claims: [{
          type: "commitment", isOutstanding: true, sourceIds: [fieldId(101, dueReference), "comment:101:21:v1"],
          excerpt: deliveryExcerpt, value: "2026-10-09T00:00:00Z", date: "2026-10-09T00:00:00Z", provenance: "team-reported",
        }],
      }),
      writeFile: async (_path, contents) => { report = contents; },
    });
    expect(signalRow(itemMarkup(report, 101), "Recommendation")).toContain("Meet the commitment.");
    expect(signalRow(itemMarkup(report, 101), "Coverage")).toMatch(/limited/i);
    expect(signalRow(itemMarkup(report, 101), "Iteration / sprint")).toMatch(/inaccessible|permission-denied/i);
  });
});

describe("Shared output boundary for new Azure evidence (A9)", () => {
      test("renders comments, custom names, iteration paths, parent values, claim excerpts and gap prose as inert redacted text", async () => {
        const hostileComment = '<img src=x onerror="syntheticCommentAttack()"> token=synthetic-comment-secret token_owner=benign-comment-owner';
        const customReference = "Custom.<svg onload=syntheticCustomAttack()>";
        const hostilePath = 'Synthetic Project\\<svg onload="syntheticIterationAttack()">';
        const hostileParent = '<script>syntheticParentAttack()</script> bearer_token=synthetic-parent-secret';
        const fixture = createFixture({
          items: [makeItem(101, {
            [customReference]: "2026-10-08T00:00:00Z",
            "System.IterationPath": hostilePath,
          }, [hierarchy(901)])],
          relatives: [makeItem(901, { "System.Title": hostileParent, "Microsoft.VSTS.Common.Severity": hostileParent })],
          fields: { count: fieldMetadata.length + 1, value: [...fieldMetadata, { referenceName: customReference, type: "dateTime" }] },
          iterations: { count: 1, value: [{ ...iteration, path: hostilePath }] },
          pages: [makePage([datedComment(1, 101, hostileComment, "2026-10-07T12:00:00Z")])],
        });
        const inventory = await fixture.collect();
        const item = inventory.items[0];
        if (!item?.signals) throw new Error("Missing collected hostile signal fixture");
        item.signals.iteration.status = "partial";
        item.signals.iteration.reason = '<img src=x onerror="syntheticReasonAttack()"> auth_token=synthetic-reason-secret';
        item.signals.iteration.nextAction = '<script>syntheticActionAttack()</script> %2574oken%253Dsynthetic-encoded-secret';
        let report = "";
        await writeAzureTriageReport({
          scope: reportScope, inventory,
          analyzeItem: async () => ({
            status: "ASSESSED", summary: "Inspect synthetic source text safely.",
            claims: [{
              type: "context", sourceIds: ["comment:101:1:v1"], excerpt: hostileComment, provenance: "team-reported",
            }],
            evidence: [{ label: "Optional unsafe link stays text.", url: "https://user:synthetic-url-secret@evidence.example.test/source" }],
          }),
          writeFile: async (_path, contents) => { report = contents; },
        });
        for (const marker of ["synthetic-comment-secret", "synthetic-parent-secret", "synthetic-reason-secret", "synthetic-encoded-secret", "synthetic-url-secret"]) {
          expect(report).not.toContain(marker);
        }
        expect(report).toContain("token_owner=benign-comment-owner");
        for (const marker of ["syntheticCommentAttack", "syntheticCustomAttack", "syntheticIterationAttack", "syntheticParentAttack", "syntheticReasonAttack", "syntheticActionAttack"]) {
          expect(report).toContain(marker);
        }
        expect(report).not.toMatch(/<(?:img|svg)\b[^>]*(?:onerror|onload)=|<script>synthetic|href="(?:javascript:|https:\/\/user:)/i);
        expect(report).toContain("&lt;img");
        expect(report).toContain("Custom.&lt;svg");
        expect(report).toContain("&lt;script&gt;syntheticParentAttack()");
        expect(report).toContain("Optional unsafe link stays text.");
        const evidence = signalRow(itemMarkup(report, 101), "Evidence");
        expect(evidence).toMatch(/comment #1 v1|#1 v1/i);
        expect(evidence).toContain(`href="${scope.organization}/${scope.project}/_workitems/edit/101"`);
        expect(evidence).not.toMatch(/href="[^"]*(?:\/comments\/|commentId=|commentVersion=)/i);
        expect(report).not.toMatch(/synthetic-private-identity-marker|synthetic-mention-marker|synthetic-reaction-marker/);
      });
    });

    describe("Failed evidence contracts preserve the prior report (A10)", () => {
      const invalidClaims = [
        { name: "unknown source", claim: { sourceIds: ["comment:101:999:v1"] } },
        { name: "cross-item source", claim: { sourceIds: ["comment:102:1:v1"] } },
        { name: "invented excerpt", claim: { excerpt: "An invented quotation absent from every source." } },
        { name: "wrong field date", claim: { value: "2026-10-01T00:00:00Z", date: "2026-10-01T00:00:00Z" } },
        { name: "wrong parent", claim: { type: "parent-dependency", parentId: 999 } },
        { name: "unsupported claim kind", claim: { type: "guaranteed-delivery" } },
        { name: "ordinary HTTPS claimed as code verification", claim: { provenance: "code-verified", url: "https://evidence.example.test/ordinary-web-page" } },
        { name: "unsafe required link", claim: { url: "javascript:syntheticClaimAttack()" } },
        { name: "required link userinfo", claim: { url: "https://user:synthetic-claim-secret@evidence.example.test/source" } },
        { name: "encoded required link credential", claim: { url: "https://evidence.example.test/%2574oken%253Dsynthetic-link-secret" } },
      ];
      test.each(invalidClaims)("rejects $name before publishing any bytes", async ({ claim }) => {
        const fixture = createFixture({
          items: [makeItem(101), makeItem(102)],
          pages: [makePage([datedComment(1, 101, deliveryExcerpt, "2026-10-07T12:00:00Z")])],
          pagesByItem: { 102: [makePage([datedComment(1, 102, deliveryExcerpt, "2026-10-07T12:00:00Z")])] },
        });
        const inventory = await fixture.collect();
        let reportBytes = previousReport;
        let writes = 0;
        const failure = await writeAzureTriageReport({
          scope: reportScope, inventory,
          analyzeItem: async (item: AzureWorkItem) => ({
            status: "ASSESSED", summary: `Invalid claim fixture ${item.id}.`, evidence: [],
            claims: item.id === 102 ? [] : [{
              type: "commitment", provenance: "team-reported", isOutstanding: true,
              sourceIds: [fieldId(101, dueReference), "comment:101:1:v1"],
              excerpt: deliveryExcerpt, value: "2026-10-09T00:00:00Z", date: "2026-10-09T00:00:00Z",
              ...claim,
            }],
          }),
          writeFile: async (_path, contents) => { writes++; reportBytes = Buffer.from(contents); },
        }).then(() => undefined, (error: unknown) => error);
        expect(failure).toBeInstanceOf(Error);
        expect(writes).toBe(0);
        expect(reportBytes).toEqual(previousReport);
      });

      test.each([
        { name: "missing analysis", analysis: undefined },
        { name: "empty analysis", analysis: {} },
        { name: "missing assessed summary", analysis: { status: "ASSESSED", claims: [] } },
        { name: "malformed claims", analysis: { status: "ASSESSED", summary: "Malformed claims.", claims: {} } },
        { name: "render-invalid analysis link", analysis: { status: "ASSESSED", summary: "[unsafe](javascript:syntheticRenderAttack)", claims: [] } },
      ])("rejects $name rather than silently inventing UNASSESSED", async ({ analysis }) => {
        const inventory = await createFixture().collect();
        let reportBytes = previousReport;
        let writes = 0;
        const failure = await writeAzureTriageReport({
          scope: reportScope, inventory, analyzeItem: async () => analysis,
          writeFile: async (_path, contents) => { writes++; reportBytes = Buffer.from(contents); },
        }).then(() => undefined, (error: unknown) => error);
        expect(failure).toBeInstanceOf(Error);
        expect(writes).toBe(0);
        expect(reportBytes).toEqual(previousReport);
      });

      test.each(["write", "replace"] as const)("preserves prior bytes and cleans owned staging files after enriched report %s failure", async (stage) => {
        const directory = `.ai-engineering/triage-signals-test-${randomUUID()}`;
        const path = `${directory}/triage.html`;
        await mkdir(directory);
        try {
          await writeFile(path, previousReport);
          const inventory = await recommendationFixture().collect();
          let publicationAttempts = 0;
          const failure = await writeAzureTriageReport({
            scope: reportScope, inventory, analyzeItem: groundedAnalysis,
            writeFile: async (_path, contents) => {
              publicationAttempts++;
              await atomicWriteReport(path, contents, stage === "write" ? {
                writeTemporaryFile: async (handle) => {
                  await handle.writeFile("partial synthetic enriched report", "utf8");
                  throw new Error("Synthetic enriched write failure");
                },
              } : {
                beforeReplace: async () => { throw new Error("Synthetic enriched replace failure"); },
              });
            },
          }).then(() => undefined, (error: unknown) => error);
          expect(failure).toBeInstanceOf(Error);
          expect(publicationAttempts).toBe(1);
          expect(await readFile(path)).toEqual(previousReport);
          expect(await readdir(directory)).toEqual(["triage.html"]);
        } finally {
          await rm(directory, { recursive: true, force: true });
        }
      });
    });
describe("Unrecognized and empty evidence report states (A8, E2 prerequisites)", () => {
  test("an undated selected sprint and custom date remain visible unrecognized planning context in native order", async () => {
    const fixture = createFixture({
      items: [
        makeItem(101, { "Microsoft.VSTS.Common.Priority": 4, "Microsoft.VSTS.Common.Severity": "4 - Low", [dueReference]: null, "Microsoft.VSTS.Scheduling.TargetDate": null }),
        makeItem(102, { [dueReference]: null, "Microsoft.VSTS.Scheduling.TargetDate": null }),
      ],
      iterations: { count: 1, value: [{ ...iteration, attributes: { startDate: null, finishDate: null, timeFrame: "current" } }] },
    });
    const { report } = await renderSignalFixture(fixture);
    expect(rankedIds(report)).toEqual([102, 101]);
    const markup = itemMarkup(report, 101);
    expect(signalRow(markup, "Delivery dates")).toContain("Custom.DeliveryDate");
    expect(signalRow(markup, "Delivery dates")).toContain("2026-10-08");
    expect(signalRow(markup, "Delivery dates")).toMatch(/unrecognized/i);
    expect(signalRow(markup, "Iteration / sprint")).toContain(iteration.path);
    expect(signalRow(markup, "Iteration / sprint")).toMatch(/iteration-dates-unset|dates.*unset|dates.*not.*set/i);
    expect(signalRow(markup, "Iteration / sprint")).toMatch(/confirm|set/i);
    expect(signalRow(markup, "Recommendation")).not.toMatch(/meet the commitment|urgent|overdue/i);
    expect(report).not.toMatch(/guaranteed delivery/i);
  });

  test("empty inventory shows truthful zero counts and the capture empty message without analyzing fabricated items", async () => {
    const { report, analyzedIds, writeCount } = await renderSignalFixture(createFixture({ items: [] }));
    expect(rankedIds(report)).toEqual([]);
    expect(analyzedIds).toEqual([]);
    expect(writeCount).toBe(1);
    expect(report).toContain("No selected backlog members were returned.");
    expect(report).toMatch(/0 inventoried/);
    expect(report).toMatch(/0 assessed/);
    expect(report).toMatch(/0 (?:explicitly )?UNASSESSED/);
    expect(report).not.toMatch(/loading|role="alert"|retry button/i);
    for (const region of ["page-header", "backlog-snapshot", "ranked-work", "type-state-summary", "coverage-method"]) {
      expect(report).toContain(`data-region="${region}"`);
    }
  });
});
