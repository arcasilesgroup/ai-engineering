import { describe, expect, test } from "bun:test";
import { collectAzureBacklog } from "../skills/ai-triage/scripts/collect-azure.mjs";

const scope = {
  organization: "https://dev.azure.com/synthetic-org",
  project: "synthetic-project",
  team: "platform-team",
  backlogId: "stories",
};

const backlogLevelsPath = `/${scope.project}/${scope.team}/_apis/work/backlogs`;
const backlogItemsPath = `${backlogLevelsPath}/${scope.backlogId}/workItems`;
const workItemTypesPath = `/${scope.project}/_apis/wit/workitemtypes`;
const workItemBatchPath = `/${scope.project}/_apis/wit/workitemsbatch`;
const storyStatesPath = `${workItemTypesPath}/Story/states`;
const bugStatesPath = `${workItemTypesPath}/Bug/states`;
const workItemUrl = `${scope.organization}/${scope.project}/_apis/wit/workItems/`;

type AzureRequest = {
  method: "GET" | "POST";
  path: string;
  organization: string;
  apiVersion: string;
  body?: {
    ids?: number[];
    errorPolicy?: string;
  };
};

type WorkItem = {
  id: number;
  fields: {
    "System.WorkItemType": string;
    "System.State": string;
  };
  relations?: Array<{ rel: string; url: string }>;
};

type StateMetadata = {
  name: string;
  stateCategory?: string;
};

type FixtureOptions = {
  workItems?: WorkItem[];
  workItemCountLimit?: number;
  unknownLimit?: boolean;
  stateMetadata?: Record<string, StateMetadata[]>;
  failRequest?: (request: AzureRequest) => Error | undefined;
};

const defaultStateMetadata: Record<string, StateMetadata[]> = {
  Story: [
    { name: "Ready for intake", stateCategory: "Proposed" },
    { name: "Moving through queue", stateCategory: "InProgress" },
    { name: "Archive complete", stateCategory: "Completed" },
  ],
  Bug: [
    { name: "Waiting on validation", stateCategory: "Resolved" },
    { name: "No longer planned", stateCategory: "Removed" },
  ],
};

function createDefaultWorkItems(): WorkItem[] {
  return [
    {
      id: 101,
      fields: {
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
        "System.WorkItemType": "Bug",
        "System.State": "Waiting on validation",
      },
    },
    {
      id: 104,
      fields: {
        "System.WorkItemType": "Story",
        "System.State": "Archive complete",
      },
    },
    {
      id: 105,
      fields: {
        "System.WorkItemType": "Bug",
        "System.State": "No longer planned",
      },
    },
  ];
}

function createAzureFixture(options: FixtureOptions = {}) {
  const calls: AzureRequest[] = [];
  const workItems = options.workItems ?? createDefaultWorkItems();
  const stateMetadata = options.stateMetadata ?? defaultStateMetadata;
  const workItemsById = new Map(workItems.map((item) => [item.id, item]));
  const selectedBacklog = options.unknownLimit
    ? { id: scope.backlogId }
    : {
        id: scope.backlogId,
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
          id,
          url: `${workItemUrl}${id}`,
        })),
      };
    }
    if (request.method === "GET" && request.path === workItemTypesPath) {
      const types = Object.keys(stateMetadata);
      return { count: types.length, value: types.map((name) => ({ name })) };
    }
    if (
      request.method === "GET" &&
      request.path.startsWith(`${workItemTypesPath}/`) &&
      request.path.endsWith("/states")
    ) {
      const workItemType = decodeURIComponent(
        request.path.slice(
          workItemTypesPath.length + 1,
          -"/states".length,
        ),
      );
      return { value: stateMetadata[workItemType] ?? [] };
    }
    if (request.method === "POST" && request.path === workItemBatchPath) {
      const ids = request.body?.ids ?? [];
      return {
        value: ids.flatMap((id) => {
          const item = workItemsById.get(id);
          return item ? [item] : [];
        }),
      };
    }

    throw new Error(`Unexpected synthetic Azure request: ${request.method} ${request.path}`);
  };

  return {
    calls,
    collect: () => collectAzureBacklog({ ...scope, invoke }),
  };
}

const allowedRoutes = new Set([
  `GET ${backlogLevelsPath}`,
  `GET ${backlogItemsPath}`,
  `GET ${workItemTypesPath}`,
  `GET ${storyStatesPath}`,
  `GET ${bugStatesPath}`,
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
        request.apiVersion === "7.1" &&
        request.path.startsWith(`/${scope.project}/`),
    ),
  ).toBe(true);
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
  test("collects only selected backlog members and keeps hierarchy as item context", async () => {
    const fixture = createAzureFixture();
    const inventory = await fixture.collect();

    expect(inventory.complete).toBe(true);
    expect(inventory.items.map((item) => item.id)).toEqual([101, 102, 103]);
    expect(inventory.items.map((item) => item.fields["System.State"])).toEqual([
      "Ready for intake",
      "Moving through queue",
      "Waiting on validation",
    ]);
    expect(inventory.items[0]?.relations).toEqual([
      { rel: "System.LinkTypes.Hierarchy-Reverse", url: `${workItemUrl}901` },
    ]);
    expect(inventory.items[1]?.relations).toEqual([
      { rel: "System.LinkTypes.Hierarchy-Forward", url: `${workItemUrl}902` },
    ]);

    const expectedRoutes = [
      `GET ${backlogLevelsPath}`,
      `GET ${backlogItemsPath}`,
      `GET ${workItemTypesPath}`,
      `GET ${storyStatesPath}`,
      `GET ${bugStatesPath}`,
      `POST ${workItemBatchPath}`,
    ].sort();
    expect(
      fixture.calls.map((request) => `${request.method} ${request.path}`).sort(),
    ).toEqual(expectedRoutes);
    expectOnlyAllowedReads(fixture.calls);

    const [batchRequest] = fixture.calls.filter(
      (request) => request.method === "POST",
    );
    expect(batchRequest?.body).toMatchObject({
      ids: [101, 102, 103, 104, 105],
      errorPolicy: "Fail",
    });
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
      { label: "reached", options: { workItemCountLimit: 5 } },
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

  test("fails closed when state metadata is missing for a selected item type", async () => {
    const fixture = createAzureFixture({
      stateMetadata: {
        Story: [
          { name: "Ready for intake", stateCategory: "Proposed" },
          { name: "Moving through queue", stateCategory: "InProgress" },
        ],
      },
    });

    await expect(fixture.collect()).rejects.toThrow();
    expectOnlyAllowedReads(fixture.calls);
  });

  test("fails closed on synthetic authentication and API errors", async () => {
    const failures = [
      {
        label: "authentication",
        failRequest: (request: AzureRequest) =>
          request.path === workItemTypesPath
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
