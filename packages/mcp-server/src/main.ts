import { readFile, readdir } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import {
  DecisionId,
  InMemoryDecisionStore,
  NdjsonTelemetryAdapter,
  NodeFilesystemAdapter,
  acceptRisk,
  runReleaseGate,
} from "@ai-engineering/runtime";

import type {
  AcceptRiskCommand,
  AgentCatalogPort,
  DecisionsPort,
  ManifestPort,
  ServerDeps,
  SkillCatalogPort,
} from "./ports.ts";
import { createServer } from "./server.ts";

/**
 * Bun.serve entry point — the ONLY module that binds to a Bun-specific
 * runtime API. Everything below the transport boundary is Web Fetch +
 * `node:fs` so the dispatch layer is portable.
 *
 * Boot order:
 *   1. Resolve repo root (workspace root that contains `ai-engineering.toml`).
 *   2. Wire filesystem-backed catalog adapters for skills/agents.
 *   3. Compose ServerDeps and start `Bun.serve` on AI_ENGINEERING_MCP_PORT
 *      (default 3737).
 *
 * Stateless per ADR-0003: no session map, no in-process auth cache.
 * Decisions are persisted via `InMemoryDecisionStore` for now —
 * Phase 5 swaps this for the JSON-backed store under
 * `.ai-engineering/state/decision-store.json`.
 */

const DEFAULT_PORT = 3737;

const findRepoRoot = (start: string): string => {
  let current = start;
  for (let i = 0; i < 16; i += 1) {
    if (existsSyncSafe(join(current, "ai-engineering.toml"))) return current;
    const parent = dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return start;
};

const existsSyncSafe = (path: string): boolean => {
  try {
    const fs = require("node:fs") as typeof import("node:fs");
    return fs.existsSync(path);
  } catch {
    return false;
  }
};

const filesystemSkillCatalog = (catalogDir: string): SkillCatalogPort => {
  const fs = new NodeFilesystemAdapter();
  return {
    async list() {
      try {
        const names = await readdir(catalogDir);
        return names
          .filter((n) => !n.startsWith("."))
          .map((name) => ({
            name,
            uri: `ai-engineering://skills/${name}`,
          }));
      } catch {
        return [];
      }
    },
    async read(name: string) {
      const path = join(catalogDir, name, "SKILL.md");
      const r = await fs.read(path);
      return r.ok ? r.value : null;
    },
  };
};

const filesystemAgentCatalog = (catalogDir: string): AgentCatalogPort => {
  const fs = new NodeFilesystemAdapter();
  return {
    async list() {
      try {
        const names = await readdir(catalogDir);
        return names
          .filter((n) => !n.startsWith("."))
          .map((name) => ({
            name,
            uri: `ai-engineering://agents/${name}`,
          }));
      } catch {
        return [];
      }
    },
    async read(name: string) {
      const path = join(catalogDir, name, "AGENT.md");
      const r = await fs.read(path);
      return r.ok ? r.value : null;
    },
  };
};

const tomlManifest = (path: string): ManifestPort => ({
  async load() {
    try {
      const raw = await readFile(path, "utf8");
      return { tomlSource: raw };
    } catch {
      return {};
    }
  },
});

const memoryBackedDecisions = (): DecisionsPort => {
  const store = new InMemoryDecisionStore();
  const ledger: AcceptRiskCommand[] = [];
  return {
    async list() {
      return ledger.map((entry) => ({
        id: entry.id,
        findingId: entry.findingId,
        severity: entry.severity,
      }));
    },
    async accept(input: AcceptRiskCommand) {
      const result = await acceptRisk(
        {
          id: DecisionId(input.id),
          findingId: input.findingId,
          severity: input.severity,
          justification: input.justification,
          owner: input.owner,
          specRef: input.specRef,
          issuedAt: input.issuedAt,
        },
        store,
      );
      if (result.ok) ledger.push(input);
      return result;
    },
  };
};

const buildDeps = async (root: string): Promise<ServerDeps> => {
  const skills = filesystemSkillCatalog(join(root, "skills", "catalog"));
  const agents = filesystemAgentCatalog(join(root, "agents"));
  const manifest = tomlManifest(join(root, "ai-engineering.toml"));
  const decisions = memoryBackedDecisions();
  const constitution = await readFile(join(root, "CONSTITUTION.md"), "utf8").catch(
    () => "# CONSTITUTION\n\n(missing)",
  );
  const telemetry = new NdjsonTelemetryAdapter(
    join(root, ".ai-engineering", "state", "framework-events.ndjson"),
  );
  return {
    skills,
    agents,
    manifest,
    decisions,
    runReleaseGate: async () => {
      const out = runReleaseGate([
        {
          gateId: "noop" as never,
          verdict: "pass",
          findings: [],
          executedAt: new Date(),
          durationMs: 0,
        },
      ]);
      if (!out.ok) {
        throw new Error("runReleaseGate failed during boot");
      }
      return out.value;
    },
    constitution,
    telemetry,
  };
};

const main = async (): Promise<void> => {
  const here = fileURLToPath(import.meta.url);
  const root = findRepoRoot(resolve(dirname(here), "..", "..", ".."));
  const deps = await buildDeps(root);
  const handler = createServer(deps);
  const port = Number(process.env.AI_ENGINEERING_MCP_PORT ?? DEFAULT_PORT);

  const server = Bun.serve({
    port,
    fetch: (req: Request) => handler(req),
  });

  // Boot banner is intentional — `console.info` is for ops, not debug.
  console.info(`[ai-engineering/mcp-server] listening on http://localhost:${server.port}`);
};

if (import.meta.main) {
  await main();
}
