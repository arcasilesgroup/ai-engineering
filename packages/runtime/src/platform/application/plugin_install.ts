import { IOError } from "../../shared/kernel/errors.ts";
import { type Result, err, isErr, ok } from "../../shared/kernel/result.ts";
import {
  type SignaturePort,
  SignatureError,
  type VerificationContext,
} from "../../shared/ports/signature.ts";
import type { TelemetryPort } from "../../shared/ports/telemetry.ts";
import {
  type Plugin,
  type PluginTier,
  createPlugin,
  pluginRef,
  scorecardThresholdFor,
} from "../domain/plugin.ts";

/**
 * PluginInstall — orchestrate the full plugin install flow.
 *
 * Constitution Article VI + ADR-0006 require, in this order:
 *   1. Resolve the plugin from the registry (in-memory fake for now).
 *   2. Verify the Sigstore keyless OIDC bundle via SignaturePort.verify.
 *   3. Verify SLSA v1.0 provenance via SignaturePort.verifySLSA.
 *   4. Validate SBOM presence (CycloneDX 1.6) — phase 7 just checks the path.
 *   5. Check OpenSSF Scorecard threshold (≥7 for verified/official).
 *   6. Check `yanked.json` (the registry stores yanked versions in-memory).
 *   7. Persist install record to the install dir port.
 *   8. Generate IDE mirrors (delegated to a pluggable mirror function).
 *   9. Emit `plugin.installed` telemetry.
 *
 * Failure short-circuits with a `PluginError` whose `reason` matches the
 * stage that failed; downstream callers map this to a CLI exit code or a
 * user-facing message without re-classifying.
 */

// -----------------------------------------------------------------------------
// Ports
// -----------------------------------------------------------------------------

export interface PluginRegistryEntry {
  /** `<owner>/<repo>` for COMMUNITY/VERIFIED, or `<name>` for OFFICIAL. */
  readonly coordinates: string;
  readonly tier: PluginTier;
  readonly plugin: PluginManifestRaw;
  readonly bundle: VerificationContext["bundle"];
  readonly attestationPath: string;
  readonly artifactPath: string;
  readonly sbomPath: string;
  readonly sourceUri: string;
  readonly contentHash: string;
  readonly scorecard: number;
  readonly artifactBytes?: Buffer;
}

/** Untyped manifest the registry returns; validated downstream. */
export type PluginManifestRaw = Readonly<Record<string, unknown>>;

export interface PluginRegistryPort {
  resolve(coordinates: string): Promise<Result<PluginRegistryEntry, IOError>>;
  search(query: string): Promise<ReadonlyArray<PluginRegistryEntry>>;
  isYanked(
    coordinates: string,
    version: string,
  ): Promise<Result<boolean, IOError>>;
}

export interface PluginInstallRecord {
  readonly plugin: Plugin;
  readonly coordinates: string;
  readonly installedAt: Date;
  readonly scorecard?: number;
  readonly artifactBytes?: Buffer;
}

export interface PluginInstallDirPort {
  persist(record: PluginInstallRecord): Promise<Result<void, IOError>>;
  list(): Promise<Result<ReadonlyArray<PluginInstallRecord>, IOError>>;
  findByName(
    name: string,
  ): Promise<Result<PluginInstallRecord | null, IOError>>;
  remove(name: string): Promise<Result<void, IOError>>;
}

export interface MirrorGeneratorPort {
  generate(plugin: Plugin): Promise<Result<void, IOError>>;
}

export interface SbomCheckPort {
  exists(path: string): Promise<boolean>;
}

// -----------------------------------------------------------------------------
// Errors
// -----------------------------------------------------------------------------

export type PluginErrorReason =
  | "not-found"
  | "manifest-invalid"
  | "invalid-bundle"
  | "identity-mismatch"
  | "slsa-failed"
  | "sbom-invalid"
  | "scorecard-too-low"
  | "yanked"
  | "install-failed"
  | "mirror-failed";

export class PluginError extends Error {
  constructor(
    message: string,
    public readonly reason: PluginErrorReason,
  ) {
    super(message);
    this.name = "PluginError";
  }
}

// -----------------------------------------------------------------------------
// Use case
// -----------------------------------------------------------------------------

export interface PluginInstallInput {
  readonly coordinates: string;
  readonly identityIssuer?: string;
  readonly identityRegex?: string;
  readonly now?: Date;
}

export interface PluginInstallDeps {
  readonly registry: PluginRegistryPort;
  readonly signature: SignaturePort;
  readonly installDir: PluginInstallDirPort;
  readonly sbom: SbomCheckPort;
  readonly mirrors: MirrorGeneratorPort;
  readonly telemetry: TelemetryPort;
}

export const installPlugin = async (
  input: PluginInstallInput,
  deps: PluginInstallDeps,
): Promise<Result<PluginInstallRecord, PluginError>> => {
  // 1. Resolve from registry.
  const resolved = await deps.registry.resolve(input.coordinates);
  if (isErr(resolved)) {
    return err(
      new PluginError(
        `plugin not found: ${input.coordinates} (${resolved.error.message})`,
        "not-found",
      ),
    );
  }
  const entry = resolved.value;

  // 2. Validate manifest + build domain entity.
  const built = createPlugin({
    manifest: entry.plugin,
    contentHash: entry.contentHash,
  });
  if (isErr(built)) {
    return err(
      new PluginError(
        `plugin manifest invalid for ${input.coordinates}: ${built.error.message}`,
        "manifest-invalid",
      ),
    );
  }
  const plugin = built.value;

  if (plugin.tier !== entry.tier) {
    return err(
      new PluginError(
        `plugin manifest tier (${plugin.tier}) does not match registry tier (${entry.tier})`,
        "manifest-invalid",
      ),
    );
  }

  // 3. Sigstore bundle verification.
  const sigCtx: VerificationContext = {
    artifactPath: entry.artifactPath,
    bundle: entry.bundle,
    expectedIdentityRegex: input.identityRegex ?? defaultIdentityRegex(plugin),
    expectedIssuer:
      input.identityIssuer ?? "https://token.actions.githubusercontent.com",
  };
  const sigResult = await deps.signature.verify(sigCtx);
  if (isErr(sigResult)) {
    return err(translateSignatureError(sigResult.error, plugin));
  }

  // 4. SLSA v1.0 provenance.
  const slsa = await deps.signature.verifySLSA(
    entry.artifactPath,
    entry.attestationPath,
    entry.sourceUri,
  );
  if (isErr(slsa)) {
    return err(
      new PluginError(
        `SLSA v1.0 provenance verification failed for ${pluginRef(plugin)}: ${slsa.error.message}`,
        "slsa-failed",
      ),
    );
  }

  // 5. SBOM presence.
  const sbomOk = await deps.sbom.exists(entry.sbomPath);
  if (!sbomOk) {
    return err(
      new PluginError(
        `SBOM not found at ${entry.sbomPath} (CycloneDX 1.6 required by ADR-0006)`,
        "sbom-invalid",
      ),
    );
  }

  // 6. Scorecard threshold.
  const threshold = scorecardThresholdFor(plugin.tier);
  if (entry.scorecard < threshold) {
    return err(
      new PluginError(
        `OpenSSF Scorecard ${entry.scorecard} below ${plugin.tier} threshold ${threshold} for ${pluginRef(plugin)}`,
        "scorecard-too-low",
      ),
    );
  }

  // 7. Yanked check.
  const yankedRes = await deps.registry.isYanked(
    entry.coordinates,
    plugin.version,
  );
  if (isErr(yankedRes)) {
    return err(
      new PluginError(
        `yanked.json check failed for ${pluginRef(plugin)}: ${yankedRes.error.message}`,
        "install-failed",
      ),
    );
  }
  if (yankedRes.value) {
    return err(
      new PluginError(
        `${pluginRef(plugin)} has been yanked — refusing to install`,
        "yanked",
      ),
    );
  }

  // 8. Persist install record.
  const record: PluginInstallRecord = {
    plugin,
    coordinates: entry.coordinates,
    installedAt: input.now ?? new Date(),
    scorecard: entry.scorecard,
    ...(entry.artifactBytes !== undefined
      ? { artifactBytes: entry.artifactBytes }
      : {}),
  };
  const persisted = await deps.installDir.persist(record);
  if (isErr(persisted)) {
    return err(
      new PluginError(
        `install persist failed for ${pluginRef(plugin)}: ${persisted.error.message}`,
        "install-failed",
      ),
    );
  }

  // 9. Mirror generation (delegated stub for Phase 7).
  const mirror = await deps.mirrors.generate(plugin);
  if (isErr(mirror)) {
    return err(
      new PluginError(
        `IDE mirror generation failed for ${pluginRef(plugin)}: ${mirror.error.message}`,
        "mirror-failed",
      ),
    );
  }

  // 10. Telemetry.
  await deps.telemetry.emit({
    level: "audit",
    type: "plugin.installed",
    attributes: Object.freeze({
      plugin: plugin.name,
      version: plugin.version,
      tier: plugin.tier,
      coordinates: entry.coordinates,
      scorecard: entry.scorecard,
    }),
  });

  return ok(record);
};

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

const translateSignatureError = (
  e: SignatureError,
  plugin: Plugin,
): PluginError => {
  if (e.reason === "identity-mismatch") {
    return new PluginError(
      `Sigstore identity mismatch for ${pluginRef(plugin)}: ${e.message}`,
      "identity-mismatch",
    );
  }
  return new PluginError(
    `Sigstore verification failed for ${pluginRef(plugin)}: ${e.message}`,
    "invalid-bundle",
  );
};

const defaultIdentityRegex = (plugin: Plugin): string => {
  if (plugin.tier === "official") {
    return "^https://github.com/ai-engineering/.+$";
  }
  return ".+";
};
