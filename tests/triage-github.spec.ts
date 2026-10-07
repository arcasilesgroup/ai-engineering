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

function isReadOnlyGhApi(command: string): boolean {
  const argumentsText = command.replace(/^gh api\b/i, "").trim();
  const argumentsList = argumentsText.match(/(?:[^\s"'`]+|"[^"]*"|'[^']*')+/g) ?? [];
  let hasEndpoint = false;

  for (let index = 0; index < argumentsList.length; index += 1) {
    const argument = argumentsList[index];
    if (argument === "--method" || argument === "-X") {
      const method = argumentsList[index + 1];
      if (method?.toUpperCase() !== "GET") return false;
      index += 1;
      continue;
    }
    if (/^(?:--method=GET|-X=?GET)$/i.test(argument)) continue;
    if (argument.startsWith("-") || hasEndpoint) return false;
    if (!/^[\w./{}?=&%:-]+$/.test(argument)) return false;
    hasEndpoint = true;
  }
  return true;
}

function isReadOnlyCommand(command: string): boolean {
  const normalizedCommand = command.trim();
  if (
    /^(?:[A-Za-z_][A-Za-z0-9_]*=(?:[^\s"'`]*|"[^"]*"|'[^']*')\s+)+/.test(
      normalizedCommand,
    )
  ) {
    return false;
  }
  const commandSyntax = normalizedCommand.replace(/<[\w./-]+>/g, "");
  if (/[\r\n;&|`$<>\\()]/.test(commandSyntax)) return false;
  const executable = normalizedCommand.match(/^(\S+)/)?.[1];
  const normalizedExecutableCommand = executable
    ? normalizedCommand.replace(/^\S+/, executable.split("/").at(-1) ?? "")
    : "";
  if (normalizedExecutableCommand === "bun test tests/artifact-scroll-spy.spec.ts") return true;
  if (/^gh api(?:\s|$)/i.test(normalizedExecutableCommand)) {
    return isReadOnlyGhApi(normalizedExecutableCommand);
  }
  return /^(?:gh issue (?:list|view)|gh pr (?:list|view|diff)|git remote get-url origin|git (?:log|show|blame|rev-parse))(?:\s|$)/i.test(
    normalizedExecutableCommand,
  );
}

function looksLikeCommand(line: string): boolean {
  return /^(?:[A-Za-z_][A-Za-z0-9_]*=(?:[^\s"'`]*|"[^"]*"|'[^']*')\s+)*(?:\/|~(?:[\w.-]+)?\/|\.{1,2}\/)?(?:[\w.-]+\/)*[a-z][\w-]*\s/.test(
    line.trim(),
  );
}

function commandExamples(markdown: string): string[] {
  const codeBlocks: string[] = [];
  const inlineLines: string[] = [];
  let fenceCharacter: string | undefined;
  let fenceLength = 0;
  let isShellFence = false;
  let isInertFence = false;
  let blockLines: string[] = [];
  const addCodeBlock = () => {
    const block = blockLines.join("\n").trim();
    if (
      block &&
      !isInertFence &&
      (isShellFence || block.split("\n").some(looksLikeCommand))
    ) {
      codeBlocks.push(block);
    }
  };

  for (const line of markdown.split(/\r?\n/)) {
    if (!fenceCharacter) {
      const opening = line.match(/^ {0,3}(`{3,}|~{3,})(.*)$/);
      if (!opening) {
        inlineLines.push(line);
        continue;
      }
      fenceCharacter = opening[1][0];
      fenceLength = opening[1].length;
      isShellFence = /^(?:sh|bash|shell|zsh)(?:\s|$)/i.test(
        opening[2].trim(),
      );
      isInertFence = /^(?:json|html)(?:\s|$)/i.test(opening[2].trim());
      blockLines = [];
      continue;
    }

    const closing = line.match(/^ {0,3}(`+|~+)[ \t]*$/);
    if (
      closing &&
      closing[1][0] === fenceCharacter &&
      closing[1].length >= fenceLength
    ) {
      addCodeBlock();
      fenceCharacter = undefined;
      blockLines = [];
      continue;
    }
    blockLines.push(line);
  }
  if (fenceCharacter) addCodeBlock();

  const inlineCode = inlineLines.join("\n");
  return [
    ...codeBlocks,
    ...[...inlineCode.matchAll(/`([^`\n]+)`/g)].map(([, command]) =>
      command.trim(),
    ),
  ]
    .filter((command) => command.includes("\n") || looksLikeCommand(command));
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
    expect(readOnlyPolicy).toMatch(
      /Only those listed `gh` reads may contact a remote service\.\s+Every other command or tool\s+capable of remote access or changing remote state is forbidden/,
    );
    expect(readOnlyPolicy).toMatch(
      /Use exactly one direct allowlisted CLI command per tool call\./,
    );
    expect(readOnlyPolicy.replace(/\s+/g, " ")).toContain(
      "Do not wrap or compose shell commands: no compound commands, shell wrappers, inline environment assignments, process substitution, command substitution, here-docs, or line continuations.",
    );
    expect(readOnlyPolicy).toContain(
      "Every mutation of GitHub state is a failure of this skill",
    );
    expect(
      commandExamples(githubInstructions).filter(
        (command) => !isReadOnlyCommand(command),
      ),
    ).toEqual([]);
    expect(
      commandExamples(reportTemplate).filter(
        (command) => !isReadOnlyCommand(command),
      ),
    ).toEqual([]);
    expect(isReadOnlyCommand("curl -X POST https://example.invalid")).toBe(false);
    expect(isReadOnlyCommand("git push origin main")).toBe(false);
    expect(isReadOnlyCommand("git log ; git push origin main")).toBe(false);
    expect(
      isReadOnlyCommand(
        "gh issue list <(curl -X POST https://example.invalid)",
      ),
    ).toBe(false);
    expect(
      isReadOnlyCommand(
        "gh issue list >(curl -X POST https://example.invalid)",
      ),
    ).toBe(false);
    expect(
      isReadOnlyCommand(
        "gh issue list =(curl -X POST https://example.invalid)",
      ),
    ).toBe(false);
    expect(isReadOnlyCommand("env gh issue list")).toBe(false);
    expect(isReadOnlyCommand("TOKEN=x gh issue list")).toBe(false);
    expect(
      isReadOnlyCommand("TOKEN=x curl -X POST https://example.invalid"),
    ).toBe(false);
    for (const command of [
      "/usr/bin/curl -X POST https://example.invalid",
      "./curl -X POST https://example.invalid",
      "~/bin/git push origin main",
    ]) {
      expect(isReadOnlyCommand(command)).toBe(false);
      for (const fence of ["```\n", "```text\n", "```python\n"]) {
        const commands = commandExamples(`${fence}${command}\n\`\`\``);
        expect(commands).toEqual([command]);
        expect(commands.every(isReadOnlyCommand)).toBe(false);
      }
    }
    expect(
      commandExamples(
        '```json\n{ "example": "curl -X POST https://example.invalid" }\n```',
      ),
    ).toEqual([]);
    expect(
      commandExamples(
        "```html\n<pre>curl -X POST https://example.invalid</pre>\n```",
      ),
    ).toEqual([]);
    const remoteWriteBlock = "```sh\ncurl -X POST https://example.invalid\n```";
    expect(commandExamples(remoteWriteBlock)).toEqual([
      "curl -X POST https://example.invalid",
    ]);
    expect(commandExamples(remoteWriteBlock).every(isReadOnlyCommand)).toBe(false);
    for (const fencedWrite of [
      "````sh\ncurl -X POST https://example.invalid\n`````",
      "~~~~~bash\nTOKEN=x curl -X POST https://example.invalid\n~~~~~~",
    ]) {
      const commands = commandExamples(fencedWrite);
      expect(commands).toEqual([
        fencedWrite.includes("TOKEN=x ")
          ? "TOKEN=x curl -X POST https://example.invalid"
          : "curl -X POST https://example.invalid",
      ]);
      expect(commands.every(isReadOnlyCommand)).toBe(false);
    }
    const hereDocBlock = [
      "```sh",
      "gh issue list <<EOF",
      "$(curl -X POST https://example.invalid)",
      "EOF",
      "```",
    ].join("\n");
    const hereDocCommands = commandExamples(hereDocBlock);
    expect(hereDocCommands).toEqual([
      "gh issue list <<EOF\n$(curl -X POST https://example.invalid)\nEOF",
    ]);
    expect(hereDocCommands.every(isReadOnlyCommand)).toBe(false);
    for (const command of [
      "gh api -fbody=value /repos/acme/repo",
      "gh api -Fbody=value /repos/acme/repo",
      "gh api --field=body=value /repos/acme/repo",
      "gh api --raw-field=body=value /repos/acme/repo",
      "gh api --input=body.json /repos/acme/repo",
      "gh api --method PATCH /repos/acme/repo",
      "gh api -XPOST /repos/acme/repo",
      "gh api \\\n  --method PATCH /repos/acme/repo",
    ]) {
      expect(isReadOnlyCommand(command)).toBe(false);
    }
    expect(isReadOnlyCommand("gh api --method GET /repos/acme/repo")).toBe(true);
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
