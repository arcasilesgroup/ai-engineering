import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import type { PluginRegistryEntry } from "@ai-engineering/runtime";

import { plugin } from "../plugin.ts";
import { capture, withTmpCwd } from "./_helpers.ts";

const sha256 = "d".repeat(64);

const officialEntry: PluginRegistryEntry = {
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
    provides: { skills: ["audit-trail"] },
    trust: {
      tier: "official",
      sigstore_keyless: true,
      slsa_level: 3,
      sbom_format: "cyclonedx-1.6",
    },
  },
  bundle: {
    signature: "/tmp/audit.bundle.json",
    certificate: "c",
    rekorEntryId: "r",
  },
  attestationPath: "/tmp/audit.att",
  artifactPath: "/tmp/audit.tgz",
  // SBOM path is checked on the FS — the test seeds it inside the tmpdir.
  sbomPath: "",
  sourceUri: "git+https://github.com/ai-engineering/audit-trail.git",
  contentHash: sha256,
  scorecard: 8.4,
};

const verifiedEntry: PluginRegistryEntry = {
  ...officialEntry,
  coordinates: "alice/banking-plugin",
  tier: "verified",
  plugin: {
    schema_version: "1",
    plugin: {
      name: "banking-plugin",
      version: "0.4.0",
      description: "Bank workflows",
      license: "Apache-2.0",
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
};

interface FixtureSetup {
  readonly fixturePath: string;
  readonly sbomPath: string;
  readonly pluginRoot: string;
  cleanup(): void;
}

const setupFixture = (
  entries: ReadonlyArray<PluginRegistryEntry>,
  yanked: ReadonlyArray<{ coordinates: string; version: string }> = [],
): FixtureSetup => {
  const tmp = mkdtempSync(join(tmpdir(), "ai-eng-plugin-cli-"));
  const fixturePath = join(tmp, "registry.json");
  const sbomPath = join(tmp, "sbom.json");
  const pluginRoot = join(tmp, "plugins-root");
  writeFileSync(sbomPath, '{"bomFormat":"CycloneDX","specVersion":"1.6"}\n');
  // Re-point each entry's sbomPath to the seeded path.
  const patched = entries.map((e) => ({ ...e, sbomPath }));
  writeFileSync(
    fixturePath,
    JSON.stringify({ entries: patched, yanked }, null, 2),
  );
  return {
    fixturePath,
    sbomPath,
    pluginRoot,
    cleanup: () => rmSync(tmp, { recursive: true, force: true }),
  };
};

let env: { fixture?: string; root?: string } = {};

beforeEach(() => {
  env = {
    fixture: process.env.AI_ENGINEERING_PLUGIN_FIXTURE_JSON,
    root: process.env.AI_ENGINEERING_PLUGIN_ROOT,
  };
});

afterEach(() => {
  if (env.fixture === undefined)
    delete process.env.AI_ENGINEERING_PLUGIN_FIXTURE_JSON;
  else process.env.AI_ENGINEERING_PLUGIN_FIXTURE_JSON = env.fixture;
  if (env.root === undefined) delete process.env.AI_ENGINEERING_PLUGIN_ROOT;
  else process.env.AI_ENGINEERING_PLUGIN_ROOT = env.root;
});

// ---------------------------------------------------------------------------
// search
// ---------------------------------------------------------------------------

describe("plugin search", () => {
  test("returns matches as a table by default", async () => {
    const fx = setupFixture([officialEntry, verifiedEntry]);
    process.env.AI_ENGINEERING_PLUGIN_FIXTURE_JSON = fx.fixturePath;
    process.env.AI_ENGINEERING_PLUGIN_ROOT = fx.pluginRoot;
    try {
      await withTmpCwd("ai-eng-plugin-search-", async () => {
        const result = await capture(() => plugin(["search", "audit"]));
        expect(result.exitCode).toBe(0);
        expect(result.stdout).toMatch(/audit-trail/);
        expect(result.stdout).toMatch(/official/);
      });
    } finally {
      fx.cleanup();
    }
  });

  test("--json emits structured hits", async () => {
    const fx = setupFixture([officialEntry, verifiedEntry]);
    process.env.AI_ENGINEERING_PLUGIN_FIXTURE_JSON = fx.fixturePath;
    process.env.AI_ENGINEERING_PLUGIN_ROOT = fx.pluginRoot;
    try {
      await withTmpCwd("ai-eng-plugin-search-json-", async () => {
        const result = await capture(() =>
          plugin(["search", "bank", "--json"]),
        );
        expect(result.exitCode).toBe(0);
        const parsed = JSON.parse(result.stdout);
        expect(parsed.hits).toBeInstanceOf(Array);
        expect(parsed.hits[0].name).toBe("banking-plugin");
        expect(parsed.hits[0].tier).toBe("verified");
      });
    } finally {
      fx.cleanup();
    }
  });

  test("empty registry prints friendly message", async () => {
    await withTmpCwd("ai-eng-plugin-search-empty-", async () => {
      delete process.env.AI_ENGINEERING_PLUGIN_FIXTURE_JSON;
      const result = await capture(() => plugin(["search", "anything"]));
      expect(result.exitCode).toBe(0);
      expect(result.stdout).toMatch(/no matches/i);
    });
  });
});

// ---------------------------------------------------------------------------
// install + list + verify + uninstall
// ---------------------------------------------------------------------------

describe("plugin install", () => {
  test("happy path persists the plugin and prints success", async () => {
    const fx = setupFixture([officialEntry]);
    process.env.AI_ENGINEERING_PLUGIN_FIXTURE_JSON = fx.fixturePath;
    process.env.AI_ENGINEERING_PLUGIN_ROOT = fx.pluginRoot;
    try {
      await withTmpCwd("ai-eng-plugin-install-", async () => {
        const result = await capture(() =>
          plugin(["install", "ai-engineering/audit-trail"]),
        );
        expect(result.exitCode).toBe(0);
        expect(result.stdout).toMatch(/installed/);
      });
    } finally {
      fx.cleanup();
    }
  });

  test("missing coordinates returns exit 1", async () => {
    await withTmpCwd("ai-eng-plugin-install-missing-", async () => {
      const result = await capture(() => plugin(["install"]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/usage/i);
    });
  });

  test("yanked plugin returns exit 2 with yanked reason", async () => {
    const fx = setupFixture(
      [officialEntry],
      [{ coordinates: "ai-engineering/audit-trail", version: "1.2.3" }],
    );
    process.env.AI_ENGINEERING_PLUGIN_FIXTURE_JSON = fx.fixturePath;
    process.env.AI_ENGINEERING_PLUGIN_ROOT = fx.pluginRoot;
    try {
      await withTmpCwd("ai-eng-plugin-install-yanked-", async () => {
        const result = await capture(() =>
          plugin(["install", "ai-engineering/audit-trail", "--json"]),
        );
        expect(result.exitCode).toBe(2);
        const parsed = JSON.parse(result.stdout);
        expect(parsed.status).toBe("error");
        expect(parsed.reason).toBe("yanked");
      });
    } finally {
      fx.cleanup();
    }
  });

  test("missing registry entry returns exit 1 with not-found reason", async () => {
    const fx = setupFixture([]);
    process.env.AI_ENGINEERING_PLUGIN_FIXTURE_JSON = fx.fixturePath;
    process.env.AI_ENGINEERING_PLUGIN_ROOT = fx.pluginRoot;
    try {
      await withTmpCwd("ai-eng-plugin-install-missing-entry-", async () => {
        const result = await capture(() =>
          plugin(["install", "nonexistent/plugin", "--json"]),
        );
        expect(result.exitCode).toBe(1);
        const parsed = JSON.parse(result.stdout);
        expect(parsed.reason).toBe("not-found");
      });
    } finally {
      fx.cleanup();
    }
  });
});

describe("plugin list + verify + uninstall + update", () => {
  test("list shows installed plugins; verify reports OK; uninstall removes", async () => {
    const fx = setupFixture([officialEntry]);
    process.env.AI_ENGINEERING_PLUGIN_FIXTURE_JSON = fx.fixturePath;
    process.env.AI_ENGINEERING_PLUGIN_ROOT = fx.pluginRoot;
    try {
      await withTmpCwd("ai-eng-plugin-flow-", async () => {
        const installed = await capture(() =>
          plugin(["install", "ai-engineering/audit-trail"]),
        );
        expect(installed.exitCode).toBe(0);

        const list = await capture(() => plugin(["list", "--json"]));
        expect(list.exitCode).toBe(0);
        const listParsed = JSON.parse(list.stdout);
        expect(listParsed.plugins).toHaveLength(1);
        expect(listParsed.plugins[0].name).toBe("audit-trail");

        const verify = await capture(() => plugin(["verify", "--json"]));
        expect(verify.exitCode).toBe(0);
        const verifyParsed = JSON.parse(verify.stdout);
        expect(verifyParsed.outcomes[0].status).toBe("ok");

        const uninstall = await capture(() =>
          plugin(["uninstall", "audit-trail"]),
        );
        expect(uninstall.exitCode).toBe(0);

        const listAfter = await capture(() => plugin(["list", "--json"]));
        const listAfterParsed = JSON.parse(listAfter.stdout);
        expect(listAfterParsed.plugins).toHaveLength(0);
      });
    } finally {
      fx.cleanup();
    }
  });

  test("verify on yanked plugin returns exit 2", async () => {
    const fx = setupFixture([officialEntry]);
    process.env.AI_ENGINEERING_PLUGIN_FIXTURE_JSON = fx.fixturePath;
    process.env.AI_ENGINEERING_PLUGIN_ROOT = fx.pluginRoot;
    try {
      await withTmpCwd("ai-eng-plugin-verify-yanked-", async () => {
        await capture(() => plugin(["install", "ai-engineering/audit-trail"]));

        // Re-publish fixture with the version yanked.
        writeFileSync(
          fx.fixturePath,
          JSON.stringify(
            {
              entries: [{ ...officialEntry, sbomPath: fx.sbomPath }],
              yanked: [
                { coordinates: "ai-engineering/audit-trail", version: "1.2.3" },
              ],
            },
            null,
            2,
          ),
        );
        const verify = await capture(() => plugin(["verify", "--json"]));
        expect(verify.exitCode).toBe(2);
        const parsed = JSON.parse(verify.stdout);
        expect(parsed.outcomes[0].reason).toBe("yanked");
      });
    } finally {
      fx.cleanup();
    }
  });

  test("uninstall missing plugin returns exit 1", async () => {
    const fx = setupFixture([]);
    process.env.AI_ENGINEERING_PLUGIN_FIXTURE_JSON = fx.fixturePath;
    process.env.AI_ENGINEERING_PLUGIN_ROOT = fx.pluginRoot;
    try {
      await withTmpCwd("ai-eng-plugin-uninstall-missing-", async () => {
        const result = await capture(() => plugin(["uninstall", "ghost"]));
        expect(result.exitCode).toBe(1);
        expect(result.stderr).toMatch(/not installed/);
      });
    } finally {
      fx.cleanup();
    }
  });

  test("update reports newer version when registry advances", async () => {
    const fx = setupFixture([officialEntry]);
    process.env.AI_ENGINEERING_PLUGIN_FIXTURE_JSON = fx.fixturePath;
    process.env.AI_ENGINEERING_PLUGIN_ROOT = fx.pluginRoot;
    try {
      await withTmpCwd("ai-eng-plugin-update-", async () => {
        await capture(() => plugin(["install", "ai-engineering/audit-trail"]));

        // Bump registry version.
        const upgraded: PluginRegistryEntry = {
          ...officialEntry,
          plugin: {
            ...officialEntry.plugin,
            plugin: {
              ...(officialEntry.plugin as { plugin: object }).plugin,
              version: "1.3.0",
            },
          },
          sbomPath: fx.sbomPath,
        };
        writeFileSync(
          fx.fixturePath,
          JSON.stringify({ entries: [upgraded], yanked: [] }, null, 2),
        );

        const update = await capture(() => plugin(["update", "--json"]));
        expect(update.exitCode).toBe(0);
        const parsed = JSON.parse(update.stdout);
        expect(parsed.updates).toHaveLength(1);
        expect(parsed.updates[0].current).toBe("1.2.3");
        expect(parsed.updates[0].latest).toBe("1.3.0");
      });
    } finally {
      fx.cleanup();
    }
  });
});

// ---------------------------------------------------------------------------
// usage / error paths
// ---------------------------------------------------------------------------

describe("plugin — error paths", () => {
  test("no subcommand returns exit 1", async () => {
    await withTmpCwd("ai-eng-plugin-noargs-", async () => {
      const result = await capture(() => plugin([]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/usage/i);
    });
  });

  test("unknown subcommand returns exit 1", async () => {
    await withTmpCwd("ai-eng-plugin-unknown-", async () => {
      const result = await capture(() => plugin(["unknown"]));
      expect(result.exitCode).toBe(1);
      expect(result.stderr).toMatch(/unknown plugin subcommand/);
    });
  });
});
