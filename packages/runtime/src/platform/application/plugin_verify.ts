import { type Result, err, isErr, ok } from "../../shared/kernel/result.ts";
import type { SignaturePort } from "../../shared/ports/signature.ts";
import { scorecardThresholdFor } from "../domain/plugin.ts";
import {
  PluginError,
  type PluginInstallDirPort,
  type PluginInstallRecord,
  type PluginRegistryPort,
  type SbomCheckPort,
} from "./plugin_install.ts";

/**
 * PluginVerify — re-run the install-time trust gates against a plugin that is
 * already on disk. The intent is to catch:
 *   - Sigstore certificate revocations / expirations
 *   - SLSA provenance changes (rare, but possible if registry is rewritten)
 *   - SBOM file deletion / tampering
 *   - Yanked versions (the registry can yank long after install)
 *   - Scorecard regressions (verified/official tiers)
 *
 * Returns one `PluginVerifyOutcome` per plugin so callers can render a table
 * or take batch action (`ai-eng plugin verify` runs across every install).
 */

export interface PluginVerifyOutcome {
  readonly name: string;
  readonly version: string;
  readonly tier: "official" | "verified" | "community";
  readonly status: "ok" | "fail";
  readonly reason?: PluginError["reason"];
  readonly message?: string;
}

export interface PluginVerifyDeps {
  readonly registry: PluginRegistryPort;
  readonly signature: SignaturePort;
  readonly installDir: PluginInstallDirPort;
  readonly sbom: SbomCheckPort;
}

export interface PluginVerifyInput {
  /** Optional plugin name; when omitted every installed plugin is verified. */
  readonly name?: string;
  readonly identityIssuer?: string;
  readonly identityRegex?: string;
}

export const verifyPlugins = async (
  input: PluginVerifyInput,
  deps: PluginVerifyDeps,
): Promise<Result<ReadonlyArray<PluginVerifyOutcome>, PluginError>> => {
  const records = await collectRecords(input.name, deps);
  if (isErr(records)) return records;

  const outcomes: PluginVerifyOutcome[] = [];
  for (const record of records.value) {
    outcomes.push(await verifyOne(record, deps));
  }
  return ok(Object.freeze(outcomes));
};

const collectRecords = async (
  name: string | undefined,
  deps: PluginVerifyDeps,
): Promise<Result<ReadonlyArray<PluginInstallRecord>, PluginError>> => {
  if (name !== undefined && name.length > 0) {
    const found = await deps.installDir.findByName(name);
    if (isErr(found)) {
      return err(
        new PluginError(
          `failed to locate installed plugin "${name}": ${found.error.message}`,
          "install-failed",
        ),
      );
    }
    if (found.value === null) {
      return err(
        new PluginError(`plugin "${name}" is not installed`, "not-found"),
      );
    }
    return ok([found.value]);
  }
  const all = await deps.installDir.list();
  if (isErr(all)) {
    return err(
      new PluginError(
        `failed to list installed plugins: ${all.error.message}`,
        "install-failed",
      ),
    );
  }
  return ok(all.value);
};

const verifyOne = async (
  record: PluginInstallRecord,
  deps: PluginVerifyDeps,
): Promise<PluginVerifyOutcome> => {
  const { plugin } = record;
  const base = {
    name: plugin.name,
    version: plugin.version,
    tier: plugin.tier,
  } as const;

  // Re-resolve from registry to get the (possibly updated) bundle + scorecard.
  const resolved = await deps.registry.resolve(record.coordinates);
  if (isErr(resolved)) {
    return {
      ...base,
      status: "fail",
      reason: "not-found",
      message: resolved.error.message,
    };
  }
  const entry = resolved.value;

  // Yank check first — short-circuits any further verification.
  const yanked = await deps.registry.isYanked(
    record.coordinates,
    plugin.version,
  );
  if (isErr(yanked)) {
    return {
      ...base,
      status: "fail",
      reason: "install-failed",
      message: yanked.error.message,
    };
  }
  if (yanked.value) {
    return {
      ...base,
      status: "fail",
      reason: "yanked",
      message: `${plugin.name}@${plugin.version} is yanked in registry`,
    };
  }

  // Re-run signature verification using the registry's bundle.
  const sig = await deps.signature.verify({
    artifactPath: entry.artifactPath,
    bundle: entry.bundle,
    expectedIdentityRegex:
      entry.tier === "official"
        ? "^https://github.com/ai-engineering/.+$"
        : ".+",
    expectedIssuer: "https://token.actions.githubusercontent.com",
  });
  if (isErr(sig)) {
    return {
      ...base,
      status: "fail",
      reason:
        sig.error.reason === "identity-mismatch"
          ? "identity-mismatch"
          : "invalid-bundle",
      message: sig.error.message,
    };
  }

  // Re-run SLSA verification.
  const slsa = await deps.signature.verifySLSA(
    entry.artifactPath,
    entry.attestationPath,
    entry.sourceUri,
  );
  if (isErr(slsa)) {
    return {
      ...base,
      status: "fail",
      reason: "slsa-failed",
      message: slsa.error.message,
    };
  }

  // SBOM presence.
  const sbomOk = await deps.sbom.exists(entry.sbomPath);
  if (!sbomOk) {
    return {
      ...base,
      status: "fail",
      reason: "sbom-invalid",
      message: `SBOM missing at ${entry.sbomPath}`,
    };
  }

  // Scorecard threshold.
  const threshold = scorecardThresholdFor(plugin.tier);
  if (entry.scorecard < threshold) {
    return {
      ...base,
      status: "fail",
      reason: "scorecard-too-low",
      message: `scorecard ${entry.scorecard} < ${threshold}`,
    };
  }

  return { ...base, status: "ok" };
};
