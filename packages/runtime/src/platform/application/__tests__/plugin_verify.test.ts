import { describe, expect, test } from "bun:test";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { isOk } from "../../../shared/kernel/result.ts";
import { ok } from "../../../shared/kernel/result.ts";
import type { TelemetryPort } from "../../../shared/ports/telemetry.ts";
import {
  FakeSignaturePort,
  FilesystemPluginInstallDir,
  InMemoryPluginRegistry,
} from "../_fakes.ts";
import {
  type MirrorGeneratorPort,
  type PluginRegistryEntry,
  type SbomCheckPort,
  installPlugin,
} from "../plugin_install.ts";
import { verifyPlugins } from "../plugin_verify.ts";

const sha256 = "c".repeat(64);

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
    signature: "/tmp/x.bundle.json",
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

class FakeTelemetry implements TelemetryPort {
  emitted: Array<{ level: string; type: string }> = [];
  async emit(event: { level: string; type: string }): Promise<void> {
    this.emitted.push(event);
  }
  startSpan(): never {
    throw new Error("not used");
  }
}

const okSbom: SbomCheckPort = {
  async exists() {
    return true;
  },
};
const failSbom: SbomCheckPort = {
  async exists() {
    return false;
  },
};
const noopMirrors: MirrorGeneratorPort = {
  async generate() {
    return ok(undefined);
  },
};

const installFixture = async (
  root: string,
  registry: InMemoryPluginRegistry,
): Promise<void> => {
  registry.publish(entry());
  const installDir = new FilesystemPluginInstallDir(root);
  const result = await installPlugin(
    { coordinates: "ai-engineering/audit-trail" },
    {
      registry,
      signature: new FakeSignaturePort(),
      installDir,
      sbom: okSbom,
      mirrors: noopMirrors,
      telemetry: new FakeTelemetry(),
    },
  );
  if (!isOk(result)) {
    throw new Error(`fixture install failed: ${result.error.message}`);
  }
};

const withTmp = async <T>(fn: (root: string) => Promise<T>): Promise<T> => {
  const root = mkdtempSync(join(tmpdir(), "ai-eng-plugin-verify-"));
  try {
    return await fn(root);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
};

describe("verifyPlugins — happy path", () => {
  test("returns ok for an installed and trusted plugin", async () => {
    await withTmp(async (root) => {
      const registry = new InMemoryPluginRegistry();
      await installFixture(root, registry);

      const result = await verifyPlugins(
        {},
        {
          registry,
          signature: new FakeSignaturePort(),
          installDir: new FilesystemPluginInstallDir(root),
          sbom: okSbom,
        },
      );
      expect(isOk(result)).toBe(true);
      if (isOk(result)) {
        expect(result.value).toHaveLength(1);
        expect(result.value[0]?.status).toBe("ok");
        expect(result.value[0]?.name).toBe("audit-trail");
      }
    });
  });

  test("filters to a single plugin by name", async () => {
    await withTmp(async (root) => {
      const registry = new InMemoryPluginRegistry();
      await installFixture(root, registry);

      const result = await verifyPlugins(
        { name: "audit-trail" },
        {
          registry,
          signature: new FakeSignaturePort(),
          installDir: new FilesystemPluginInstallDir(root),
          sbom: okSbom,
        },
      );
      expect(isOk(result)).toBe(true);
      if (isOk(result)) expect(result.value).toHaveLength(1);
    });
  });
});

describe("verifyPlugins — failure paths", () => {
  test("flags yanked plugin", async () => {
    await withTmp(async (root) => {
      const registry = new InMemoryPluginRegistry();
      await installFixture(root, registry);
      registry.yank("ai-engineering/audit-trail", "1.2.3");

      const result = await verifyPlugins(
        {},
        {
          registry,
          signature: new FakeSignaturePort(),
          installDir: new FilesystemPluginInstallDir(root),
          sbom: okSbom,
        },
      );
      expect(isOk(result)).toBe(true);
      if (isOk(result)) {
        expect(result.value[0]?.status).toBe("fail");
        expect(result.value[0]?.reason).toBe("yanked");
      }
    });
  });

  test("flags missing SBOM", async () => {
    await withTmp(async (root) => {
      const registry = new InMemoryPluginRegistry();
      await installFixture(root, registry);

      const result = await verifyPlugins(
        {},
        {
          registry,
          signature: new FakeSignaturePort(),
          installDir: new FilesystemPluginInstallDir(root),
          sbom: failSbom,
        },
      );
      if (isOk(result)) {
        expect(result.value[0]?.status).toBe("fail");
        expect(result.value[0]?.reason).toBe("sbom-invalid");
      }
    });
  });

  test("flags Sigstore signature regression", async () => {
    await withTmp(async (root) => {
      const registry = new InMemoryPluginRegistry();
      await installFixture(root, registry);

      const result = await verifyPlugins(
        {},
        {
          registry,
          signature: new FakeSignaturePort({ verifyShouldFail: true }),
          installDir: new FilesystemPluginInstallDir(root),
          sbom: okSbom,
        },
      );
      if (isOk(result)) {
        expect(result.value[0]?.status).toBe("fail");
        expect(result.value[0]?.reason).toBe("invalid-bundle");
      }
    });
  });

  test("returns not-found error when filtering by missing plugin name", async () => {
    await withTmp(async (root) => {
      const registry = new InMemoryPluginRegistry();
      await installFixture(root, registry);

      const result = await verifyPlugins(
        { name: "missing" },
        {
          registry,
          signature: new FakeSignaturePort(),
          installDir: new FilesystemPluginInstallDir(root),
          sbom: okSbom,
        },
      );
      expect(isOk(result)).toBe(false);
    });
  });
});
