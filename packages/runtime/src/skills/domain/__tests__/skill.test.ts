import { describe, expect, test } from "bun:test";
import fc from "fast-check";

import { SkillId } from "../../../shared/kernel/branded.ts";
import { isOk, isErr } from "../../../shared/kernel/result.ts";
import { createSkill, type SkillFrontmatter } from "../skill.ts";

const validFrontmatter: SkillFrontmatter = {
  name: "specify",
  description:
    "Use when the user wants to think through a problem before coding.",
  effort: "high",
  tier: "core",
  capabilities: ["tool_use"],
};

describe("Skill — happy path", () => {
  test("creates a valid skill", () => {
    const result = createSkill({
      id: SkillId("specify"),
      frontmatter: validFrontmatter,
      body: "# /ai-specify\n\nInterrogate user requirements.",
      contentHash: "sha256:abc",
    });
    expect(isOk(result)).toBe(true);
    if (isOk(result)) {
      expect(result.value.frontmatter.name).toBe("specify");
      expect(Object.isFrozen(result.value)).toBe(true);
      expect(Object.isFrozen(result.value.frontmatter)).toBe(true);
    }
  });
});

describe("Skill — validation: name", () => {
  test("rejects uppercase", () => {
    const result = createSkill({
      id: SkillId("Foo"),
      frontmatter: { ...validFrontmatter, name: "Foo" },
      body: "body",
      contentHash: "x",
    });
    expect(isErr(result)).toBe(true);
  });

  test("rejects empty name", () => {
    expect(() => SkillId("")).toThrow();
  });

  test("rejects too-long name (>64)", () => {
    const longName = "a".repeat(65);
    const result = createSkill({
      id: SkillId(longName),
      frontmatter: { ...validFrontmatter, name: longName },
      body: "body",
      contentHash: "x",
    });
    expect(isErr(result)).toBe(true);
  });

  test("accepts hyphens", () => {
    const result = createSkill({
      id: SkillId("audit-trail"),
      frontmatter: { ...validFrontmatter, name: "audit-trail" },
      body: "body",
      contentHash: "x",
    });
    expect(isOk(result)).toBe(true);
  });
});

describe("Skill — validation: description", () => {
  test("rejects empty description", () => {
    const result = createSkill({
      id: SkillId("specify"),
      frontmatter: { ...validFrontmatter, description: "" },
      body: "body",
      contentHash: "x",
    });
    expect(isErr(result)).toBe(true);
  });

  test("rejects description >1024 chars", () => {
    const result = createSkill({
      id: SkillId("specify"),
      frontmatter: { ...validFrontmatter, description: "x".repeat(1025) },
      body: "body",
      contentHash: "x",
    });
    expect(isErr(result)).toBe(true);
  });

  test("accepts description at 1024 chars exactly", () => {
    const result = createSkill({
      id: SkillId("specify"),
      frontmatter: { ...validFrontmatter, description: "x".repeat(1024) },
      body: "body",
      contentHash: "x",
    });
    expect(isOk(result)).toBe(true);
  });
});

describe("Skill — validation: body", () => {
  test("rejects whitespace-only body", () => {
    const result = createSkill({
      id: SkillId("specify"),
      frontmatter: validFrontmatter,
      body: "   \n\t  ",
      contentHash: "x",
    });
    expect(isErr(result)).toBe(true);
  });
});

describe("Skill — property-based", () => {
  test("any valid name (lowercase alphanumeric+hyphens, 1..64 chars) is accepted", () => {
    fc.assert(
      fc.property(fc.stringMatching(/^[a-z][a-z0-9-]{0,63}$/), (name) => {
        const result = createSkill({
          id: SkillId(name),
          frontmatter: { ...validFrontmatter, name },
          body: "body",
          contentHash: "x",
        });
        return isOk(result);
      }),
      { numRuns: 200 },
    );
  });

  test("any description in [1, 1024] chars is accepted", () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 1024 }),
        (description) => {
          const result = createSkill({
            id: SkillId("specify"),
            frontmatter: { ...validFrontmatter, description },
            body: "body",
            contentHash: "x",
          });
          return isOk(result);
        },
      ),
      { numRuns: 100 },
    );
  });
});
