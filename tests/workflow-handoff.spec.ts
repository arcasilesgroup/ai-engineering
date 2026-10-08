import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = join(import.meta.dir, "..");

function lifecycle(path: string): string {
  const text = readFileSync(join(root, path), "utf8");
  const block = text.split("## Lifecycle")[1] ?? "";
  return block.split("\n## ")[0] ?? "";
}

function section(path: string, heading: string): { text: string; body: string } {
  const text = readFileSync(join(root, path), "utf8");
  const start = text.indexOf(heading);
  if (start < 0) return { text, body: "" };
  const bodyStart = start + heading.length;
  const nextHeading = /^#{1,3} /m.exec(text.slice(bodyStart));
  return {
    text,
    body: text.slice(bodyStart, nextHeading ? bodyStart + nextHeading.index : undefined),
  };
}

describe("workflow kit — feature work hands off to ai-orchestrator", () => {
  test("ai-brainstorm Lifecycle names ai-orchestrator", () => {
    expect(lifecycle("skills/ai-brainstorm/SKILL.md")).toContain("ai-orchestrator");
  });

  test("ai-orchestrator owns the approve stop", () => {
    const block = lifecycle("skills/ai-orchestrator/SKILL.md");
    expect(block).toContain("Stop: approve");
    expect(block).toContain("approve");
  });

  test("U13: Phase 0 selects or creates the clean same-slug worktree before Phase 1", () => {
    const { text, body } = section("skills/ai-orchestrator/SKILL.md", "## Phase 0: Preflight");
    const phase1 = text.indexOf("## Phase 1: Plan");
    const list = body.indexOf("ai-eng worktree list");
    expect(list).toBeGreaterThanOrEqual(0);

    const afterPreflight = body.slice(list);
    const normalizedAfterPreflight = afterPreflight.replace(/\s+/g, " ");
    const create = afterPreflight.indexOf("ai-eng worktree new");

    expect(afterPreflight).toMatch(/same slug/i);
    expect(afterPreflight).toMatch(/Git-listed path/i);
    expect(afterPreflight).toMatch(/\b(?:resume|existing worktree)\b/i);
    expect(normalizedAfterPreflight).toMatch(
      /only if that same-slug entry is clean[\s\S]{0,160}resume it using its exact git-listed path/i,
    );
    expect(normalizedAfterPreflight).toMatch(/(?:only|otherwise|else)[\s\S]{0,100}(?:slug[\s\S]{0,40}not listed|no matching slug)[\s\S]{0,100}ai-eng worktree new/i);
    expect(body).toMatch(/\bclean\b/i);
    expect(body).toMatch(/\btrusted\b/i);
    expect(create).toBeGreaterThan(0);
    expect(text.indexOf("## Phase 0: Preflight")).toBeLessThan(phase1);
  });

  test("U14: Phase 0 pauses likely overlaps but allows clearly unrelated work", () => {
    const { body } = section("skills/ai-orchestrator/SKILL.md", "## Phase 0: Preflight");

    expect(body).toMatch(/likely overlap/i);
    expect(body).toMatch(/\bpause\b/i);
    expect(body).toMatch(/(?:pause|stop)[\s\S]{0,100}(?:human|user)[\s\S]{0,100}(?:decision|choose|confirm)/i);
    expect(body).toMatch(/clearly unrelated/i);
    expect(body).toMatch(/\b(?:continue|proceed)\b/i);
  });

  test("U16a: Phase 0 stops on dirty or unknown same-slug status before lifecycle actions", () => {
    const { body } = section("skills/ai-orchestrator/SKILL.md", "## Phase 0: Preflight");
    const normalized = body.replace(/[`*_]/g, "").replace(/\s+/g, " ").toLowerCase();
    const listing = normalized.indexOf("ai-eng worktree list");
    const dirtyGuard = normalized.indexOf("has dirty or unknown status", listing);
    const refusal = normalized.slice(dirtyGuard, normalized.indexOf("only if that same-slug entry is clean", dirtyGuard));
    const resume = normalized.indexOf("resume it using its exact git-listed path", dirtyGuard);
    const noMatch = normalized.indexOf("if the slug is not listed", resume);
    const create = normalized.indexOf("ai-eng worktree new", noMatch);

    expect(listing).toBeGreaterThanOrEqual(0);
    expect(dirtyGuard).toBeGreaterThan(listing);
    expect(refusal).toContain("has dirty or unknown status");
    for (const status of ["dirty", "unknown", "missing", "untrusted"]) {
      expect(refusal).toContain(status);
    }
    expect(refusal).toMatch(/preserve it[\s\S]*report its exact git-listed path and evidence[\s\S]*stop phase 0 immediately/);
    expect(refusal).toMatch(
      /do not run ai-eng worktree new, resume it, rebase it, run ai-eng worktree rm, reset it, switch branches, or otherwise mutate it/,
    );
    expect(resume).toBeGreaterThan(dirtyGuard);
    expect(noMatch).toBeGreaterThan(resume);
    expect(create).toBeGreaterThan(noMatch);
  });
});
