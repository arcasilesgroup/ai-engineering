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

  test("merges only when the human asked for the pull request", () => {
    expect(skill).toMatch(/human|the person|the user/i);
    expect(skill).toMatch(/ask|request/i);
    expect(skill).toMatch(/merge/i);
  });
});

describe("ai-pr replaces ai-pr-loop-fix", () => {
  test("skills/ai-pr-loop-fix no longer exists", () => {
    expect(existsSync(join(import.meta.dir, "..", "skills", "ai-pr-loop-fix"))).toBe(false);
  });
});
