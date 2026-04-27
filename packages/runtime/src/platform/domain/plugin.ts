import {
  ValidationError,
  type Result,
  err,
  isErr,
  ok,
} from "../../shared/kernel/index.ts";
import {
  type PluginManifest,
  validateManifest,
} from "../../governance/application/validate_manifest.ts";

/**
 * Plugin — a third-party extension loaded into the framework at install time.
 *
 * Constitution Article VI (Supply Chain Integrity) and ADR-0006 define the
 * three-tier trust model:
 *   - OFFICIAL  — `@ai-engineering/*` org, signed by team
 *   - VERIFIED  — community-approved authors, manual review
 *   - COMMUNITY — any GitHub repo with `ai-engineering-plugin` topic
 *
 * Every plugin manifest MUST validate against `shared/schemas/plugin.schema.json`
 * before any of the trust gates run. The domain stays pure: no IO, no async.
 * Behavior (install / verify / persist) lives in the application layer.
 */

export type PluginTier = "official" | "verified" | "community";

export const SCORECARD_THRESHOLD: Readonly<Record<PluginTier, number>> =
  Object.freeze({
    official: 7,
    verified: 7,
    community: 0,
  });

const NAME_RE = /^[a-z][a-z0-9-]{0,127}$/;

const SEMVER_RE = /^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?$/;

const HEX64_RE = /^[a-f0-9]{64}$/i;

export interface Plugin {
  readonly name: string;
  readonly version: string;
  readonly tier: PluginTier;
  readonly manifest: PluginManifest;
  readonly contentHash: string;
}

export interface CreatePluginInput {
  readonly manifest: unknown;
  readonly contentHash: string;
}

/**
 * Builds a Plugin entity from an untyped manifest.
 *
 * Steps:
 *   1. Validate against the JSON Schema (shared/schemas/plugin.schema.json).
 *   2. Re-derive name/version/tier from the validated manifest.
 *   3. Enforce defense-in-depth invariants (sha256 contentHash, name + version
 *      patterns, tier consistency between manifest and entity).
 */
export const createPlugin = (
  input: CreatePluginInput,
): Result<Plugin, ValidationError> => {
  const validated = validateManifest(input.manifest, "plugin");
  if (isErr(validated)) return validated;

  const manifest = validated.value;
  const pluginBlock = manifest.plugin as { name?: unknown; version?: unknown };
  const trustBlock = manifest.trust as { tier?: unknown };

  const name = pluginBlock.name;
  if (typeof name !== "string" || !NAME_RE.test(name)) {
    return err(
      new ValidationError(
        `Plugin name must match ^[a-z][a-z0-9-]{0,127}$ (got ${JSON.stringify(name)})`,
        "plugin.name",
      ),
    );
  }

  const version = pluginBlock.version;
  if (typeof version !== "string" || !SEMVER_RE.test(version)) {
    return err(
      new ValidationError(
        `Plugin version must be semver MAJOR.MINOR.PATCH[-pre] (got ${JSON.stringify(version)})`,
        "plugin.version",
      ),
    );
  }

  const tier = trustBlock.tier;
  if (tier !== "official" && tier !== "verified" && tier !== "community") {
    return err(
      new ValidationError(
        `Plugin trust.tier must be one of official|verified|community (got ${JSON.stringify(tier)})`,
        "trust.tier",
      ),
    );
  }

  if (!HEX64_RE.test(input.contentHash)) {
    return err(
      new ValidationError(
        `Plugin contentHash must be a 64-char hex sha256 digest (got length ${input.contentHash.length})`,
        "contentHash",
      ),
    );
  }

  return ok(
    Object.freeze({
      name,
      version,
      tier,
      manifest,
      contentHash: input.contentHash.toLowerCase(),
    }),
  );
};

/**
 * Returns the OpenSSF Scorecard threshold required for a given tier.
 * VERIFIED + OFFICIAL must clear ≥7; COMMUNITY is informational (≥0).
 */
export const scorecardThresholdFor = (tier: PluginTier): number =>
  SCORECARD_THRESHOLD[tier];

/**
 * Stable string identifier — `name@version`. Useful for logs + telemetry.
 */
export const pluginRef = (plugin: Plugin): string =>
  `${plugin.name}@${plugin.version}`;
