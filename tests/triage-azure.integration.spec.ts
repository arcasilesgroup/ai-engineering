import { describe, expect, test } from "bun:test";
import {
  collectAzureBacklog,
  createAzureDevOpsInvoker,
} from "../skills/ai-triage/scripts/collect-azure.mjs";

const scope = {
  organization: "https://dev.azure.com/synthetic-org",
  project: "synthetic-project",
  team: "platform-team",
  backlogId: "stories",
};

const backlogLevelsPath = `/${scope.project}/${scope.team}/_apis/work/backlogs`;
const backlogItemsPath = `${backlogLevelsPath}/${scope.backlogId}/workItems`;
const projectPath = `/_apis/projects/${scope.project}`;
const workItemBatchPath = `/${scope.project}/_apis/wit/workitemsbatch`;
const syntheticProjectId = "fa918c8b-73ef-43d7-8f62-f664bae82720";
const workItemUrl = `${scope.organization}/${syntheticProjectId}/_apis/wit/workItems/`;

type AzureRequest = {
  method: "GET" | "POST";
  path: string;
  organization: string;
  project: string;
  team: string;
  backlogId: string;
  apiVersion: "7.1";
  body?: {
    ids: number[];
    errorPolicy: "Fail";
    "$expand"?: "Relations";
    fields?: string[];
  };
};

type WorkItem = {
  id: number;
  fields: Record<string, string | undefined> & {
    "System.AreaPath"?: string;
    "System.Title"?: string;
    "System.WorkItemType": string;
    "System.State": string;
  };
  relations?: Array<{
    rel: string;
    url: string;
    relatedItem?: {
      id: number;
      type: string;
      state: string;
      title: string;
    };
  }>;
};

type FixtureOptions = {
  workItems?: WorkItem[];
  relatedItems?: WorkItem[];
  workItemCountLimit?: number;
  unknownLimit?: boolean;
  organization?: string;
  failRequest?: (request: AzureRequest) => Error | undefined;
  detailResponse?: (
    requestedIds: number[],
    defaultDetails: WorkItem[],
  ) => WorkItem[];
};

function createDefaultWorkItems(): WorkItem[] {
  return [
    {
      id: 101,
      fields: {
        "System.AreaPath": "Synthetic Project\\Platform",
        "System.Title": "Story with a Feature parent",
        "System.WorkItemType": "Story",
        "System.State": "Ready for intake",
      },
      relations: [
        { rel: "System.LinkTypes.Hierarchy-Reverse", url: `${workItemUrl}901` },
      ],
    },
    {
      id: 102,
      fields: {
        "System.AreaPath": "Synthetic Project\\Platform",
        "System.Title": "Story with a child task",
        "System.WorkItemType": "Story",
        "System.State": "Moving through queue",
      },
      relations: [
        { rel: "System.LinkTypes.Hierarchy-Forward", url: `${workItemUrl}902` },
      ],
    },
    {
      id: 103,
      fields: {
        "System.AreaPath": "Synthetic Project\\Quality",
        "System.Title": "Bug with a custom state",
        "System.WorkItemType": "Bug",
        "System.State": "Needs product review",
      },
    },
    {
      id: 104,
      fields: {
        "System.WorkItemType": "Story",
        "System.State": "Done in this board",
      },
    },
    {
      id: 105,
      fields: {
        "System.WorkItemType": "Bug",
        "System.State": "Won't fix",
      },
    },
  ];
}

function createDefaultRelatedItems(): WorkItem[] {
  return [
    {
      id: 901,
      fields: {
        "System.Title": "Parent feature for intake",
        "System.WorkItemType": "Feature",
        "System.State": "Feature in progress",
      },
    },
    {
      id: 902,
      fields: {
        "System.Title": "Break down validation",
        "System.WorkItemType": "Task",
        "System.State": "Task ready",
      },
    },
  ];
}

function createAzureFixture(options: FixtureOptions = {}) {
  const calls: AzureRequest[] = [];
  const workItems = options.workItems ?? createDefaultWorkItems();
  const relatedItems = options.relatedItems ?? createDefaultRelatedItems();
  const requestScope = {
    ...scope,
    organization: options.organization ?? scope.organization,
  };
  const workItemsById = new Map(
    [...workItems, ...relatedItems].map((item) => [item.id, item]),
  );
  const selectedBacklog = options.unknownLimit
    ? { id: requestScope.backlogId }
    : {
        id: requestScope.backlogId,
        workItemCountLimit: options.workItemCountLimit ?? 1000,
      };
  const invoke = async (request: AzureRequest): Promise<unknown> => {
    calls.push(request);
    const failure = options.failRequest?.(request);
    if (failure) {
      throw failure;
    }

    if (request.method === "GET" && request.path === backlogLevelsPath) {
      return {
        count: 2,
        value: [
          { id: "epics", workItemCountLimit: 1000 },
          selectedBacklog,
        ],
      };
    }
    if (request.method === "GET" && request.path === backlogItemsPath) {
      return {
        workItems: workItems.map(({ id }) => ({
          target: {
            id,
            url: `${workItemUrl}${id}`,
          },
        })),
      };
    }
    if (request.method === "GET" && request.path === projectPath) {
      return { id: syntheticProjectId };
    }
    if (request.method === "POST" && request.path === workItemBatchPath) {
      const ids = request.body?.ids ?? [];
      const defaultDetails: WorkItem[] = [];
      for (const id of ids) {
        const item = workItemsById.get(id);
        if (!item) continue;
        const fields = request.body?.fields;
        if (fields) {
          defaultDetails.push({
            id,
            fields: {
              "System.WorkItemType": item.fields["System.WorkItemType"],
              "System.State": item.fields["System.State"],
              "System.Title": item.fields["System.Title"] ?? "",
            },
          });
        } else {
          defaultDetails.push(item);
        }
      }
      return {
        value: options.detailResponse?.(ids, defaultDetails) ?? defaultDetails,
      };
    }

    throw new Error(`Unexpected synthetic Azure request: ${request.method} ${request.path}`);
  };

  return {
    calls,
    collect: () => collectAzureBacklog({ ...requestScope, invoke }),
  };
}

const allowedRoutes = new Set([
  `GET ${backlogLevelsPath}`,
  `GET ${backlogItemsPath}`,
  `GET ${projectPath}`,
  `POST ${workItemBatchPath}`,
]);

function expectOnlyAllowedReads(calls: AzureRequest[]): void {
  expect(
    calls.every((request) =>
      allowedRoutes.has(`${request.method} ${request.path}`),
    ),
  ).toBe(true);
  expect(
    calls.every(
      (request) =>
        request.organization === scope.organization &&
        request.project === scope.project &&
        request.team === scope.team &&
        request.backlogId === scope.backlogId &&
        request.apiVersion === "7.1" &&
        (request.path.startsWith(`/${scope.project}/`) ||
          request.path === projectPath),
    ),
  ).toBe(true);
  for (const request of calls) {
    const expectedKeys = [
      "method",
      "path",
      "organization",
      "project",
      "team",
      "backlogId",
      "apiVersion",
      ...(request.method === "POST" ? ["body"] : []),
    ].sort();
    expect(Object.keys(request).sort()).toEqual(expectedKeys);
    if (request.method === "POST") {
      expect(request.body?.ids.length).toBeLessThanOrEqual(200);
      expect(request.body).toMatchObject({
        ids: expect.any(Array),
        errorPolicy: "Fail",
      });
      if (request.body?.fields) {
        expect(request.body.fields).toEqual([
          "System.WorkItemType",
          "System.State",
          "System.Title",
        ]);
      } else {
        expect(request.body?.["$expand"]).toBe("Relations");
      }
    } else {
      expect("body" in request).toBe(false);
    }
  }
  expect(
    calls.every(
      (request) =>
        request.method === "GET" ||
        (request.method === "POST" && request.path === workItemBatchPath),
    ),
  ).toBe(true);
  expect(calls.some((request) => /wiql|queries/i.test(request.path))).toBe(false);
}

describe("Azure backlog collection integration", () => {
  test("uses az rest against the exact scoped membership route", async () => {
    const calls: string[][] = [];
    const invoke = createAzureDevOpsInvoker({
      ...scope,
      run: async (args) => {
        calls.push(args);
        return JSON.stringify({ workItems: [] });
      },
    });

    const result = await invoke({
      method: "GET",
      path: backlogItemsPath,
      ...scope,
      apiVersion: "7.1",
    });

    expect(result).toEqual({ workItems: [] });
    expect(calls).toEqual([
      [
        "rest",
        "--method",
        "get",
        "--url",
        `${scope.organization}${backlogItemsPath}?api-version=7.1`,
        "--resource",
        "499b84ac-1321-427f-aa17-267ca6975798",
        "--only-show-errors",
        "--output",
        "json",
      ],
    ]);
  });

  test("uses the selected project route to resolve the project ID", async () => {
    const calls: string[][] = [];
    const invoke = createAzureDevOpsInvoker({
      ...scope,
      run: async (args) => {
        calls.push(args);
        return JSON.stringify({ id: syntheticProjectId });
      },
    });

    const result = await invoke({
      method: "GET",
      path: projectPath,
      ...scope,
      apiVersion: "7.1",
    });

    expect(result).toEqual({ id: syntheticProjectId });
    expect(calls[0]).toContain(
      `${scope.organization}${projectPath}?api-version=7.1`,
    );
  });

  test("sends detail batches as JSON through az rest", async () => {
    const calls: string[][] = [];
    const invoke = createAzureDevOpsInvoker({
      ...scope,
      run: async (args) => {
        calls.push(args);
        return JSON.stringify({ value: [] });
      },
    });
    const body = {
      ids: [101, 102],
      errorPolicy: "Fail" as const,
      "$expand": "Relations" as const,
    };

    await invoke({
      method: "POST",
      path: workItemBatchPath,
      ...scope,
      apiVersion: "7.1",
      body,
    });

    expect(calls[0]).toEqual([
      "rest",
      "--method",
      "post",
      "--url",
      `${scope.organization}${workItemBatchPath}?api-version=7.1`,
      "--resource",
      "499b84ac-1321-427f-aa17-267ca6975798",
      "--only-show-errors",
      "--output",
      "json",
      "--body",
      JSON.stringify(body),
    ]);
  });

  test("reads only type, state, and title for related-item context", async () => {
    const calls: string[][] = [];
    const invoke = createAzureDevOpsInvoker({
      ...scope,
      run: async (args) => {
        calls.push(args);
        return JSON.stringify({ value: [] });
      },
    });

    await invoke({
      method: "POST",
      path: workItemBatchPath,
      ...scope,
      apiVersion: "7.1",
      body: {
        ids: [901],
        fields: ["System.WorkItemType", "System.State", "System.Title"],
        errorPolicy: "Fail",
      },
    });

    expect(calls[0]?.slice(-2)).toEqual([
      "--body",
      JSON.stringify({
        ids: [901],
        fields: ["System.WorkItemType", "System.State", "System.Title"],
        errorPolicy: "Fail",
      }),
    ]);
  });

  test("rejects Azure requests outside the selected scope", async () => {
    const calls: string[][] = [];
    const invoke = createAzureDevOpsInvoker({
      ...scope,
      run: async (args) => {
        calls.push(args);
        return "{}";
      },
    });

    await expect(
      invoke({
        method: "GET",
        path: backlogItemsPath,
        ...scope,
        project: "another-project",
        apiVersion: "7.1",
      }),
    ).rejects.toThrow();
    expect(calls).toEqual([]);
  });

  test("rejects related-item reads for fields outside the context allowlist", async () => {
    const calls: string[][] = [];
    const invoke = createAzureDevOpsInvoker({
      ...scope,
      run: async (args) => {
        calls.push(args);
        return JSON.stringify({ value: [] });
      },
    });

    await expect(
      invoke({
        method: "POST",
        path: workItemBatchPath,
        ...scope,
        apiVersion: "7.1",
        body: {
          ids: [901],
          fields: ["System.Description"],
          errorPolicy: "Fail",
        },
      }),
    ).rejects.toThrow();
    expect(calls).toEqual([]);
  });

  test("collects only selected backlog members and keeps hierarchy as item context", async () => {
    const fixture = createAzureFixture();
    const inventory = await fixture.collect();

    expect(inventory.complete).toBe(true);
    expect(inventory.items.map((item) => item.id)).toEqual([101, 102, 103, 104, 105]);
    expect(inventory.items.map((item) => item.fields["System.State"])).toEqual([
      "Ready for intake",
      "Moving through queue",
      "Needs product review",
      "Done in this board",
      "Won't fix",
    ]);
    expect(
      inventory.items.map((item) => item.fields["System.AreaPath"]),
    ).toEqual([
      "Synthetic Project\\Platform",
      "Synthetic Project\\Platform",
      "Synthetic Project\\Quality",
    ]);
    expect(inventory.items[0]?.relations?.[0]).toMatchObject({
      rel: "System.LinkTypes.Hierarchy-Reverse",
      url: `${workItemUrl}901`,
      relatedItem: {
        id: 901,
        type: "Feature",
        state: "Feature in progress",
        title: "Parent feature for intake",
      },
    });
    expect(inventory.items[1]?.relations?.[0]).toMatchObject({
      rel: "System.LinkTypes.Hierarchy-Forward",
      relatedItem: {
        id: 902,
        type: "Task",
        state: "Task ready",
        title: "Break down validation",
      },
    });

    const expectedRoutes = [
      `GET ${backlogLevelsPath}`,
      `GET ${backlogItemsPath}`,
      `GET ${projectPath}`,
      `POST ${workItemBatchPath}`,
      `POST ${workItemBatchPath}`,
    ].sort();
    expect(
      fixture.calls.map((request) => `${request.method} ${request.path}`).sort(),
    ).toEqual(expectedRoutes);
    expectOnlyAllowedReads(fixture.calls);

    const batchRequests = fixture.calls.filter(
      (request) => request.method === "POST",
    );
    expect(batchRequests[0]?.body).toMatchObject({
      ids: [101, 102, 103, 104, 105],
      errorPolicy: "Fail",
      "$expand": "Relations",
    });
    expect(batchRequests[1]?.body).toMatchObject({
      ids: [901, 902],
      fields: ["System.WorkItemType", "System.State", "System.Title"],
      errorPolicy: "Fail",
    });
  });

  test("preserves custom states and includes each selected backlog member", async () => {
    const workItems = [
      {
        id: 501,
        fields: {
          "System.WorkItemType": "Story",
          "System.State": "New",
        },
      },
      {
        id: 502,
        fields: {
          "System.WorkItemType": "Bug",
          "System.State": "Waiting on triage",
        },
      },
    ];
    const fixture = createAzureFixture({ workItems, relatedItems: [] });

    const inventory = await fixture.collect();

    expect(inventory.items).toEqual(workItems);
    expect(fixture.calls.map((request) => request.path)).not.toContain(
      "/synthetic-project/_apis/wit/workitemtypes",
    );
  });

  test("does not read related items from another Azure project", async () => {
    const otherProjectId = "30000000-0000-0000-0000-000000000000";
    const workItems = createDefaultWorkItems().map((item) => ({
      ...item,
      ...(item.relations
        ? {
            relations: item.relations.map((relation) => ({
              ...relation,
              url: relation.url.replace(syntheticProjectId, otherProjectId),
            })),
          }
        : {}),
    }));
    const fixture = createAzureFixture({ workItems, relatedItems: [] });

    const inventory = await fixture.collect();

    expect(inventory.items.map((item) => item.id)).toEqual([
      101, 102, 103, 104, 105,
    ]);
    expect(
      fixture.calls.some(
        (request) => request.method === "POST" && request.body?.fields,
      ),
    ).toBe(false);
    expectOnlyAllowedReads(fixture.calls);
  });

  test("fetches every below-cap member in detail batches of at most 200", async () => {
    const workItems = Array.from({ length: 201 }, (_, index) => ({
      id: index + 1,
      fields: {
        "System.WorkItemType": "Story",
        "System.State": "Moving through queue",
      },
    }));
    const fixture = createAzureFixture({ workItems });
    const inventory = await fixture.collect();
    const batchRequests = fixture.calls.filter(
      (request) => request.method === "POST",
    );

    expect(inventory.complete).toBe(true);
    expect(inventory.items.map((item) => item.id)).toEqual(
      workItems.map((item) => item.id),
    );
    expect(batchRequests.map((request) => request.body?.ids)).toEqual([
      workItems.slice(0, 200).map((item) => item.id),
      [201],
    ]);
    expect(
      batchRequests.every(
        (request) =>
          request.body?.errorPolicy === "Fail" &&
          (request.body.ids?.length ?? 201) <= 200,
      ),
    ).toBe(true);
    expectOnlyAllowedReads(fixture.calls);
  });

  test("fails closed when the selected backlog cap is unknown or reached", async () => {
    const capCases = [
      { label: "unknown", options: { unknownLimit: true } },
      { label: "at cap", options: { workItemCountLimit: 5 } },
      { label: "above cap", options: { workItemCountLimit: 4 } },
    ] as const;

    for (const capCase of capCases) {
      const fixture = createAzureFixture(capCase.options);

      await expect(fixture.collect()).rejects.toThrow();
      expect(fixture.calls.some((request) => request.method === "POST")).toBe(
        false,
      );
      expectOnlyAllowedReads(fixture.calls);
    }
  });

  test("fails closed when a detail batch omits or mismatches a requested item", async () => {
    const invalidDetailResponses = [
      {
        label: "omitted item",
        detailResponse: (_requestedIds: number[], defaultDetails: WorkItem[]) =>
          defaultDetails.slice(0, -1),
      },
      {
        label: "mismatched item",
        detailResponse: (_requestedIds: number[], defaultDetails: WorkItem[]) =>
          defaultDetails.map((item, index) =>
            index === 0 ? { ...item, id: 999 } : item,
          ),
      },
    ];

    for (const invalidResponse of invalidDetailResponses) {
      const fixture = createAzureFixture(invalidResponse);

      await expect(fixture.collect()).rejects.toThrow();
      expectOnlyAllowedReads(fixture.calls);
    }
  });

  test("fails closed when a related Feature or Task is missing from its detail batch", async () => {
    const fixture = createAzureFixture({
      detailResponse: (ids, details) =>
        ids.includes(901) ? details.slice(1) : details,
    });

    await expect(fixture.collect()).rejects.toThrow();
    expectOnlyAllowedReads(fixture.calls);
  });

  test("rejects non-Services organization scope before invoking the adapter", async () => {
    const fixture = createAzureFixture({
      organization: "https://synthetic-server.invalid/tfs/collection",
    });

    await expect(fixture.collect()).rejects.toThrow();
    expect(fixture.calls).toEqual([]);
  });

  test("fails closed on synthetic authentication and API errors", async () => {
    const failures = [
      {
        label: "authentication",
        failRequest: (request: AzureRequest) =>
          request.path === backlogItemsPath
            ? new Error("401 synthetic authentication failure")
            : undefined,
      },
      {
        label: "batch API",
        failRequest: (request: AzureRequest) =>
          request.path === workItemBatchPath
            ? new Error("500 synthetic API failure")
            : undefined,
      },
    ];

    for (const failure of failures) {
      const fixture = createAzureFixture(failure);

      await expect(fixture.collect()).rejects.toThrow();
      expectOnlyAllowedReads(fixture.calls);
    }
  });
});
