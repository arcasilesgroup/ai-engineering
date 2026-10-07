import { describe, expect, test } from "bun:test";
import { resolveTargetAndRead } from "../skills/ai-triage/scripts/resolve-target.mjs";

type AmbiguousField = "provider" | "project" | "team" | "board" | "backlog";

type AzureScope = {
  provider: "azure-devops";
  organization: string;
  project: string;
  team: string;
  board: string;
  backlog: string;
};

type ResolverInput = {
  url?: string;
  remotes?: string[];
  selection?: AzureScope;
};

const ambiguousTargets: Array<{
  field: AmbiguousField;
  input: ResolverInput;
}> = [
  {
    field: "provider",
    input: {
      remotes: [
        "https://github.com/synthetic-org/alpha.git",
        "https://dev.azure.com/synthetic-org/alpha/_git/alpha",
      ],
    },
  },
  {
    field: "project",
    input: {
      remotes: [
        "https://dev.azure.com/synthetic-org/alpha/_git/alpha",
        "https://dev.azure.com/synthetic-org/beta/_git/beta",
      ],
    },
  },
  {
    field: "team",
    input: { url: "https://dev.azure.com/synthetic-org/alpha" },
  },
  {
    field: "board",
    input: {
      url: "https://dev.azure.com/synthetic-org/alpha/platform-team/_boards",
    },
  },
  {
    field: "backlog",
    input: {
      url: "https://dev.azure.com/synthetic-org/alpha/platform-team/_boards/board",
    },
  },
];

describe("triage target routing integration", () => {
  test.each(ambiguousTargets)(
    "does not read when $field is ambiguous",
    async ({ field, input }) => {
      const reads: AzureScope[] = [];
      const read = async (scope: AzureScope) => {
        reads.push(scope);
      };

      const result = await resolveTargetAndRead(input, read);

      expect(result).toMatchObject({ status: "needs-answer", field });
      expect(reads).toEqual([]);
    },
  );

  test("does not read an unsupported Azure DevOps Server target", async () => {
    const reads: AzureScope[] = [];
    const read = async (scope: AzureScope) => {
      reads.push(scope);
    };

    const result = await resolveTargetAndRead(
      {
        url: "https://tfs.synthetic.invalid/tfs/collection/alpha/_git/alpha",
      },
      read,
    );

    expect(result).toMatchObject({ status: "unsupported" });
    expect(reads).toEqual([]);
  });

  test("reads only the explicit scope selected after an ambiguity", async () => {
    const reads: AzureScope[] = [];
    const read = async (scope: AzureScope) => {
      reads.push(scope);
    };
    const unresolvedTarget: ResolverInput = {
      url: "https://dev.azure.com/synthetic-org/alpha/platform-team/_boards/board",
    };
    const selectedScope: AzureScope = {
      provider: "azure-devops",
      organization: "synthetic-org",
      project: "alpha",
      team: "platform-team",
      board: "platform",
      backlog: "features",
    };

    const unresolvedResult = await resolveTargetAndRead(unresolvedTarget, read);
    expect(unresolvedResult).toMatchObject({
      status: "needs-answer",
      field: "backlog",
    });
    expect(reads).toEqual([]);

    const resolvedResult = await resolveTargetAndRead(
      { ...unresolvedTarget, selection: selectedScope },
      read,
    );

    expect(resolvedResult).toMatchObject({ status: "read" });
    expect(reads).toEqual([selectedScope]);
  });
});
