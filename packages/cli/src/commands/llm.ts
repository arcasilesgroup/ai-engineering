import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { hasFlag, parseArgs } from "./_args.ts";
import type { CommandHandler } from "./index.ts";

/**
 * `ai-eng llm <list-providers|test|route|cost>` — multi-LLM thin wrapper.
 *
 * Constitution Article IV (subscription piggyback): Layer 1 needs no LLM,
 * Layer 2 delegates to the IDE host, Layer 3 (BYOK) is opt-in for CI.
 * This command is the BYOK surface; in Phase 4.1 it is intentionally a
 * stub that emits the manifest's provider configuration.
 */
interface ManifestLlm {
  readonly mode?: string;
  readonly privacy_tier?: string;
  readonly providers?: ReadonlyArray<Readonly<Record<string, unknown>>>;
}

const readLlmConfig = (): ManifestLlm => {
  const path = join(process.cwd(), ".ai-engineering", "manifest.json");
  if (!existsSync(path)) {
    return Object.freeze({
      mode: "piggyback",
      privacy_tier: "standard",
      providers: Object.freeze([Object.freeze({ id: "claude-code", method: "piggyback" })]),
    });
  }
  try {
    const parsed = JSON.parse(readFileSync(path, "utf8")) as {
      llm?: ManifestLlm;
    };
    if (parsed.llm !== undefined) {
      return Object.freeze({
        mode: parsed.llm.mode ?? "piggyback",
        privacy_tier: parsed.llm.privacy_tier ?? "standard",
        providers: Object.freeze([...(parsed.llm.providers ?? [])]),
      });
    }
  } catch {
    // fall through to default
  }
  return Object.freeze({
    mode: "piggyback",
    privacy_tier: "standard",
    providers: Object.freeze([Object.freeze({ id: "claude-code", method: "piggyback" })]),
  });
};

const listProvidersHandler = async (rest: ReadonlyArray<string>): Promise<number> => {
  const parsed = parseArgs(rest);
  const cfg = readLlmConfig();
  if (hasFlag(parsed, "json")) {
    process.stdout.write(`${JSON.stringify(cfg, null, 2)}\n`);
    return 0;
  }
  const providers = cfg.providers ?? [];
  if (providers.length === 0) {
    process.stdout.write("[ai-eng] llm list-providers: no providers configured.\n");
    return 0;
  }
  process.stdout.write(`[ai-eng] llm providers (mode=${cfg.mode}, tier=${cfg.privacy_tier})\n`);
  for (const p of providers) {
    const id = String((p as { id?: unknown }).id ?? "?");
    const method = String((p as { method?: unknown }).method ?? "?");
    process.stdout.write(`  - ${id} (${method})\n`);
  }
  return 0;
};

const testHandler = async (rest: ReadonlyArray<string>): Promise<number> => {
  const parsed = parseArgs(rest);
  if (hasFlag(parsed, "json")) {
    process.stdout.write(
      `${JSON.stringify(
        {
          status: "stubbed",
          phase: "4.1",
          message: "llm test lands in Phase 5",
        },
        null,
        2,
      )}\n`,
    );
  } else {
    process.stdout.write("[ai-eng] llm test: (Phase 5 — not yet implemented)\n");
  }
  return 0;
};

const routeHandler = async (rest: ReadonlyArray<string>): Promise<number> => {
  const [sub, ...subRest] = rest;
  const parsed = parseArgs(subRest);
  if (sub !== "show") {
    process.stderr.write("usage: ai-eng llm route show [--json]\n");
    return 1;
  }
  const cfg = readLlmConfig();
  const route = {
    mode: cfg.mode,
    default: cfg.providers?.[0] ?? null,
  };
  if (hasFlag(parsed, "json")) {
    process.stdout.write(`${JSON.stringify(route, null, 2)}\n`);
    return 0;
  }
  process.stdout.write(
    `[ai-eng] llm route show: mode=${route.mode}, default=${
      route.default !== null ? String((route.default as { id?: unknown }).id ?? "?") : "(none)"
    }\n`,
  );
  return 0;
};

const costHandler = async (rest: ReadonlyArray<string>): Promise<number> => {
  const [sub, ...subRest] = rest;
  const parsed = parseArgs(subRest);
  if (sub !== "report") {
    process.stderr.write("usage: ai-eng llm cost report [--json]\n");
    return 1;
  }
  if (hasFlag(parsed, "json")) {
    process.stdout.write(
      `${JSON.stringify(
        {
          status: "stubbed",
          phase: "4.1",
          message: "llm cost report aggregates from telemetry in Phase 9",
        },
        null,
        2,
      )}\n`,
    );
  } else {
    process.stdout.write(
      "[ai-eng] llm cost report: (Phase 9 — telemetry-driven aggregate not yet wired)\n",
    );
  }
  return 0;
};

const usage = (): void => {
  process.stderr.write(
    ["usage: ai-eng llm <list-providers|test|route show|cost report> [--json]", ""].join("\n"),
  );
};

export const llm: CommandHandler = async (args) => {
  const [sub, ...rest] = args;
  if (sub === undefined) {
    usage();
    return 1;
  }
  if (sub === "list-providers") return listProvidersHandler(rest);
  if (sub === "test") return testHandler(rest);
  if (sub === "route") return routeHandler(rest);
  if (sub === "cost") return costHandler(rest);
  process.stderr.write(`unknown llm subcommand: ${sub}\n`);
  usage();
  return 1;
};
