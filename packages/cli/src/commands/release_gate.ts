import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { GateId, type ReleaseAggregate, isErr, runReleaseGate } from "@ai-engineering/runtime";
import type { GateFinding, GateOutcome, GateVerdict } from "@ai-engineering/runtime";
import type { Severity } from "@ai-engineering/runtime";

import { hasFlag, parseArgs } from "./_args.ts";
import type { CommandHandler } from "./index.ts";

/**
 * `ai-eng release-gate` — aggregates persisted gate outcomes into a release
 * verdict (GO / CONDITIONAL / NO-GO).
 *
 * The CLI command is the deterministic adapter for the pure
 * `runReleaseGate` use case. It reads a JSON document at
 * `.ai-engineering/state/gate-outcomes.json` shaped as
 *   { outcomes: [<persisted-outcome>, ...] }
 *
 * Each persisted outcome mirrors the domain `GateOutcome` (string dates,
 * findings array, etc.); we hydrate them into branded values before calling
 * the use case so the aggregation layer stays pure.
 *
 * Exit codes (Constitution III, dual-plane):
 *   - 0 → GO (release unblocked)
 *   - 1 → CONDITIONAL (warn / non-blocking failures; needs explicit ack)
 *   - 2 → NO-GO (blocking failure; release halted)
 */
const VERDICT_TO_EXIT: Readonly<Record<ReleaseAggregate["verdict"], number>> = Object.freeze({
  GO: 0,
  CONDITIONAL: 1,
  "NO-GO": 2,
});

interface PersistedFinding {
  readonly findingId: string;
  readonly severity: Severity;
  readonly message: string;
  readonly location?: { readonly file: string; readonly line?: number };
}

interface PersistedOutcome {
  readonly gateId: string;
  readonly verdict: GateVerdict;
  readonly findings?: ReadonlyArray<PersistedFinding>;
  readonly executedAt: string;
  readonly durationMs: number;
  readonly severity?: Severity;
}

interface PersistedDoc {
  readonly outcomes: ReadonlyArray<PersistedOutcome>;
}

const persistedToOutcome = (p: PersistedOutcome): GateOutcome => {
  const findings: ReadonlyArray<GateFinding> = (p.findings ?? []).map((f) =>
    Object.freeze({
      findingId: f.findingId,
      severity: f.severity,
      message: f.message,
      ...(f.location !== undefined ? { location: f.location } : {}),
    }),
  );
  return Object.freeze({
    gateId: GateId(p.gateId),
    verdict: p.verdict,
    findings: Object.freeze([...findings]),
    executedAt: new Date(p.executedAt),
    durationMs: p.durationMs,
    ...(p.severity !== undefined ? { severity: p.severity } : {}),
  });
};

const readOutcomes = (
  path: string,
): { ok: true; outcomes: GateOutcome[] } | { ok: false; reason: string } => {
  if (!existsSync(path)) {
    return {
      ok: false,
      reason: "no gate outcomes found at .ai-engineering/state/gate-outcomes.json",
    };
  }
  let raw: string;
  try {
    raw = readFileSync(path, "utf8");
  } catch (e) {
    return {
      ok: false,
      reason: `failed to read gate outcomes: ${e instanceof Error ? e.message : String(e)}`,
    };
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (e) {
    return {
      ok: false,
      reason: `failed to parse gate outcomes (invalid JSON): ${e instanceof Error ? e.message : String(e)}`,
    };
  }
  if (
    parsed === null ||
    typeof parsed !== "object" ||
    !Array.isArray((parsed as { outcomes?: unknown }).outcomes)
  ) {
    return {
      ok: false,
      reason: "invalid gate outcomes schema: expected { outcomes: [...] } with array",
    };
  }
  const doc = parsed as PersistedDoc;
  return { ok: true, outcomes: doc.outcomes.map(persistedToOutcome) };
};

const summariseAggregate = (agg: ReleaseAggregate): string => {
  const lines = [
    `[ai-eng] release-gate verdict: ${agg.verdict}`,
    `  pass=${agg.totals.pass} fail=${agg.totals.fail} warn=${agg.totals.warn} error=${agg.totals.error}`,
  ];
  if (agg.blocking.length > 0) {
    lines.push(`  blocking gates: ${agg.blocking.length}`);
    for (const b of agg.blocking) {
      lines.push(`    - ${String(b.gateId)} (${b.verdict})`);
    }
  }
  return `${lines.join("\n")}\n`;
};

const aggregateToJson = (agg: ReleaseAggregate): string => {
  return `${JSON.stringify(
    {
      verdict: agg.verdict,
      totals: agg.totals,
      blocking: agg.blocking.map((b) => ({
        gateId: String(b.gateId),
        verdict: b.verdict,
        findings: b.findings,
      })),
      outcomes: agg.outcomes.map((o) => ({
        gateId: String(o.gateId),
        verdict: o.verdict,
        findings: o.findings,
        executedAt: o.executedAt instanceof Date ? o.executedAt.toISOString() : o.executedAt,
        durationMs: o.durationMs,
      })),
    },
    null,
    2,
  )}\n`;
};

export const releaseGate: CommandHandler = async (args) => {
  const parsed = parseArgs(args);
  const path = join(process.cwd(), ".ai-engineering", "state", "gate-outcomes.json");
  const read = readOutcomes(path);
  if (!read.ok) {
    process.stderr.write(`${read.reason}\n`);
    return 1;
  }
  const result = runReleaseGate(read.outcomes);
  if (isErr(result)) {
    process.stderr.write(`release-gate aggregation failed: ${result.error.message}\n`);
    return 1;
  }
  const aggregate = result.value;
  if (hasFlag(parsed, "json")) {
    process.stdout.write(aggregateToJson(aggregate));
  } else {
    process.stdout.write(summariseAggregate(aggregate));
  }
  return VERDICT_TO_EXIT[aggregate.verdict];
};
