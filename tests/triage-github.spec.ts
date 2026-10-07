import { describe, expect, test } from "bun:test";
import { runGithubTriage } from "../skills/ai-triage/scripts/github.mjs";

const repository = "octocat/triage-fixtures";
const commit = "0123456789abcdef0123456789abcdef01234567";
const issueFields = [
  "number",
  "title",
  "labels",
  "milestone",
  "reactionGroups",
  "comments",
  "createdAt",
  "updatedAt",
  "author",
  "closedByPullRequestsReferences",
  "body",
];
const pullRequestFields = [
  "number",
  "title",
  "labels",
  "milestone",
  "reactionGroups",
  "comments",
  "createdAt",
  "updatedAt",
  "author",
  "closingIssuesReferences",
  "mergeStateStatus",
  "mergeable",
  "reviewDecision",
  "headRefName",
  "isDraft",
];

function makeIssue(
  number: number,
  title: string,
  overrides: Record<string, unknown> = {},
) {
  return {
    number,
    title,
    labels: [{ name: "triage-fixture" }],
    milestone: { title: "fixture-milestone" },
    reactionGroups: [{ content: "THUMBS_UP", users: { totalCount: 4 } }],
    comments: { totalCount: 2 },
    createdAt: "2026-09-01T00:00:00Z",
    updatedAt: "2026-10-06T00:00:00Z",
    author: { login: "synthetic-owner" },
    closedByPullRequestsReferences: [],
    body: `Synthetic issue body for #${number}.`,
    ...overrides,
  };
}

function makePullRequest(
  number: number,
  title: string,
  overrides: Record<string, unknown> = {},
) {
  return {
    number,
    title,
    labels: [{ name: "triage-fixture" }],
    milestone: { title: "fixture-milestone" },
    reactionGroups: [{ content: "THUMBS_UP", users: { totalCount: 3 } }],
    comments: { totalCount: 1 },
    createdAt: "2026-09-02T00:00:00Z",
    updatedAt: "2026-10-05T00:00:00Z",
    author: { login: "synthetic-contributor" },
    closingIssuesReferences: [],
    mergeStateStatus: "CLEAN",
    mergeable: "MERGEABLE",
    reviewDecision: "APPROVED",
    headRefName: "fixture/ready-change",
    isDraft: false,
    ...overrides,
  };
}

function makeAssessment(overrides: Record<string, string>) {
  return {
    type: "OTHER",
    verdict: "NEEDS_INFO",
    severity: "LOW",
    severityBasis: "Synthetic fixture only.",
    effort: "UNKNOWN",
    repro: "NO",
    depends: "none",
    signals: "fixture signals",
    context: "A synthetic item used to prove report coverage.",
    evidence: [
      `https://github.com/${repository}/issues/41#issuecomment-100`,
    ],
    rootCause: "none",
    draftAnswer: "NEEDS_MANUAL_REVIEW",
    firstMove: "Review the synthetic fixture.",
    ...overrides,
  };
}

const issues = [
  makeIssue(41, "Synthetic confirmed bug", {
    labels: [{ name: "bug" }, { name: "fixture-important" }],
    milestone: { title: "v2.4-fixture" },
    body: "Synthetic report: startup fails after a fixture-only sync.",
  }),
  makeIssue(42, "Synthetic answered question", {
    labels: [{ name: "question" }],
  }),
  makeIssue(43, "Synthetic already-fixed issue", {
    labels: [{ name: "bug" }],
    closedByPullRequestsReferences: [
      {
        number: 52,
        url: `https://github.com/${repository}/pull/52`,
      },
    ],
  }),
  makeIssue(44, "Synthetic feature request", {
    labels: [{ name: "enhancement" }],
  }),
  makeIssue(45, "Synthetic unassessed issue"),
];

const pullRequests = [
  makePullRequest(51, "Synthetic ready pull request", {
    labels: [{ name: "ready-fixture" }],
    headRefName: "fixture/ready-branch",
  }),
  makePullRequest(52, "Synthetic fix for #43", {
    closingIssuesReferences: [
      {
        number: 43,
        url: `https://github.com/${repository}/issues/43`,
      },
    ],
    mergeStateStatus: "MERGED",
    mergeable: "MERGEABLE",
    reviewDecision: "APPROVED",
    headRefName: "fixture/fix-branch",
  }),
];

const assessments = new Map([
  [
    "ISSUE#41",
    makeAssessment({
      type: "BUG",
      verdict: "CONFIRMED_BUG",
      severity: "HIGH",
      severityBasis: "The synthetic report names the failing behavior.",
      effort: "DAY",
      repro: "YES",
      context: "The fixture reproduces a startup failure after syncing.",
      evidence: [
        `https://github.com/${repository}/blob/${commit}/src/fixture.ts#L4-L8`,
      ],
      rootCause: "src/fixture.ts:4",
      firstMove: "Inspect the synthetic startup regression.",
    }),
  ],
  [
    "ISSUE#42",
    makeAssessment({
      type: "QUESTION",
      verdict: "ANSWERED",
      severity: "NONE",
      context: "The synthetic question has a maintainer answer.",
      evidence: [
        `https://github.com/${repository}/issues/42#issuecomment-102`,
      ],
    }),
  ],
  [
    "ISSUE#43",
    makeAssessment({
      type: "BUG",
      verdict: "ALREADY_FIXED",
      severity: "NONE",
      context: "The synthetic issue is linked to its fixing pull request.",
      evidence: [
        `https://github.com/${repository}/pull/52`,
      ],
    }),
  ],
  [
    "ISSUE#44",
    makeAssessment({
      type: "FEATURE",
      verdict: "FEATURE",
      severity: "NONE",
      context: "The synthetic request proposes a small feature.",
      evidence: [
        `https://github.com/${repository}/issues/44`,
      ],
    }),
  ],
  [
    "PR#51",
    makeAssessment({
      type: "PR_OTHER",
      verdict: "PR_READY",
      severity: "NONE",
      context: "The synthetic pull request is ready for human review.",
      evidence: [
        `https://github.com/${repository}/pull/51`,
      ],
      firstMove: "Review the synthetic pull request.",
    }),
  ],
  [
    "PR#52",
    makeAssessment({
      type: "PR_BUGFIX",
      verdict: "ALREADY_FIXED",
      severity: "NONE",
      context: "The synthetic pull request closes issue #43.",
      evidence: [
        `https://github.com/${repository}/pull/52`,
      ],
    }),
  ],
]);

describe("replacement GitHub triage route", () => {
  test("reports the complete synthetic inventory and preserves the read-only report contract", async () => {
    const reads: Array<Record<string, unknown>> = [];
    const writes: Array<Record<string, unknown>> = [];
    const github = {
      async listIssues(request: Record<string, unknown>) {
        reads.push({ kind: "issues", ...request });
        return issues;
      },
      async listPullRequests(request: Record<string, unknown>) {
        reads.push({ kind: "pull requests", ...request });
        return pullRequests;
      },
      async write(request: Record<string, unknown>) {
        writes.push(request);
        throw new Error("GitHub writes are forbidden in triage tests.");
      },
    };

    const result = await runGithubTriage({
      repository,
      commit,
      date: "2026-10-07",
      github,
      assess: async (item: { kind: string; number: number }) =>
        assessments.get(`${item.kind}#${item.number}`) ?? null,
    });
    const inventory = result.inventory as Array<{ kind: string; number: number }>;
    const html = result.html as string;

    expect(inventory.map(({ kind, number }) => `${kind}#${number}`).sort()).toEqual([
      "ISSUE#41",
      "ISSUE#42",
      "ISSUE#43",
      "ISSUE#44",
      "ISSUE#45",
      "PR#51",
      "PR#52",
    ]);
    expect(reads).toEqual([
      {
        kind: "issues",
        repository,
        state: "open",
        fields: issueFields,
      },
      {
        kind: "pull requests",
        repository,
        state: "open",
        fields: pullRequestFields,
      },
    ]);
    expect(writes).toEqual([]);

    expect(html).toContain(`<meta name="ai-triage-repo" content="${repository}">`);
    expect(html).toContain(`<meta name="ai-triage-sha" content="${commit}">`);
    expect(html).toContain(`Triage · ${repository} · 2026-10-07`);
    expect(html).toContain("Snapshot");
    expect(html).toContain("Start here");
    expect(html).toContain("Fix now");
    expect(html).toContain("Answer");
    expect(html).toContain("Close or park");
    expect(html).toContain("Feature requests");
    expect(html).toContain("Pull requests");
    expect(html).toContain("Catalogued");
    expect(html).toContain("First moves");
    expect(html).toContain("Method");

    for (const item of issues) {
      expect(html).toContain(`https://github.com/${repository}/issues/${item.number}`);
      expect(html).toContain(item.title);
    }
    for (const item of pullRequests) {
      expect(html).toContain(`https://github.com/${repository}/pull/${item.number}`);
      expect(html).toContain(item.title);
    }
    expect(html).toContain("UNASSESSED");
    expect(html).toContain("Synthetic unassessed issue");
    expect(html).toContain("fixture-important");
    expect(html).toContain("v2.4-fixture");
    expect(html).toContain("synthetic-owner");
    expect(html).toContain("fixture/ready-branch");
    expect(html).toContain("MERGED");
    expect(html).toContain("also in");
    expect(html).toContain('id="i43-s05"');
    expect(html).toContain('href="#i43-s05"');
  });
});
