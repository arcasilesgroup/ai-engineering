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
const unapprovedGitHubCommand =
  /\bgh\s+(?!(?:issue\s+(?:list|view)|pr\s+(?:list|view|diff)|api\b))[\w-]+(?:\s+[\w-]+)?|\bgh\s+api\b(?=[^\n]*(?:(?:^|\s)(?:-X|--method)(?:=|\s+)?(?!GET\b)\S+|(?:^|\s)(?:-F|-f|--field|--raw-field|--input)(?:=|\s|$)))/i;

function normalizeShellContinuations(text: string): string {
  return text.replace(/\\\r?\n[ \t]*/g, " ");
}

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
    const issueInventory = inventoryStep.slice(
      inventoryStep.indexOf("gh issue list"),
      inventoryStep.indexOf("gh pr list"),
    );
    const pullRequestInventory = inventoryStep.slice(
      inventoryStep.indexOf("gh pr list"),
    );

    expect(issueInventory).toContain(
      "gh issue list --repo <owner/repo> --state open --limit 1000 --json number,title,labels,milestone,reactionGroups,comments,createdAt,updatedAt,author,closedByPullRequestsReferences,body",
    );
    expect(pullRequestInventory).toContain(
      "gh pr list --repo <owner/repo> --state open --limit 1000 --json number,title,labels,milestone,reactionGroups,comments,createdAt,updatedAt,author,closingIssuesReferences,mergeStateStatus,mergeable,reviewDecision,headRefName,isDraft",
    );
    expect(issueInventory).toMatch(
      /If this issue inventory returns 1000\s+items, page it with\s+`--search "created:<oldest-in-page"`\s+until a page comes back\s+empty\./,
    );
    expect(issueInventory).toMatch(
      /Write down\s+the fetched issue count and make the page's open-issue count agree\s+with it\./,
    );
    expect(pullRequestInventory).toMatch(
      /If this pull-request inventory returns 1000\s+items, page it with\s+`--search "created:<oldest-in-page"`\s+until a page comes back\s+empty\./,
    );
    expect(pullRequestInventory).toMatch(
      /Write down\s+the fetched pull-request count and make the page's pull-request count agree\s+with it\./,
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
    expect(readOnlyPolicy).toMatch(
      /The only permitted GitHub reads are `gh issue list`, `gh issue view`,\s+`gh pr list`, `gh pr view`, `gh pr diff`, and `gh api` with GET only\./,
    );
    expect(readOnlyPolicy).toMatch(
      /Treat every\s+other `gh` command as forbidden\b/,
    );
    expect(readOnlyPolicy).toContain(
      "Every mutation of GitHub state is a failure of this skill",
    );
    expect(readOnlyPolicy).toContain(
      "Every other remote-state write, through any tool, remains forbidden.",
    );

    expect(
      normalizeShellContinuations(githubInstructions),
    ).not.toMatch(unapprovedGitHubCommand);
    expect(
      normalizeShellContinuations(reportTemplate),
    ).not.toMatch(unapprovedGitHubCommand);
    expect("gh pr lock").toMatch(unapprovedGitHubCommand);
    expect("gh release create").toMatch(unapprovedGitHubCommand);
    expect(
      normalizeShellContinuations("gh api \\\n  --method PATCH /repos/acme/repo"),
    ).toMatch(unapprovedGitHubCommand);
    expect("gh api --method GET /repos/acme/repo").not.toMatch(
      unapprovedGitHubCommand,
    );
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
