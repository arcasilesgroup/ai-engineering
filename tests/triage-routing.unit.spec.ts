import { describe, expect, test } from "bun:test";
import { resolveTarget } from "../skills/ai-triage/scripts/resolve-target.mjs";

const githubUrl = "https://github.com/example-owner/example-repo";
const githubRemote = `${githubUrl}.git`;
const azureUrl =
  "https://dev.azure.com/example-org/example-project/_boards/board/t/example-team/backlogs/Stories";
const azureRemote =
  "https://dev.azure.com/example-org/example-project/_git/example-repo";
const discoveredBoard = {
  organization: "example-org",
  project: "example-project",
  team: "example-team",
  backlogLevel: "Stories",
};

describe("resolveTarget", () => {
  test("an explicit URL takes precedence over disagreeing remotes", () => {
    expect(
      resolveTarget({ explicitUrl: githubUrl, remotes: [azureRemote] }),
    ).toMatchObject({
      status: "ready",
      provider: "github",
      owner: "example-owner",
      repository: "example-repo",
    });
  });

  test("recognizes an explicit Azure DevOps Services board URL", () => {
    expect(resolveTarget({ explicitUrl: azureUrl, remotes: [] })).toMatchObject({
      status: "ready",
      provider: "azure-devops",
      organization: "example-org",
      project: "example-project",
      team: "example-team",
      backlogLevel: "Stories",
    });
  });

  test("resolves one GitHub repository remote", () => {
    expect(resolveTarget({ remotes: [githubRemote] })).toMatchObject({
      status: "ready",
      provider: "github",
      owner: "example-owner",
      repository: "example-repo",
    });
  });

  test("resolves one Azure remote only when discovery identifies one board level", () => {
    expect(
      resolveTarget({ remotes: [azureRemote], discoveredBoards: [discoveredBoard] }),
    ).toMatchObject({
      status: "ready",
      provider: "azure-devops",
      organization: "example-org",
      project: "example-project",
      team: "example-team",
      backlogLevel: "Stories",
    });
  });

  test("does not infer a target from active Azure defaults or config", () => {
    expect(
      resolveTarget({
        remotes: [],
        activeAzureDefaults: {
          organization: "ignored-org",
          project: "ignored-project",
        },
        config: { provider: "azure-devops", project: "ignored-project" },
      }),
    ).toMatchObject({ status: "needs-answer" });
  });

  test("asks when multiple remotes disagree about provider or repository", () => {
    expect(
      resolveTarget({ remotes: [githubRemote, azureRemote] }),
    ).toMatchObject({ status: "needs-answer" });
    expect(
      resolveTarget({
        remotes: [githubRemote, "https://github.com/other-owner/other-repo.git"],
      }),
    ).toMatchObject({ status: "needs-answer" });
  });

  test("asks when no project is identified", () => {
    expect(
      resolveTarget({ explicitUrl: "https://dev.azure.com/example-org", remotes: [] }),
    ).toMatchObject({ status: "needs-answer" });
  });

  test("asks when discovery finds multiple boards", () => {
    expect(
      resolveTarget({
        remotes: [azureRemote],
        discoveredBoards: [
          discoveredBoard,
          { ...discoveredBoard, team: "another-team" },
        ],
      }),
    ).toMatchObject({ status: "needs-answer" });
  });

  test("asks when the selected board has multiple backlog levels", () => {
    expect(
      resolveTarget({
        remotes: [azureRemote],
        discoveredBoards: [
          discoveredBoard,
          { ...discoveredBoard, backlogLevel: "Features" },
        ],
      }),
    ).toMatchObject({ status: "needs-answer" });
  });

  test("fails closed for an Azure DevOps Server URL", () => {
    expect(
      resolveTarget({
        explicitUrl:
          "https://devops.example.test/tfs/example-collection/example-project/_boards/board",
        remotes: [],
      }),
    ).toMatchObject({ status: "unsupported" });
  });
});
