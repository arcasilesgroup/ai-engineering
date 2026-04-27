import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import {
  type AcceptRiskInput,
  type Decision,
  DecisionId,
  type DecisionStorePort,
  type NotFoundError,
  NotFoundError as NotFoundErrorClass,
  type Result,
  type Severity,
  StoreError,
  acceptRisk,
  err,
  isErr,
  ok,
} from "@ai-engineering/runtime";

import { hasFlag, parseArgs, stringFlag } from "./_args.ts";
import type { CommandHandler } from "./index.ts";

/**
 * `ai-eng risk accept` — wires the AcceptRisk use case to a JSON-backed store.
 *
 * The decision store is a single JSON document at
 * `.ai-engineering/state/decision-store.json` shaped as `{ decisions: [...] }`.
 * Append-only at the application level (via use case + new id per call).
 *
 * Constitution Article VII: risk acceptance is logged-acceptance, NOT
 * weakening. The use case enforces the invariants; this command provides the
 * deterministic adapter to flush the entry to disk.
 */
const SEVERITIES: ReadonlySet<Severity> = new Set(["critical", "high", "medium", "low"]);

interface PersistedStore {
  decisions: ReadonlyArray<PersistedDecision>;
}

interface PersistedDecision {
  readonly id: string;
  readonly findingId: string;
  readonly severity: Severity;
  readonly justification: string;
  readonly owner: string;
  readonly specRef: string;
  readonly issuedAt: string;
  readonly expiresAt: string;
  readonly renewals: number;
}

const decisionToPersisted = (d: Decision): PersistedDecision => ({
  id: d.id,
  findingId: d.findingId,
  severity: d.severity,
  justification: d.justification,
  owner: d.owner,
  specRef: d.specRef,
  issuedAt: d.issuedAt.toISOString(),
  expiresAt: d.expiresAt.toISOString(),
  renewals: d.renewals,
});

const persistedToDecision = (p: PersistedDecision): Decision =>
  Object.freeze({
    id: DecisionId(p.id),
    findingId: p.findingId,
    severity: p.severity,
    justification: p.justification,
    owner: p.owner,
    specRef: p.specRef,
    issuedAt: new Date(p.issuedAt),
    expiresAt: new Date(p.expiresAt),
    renewals: p.renewals,
  });

class JsonFileDecisionStore implements DecisionStorePort {
  constructor(private readonly path: string) {}

  private readDoc(): PersistedStore {
    if (!existsSync(this.path)) return { decisions: [] };
    try {
      const raw = readFileSync(this.path, "utf8");
      const parsed = JSON.parse(raw) as Partial<PersistedStore>;
      if (!parsed || !Array.isArray(parsed.decisions)) {
        return { decisions: [] };
      }
      return { decisions: parsed.decisions };
    } catch {
      // Corrupt store treated as empty so the use case can append a fresh
      // entry; the previous content is preserved on disk only until the next
      // successful save (writeFileSync below).
      return { decisions: [] };
    }
  }

  private writeDoc(doc: PersistedStore): Result<void, StoreError> {
    try {
      const dir = this.path.slice(0, this.path.lastIndexOf("/"));
      if (dir.length > 0) mkdirSync(dir, { recursive: true });
      writeFileSync(this.path, `${JSON.stringify(doc, null, 2)}\n`, "utf8");
      return ok(undefined);
    } catch (e) {
      return err(
        new StoreError(
          `decision-store write failed: ${e instanceof Error ? e.message : String(e)}`,
        ),
      );
    }
  }

  async save(decision: Decision): Promise<Result<void, StoreError>> {
    const doc = this.readDoc();
    const next: PersistedStore = {
      decisions: [
        ...doc.decisions.filter((d) => d.id !== decision.id),
        decisionToPersisted(decision),
      ],
    };
    return this.writeDoc(next);
  }

  async findById(id: string): Promise<Result<Decision, NotFoundError | StoreError>> {
    const doc = this.readDoc();
    const found = doc.decisions.find((d) => d.id === id);
    if (!found) return err(new NotFoundErrorClass("Decision", id));
    return ok(persistedToDecision(found));
  }
}

const usage = (): void => {
  process.stderr.write(
    [
      "usage: ai-eng risk accept --finding-id <id> --severity <critical|high|medium|low>",
      "                          --justification <text> --owner <email> --spec-ref <id>",
      "                          [--id <decision-id>] [--json]",
      "",
    ].join("\n"),
  );
};

const requireFlag = (name: string, value: string | undefined): Result<string, string> => {
  if (value === undefined || value.length === 0) {
    return err(`missing required flag --${name}`);
  }
  return ok(value);
};

const acceptHandler = async (rest: ReadonlyArray<string>): Promise<number> => {
  const args = parseArgs(rest);
  const required = [
    requireFlag("finding-id", stringFlag(args, "finding-id")),
    requireFlag("severity", stringFlag(args, "severity")),
    requireFlag("owner", stringFlag(args, "owner")),
    requireFlag("spec-ref", stringFlag(args, "spec-ref")),
  ];
  // justification is special: empty string is allowed at parse time so the
  // domain layer can return its own validation error and we exercise that
  // path; we still flag missing flag (undefined) here.
  const justification = stringFlag(args, "justification");
  if (justification === undefined) {
    process.stderr.write("missing required flag --justification\n");
    usage();
    return 1;
  }
  for (const r of required) {
    if (!r.ok) {
      process.stderr.write(`${r.error}\n`);
      usage();
      return 1;
    }
  }
  const findingId = stringFlag(args, "finding-id") as string;
  const owner = stringFlag(args, "owner") as string;
  const specRef = stringFlag(args, "spec-ref") as string;
  const severityRaw = stringFlag(args, "severity") as string;
  if (!SEVERITIES.has(severityRaw as Severity)) {
    process.stderr.write(`invalid severity "${severityRaw}" (expected critical|high|medium|low)\n`);
    return 1;
  }
  const severity = severityRaw as Severity;
  const id = stringFlag(args, "id") ?? `DEC-${Date.now()}-${findingId}`;

  const store = new JsonFileDecisionStore(
    join(process.cwd(), ".ai-engineering", "state", "decision-store.json"),
  );

  const input: AcceptRiskInput = {
    id: DecisionId(id),
    findingId,
    severity,
    justification,
    owner,
    specRef,
    issuedAt: new Date(),
  };

  const result = await acceptRisk(input, store);
  if (isErr(result)) {
    process.stderr.write(`risk accept failed: ${result.error.message}\n`);
    return 1;
  }
  const persisted = decisionToPersisted(result.value);
  if (hasFlag(args, "json")) {
    process.stdout.write(`${JSON.stringify(persisted, null, 2)}\n`);
  } else {
    process.stdout.write(
      `[ai-eng] risk accepted: ${persisted.findingId} (severity=${persisted.severity}) → expires ${persisted.expiresAt}\n`,
    );
  }
  return 0;
};

export const risk: CommandHandler = async (args) => {
  const [sub, ...rest] = args;
  if (sub === undefined) {
    process.stderr.write("usage: ai-eng risk <accept> [flags]\n");
    return 1;
  }
  if (sub === "accept") {
    return acceptHandler(rest);
  }
  process.stderr.write(`unknown risk subcommand: ${sub}\nusage: ai-eng risk <accept>\n`);
  return 1;
};
