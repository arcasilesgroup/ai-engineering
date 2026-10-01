// tests/git-cleanup-pass.spec.ts — document check of the rewritten ai-git-cleanup skill
// (git-worktree-flow test plan, cli layer, checkpoint 4; C15-C18). This pins the prose the
// rewrite must carry, reading SKILL.md as a document — it drives no script, because the
// script the old skill shipped is deleted and no executable code remains behind the verb.

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const skill = readFileSync(join(import.meta.dir, "..", "skills", "ai-git-cleanup", "SKILL.md"), "utf8");
const orchestrator = readFileSync(join(import.meta.dir, "..", "skills", "ai-orchestrator", "SKILL.md"), "utf8");

describe("ai-git-cleanup skill — the one-pass, name-free rewrite", () => {
  test("documents the merged-branch delete with the explicit main ref", () => {
    expect(skill).toContain("git branch --delete-merged refs/heads/main");
  });

  test("documents the --merged main + -d fallback for branches without that upstream", () => {
    expect(skill).toContain("git branch --merged main");
  });

  test("never force-deletes: -D appears nowhere in the skill", () => {
    expect(skill).not.toContain("-D");
  });

  test("asks for no name and has no interactive question", () => {
    // The old prompt words must be gone...
    expect(skill).not.toContain("asks you once");
    expect(skill).not.toMatch(/the one ask/i);
    // ...and the rewrite must say it never asks.
    expect(skill).toMatch(/never asks|no name is ever asked|asks for no name|no interactive question/i);
  });

  test("keeps a Lifecycle block", () => {
    expect(skill).toContain("## Lifecycle");
  });
});

describe("orchestrator close — merge verified before cleanup", () => {
  test("names the ancestry check on feat/<slug> against main before the cleanup, and promises no git branch -D", () => {
    // The close is the `Approve:` bullet; the guard must live in it, before the removal.
    const approveStart = orchestrator.indexOf("- **Approve:**");
    const stopHere = orchestrator.indexOf("- **Stop here:**", approveStart);
    const close = orchestrator.slice(approveStart, stopHere > -1 ? stopHere : undefined);
    const check = close.indexOf("merge-base --is-ancestor");
    expect(check).toBeGreaterThan(-1);
    // The target branch and destination sit in the same clause as the check.
    expect(close.slice(check, check + 120)).toContain("feat/<slug>");
    expect(close.slice(check, check + 160)).toContain("main");
    // Verified first, removed after: the removal instruction follows the check.
    expect(close.lastIndexOf("worktree rm")).toBeGreaterThan(check);
    // And the close never promises the forced delete the verb no longer does.
    expect(orchestrator).not.toContain("branch -D");
  });
});

describe("ai-git-cleanup skill — ignored content is data unless regenerable", () => {
  const regenerable = [
    "node_modules/",
    "dist/",
    "coverage/",
    ".stryker-tmp/",
    "reports/",
    ".ai-engineering/receipts/",
    ".ai-engineering/cache/",
    ".ai-engineering/workflow/playwright/",
  ];

  test("U-CP4-a names the regenerable-output list and says anything else ignored is data", () => {
    for (const entry of regenerable) expect(skill).toContain(entry);
    // The list is bounded by a sentence: this is what the framework regenerates, and
    // any other ignored content is treated as data (so it keeps the worktree).
    expect(skill).toMatch(/regenerat/i);
    expect(skill).toMatch(/\bdata\b/i);
  });

  test("U-CP4-b requires reporting the ignored paths found when it removes a worktree", () => {
    // The reporting word and "ignored" must be in the same sentence about the removal.
    expect(skill).toMatch(
      /ignored[^.]{0,200}(report|name|say|state|list|tell)|(report|name|say|state|list|tell)[^.]{0,200}ignored/i,
    );
  });

  test("U-CP4-c marks ai-eng worktree rm as the explicit human path, not the automatic pass", () => {
    expect(skill).toContain("ai-eng worktree rm");
    expect(skill).toMatch(/explicit|human|a person|the person|by hand/i);
  });
});
