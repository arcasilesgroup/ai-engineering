import { describe, expect, test } from "bun:test";

import { SpecId } from "../../../shared/kernel/branded.ts";
import { isErr, isOk } from "../../../shared/kernel/result.ts";
import {
  canTransition,
  createSpec,
  transitionSpec,
  type SpecState,
} from "../spec.ts";

const NOW = new Date("2026-04-27T00:00:00Z");

describe("Spec — creation", () => {
  test("creates a draft spec with all required fields", () => {
    const result = createSpec({
      id: SpecId("spec-001-magic-link"),
      title: "Magic link auth",
      motivation: "Reduce password friction",
      acceptanceCriteria: ["User receives email", "Link expires in 15 min"],
      createdAt: NOW,
    });
    expect(isOk(result)).toBe(true);
    if (isOk(result)) {
      expect(result.value.state).toBe("draft");
      expect(Object.isFrozen(result.value)).toBe(true);
      expect(Object.isFrozen(result.value.acceptanceCriteria)).toBe(true);
    }
  });

  test("rejects empty acceptance criteria", () => {
    const result = createSpec({
      id: SpecId("spec-002"),
      title: "Foo",
      motivation: "Bar",
      acceptanceCriteria: [],
      createdAt: NOW,
    });
    expect(isErr(result)).toBe(true);
  });
});

describe("Spec — state machine", () => {
  test.each<[SpecState, SpecState, boolean]>([
    ["draft", "approved", true],
    ["draft", "in_progress", false],
    ["draft", "merged", false],
    ["approved", "in_progress", true],
    ["approved", "draft", false],
    ["in_progress", "merged", true],
    ["in_progress", "approved", false],
    ["merged", "in_progress", false],
    ["merged", "abandoned", false],
    ["abandoned", "draft", false],
  ])("canTransition(%s → %s) === %s", (from, to, expected) => {
    expect(canTransition(from, to)).toBe(expected);
  });

  test("transitionSpec rejects illegal transitions", () => {
    const created = createSpec({
      id: SpecId("spec-003"),
      title: "X",
      motivation: "Y",
      acceptanceCriteria: ["AC1"],
      createdAt: NOW,
    });
    expect(isOk(created)).toBe(true);
    if (!isOk(created)) return;
    const illegal = transitionSpec(created.value, "merged", NOW);
    expect(isErr(illegal)).toBe(true);
  });

  test("transitionSpec advances updatedAt", () => {
    const created = createSpec({
      id: SpecId("spec-004"),
      title: "X",
      motivation: "Y",
      acceptanceCriteria: ["AC1"],
      createdAt: NOW,
    });
    expect(isOk(created)).toBe(true);
    if (!isOk(created)) return;
    const later = new Date(NOW.getTime() + 86400000);
    const approved = transitionSpec(created.value, "approved", later);
    expect(isOk(approved)).toBe(true);
    if (isOk(approved)) {
      expect(approved.value.updatedAt.toISOString()).toBe(later.toISOString());
      expect(approved.value.createdAt.toISOString()).toBe(NOW.toISOString());
    }
  });
});
