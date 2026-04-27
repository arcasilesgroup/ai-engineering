import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

import {
  FakeSignaturePort,
  FilesystemPluginInstallDir,
  InMemoryPluginRegistry,
  NdjsonTelemetryAdapter,
  type MirrorGeneratorPort,
  type PluginInstallRecord,
  type PluginRegistryEntry,
  type PluginVerifyOutcome,
  type SbomCheckPort,
  installPlugin,
  isErr,
  isOk,
  ok,
  searchPlugins,
  verifyPlugins,
} from "@ai-engineering/runtime";

import { hasFlag, parseArgs, stringFlag } from "./_args.ts";
import type { CommandHandler } from "./index.ts";

/**
 * `ai-eng plugin <search|install|list|verify|uninstall|update>` — Phase 7
 * marketplace command (Constitution Article VI / ADR-0006).
 *
 * Phase 7 ships with an in-memory registry seeded from a single fixture path
 * (`AI_ENGINEERING_PLUGIN_FIXTURE_JSON`) so the CLI can demonstrate the full
 * trust pipeline without a network. Phase 8+ swaps this for a curated HTTPS
 * registry (OFFICIAL/VERIFIED) plus GitHub topic search (COMMUNITY).
 *
 * Exit codes:
 *   0 — success
 *   1 — user error (missing args, unknown subcommand, plugin not installed)
 *   2 — verification failure (Sigstore, SLSA, SBOM, scorecard, yanked)
 */

const PLUGIN_ROOT = (): string =>
  process.env.AI_ENGINEERING_PLUGIN_ROOT ??
  join(homedir(), ".ai-engineering", "plugins");

const TELEMETRY_PATH = (): string =>
  join(process.cwd(), ".ai-engineering", "state", "framework-events.ndjson");

const REGISTRY_FIXTURE = (): string | undefined =>
  process.env.AI_ENGINEERING_PLUGIN_FIXTURE_JSON;

// -----------------------------------------------------------------------------
// Registry loading — Phase 7 reads a JSON fixture so the CLI is testable.
// -----------------------------------------------------------------------------

interface FixtureFile {
  readonly entries: ReadonlyArray<PluginRegistryEntry>;
  readonly yanked?: ReadonlyArray<{
    readonly coordinates: string;
    readonly version: string;
  }>;
}

const loadRegistry = (): InMemoryPluginRegistry => {
  const registry = new InMemoryPluginRegistry();
  const path = REGISTRY_FIXTURE();
  if (path === undefined || !existsSync(path)) return registry;
  try {
    const raw = readFileSync(path, "utf8");
    const parsed = JSON.parse(raw) as FixtureFile;
    for (const e of parsed.entries) registry.publish(e);
    for (const y of parsed.yanked ?? []) {
      registry.yank(y.coordinates, y.version);
    }
  } catch {
    // Fixture parse errors leave the registry empty; CLI subcommands report
    // "no plugin found" / "no entries" rather than crashing.
  }
  return registry;
};

const filesystemSbom: SbomCheckPort = {
  async exists(path: string) {
    return existsSync(path);
  },
};

const noopMirrors: MirrorGeneratorPort = {
  async generate() {
    return ok(undefined);
  },
};

// -----------------------------------------------------------------------------
// Render helpers
// -----------------------------------------------------------------------------

const padEnd = (s: string, width: number): string =>
  s.length >= width ? s : s + " ".repeat(width - s.length);

const renderSearchTable = (
  hits: ReadonlyArray<{
    coordinates: string;
    tier: string;
    name: string;
    version: string;
    scorecard: number;
  }>,
): string => {
  if (hits.length === 0) {
    return "[ai-eng] plugin search: no matches.\n";
  }
  const header = `  ${padEnd("TIER", 10)} ${padEnd("NAME", 28)} ${padEnd(
    "VERSION",
    10,
  )} ${padEnd("SCORE", 6)} COORDINATES`;
  const rows = hits
    .map(
      (h) =>
        `  ${padEnd(h.tier, 10)} ${padEnd(h.name, 28)} ${padEnd(
          h.version,
          10,
        )} ${padEnd(h.scorecard.toFixed(1), 6)} ${h.coordinates}`,
    )
    .join("\n");
  return `${header}\n${rows}\n`;
};

const renderListTable = (
  records: ReadonlyArray<PluginInstallRecord>,
): string => {
  if (records.length === 0) {
    return "[ai-eng] plugin list: no plugins installed.\n";
  }
  const header = `  ${padEnd("TIER", 10)} ${padEnd("NAME", 28)} ${padEnd(
    "VERSION",
    10,
  )} INSTALLED`;
  const rows = records
    .map(
      (r) =>
        `  ${padEnd(r.plugin.tier, 10)} ${padEnd(r.plugin.name, 28)} ${padEnd(
          r.plugin.version,
          10,
        )} ${r.installedAt.toISOString()}`,
    )
    .join("\n");
  return `${header}\n${rows}\n`;
};

const renderVerifyTable = (
  outcomes: ReadonlyArray<PluginVerifyOutcome>,
): string => {
  if (outcomes.length === 0) {
    return "[ai-eng] plugin verify: no plugins installed.\n";
  }
  return outcomes
    .map((o) => {
      const mark = o.status === "ok" ? "OK" : "FAIL";
      const reason = o.reason !== undefined ? ` (${o.reason})` : "";
      const msg = o.message !== undefined ? ` -- ${o.message}` : "";
      return `  [${mark}] ${o.tier} ${o.name}@${o.version}${reason}${msg}`;
    })
    .join("\n")
    .concat("\n");
};

// -----------------------------------------------------------------------------
// Subcommand handlers
// -----------------------------------------------------------------------------

const searchHandler = async (rest: ReadonlyArray<string>): Promise<number> => {
  const parsed = parseArgs(rest);
  const query = parsed.positional[0] ?? "";
  const registry = loadRegistry();
  const result = await searchPlugins({ query }, registry);
  if (!isOk(result)) {
    process.stderr.write("[ai-eng] plugin search: unexpected error\n");
    return 1;
  }
  if (hasFlag(parsed, "json")) {
    process.stdout.write(
      `${JSON.stringify({ hits: result.value }, null, 2)}\n`,
    );
    return 0;
  }
  process.stdout.write(renderSearchTable(result.value));
  return 0;
};

const installHandler = async (rest: ReadonlyArray<string>): Promise<number> => {
  const parsed = parseArgs(rest);
  const coordinates = parsed.positional[0];
  if (coordinates === undefined || coordinates.length === 0) {
    process.stderr.write(
      "usage: ai-eng plugin install <owner>/<repo> | <name>\n",
    );
    return 1;
  }
  const registry = loadRegistry();
  const installDir = new FilesystemPluginInstallDir(PLUGIN_ROOT());
  const signature = new FakeSignaturePort();
  const telemetry = new NdjsonTelemetryAdapter(TELEMETRY_PATH());

  const result = await installPlugin(
    { coordinates },
    {
      registry,
      signature,
      installDir,
      sbom: filesystemSbom,
      mirrors: noopMirrors,
      telemetry,
    },
  );
  if (isErr(result)) {
    if (hasFlag(parsed, "json")) {
      process.stdout.write(
        `${JSON.stringify(
          {
            status: "error",
            reason: result.error.reason,
            message: result.error.message,
          },
          null,
          2,
        )}\n`,
      );
    } else {
      process.stderr.write(
        `[ai-eng] plugin install failed: ${result.error.message}\n`,
      );
    }
    if (result.error.reason === "not-found") return 1;
    return 2;
  }
  if (hasFlag(parsed, "json")) {
    process.stdout.write(
      `${JSON.stringify(
        {
          status: "ok",
          plugin: {
            name: result.value.plugin.name,
            version: result.value.plugin.version,
            tier: result.value.plugin.tier,
          },
          coordinates: result.value.coordinates,
          installedAt: result.value.installedAt.toISOString(),
        },
        null,
        2,
      )}\n`,
    );
  } else {
    process.stdout.write(
      `[ai-eng] plugin install: ${result.value.plugin.tier} ${result.value.plugin.name}@${result.value.plugin.version} installed.\n`,
    );
  }
  return 0;
};

const listHandler = async (rest: ReadonlyArray<string>): Promise<number> => {
  const parsed = parseArgs(rest);
  const installDir = new FilesystemPluginInstallDir(PLUGIN_ROOT());
  const result = await installDir.list();
  if (isErr(result)) {
    process.stderr.write(`[ai-eng] plugin list: ${result.error.message}\n`);
    return 1;
  }
  if (hasFlag(parsed, "json")) {
    process.stdout.write(
      `${JSON.stringify(
        {
          plugins: result.value.map((r) => ({
            name: r.plugin.name,
            version: r.plugin.version,
            tier: r.plugin.tier,
            coordinates: r.coordinates,
            installedAt: r.installedAt.toISOString(),
          })),
        },
        null,
        2,
      )}\n`,
    );
    return 0;
  }
  process.stdout.write(renderListTable(result.value));
  return 0;
};

const verifyHandler = async (rest: ReadonlyArray<string>): Promise<number> => {
  const parsed = parseArgs(rest);
  const name = parsed.positional[0];
  const registry = loadRegistry();
  const installDir = new FilesystemPluginInstallDir(PLUGIN_ROOT());
  const signature = new FakeSignaturePort();
  const result = await verifyPlugins(name !== undefined ? { name } : {}, {
    registry,
    signature,
    installDir,
    sbom: filesystemSbom,
  });
  if (isErr(result)) {
    process.stderr.write(`[ai-eng] plugin verify: ${result.error.message}\n`);
    return result.error.reason === "not-found" ? 1 : 2;
  }
  if (hasFlag(parsed, "json")) {
    process.stdout.write(
      `${JSON.stringify({ outcomes: result.value }, null, 2)}\n`,
    );
  } else {
    process.stdout.write(renderVerifyTable(result.value));
  }
  const failed = result.value.filter((o) => o.status === "fail").length;
  return failed > 0 ? 2 : 0;
};

const uninstallHandler = async (
  rest: ReadonlyArray<string>,
): Promise<number> => {
  const parsed = parseArgs(rest);
  const name = parsed.positional[0];
  if (name === undefined || name.length === 0) {
    process.stderr.write("usage: ai-eng plugin uninstall <name>\n");
    return 1;
  }
  const installDir = new FilesystemPluginInstallDir(PLUGIN_ROOT());
  const found = await installDir.findByName(name);
  if (isErr(found)) {
    process.stderr.write(`[ai-eng] plugin uninstall: ${found.error.message}\n`);
    return 1;
  }
  if (found.value === null) {
    process.stderr.write(
      `[ai-eng] plugin uninstall: "${name}" is not installed.\n`,
    );
    return 1;
  }
  const removed = await installDir.remove(name);
  if (isErr(removed)) {
    process.stderr.write(
      `[ai-eng] plugin uninstall: ${removed.error.message}\n`,
    );
    return 2;
  }
  const telemetry = new NdjsonTelemetryAdapter(TELEMETRY_PATH());
  await telemetry.emit({
    level: "audit",
    type: "plugin.uninstalled",
    attributes: {
      name,
      version: found.value.plugin.version,
      tier: found.value.plugin.tier,
    },
  });
  if (hasFlag(parsed, "json")) {
    process.stdout.write(
      `${JSON.stringify({ status: "ok", name }, null, 2)}\n`,
    );
  } else {
    process.stdout.write(`[ai-eng] plugin uninstall: ${name} removed.\n`);
  }
  return 0;
};

const updateHandler = async (rest: ReadonlyArray<string>): Promise<number> => {
  const parsed = parseArgs(rest);
  const filter = parsed.positional[0];
  const registry = loadRegistry();
  const installDir = new FilesystemPluginInstallDir(PLUGIN_ROOT());
  const installed = await installDir.list();
  if (isErr(installed)) {
    process.stderr.write(
      `[ai-eng] plugin update: ${installed.error.message}\n`,
    );
    return 1;
  }
  const candidates = filter
    ? installed.value.filter((r) => r.plugin.name === filter)
    : installed.value;
  const updates: Array<{
    name: string;
    current: string;
    latest: string;
    coordinates: string;
  }> = [];
  for (const r of candidates) {
    const latestRes = await registry.resolve(r.coordinates);
    if (!isOk(latestRes)) continue;
    // Per plugin.schema.json the manifest top-level is
    // `{ schema_version, plugin: { name, version, … }, … }`. The registry
    // entry stores the whole manifest as `entry.plugin`, so the latest
    // version lives at `entry.plugin.plugin.version` (not `entry.plugin.version`).
    const manifest = latestRes.value.plugin as { plugin?: unknown };
    const inner =
      manifest.plugin !== undefined && typeof manifest.plugin === "object"
        ? (manifest.plugin as { version?: unknown })
        : {};
    const latestVersion = inner.version;
    if (
      typeof latestVersion === "string" &&
      latestVersion !== r.plugin.version
    ) {
      updates.push({
        name: r.plugin.name,
        current: r.plugin.version,
        latest: latestVersion,
        coordinates: r.coordinates,
      });
    }
  }
  // Surface optional --check flag for clarity (default behavior already
  // dry-run): the alpha drop only reports updates; install is a separate cmd.
  void stringFlag(parsed, "check");
  if (hasFlag(parsed, "json")) {
    process.stdout.write(`${JSON.stringify({ updates }, null, 2)}\n`);
  } else if (updates.length === 0) {
    process.stdout.write("[ai-eng] plugin update: all plugins up-to-date.\n");
  } else {
    process.stdout.write(
      `[ai-eng] plugin update: ${updates.length} updates available\n`,
    );
    for (const u of updates) {
      process.stdout.write(
        `  ${u.name}: ${u.current} -> ${u.latest} (${u.coordinates})\n`,
      );
    }
  }
  return 0;
};

const usage = (): void => {
  process.stderr.write(
    [
      "usage: ai-eng plugin <search|install|list|verify|uninstall|update>",
      "  search <query>                search the registry",
      "  install <owner>/<repo>|<name> install + verify a plugin",
      "  list                          list installed plugins",
      "  verify [name]                 re-verify installed plugins",
      "  uninstall <name>              remove an installed plugin",
      "  update [name]                 check for newer versions",
      "  --json                        emit structured JSON output",
      "",
    ].join("\n"),
  );
};

export const plugin: CommandHandler = async (args) => {
  const [sub, ...rest] = args;
  if (sub === undefined) {
    usage();
    return 1;
  }
  if (sub === "search") return searchHandler(rest);
  if (sub === "install") return installHandler(rest);
  if (sub === "list") return listHandler(rest);
  if (sub === "verify") return verifyHandler(rest);
  if (sub === "uninstall") return uninstallHandler(rest);
  if (sub === "update") return updateHandler(rest);
  process.stderr.write(`unknown plugin subcommand: ${sub}\n`);
  usage();
  return 1;
};
