import { mkdir, readdir, readFile, rm, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";

import { IOError } from "../../shared/kernel/errors.ts";
import { type Result, err, ok } from "../../shared/kernel/result.ts";
import {
  type SLSAProvenance,
  SignatureError,
  type SignaturePort,
  type VerificationContext,
} from "../../shared/ports/signature.ts";
import type { FilesystemPort } from "../../shared/ports/filesystem.ts";
import type {
  PluginInstallDirPort,
  PluginRegistryEntry,
  PluginRegistryPort,
  PluginInstallRecord,
} from "./plugin_install.ts";

/**
 * In-memory fakes for the platform.application plugin use cases.
 *
 * Real adapters (e.g. an HTTPS GitHub registry, a tar-extracting FS adapter)
 * live behind the ports. The fakes here mirror the interfaces 1:1 so tests
 * cover the use case orchestration without spinning up subprocesses or hitting
 * the network. Constitution Article VI: even fakes never silently no-op
 * verification — failure paths are explicit and observable.
 */

// -----------------------------------------------------------------------------
// FakeSignaturePort
// -----------------------------------------------------------------------------

export interface FakeSignatureCallLog {
  readonly verify: ReadonlyArray<VerificationContext>;
  readonly verifySLSA: ReadonlyArray<{
    artifactPath: string;
    attestationPath: string;
    sourceUri: string;
  }>;
}

export interface FakeSignatureOptions {
  readonly verifyShouldFail?: boolean;
  readonly verifyFailureReason?: SignatureError["reason"];
  readonly slsaShouldFail?: boolean;
  readonly slsaProvenance?: SLSAProvenance;
}

const defaultProvenance: SLSAProvenance = {
  builderId:
    "https://github.com/slsa-framework/slsa-github-generator/.github/workflows/generator_generic_slsa3.yml@v2.1.0",
  buildType:
    "https://github.com/slsa-framework/slsa-github-generator/generic@v1",
  invocation: Object.freeze({}),
  materials: Object.freeze([
    Object.freeze({
      uri: "git+https://github.com/example/plugin.git",
      digest: Object.freeze({ sha1: "deadbeef" }),
    }),
  ]),
};

export class FakeSignaturePort implements SignaturePort {
  private readonly options: FakeSignatureOptions;
  private readonly verifyCalls: VerificationContext[] = [];
  private readonly slsaCalls: Array<{
    artifactPath: string;
    attestationPath: string;
    sourceUri: string;
  }> = [];

  constructor(options: FakeSignatureOptions = {}) {
    this.options = options;
  }

  async verify(
    ctx: VerificationContext,
  ): Promise<Result<void, SignatureError>> {
    this.verifyCalls.push(ctx);
    if (this.options.verifyShouldFail) {
      const reason = this.options.verifyFailureReason ?? "invalid-bundle";
      return err(new SignatureError(`fake-sigstore: forced ${reason}`, reason));
    }
    return ok(undefined);
  }

  async verifySLSA(
    artifactPath: string,
    attestationPath: string,
    sourceUri: string,
  ): Promise<Result<SLSAProvenance, SignatureError>> {
    this.slsaCalls.push({ artifactPath, attestationPath, sourceUri });
    if (this.options.slsaShouldFail) {
      return err(
        new SignatureError(
          "fake-sigstore: forced SLSA verification failure",
          "invalid-bundle",
        ),
      );
    }
    return ok(this.options.slsaProvenance ?? defaultProvenance);
  }

  get calls(): FakeSignatureCallLog {
    return {
      verify: [...this.verifyCalls],
      verifySLSA: [...this.slsaCalls],
    };
  }
}

// -----------------------------------------------------------------------------
// InMemoryPluginRegistry — search + resolve a plugin by `<owner>/<repo>` or
// `<name>` (OFFICIAL tier). Maintains a per-name yanked-versions set the
// install flow consults before persisting.
// -----------------------------------------------------------------------------

export class InMemoryPluginRegistry implements PluginRegistryPort {
  private readonly entries = new Map<string, PluginRegistryEntry>();
  private readonly yanked = new Map<string, Set<string>>();

  publish(entry: PluginRegistryEntry): void {
    const key = entry.coordinates.toLowerCase();
    this.entries.set(key, entry);
  }

  yank(coordinates: string, version: string): void {
    const key = coordinates.toLowerCase();
    const versions = this.yanked.get(key) ?? new Set<string>();
    versions.add(version);
    this.yanked.set(key, versions);
  }

  async resolve(
    coordinates: string,
  ): Promise<Result<PluginRegistryEntry, IOError>> {
    const found = this.entries.get(coordinates.toLowerCase());
    if (!found) {
      return err(
        new IOError(
          `registry: plugin not found for coordinates "${coordinates}"`,
        ),
      );
    }
    return ok(found);
  }

  async search(query: string): Promise<ReadonlyArray<PluginRegistryEntry>> {
    const needle = query.toLowerCase();
    return Object.freeze(
      Array.from(this.entries.values()).filter((e) => {
        const haystack =
          `${e.coordinates} ${e.plugin.name} ${e.tier}`.toLowerCase();
        return haystack.includes(needle);
      }),
    );
  }

  async isYanked(
    coordinates: string,
    version: string,
  ): Promise<Result<boolean, IOError>> {
    const set = this.yanked.get(coordinates.toLowerCase());
    return ok(set?.has(version) ?? false);
  }
}

// -----------------------------------------------------------------------------
// FilesystemPluginInstallDir — persists an installed plugin under a root dir
// (e.g. `~/.ai-engineering/plugins/`). Each install lands in
// `<root>/<name>/<version>/` and writes:
//   - manifest.json    — the plugin manifest
//   - record.json      — install record (tier, contentHash, timestamps)
//   - tarball.bin      — the artifact bytes (placeholder — real adapter
//                        downloads + extracts; the use case stays agnostic)
// -----------------------------------------------------------------------------

export class FilesystemPluginInstallDir implements PluginInstallDirPort {
  constructor(private readonly root: string) {}

  async persist(record: PluginInstallRecord): Promise<Result<void, IOError>> {
    try {
      const dir = join(this.root, record.plugin.name, record.plugin.version);
      await mkdir(dir, { recursive: true });
      await writeFile(
        join(dir, "manifest.json"),
        `${JSON.stringify(record.plugin.manifest, null, 2)}\n`,
        "utf8",
      );
      await writeFile(
        join(dir, "record.json"),
        `${JSON.stringify(
          {
            name: record.plugin.name,
            version: record.plugin.version,
            tier: record.plugin.tier,
            contentHash: record.plugin.contentHash,
            coordinates: record.coordinates,
            installedAt: record.installedAt.toISOString(),
            scorecard: record.scorecard,
          },
          null,
          2,
        )}\n`,
        "utf8",
      );
      await writeFile(
        join(dir, "tarball.bin"),
        record.artifactBytes ?? Buffer.alloc(0),
      );
      return ok(undefined);
    } catch (e) {
      return err(
        new IOError(
          `plugin install dir write failed: ${
            e instanceof Error ? e.message : String(e)
          }`,
        ),
      );
    }
  }

  async list(): Promise<Result<ReadonlyArray<PluginInstallRecord>, IOError>> {
    try {
      if (!existsSync(this.root)) return ok(Object.freeze([]));
      const names = await readdir(this.root);
      const records: PluginInstallRecord[] = [];
      for (const name of names) {
        const versions = await readdir(join(this.root, name)).catch(
          () => [] as string[],
        );
        for (const version of versions) {
          const recordPath = join(this.root, name, version, "record.json");
          if (!existsSync(recordPath)) continue;
          try {
            const raw = await readFile(recordPath, "utf8");
            const parsed = JSON.parse(raw) as {
              name: string;
              version: string;
              tier: "official" | "verified" | "community";
              contentHash: string;
              coordinates: string;
              installedAt: string;
              scorecard?: number;
            };
            const manifestRaw = await readFile(
              join(this.root, name, version, "manifest.json"),
              "utf8",
            );
            records.push({
              plugin: {
                name: parsed.name,
                version: parsed.version,
                tier: parsed.tier,
                contentHash: parsed.contentHash,
                manifest: JSON.parse(manifestRaw),
              },
              coordinates: parsed.coordinates,
              installedAt: new Date(parsed.installedAt),
              ...(parsed.scorecard !== undefined
                ? { scorecard: parsed.scorecard }
                : {}),
            });
          } catch {
            // skip corrupted entries — the next verify run flags them.
          }
        }
      }
      return ok(Object.freeze(records));
    } catch (e) {
      return err(
        new IOError(
          `plugin install dir list failed: ${
            e instanceof Error ? e.message : String(e)
          }`,
        ),
      );
    }
  }

  async findByName(
    name: string,
  ): Promise<Result<PluginInstallRecord | null, IOError>> {
    const all = await this.list();
    if (!all.ok) return all;
    const found = all.value.find((r) => r.plugin.name === name);
    return ok(found ?? null);
  }

  async remove(name: string): Promise<Result<void, IOError>> {
    try {
      const dir = join(this.root, name);
      await rm(dir, { recursive: true, force: true });
      return ok(undefined);
    } catch (e) {
      return err(
        new IOError(
          `plugin install dir remove failed: ${
            e instanceof Error ? e.message : String(e)
          }`,
        ),
      );
    }
  }
}

// -----------------------------------------------------------------------------
// InMemoryFilesystem — minimal FilesystemPort fake for use cases that need a
// generic FS dependency (e.g. checking SBOM presence at a path). Tests can
// preload files via `seed()`.
// -----------------------------------------------------------------------------

export class InMemoryFilesystem implements FilesystemPort {
  private readonly files = new Map<string, string>();

  seed(path: string, content: string): void {
    this.files.set(path, content);
  }

  async read(path: string): Promise<Result<string, IOError>> {
    const content = this.files.get(path);
    if (content === undefined) {
      return err(new IOError(`fs.read failed for ${path}: not found`));
    }
    return ok(content);
  }

  async write(path: string, content: string): Promise<Result<void, IOError>> {
    this.files.set(path, content);
    // Mirror node_filesystem behaviour: ensure parent "exists" by also
    // touching the directory key. Simulated dir is implicit.
    void dirname(path);
    return ok(undefined);
  }

  async exists(path: string): Promise<boolean> {
    return this.files.has(path);
  }

  async list(path: string): Promise<Result<string[], IOError>> {
    const prefix = path.endsWith("/") ? path : `${path}/`;
    const entries = new Set<string>();
    for (const k of this.files.keys()) {
      if (k.startsWith(prefix)) {
        const remainder = k.slice(prefix.length);
        const head = remainder.split("/")[0];
        if (head !== undefined && head.length > 0) entries.add(head);
      }
    }
    return ok([...entries].sort());
  }

  async remove(path: string): Promise<Result<void, IOError>> {
    this.files.delete(path);
    return ok(undefined);
  }

  async hash(path: string): Promise<Result<string, IOError>> {
    const content = this.files.get(path);
    if (content === undefined) {
      return err(new IOError(`fs.hash failed for ${path}: not found`));
    }
    // Deterministic faux-hash: 64-hex from content length + first chars.
    // Only used in tests where contentHash is irrelevant for assertions.
    const hex = "0123456789abcdef";
    let out = "";
    for (let i = 0; i < 64; i += 1) {
      const c = content.charCodeAt(i % Math.max(1, content.length)) || 0;
      const idx = (c + i) % 16;
      out += hex[idx];
    }
    return ok(out);
  }
}
