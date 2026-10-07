import { readFileSync } from "node:fs";
import { describe, expect, test } from "bun:test";

const githubInstructions = readFileSync(
  new URL("../skills/ai-triage/references/github.md", import.meta.url),
  "utf8",
);
const reportTemplate = readFileSync(
  new URL("../templates/triage.html.tpl", import.meta.url),
  "utf8",
);

describe("GitHub triage instruction contract", () => {
  test("preserves separate complete issue and pull-request inventories", () => {
    const steps = githubInstructions.slice(
      githubInstructions.indexOf("## Steps"),
      githubInstructions.indexOf("## The analysis block"),
    );
    const inventoryStep = steps.slice(
      steps.indexOf("2. Read the whole open backlog"),
      steps.indexOf("3. Join the two halves"),
    );

    expect(inventoryStep).toContain(
      "gh issue list --repo <owner/repo> --state open --limit 1000 --json number,title,labels,milestone,reactionGroups,comments,createdAt,updatedAt,author,closedByPullRequestsReferences,body",
    );
    expect(inventoryStep).toContain(
      "gh pr list --repo <owner/repo> --state open --limit 1000 --json number,title,labels,milestone,reactionGroups,comments,createdAt,updatedAt,author,closingIssuesReferences,mergeStateStatus,mergeable,reviewDecision,headRefName,isDraft",
    );
    expect(
      inventoryStep.slice(inventoryStep.indexOf("gh issue list")),
    ).toMatch(
      /Above 1000\s+items, page with `--search "created:<oldest-in-page"` until a page comes back\s+empty\./,
    );
    expect(
      inventoryStep.slice(inventoryStep.indexOf("gh pr list")),
    ).toMatch(
      /Above 1000\s+items, page with `--search "created:<oldest-in-page"` until a page comes back\s+empty\./,
    );
    expect(inventoryStep).toMatch(
      /\*\*Write down the count you fetched and make the page\s+agree with it\.\*\*/,
    );
  });

  test("preserves per-item analysis, evidence, ranking, and read-only rules", () => {
    const steps = githubInstructions.slice(
      githubInstructions.indexOf("## Steps"),
      githubInstructions.indexOf("## The analysis block"),
    );
    const analysisStep = steps.slice(
      steps.indexOf("5. One subagent per item"),
      steps.indexOf("6. Rank what came back"),
    );
    const analysisBlock = githubInstructions.slice(
      githubInstructions.indexOf("## The analysis block"),
      githubInstructions.indexOf("## Verdict and severity"),
    );
    expect(analysisStep).toMatch(
      /Each reads its own item and returns\s+one analysis block/,
    );
    expect(analysisStep).toContain("require one block per item");
    expect(analysisBlock).toMatch(/exactly this shape, one per item/);
    for (const field of [
      "ITEM:",
      "KIND:",
      "TYPE:",
      "VERDICT:",
      "SEVERITY:",
      "EVIDENCE:",
      "ROOT_CAUSE:",
      "FIRST_MOVE:",
    ]) {
      expect(analysisBlock).toContain(field);
    }

    expect(githubInstructions).toContain("## Evidence rule");
    expect(githubInstructions).toContain("A claim without a permalink carries no weight");
    expect(githubInstructions).toContain("## Ranking: what to start on first");
    for (const band of ["P0", "P1", "P2", "P3", "P4", "P5"]) {
      expect(githubInstructions).toContain(`| ${band} |`);
    }
    expect(githubInstructions).toContain(
      "Tie breaks, in order: severity, how many people the item blocks",
    );

    const readOnlyPolicy = githubInstructions.slice(
      0,
      githubInstructions.indexOf("## Which repository"),
    );
    expect(readOnlyPolicy).toContain("| Forbidden | Allowed |");
    expect(readOnlyPolicy).toContain(
      "Every mutation of GitHub state is a failure of this skill",
    );
    expect(readOnlyPolicy).toContain(
      "No subagent gets a verb from the left column.",
    );

    const activeInstructions = githubInstructions.slice(
      githubInstructions.indexOf("## Which repository"),
    );
    const remoteMutationCommand =
      /\bgh\s+(?:(?:issue\s+(?:comment|close|edit)|pr\s+(?:comment|merge|review|edit|checkout)|repo\s+edit)\b|api\b(?=[^\n]*(?:(?:^|\s)(?:-X|--method)(?:=|\s+)(?:POST|PUT|PATCH|DELETE)\b|(?:^|\s)(?:-F|-f|--field|--raw-field)(?:=|\s)))[^\n]*)/i;
    for (const method of ["POST", "PUT", "PATCH", "DELETE"]) {
      for (const option of ["-X", "--method"]) {
        expect(`gh api ${option} ${method}`).toMatch(remoteMutationCommand);
      }
    }
    for (const fieldOption of ["-f", "--raw-field", "-F", "--field"]) {
      expect(`gh api ${fieldOption} key=value`).toMatch(remoteMutationCommand);
    }
    for (const command of ["gh repo edit"]) {
      expect(command).toMatch(remoteMutationCommand);
    }
    expect(activeInstructions).not.toMatch(remoteMutationCommand);
    expect(reportTemplate).not.toMatch(remoteMutationCommand);
  });

  test("keeps the report template's full-inventory and evidence sections", () => {
    expect(reportTemplate).toContain('<div class="v">{{open_items}}</div>');
    expect(reportTemplate).toContain('<div class="v">{{issues}}</div>');
    expect(reportTemplate).toContain('<div class="v">{{pull_requests}}</div>');
    expect(reportTemplate).toContain("02 · Start here");
    expect(reportTemplate).toContain("07 · Pull requests");
    expect(reportTemplate).toContain("{{evidence}}");
    expect(reportTemplate).toContain("UNASSESSED .item each");
    expect(reportTemplate).toContain("{{method}}");
    expect(reportTemplate).toContain("{{coverage}}");
  });
});
