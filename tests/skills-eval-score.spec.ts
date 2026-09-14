// tests/skills-eval-score.spec.ts — the two guards that stand between a manifest (a file
// a person writes, and gets wrong) and the scorer: a pattern that can backtrack forever,
// and a path that is compared segment by segment rather than as a string.

import { describe, expect, test } from "bun:test";
import { riskyPattern } from "../skills/ai-verify/evals/scripts/score.ts";
import { pathMatches } from "../skills/ai-verify/evals/scripts/score.ts";

describe("riskyPattern — a typo in a manifest must not hang the scorer", () => {
  test("the patterns a manifest actually carries are accepted", () => {
    expect(riskyPattern("admin|authoriz|permission")).toBeNull();
    expect(riskyPattern("(admin|authoriz)\\w*")).toBeNull();
    expect(riskyPattern("^\\[HIGH\\] .+")).toBeNull();
    expect(riskyPattern("a+b*c?")).toBeNull();
    expect(riskyPattern("")).toBeNull();
  });

  test("a quantifier over a group that already quantifies is refused by name", () => {
    expect(riskyPattern("(a+)+")).toMatch(/quantifier applied to a group/);
    expect(riskyPattern("(a*)*")).toMatch(/quantifier applied to a group/);
    expect(riskyPattern("(\\w+){2,}")).toMatch(/quantifier applied to a group/);
  });

  test("a nested group is judged by what it contains, not by its own text", () => {
    expect(riskyPattern("((a+))+")).toMatch(/quantifier applied to a group/);
    expect(riskyPattern("(a(b)c)+")).toBeNull();
  });

  test("escapes and character classes are read as the pattern does", () => {
    expect(riskyPattern("\\(a+\\)")).toBeNull(); // literal parens, no group at all
    expect(riskyPattern("[+*{()]+")).toBeNull(); // quantifier characters inside a class
    expect(riskyPattern("(a+)\\+")).toBeNull(); // the following character is escaped
  });

  test("a pattern long enough to be a paste accident is refused before it is compiled", () => {
    expect(riskyPattern("a".repeat(301))).toMatch(/longer than 300/);
    expect(riskyPattern("a".repeat(300))).toBeNull();
  });
});

describe("pathMatches — a reference path matches a bug path by its tail segments", () => {
  test("the same file written differently is the same file", () => {
    expect(pathMatches("./src/a.ts", "src/a.ts")).toBe(true);
    expect(pathMatches("src/a.ts", "./src/a.ts")).toBe(true);
    expect(pathMatches("/abs/src/a.ts", "src/a.ts")).toBe(true);
    expect(pathMatches("src/a.ts", "src/a.ts")).toBe(true);
  });

  test("a longer path matches by its tail, and a different one does not", () => {
    expect(pathMatches("b/src/a.ts", "src/a.ts")).toBe(true);
    expect(pathMatches("src/a.ts", "b/src/a.ts")).toBe(true);
    expect(pathMatches("src/b.ts", "src/a.ts")).toBe(false);
    expect(pathMatches("src/a.ts", "")).toBe(false);
  });
});
