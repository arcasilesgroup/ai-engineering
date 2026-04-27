import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { appendFile, mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";

import { NdjsonTelemetryAdapter } from "@ai-engineering/runtime";

import { hasFlag, parseArgs } from "./_args.ts";
import type { CommandHandler } from "./index.ts";

/**
 * `ai-eng board <discover|sync|status|map>` — fail-open board adapter.
 *
 * Per `skills/catalog/board/SKILL.md`: NEVER block a workflow on board
 * reachability. Each subcommand returns 0 even when the provider is
 * absent or unreachable; the gap is logged for later reconciliation.
 *
 * Phase 4.1 ships discover/sync as deterministic stubs. The full
 * provider matrix (Jira, Linear, GitHub Issues, Azure Boards) lands in
 * Phase 7 with the plugin marketplace.
 */
const STATE_DIR = (): string => join(process.cwd(), ".ai-engineering", "state");
const BOARD_EVENTS_PATH = (): string => join(STATE_DIR(), "board-events.ndjson");
const TELEMETRY_PATH = (): string => join(STATE_DIR(), "framework-events.ndjson");

const which = (cmd: string): Promise<boolean> =>
  new Promise((resolve) => {
    const child = spawn("which", [cmd], { stdio: "ignore" });
    child.on("error", () => resolve(false));
    child.on("close", (code) => resolve(code === 0));
  });

const ghAuthStatus = (): Promise<boolean> =>
  new Promise((resolve) => {
    const child = spawn("gh", ["auth", "status"], { stdio: "ignore" });
    child.on("error", () => resolve(false));
    child.on("close", (code) => resolve(code === 0));
  });

const discoverHandler = async (rest: ReadonlyArray<string>): Promise<number> => {
  const parsed = parseArgs(rest);
  const ghOnPath = await which("gh");
  let authenticated = false;
  if (ghOnPath) authenticated = await ghAuthStatus();
  const provider = ghOnPath ? "github-issues" : null;
  if (hasFlag(parsed, "json")) {
    process.stdout.write(`${JSON.stringify({ provider, ghOnPath, authenticated }, null, 2)}\n`);
  } else if (provider === null) {
    process.stdout.write("[ai-eng] board discover: no provider detected (gh not on PATH).\n");
  } else {
    const auth = authenticated ? "authenticated" : "unauthenticated";
    process.stdout.write(`[ai-eng] board discover: provider=${provider} (${auth}).\n`);
  }
  return 0;
};

const writeBoardEvent = async (event: Record<string, unknown>): Promise<void> => {
  const path = BOARD_EVENTS_PATH();
  await mkdir(dirname(path), { recursive: true });
  await appendFile(path, `${JSON.stringify(event)}\n`, "utf8");
};

const PHASES: ReadonlySet<string> = new Set([
  "spec",
  "plan",
  "impl",
  "review",
  "release",
  "incident",
]);

const syncHandler = async (rest: ReadonlyArray<string>): Promise<number> => {
  const parsed = parseArgs(rest);
  const [phase, ref] = parsed.positional;
  if (phase === undefined || ref === undefined) {
    process.stderr.write("usage: ai-eng board sync <phase> <ref>\n");
    return 1;
  }
  if (!PHASES.has(phase)) {
    process.stderr.write(`invalid phase "${phase}" (expected ${[...PHASES].join("|")})\n`);
    return 1;
  }
  const event = {
    type: "board.sync_intent",
    phase,
    ref,
    timestamp: new Date().toISOString(),
  };
  await writeBoardEvent(event);
  const telemetry = new NdjsonTelemetryAdapter(TELEMETRY_PATH());
  await telemetry.emit({
    level: "info",
    type: "board.sync_intent",
    attributes: { phase, ref },
  });
  if (hasFlag(parsed, "json")) {
    process.stdout.write(`${JSON.stringify({ status: "queued", event }, null, 2)}\n`);
  } else {
    process.stdout.write(`[ai-eng] board sync: intent queued (phase=${phase}, ref=${ref}).\n`);
  }
  return 0;
};

const readManifestBoardSection = (): Readonly<Record<string, unknown>> | null => {
  const json = join(process.cwd(), ".ai-engineering", "manifest.json");
  if (!existsSync(json)) return null;
  try {
    const parsed = JSON.parse(readFileSync(json, "utf8")) as {
      board?: Readonly<Record<string, unknown>>;
    };
    return parsed.board ?? null;
  } catch {
    return null;
  }
};

const statusHandler = async (rest: ReadonlyArray<string>): Promise<number> => {
  const parsed = parseArgs(rest);
  const board = readManifestBoardSection();
  if (hasFlag(parsed, "json")) {
    process.stdout.write(`${JSON.stringify({ board }, null, 2)}\n`);
    return 0;
  }
  if (board === null) {
    process.stdout.write("[ai-eng] board status: (not configured)\n");
    return 0;
  }
  process.stdout.write(`[ai-eng] board status: ${JSON.stringify(board)}\n`);
  return 0;
};

const mapHandler = async (rest: ReadonlyArray<string>): Promise<number> => {
  const parsed = parseArgs(rest);
  if (hasFlag(parsed, "json")) {
    process.stdout.write(`${JSON.stringify({ specs: [], orphans: [], gaps: [] }, null, 2)}\n`);
    return 0;
  }
  process.stdout.write("[ai-eng] board map: (not configured)\n");
  return 0;
};

const usage = (): void => {
  process.stderr.write(
    [
      "usage: ai-eng board <discover|sync|status|map>",
      "  discover                    detect provider on PATH (gh, jira-cli, ...)",
      "  sync <phase> <ref>          enqueue a state transition (fail-open)",
      "  status                      print current board configuration",
      "  map                         cross-reference specs with issues",
      "",
    ].join("\n"),
  );
};

export const board: CommandHandler = async (args) => {
  const [sub, ...rest] = args;
  if (sub === undefined) {
    usage();
    return 1;
  }
  if (sub === "discover") return discoverHandler(rest);
  if (sub === "sync") return syncHandler(rest);
  if (sub === "status") return statusHandler(rest);
  if (sub === "map") return mapHandler(rest);
  process.stderr.write(`unknown board subcommand: ${sub}\n`);
  usage();
  return 1;
};
