import { describe, expect, test } from "bun:test";

import { isOk } from "../../../shared/kernel/result.ts";
import { InMemoryPluginRegistry } from "../_fakes.ts";
import type { PluginRegistryEntry } from "../plugin_install.ts";
import { searchPlugins } from "../plugin_search.ts";

const sha256 = "b".repeat(64);

const entry = (
  overrides: Partial<PluginRegistryEntry> = {},
): PluginRegistryEntry => ({
  coordinates: "ai-engineering/audit-trail",
  tier: "official",
  plugin: {
    schema_version: "1",
    plugin: {
      name: "audit-trail",
      version: "1.2.3",
      description: "Regulated audit trail plugin",
      license: "MIT",
    },
    compatibility: { ai_engineering: ">=3.0.0" },
    provides: {},
    trust: {
      tier: "official",
      sigstore_keyless: true,
      slsa_level: 3,
      sbom_format: "cyclonedx-1.6",
    },
  },
  bundle: {
    signature: "/tmp/x",
    certificate: "c",
    rekorEntryId: "r",
  },
  attestationPath: "/tmp/x.att",
  artifactPath: "/tmp/x.tgz",
  sbomPath: "/tmp/x.sbom.json",
  sourceUri: "git+https://github.com/ai-engineering/audit-trail.git",
  contentHash: sha256,
  scorecard: 8.4,
  ...overrides,
});

describe("searchPlugins — happy path", () => {
  test("matches by coordinate substring", async () => {
    const registry = new InMemoryPluginRegistry();
    registry.publish(entry());
    registry.publish(
      entry({
        coordinates: "alice/banking-plugin",
        tier: "verified",
        plugin: {
          schema_version: "1",
          plugin: {
            name: "banking-plugin",
            version: "0.4.0",
            description: "Bank workflows",
            license: "MIT",
          },
          compatibility: { ai_engineering: ">=3.0.0" },
          provides: {},
          trust: {
            tier: "verified",
            sigstore_keyless: true,
            slsa_level: 3,
            sbom_format: "cyclonedx-1.6",
          },
        },
        scorecard: 7.5,
      }),
    );

    const result = await searchPlugins({ query: "bank" }, registry);
    expect(isOk(result)).toBe(true);
    if (isOk(result)) {
      expect(result.value).toHaveLength(1);
      expect(result.value[0]?.coordinates).toBe("alice/banking-plugin");
      expect(result.value[0]?.tier).toBe("verified");
    }
  });

  test("returns all entries when query is empty", async () => {
    const registry = new InMemoryPluginRegistry();
    registry.publish(entry());
    registry.publish(entry({ coordinates: "alice/x", tier: "community" }));

    const result = await searchPlugins({ query: "" }, registry);
    expect(isOk(result)).toBe(true);
    if (isOk(result)) expect(result.value.length).toBe(2);
  });

  test("respects --limit", async () => {
    const registry = new InMemoryPluginRegistry();
    for (let i = 0; i < 5; i += 1) {
      registry.publish(
        entry({
          coordinates: `acme/p${i}`,
          tier: "community",
          plugin: {
            schema_version: "1",
            plugin: {
              name: `p${i}`,
              version: "0.0.1",
              description: "x",
              license: "MIT",
            },
            compatibility: { ai_engineering: ">=3.0.0" },
            provides: {},
            trust: {
              tier: "community",
              sigstore_keyless: true,
              slsa_level: 3,
              sbom_format: "cyclonedx-1.6",
            },
          },
        }),
      );
    }
    const result = await searchPlugins({ query: "acme", limit: 2 }, registry);
    if (isOk(result)) expect(result.value.length).toBe(2);
  });
});

describe("searchPlugins — empty registry", () => {
  test("returns empty array", async () => {
    const registry = new InMemoryPluginRegistry();
    const result = await searchPlugins({ query: "anything" }, registry);
    expect(isOk(result)).toBe(true);
    if (isOk(result)) expect(result.value).toEqual([]);
  });
});
