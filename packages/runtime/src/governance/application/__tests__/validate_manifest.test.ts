import { describe, expect, test } from "bun:test";

import { isErr, isOk } from "../../../shared/kernel/result.ts";
import { validateManifest } from "../validate_manifest.ts";

const validSkill = {
  name: "specify",
  description: "Use when the user wants to think through a problem.",
  effort: "high",
  tier: "core",
  capabilities: ["tool_use"],
};

const validPlugin = {
  schema_version: "1",
  plugin: {
    name: "ai-platform-bank",
    version: "1.2.3",
    description: "Regulated banking plugin",
    license: "MIT",
  },
  compatibility: { ai_engineering: ">=3.0.0" },
  provides: { skills: ["audit-trail"] },
  trust: {
    tier: "verified",
    sigstore_keyless: true,
    slsa_level: 3,
    sbom_format: "cyclonedx-1.5",
  },
};

describe("validateManifest — happy path", () => {
  test("validates a correct skill frontmatter", () => {
    const result = validateManifest(validSkill, "skill");
    expect(isOk(result)).toBe(true);
    if (isOk(result)) {
      expect(result.value).toEqual(validSkill);
      expect(Object.isFrozen(result.value)).toBe(true);
    }
  });

  test("validates a correct plugin manifest", () => {
    const result = validateManifest(validPlugin, "plugin");
    expect(isOk(result)).toBe(true);
  });
});

describe("validateManifest — error paths", () => {
  test("rejects skill missing required fields", () => {
    const result = validateManifest(
      { name: "specify", description: "ok" },
      "skill",
    );
    expect(isErr(result)).toBe(true);
    if (isErr(result)) {
      expect(result.error.message).toMatch(/required|missing/i);
    }
  });

  test("rejects skill with invalid name pattern (uppercase)", () => {
    const result = validateManifest({ ...validSkill, name: "Foo" }, "skill");
    expect(isErr(result)).toBe(true);
  });

  test("rejects skill with invalid effort enum", () => {
    const result = validateManifest(
      { ...validSkill, effort: "extreme" },
      "skill",
    );
    expect(isErr(result)).toBe(true);
  });

  test("rejects skill with description over 1024 chars", () => {
    const result = validateManifest(
      { ...validSkill, description: "x".repeat(1025) },
      "skill",
    );
    expect(isErr(result)).toBe(true);
  });

  test("rejects plugin missing trust block", () => {
    const { trust: _trust, ...withoutTrust } = validPlugin;
    const result = validateManifest(withoutTrust, "plugin");
    expect(isErr(result)).toBe(true);
  });

  test("rejects unknown schema kind", () => {
    const result = validateManifest({}, "unknown" as never);
    expect(isErr(result)).toBe(true);
  });

  test("rejects null input", () => {
    const result = validateManifest(null, "skill");
    expect(isErr(result)).toBe(true);
  });
});
