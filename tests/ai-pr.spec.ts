// tests/ai-pr.spec.ts — document check of the ai-pr full-loop skill
// (git-worktree-flow test plan, cli layer, checkpoint 5; C22). This pins the behaviours the
// loop must carry, reading SKILL.md as a document — it drives no command, because the loop
// itself is prose an agent follows and needs live GitHub, credentials and a human decision.

import { describe, expect, test } from "bun:test";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const skillFile = join(import.meta.dir, "..", "skills", "ai-pr", "SKILL.md");
const skill = existsSync(skillFile) ? readFileSync(skillFile, "utf8") : "";

describe("ai-pr skill — the full pull-request loop", () => {
  test("exists and keeps a Lifecycle block", () => {
    expect(existsSync(skillFile)).toBe(true);
    expect(skill).toContain("## Lifecycle");
  });

  test("opens the pull request against main with gh pr create --base main", () => {
    expect(skill).toMatch(/gh pr create/);
    expect(skill).toMatch(/--base\s+main|--base=main/);
  });

  test("assembles the pull-request body from the merge commits the branch carries", () => {
    // The body is built from the merge commits, not written from scratch.
    expect(skill).toMatch(/merge commits?/i);
    expect(skill).toMatch(/body|description/i);
    expect(skill).toMatch(/assemble|build|compose|gather|collect|derive/i);
  });

  test("watches both CI and review comments", () => {
    expect(skill).toMatch(/gh pr checks|gh run (list|watch|view)/);
    expect(skill).toMatch(/review/i);
    expect(skill).toMatch(/comment/i);
  });

  test("fixes only obvious failures and states a bounded cap on the iterations", () => {
    expect(skill).toMatch(/obvious/i);
    expect(skill).toMatch(/iteration/i);
    expect(skill).toMatch(/bounded|cap|at most|maximum|\bmax\b|\blimit\b/i);
  });

  test("merges with auto-merge on by default and states a way to switch it off", () => {
    expect(skill).toMatch(/gh pr merge/);
    expect(skill).toMatch(/auto-?merge/i);
    expect(skill).toMatch(/--auto/);
    expect(skill).toMatch(/off|disable|opt[- ]?out|--no-auto|without/i);
  });

  test("never deletes a remote branch", () => {
    // The delete forms are absent; a sentence promising not to delete is fine.
    expect(skill).not.toMatch(/push\s+(\S+\s+)?--delete/);
    expect(skill).not.toMatch(/push\s+\S+\s+:\S/);
    expect(skill).not.toMatch(/origin\s+--delete/);
  });

  test("U-PR-a: the merge command does not delete the branch (no --delete-branch)", () => {
    const mergeLines = skill
      .split("\n")
      .filter((line) => /gh pr merge|pr merge/.test(line))
      .join("\n");
    expect(mergeLines).not.toBe(""); // there is a merge command at all
    expect(mergeLines).not.toMatch(/--delete-branch/);
  });

  test("U-PR-b: running the skill is the request to finish; there is an explicit open-only mode", () => {
    // Rolling the skill is the human's request to finish the pull request, not mere advice.
    expect(skill).toMatch(
      /(running|invok|us(e|ing)|start(ing)?|ask(ing)? for|request(ing)?)[^.]{0,150}(skill|this)[^.]{0,150}(is|means|counts as|is treated as)[^.]{0,150}(request|ask|instruction|decision)[^.]{0,150}(finish|complete|land|merge|pull request)/i,
    );
    // And an explicit mode that opens the pull request only, with no merge.
    const openOnly =
      /(open (the )?(pull request|pr)? ?only|only open|just open|open-only|--open-only|without merg|no-?merge)/i;
    expect(skill).toMatch(openOnly);
    // In that mode the merge does not happen.
    expect(skill).toMatch(
      /(open (the )?(pull request|pr)? ?only|only open|just open|open-only)[^.]{0,250}(not|never|no|without)[^.]{0,60}merg/i,
    );
    // The deciding word is the request verb: "open" ends with the pull request created and no merge.
    expect(skill).toMatch(
      /(open|opening)[^.]{0,220}(pull request|pr)[^.]{0,220}(creat|open)[^.]{0,160}(no|not|never|without)[^.]{0,60}merg/i,
    );
    // "finish" / "land" / "merge" continues all the way to the merge.
    expect(skill).toMatch(
      /(finish|finishing|complete|completing|land|landing|merge|merging)[^.]{0,220}(green|checks?|ci|merge|land|pr\b|pull request)/i,
    );
    // An ambiguous request is treated as the open-only one.
    expect(skill).toMatch(
      /(ambiguous|unclear|not clear|unspecified|no (explicit )?(request|ask|instruction|word)|otherwise|default)[^.]{0,200}(open|only open|no merg|not merg|never merg)/i,
    );
    // A sentence that merges on "green" alone, with no request verb, is the failure this guards.
    const mergesOnGreen = skill
      .split(/(?<=[.!?])\s+|\n/)
      .filter((s) => /merg/i.test(s) && /(green|pass(ing|es)?|checks? pass|all checks)/i.test(s))
      .filter((s) => !/(finish|request|ask|asked|human|land|open|decision|explicit|verb)/i.test(s));
    expect(mergesOnGreen).toEqual([]);
  });

  test("U-PR-c: the merge names an explicit strategy, a rule choosing it, and a command listing allowed methods", () => {
    const mergeLines = skill
      .split("\n")
      .filter((line) => /gh pr merge/.test(line))
      .join("\n");
    expect(mergeLines).toMatch(/--squash|--rebase|--merge\b/);
    // A stated rule picks the strategy rather than leaving it to taste.
    expect(skill).toMatch(/(rule|choose|chosen|pick|prefer|decide|depending|when|if)[^.]{0,150}(squash|rebase|merge commit)/i);
    // The allowed methods come from the repository, not from a guess.
    expect(skill).toMatch(/gh api/);
    expect(skill).toMatch(/allow_(squash|merge|rebase)|allowed_merge_methods/);
  });

  test("U-PR-d: fetches before reading origin/main..HEAD for the body", () => {
    expect(skill).toMatch(/git fetch/);
    const range = /origin\/main\s*\.\.\s*HEAD/;
    expect(skill).toMatch(range);
    // The fetch precedes the range in the text of the body assembly.
    expect(skill.search(/git fetch/)).toBeGreaterThan(-1);
    expect(skill.search(/git fetch/)).toBeLessThan(skill.search(range));
  });

  test("U-PR-e: the loop states a maximum number of attempts or polls and what reaching it does", () => {
    // A numeric maximum of attempts/polls.
    expect(skill).toMatch(
      /((attempt|poll|round|iteration|try|tries|pass)[^.\n]{0,40}\b\d+\b|\b\d+\b[^.\n]{0,40}(attempt|poll|round|iteration|try|tries|pass))/i,
    );
    // Reaching the cap has a stated outcome, not a silent stop.
    expect(skill).toMatch(
      /(reach|reaches|reached|exceed|hit|after|once|when|at)[^.]{0,140}(attempt|poll|round|iteration|cap|limit|maximum|max)[^.]{0,180}(stop|report|escalat|ask|hand|give up|abort|fail|leave|not)/i,
    );
    // A wait interval between polls is stated — three polls in a row with none does not pass.
    expect(skill).toMatch(
      /(interval|wait|sleep|every|between|delay)[^.\n]{0,60}\b\d+\s*(s\b|sec|secs|seconds?|minutes?|m\b)|\b\d+\s*(s\b|sec|secs|seconds?)\b[^.\n]{0,50}(interval|wait|between|poll)/i,
    );
  });

  test("U-PR-f: it reads the required status checks and says the rest only inform", () => {
    // The blocking gates are queried from branch protection, not guessed.
    expect(skill).toMatch(/required_status_checks/);
    expect(skill).toMatch(/gh api/);
    expect(skill).toMatch(/branches\/main\/protection|branch protection/i);
    // Everything else is advisory.
    expect(skill).toMatch(
      /(rest|other|remaining|non-required)[^.]{0,150}(workflow|check|job)[^.]{0,150}(inform|advisory|non-?blocking|do(es)? not block|don't block|report only)/i,
    );
  });

  test("merges only when the human asked for the pull request", () => {
    expect(skill).toMatch(/human|the person|the user/i);
    expect(skill).toMatch(/ask|request/i);
    expect(skill).toMatch(/merge/i);
  });

  test("U-PR-g: a re-run continues the same pull request instead of creating a second one", () => {
    // The existing pull request is found by branch, its number read, and creation is skipped.
    expect(skill).toMatch(/gh pr (view|list)\b/);
    expect(skill).toMatch(
      /(already exists|existing (pull request|pr)|if (a |the |one )?(pull request|pr) (already )?exists|re-?run|rerun|run again|second run)[^.]{0,220}(number|#\d|view|reuse|same (pull request|pr)|do not (create|open)|never (create|open)|without (re)?creat|no(new)? (creat|open))/i,
    );
    // The existence check comes before the create command, not after it.
    const view = skill.search(/gh pr (view|list)\b/);
    const create = skill.indexOf("gh pr create");
    expect(view).toBeGreaterThan(-1);
    expect(create).toBeGreaterThan(-1);
    expect(view).toBeLessThan(create);
  });

  test("U-PR-h: a rejected merge is reported, not retried blindly", () => {
    expect(skill).toMatch(/gh pr merge/);
    // A rejection branch exists: gh's own message is surfaced.
    expect(skill).toMatch(
      /(fail|fails|failed|failure|refus|reject|error|non-?zero exit|exit code)[^.]{0,250}(report|print|show|surface|relay|paste|quote|state)[^.]{0,150}(message|output|stderr|error|gh)/i,
    );
    // The pull request is left open.
    expect(skill).toMatch(/(leave|keep|remain|stay)[^.]{0,150}(open|unmerged|not merged|as is)/i);
    // And the loop does not retry the merge blindly.
    expect(skill).toMatch(
      /(no|not|never|do not|don't|without)[^.]{0,100}(blind|blindly)?[^.]{0,40}(retry|re-?try|retrying|re-?run|repeat|loop|again)/i,
    );
  });
});

describe("ai-pr replaces ai-pr-loop-fix", () => {
  test("skills/ai-pr-loop-fix no longer exists", () => {
    expect(existsSync(join(import.meta.dir, "..", "skills", "ai-pr-loop-fix"))).toBe(false);
  });
});
