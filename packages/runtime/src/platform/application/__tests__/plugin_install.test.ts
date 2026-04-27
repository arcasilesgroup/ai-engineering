import { describe, expect, test } from "bun:test";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { isErr, isOk } from "../../../shared/kernel/result.ts";
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
import { ok } from "../../../shared/kernel/result.ts";

const sha256 = "a".repeat(64);

const baseEntry = (
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
    provides: { skills: ["audit-trail"] },
    trust: {
      tier: "official",
      sigstore_keyless: true,
      slsa_level: 3,
      sbom_format: "cyclonedx-1.6",
    },
  },
  bundle: {
    signature: "/tmp/audit-trail.bundle.json",
    certificate: "cert",
    rekorEntryId: "rekor-entry-1",
  },
  attestationPath: "/tmp/audit-trail.attestation.json",
  artifactPath: "/tmp/audit-trail.tgz",
  sbomPath: "/tmp/audit-trail.sbom.json",
  sourceUri: "git+https://github.com/ai-engineering/audit-trail.git",
  contentHash: sha256,
  scorecard: 8.4,
  ...overrides,
});

class FakeTelemetry implements TelemetryPort {
  emitted: Array<{ level: string; type: string; attributes: unknown }> = [];
  async emit(event: {
    level: string;
    type: string;
    attributes: Record<string, unknown>;
  }): Promise<void> {
    this.emitted.push(event);
  }
  startSpan(): never {
    throw new Error("not used by plugin_install");
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

const withTmp = async <T>(fn: (root: string) => Promise<T>): Promise<T> => {
  const root = mkdtempSync(join(tmpdir(), "ai-eng-plugin-install-"));
  try {
    return await fn(root);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
};

describe("installPlugin — happy path", () => {
  test("verifies, persists, mirrors, and emits plugin.installed", async () => {
    await withTmp(async (root) => {
      const registry = new InMemoryPluginRegistry();
      registry.publish(baseEntry());
      const installDir = new FilesystemPluginInstallDir(root);
      const signature = new FakeSignaturePort();
      const telemetry = new FakeTelemetry();

      const result = await installPlugin(
        { coordinates: "ai-engineering/audit-trail" },
        {
          registry,
          signature,
          installDir,
          sbom: okSbom,
          mirrors: noopMirrors,
          telemetry,
        },
      );
      expect(isOk(result)).toBe(true);
      if (isOk(result)) {
        expect(result.value.plugin.name).toBe("audit-trail");
        expect(result.value.plugin.tier).toBe("official");
        const recordPath = join(root, "audit-trail", "1.2.3", "record.json");
        expect(existsSync(recordPath)).toBe(true);
        const record = JSON.parse(readFileSync(recordPath, "utf8"));
        expect(record.tier).toBe("official");
        expect(record.contentHash).toBe(sha256);
        expect(telemetry.emitted).toHaveLength(1);
        expect(telemetry.emitted[0].type).toBe("plugin.installed");
      }
    });
  });
});

describe("installPlugin — failure paths", () => {
  test("returns not-found when registry has no entry", async () => {
    await withTmp(async (root) => {
      const registry = new InMemoryPluginRegistry();
      const installDir = new FilesystemPluginInstallDir(root);
      const signature = new FakeSignaturePort();
      const telemetry = new FakeTelemetry();

      const result = await installPlugin(
        { coordinates: "missing/plugin" },
        {
          registry,
          signature,
          installDir,
          sbom: okSbom,
          mirrors: noopMirrors,
          telemetry,
        },
      );
      expect(isErr(result)).toBe(true);
      if (isErr(result)) expect(result.error.reason).toBe("not-found");
      expect(telemetry.emitted).toHaveLength(0);
    });
  });

  test("returns invalid-bundle when Sigstore verification fails", async () => {
    await withTmp(async (root) => {
      const registry = new InMemoryPluginRegistry();
      registry.publish(baseEntry());
      const installDir = new FilesystemPluginInstallDir(root);
      const signature = new FakeSignaturePort({ verifyShouldFail: true });
      const telemetry = new FakeTelemetry();

      const result = await installPlugin(
        { coordinates: "ai-engineering/audit-trail" },
        {
          registry,
          signature,
          installDir,
          sbom: okSbom,
          mirrors: noopMirrors,
          telemetry,
        },
      );
      expect(isErr(result)).toBe(true);
      if (isErr(result)) expect(result.error.reason).toBe("invalid-bundle");
      expect(telemetry.emitted).toHaveLength(0);
    });
  });

  test("returns identity-mismatch when Sigstore returns identity-mismatch reason", async () => {
    await withTmp(async (root) => {
      const registry = new InMemoryPluginRegistry();
      registry.publish(baseEntry());
      const installDir = new FilesystemPluginInstallDir(root);
      const signature = new FakeSignaturePort({
        verifyShouldFail: true,
        verifyFailureReason: "identity-mismatch",
      });
      const telemetry = new FakeTelemetry();

      const result = await installPlugin(
        { coordinates: "ai-engineering/audit-trail" },
        {
          registry,
          signature,
          installDir,
          sbom: okSbom,
          mirrors: noopMirrors,
          telemetry,
        },
      );
      expect(isErr(result)).toBe(true);
      if (isErr(result)) expect(result.error.reason).toBe("identity-mismatch");
    });
  });

  test("returns sbom-invalid when SBOM file missing", async () => {
    await withTmp(async (root) => {
      const registry = new InMemoryPluginRegistry();
      registry.publish(baseEntry());
      const installDir = new FilesystemPluginInstallDir(root);
      const signature = new FakeSignaturePort();
      const telemetry = new FakeTelemetry();

      const result = await installPlugin(
        { coordinates: "ai-engineering/audit-trail" },
        {
          registry,
          signature,
          installDir,
          sbom: failSbom,
          mirrors: noopMirrors,
          telemetry,
        },
      );
      expect(isErr(result)).toBe(true);
      if (isErr(result)) expect(result.error.reason).toBe("sbom-invalid");
    });
  });

  test("returns scorecard-too-low when verified plugin has scorecard < 7", async () => {
    await withTmp(async (root) => {
      const registry = new InMemoryPluginRegistry();
      registry.publish(
        baseEntry({
          coordinates: "alice/community-plugin",
          tier: "verified",
          plugin: {
            schema_version: "1",
            plugin: {
              name: "community-plugin",
              version: "0.1.0",
              description: "x",
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
          scorecard: 4.2,
        }),
      );
      const installDir = new FilesystemPluginInstallDir(root);
      const signature = new FakeSignaturePort();
      const telemetry = new FakeTelemetry();

      const result = await installPlugin(
        { coordinates: "alice/community-plugin" },
        {
          registry,
          signature,
          installDir,
          sbom: okSbom,
          mirrors: noopMirrors,
          telemetry,
        },
      );
      expect(isErr(result)).toBe(true);
      if (isErr(result)) expect(result.error.reason).toBe("scorecard-too-low");
    });
  });

  test("returns yanked when registry has yanked the version", async () => {
    await withTmp(async (root) => {
      const registry = new InMemoryPluginRegistry();
      registry.publish(baseEntry());
      registry.yank("ai-engineering/audit-trail", "1.2.3");
      const installDir = new FilesystemPluginInstallDir(root);
      const signature = new FakeSignaturePort();
      const telemetry = new FakeTelemetry();

      const result = await installPlugin(
        { coordinates: "ai-engineering/audit-trail" },
        {
          registry,
          signature,
          installDir,
          sbom: okSbom,
          mirrors: noopMirrors,
          telemetry,
        },
      );
      expect(isErr(result)).toBe(true);
      if (isErr(result)) expect(result.error.reason).toBe("yanked");
    });
  });
});
