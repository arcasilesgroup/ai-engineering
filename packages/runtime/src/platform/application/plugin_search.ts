import { type Result, ok } from "../../shared/kernel/result.ts";
import type { PluginTier } from "../domain/plugin.ts";
import type {
  PluginRegistryEntry,
  PluginRegistryPort,
} from "./plugin_install.ts";

/**
 * PluginSearch — query the (currently in-memory) plugin registry.
 *
 * Phase 7+ swaps the in-memory implementation for a curated HTTPS registry
 * (OFFICIAL/VERIFIED) plus GitHub topic search (COMMUNITY). Both back-ends
 * implement the same `PluginRegistryPort`, so this use case stays pure.
 *
 * Output shape is deliberately minimal — the CLI renders to a table or JSON;
 * the use case is not concerned with presentation.
 */

export interface PluginSearchHit {
  readonly coordinates: string;
  readonly tier: PluginTier;
  readonly name: string;
  readonly version: string;
  readonly description?: string;
  readonly scorecard: number;
}

export interface PluginSearchInput {
  readonly query: string;
  readonly limit?: number;
}

export const searchPlugins = async (
  input: PluginSearchInput,
  registry: PluginRegistryPort,
): Promise<Result<ReadonlyArray<PluginSearchHit>, never>> => {
  const limit = input.limit !== undefined && input.limit > 0 ? input.limit : 50;
  const raw = await registry.search(input.query.trim());
  const hits: PluginSearchHit[] = raw.slice(0, limit).map(toHit);
  return ok(Object.freeze(hits));
};

const toHit = (entry: PluginRegistryEntry): PluginSearchHit => {
  // Manifest shape (plugin.schema.json): top-level `plugin` block holds
  // name/version/description. `entry.plugin` is the *whole manifest*, so we
  // drill into `entry.plugin.plugin` to read those fields. Falling back to
  // `entry.coordinates` for `name` and `"0.0.0"` for `version` keeps the
  // search use case resilient against malformed registry entries (the
  // install + verify gates are the authoritative validators).
  const manifest = entry.plugin as { plugin?: unknown };
  const block =
    manifest.plugin !== undefined && typeof manifest.plugin === "object"
      ? (manifest.plugin as {
          name?: unknown;
          version?: unknown;
          description?: unknown;
        })
      : {};
  const name = typeof block.name === "string" ? block.name : entry.coordinates;
  const version = typeof block.version === "string" ? block.version : "0.0.0";
  return {
    coordinates: entry.coordinates,
    tier: entry.tier,
    name,
    version,
    ...(typeof block.description === "string"
      ? { description: block.description }
      : {}),
    scorecard: entry.scorecard,
  };
};
