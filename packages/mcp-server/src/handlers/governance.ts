import { DecisionId, type Severity, isErr } from "@ai-engineering/runtime";

import { INVALID_PARAMS, type Tool, type ToolResult } from "../jsonrpc.ts";
import type { DecisionsPort, RunReleaseGateFn } from "../ports.ts";

/**
 * Governance tools — exposes `accept_risk` and `run_release_gate`.
 *
 * Tools are MCP-callable verbs distinct from resources (which are
 * read-only data). Each tool publishes an `inputSchema` so MCP clients
 * can validate arguments before invocation.
 */

const SEVERITIES: ReadonlyArray<Severity> = Object.freeze(["critical", "high", "medium", "low"]);

const isSeverity = (value: unknown): value is Severity =>
  typeof value === "string" && SEVERITIES.includes(value as Severity);

export const acceptRiskTool: Tool = Object.freeze({
  name: "accept_risk",
  description:
    "Record a logged risk acceptance per Constitution Article VII. Requires finding_id, severity, justification, owner, and spec_ref. Returns the persisted Decision with TTL.",
  inputSchema: {
    type: "object",
    required: ["finding_id", "severity", "justification", "owner", "spec_ref"],
    properties: {
      finding_id: { type: "string" },
      severity: {
        type: "string",
        enum: ["critical", "high", "medium", "low"],
      },
      justification: { type: "string" },
      owner: { type: "string" },
      spec_ref: { type: "string" },
      decision_id: { type: "string" },
    },
    additionalProperties: false,
  },
});

export const runReleaseGateTool: Tool = Object.freeze({
  name: "run_release_gate",
  description: "Aggregate gate outcomes into a release verdict (GO / CONDITIONAL / NO-GO).",
  inputSchema: {
    type: "object",
    properties: {},
    additionalProperties: false,
  },
});

interface AcceptRiskArgs {
  readonly finding_id: unknown;
  readonly severity: unknown;
  readonly justification: unknown;
  readonly owner: unknown;
  readonly spec_ref: unknown;
  readonly decision_id?: unknown;
}

const validateAcceptRiskArgs = (
  args: unknown,
): { ok: true; value: AcceptRiskArgs } | { ok: false; message: string } => {
  if (args === null || typeof args !== "object") {
    return { ok: false, message: "accept_risk requires an arguments object" };
  }
  const a = args as AcceptRiskArgs;
  const required: ReadonlyArray<keyof AcceptRiskArgs> = [
    "finding_id",
    "severity",
    "justification",
    "owner",
    "spec_ref",
  ];
  for (const key of required) {
    if (typeof a[key] !== "string" || (a[key] as string).trim() === "") {
      return {
        ok: false,
        message: `accept_risk argument "${String(key)}" must be a non-empty string`,
      };
    }
  }
  if (!isSeverity(a.severity)) {
    return {
      ok: false,
      message: `accept_risk severity must be one of: ${SEVERITIES.join(", ")}`,
    };
  }
  return { ok: true, value: a };
};

export const callAcceptRisk = async (
  args: unknown,
  decisions: DecisionsPort,
  now: () => Date = () => new Date(),
): Promise<{ ok: true; result: ToolResult } | { ok: false; code: number; message: string }> => {
  const validated = validateAcceptRiskArgs(args);
  if (!validated.ok) {
    return { ok: false, code: INVALID_PARAMS, message: validated.message };
  }
  const a = validated.value;
  const findingId = a.finding_id as string;
  const decisionIdRaw =
    typeof a.decision_id === "string" && a.decision_id.trim() !== ""
      ? (a.decision_id as string)
      : `DEC-${findingId}`;
  const result = await decisions.accept({
    id: DecisionId(decisionIdRaw),
    findingId,
    severity: a.severity as Severity,
    justification: a.justification as string,
    owner: a.owner as string,
    specRef: a.spec_ref as string,
    issuedAt: now(),
  });
  if (isErr(result)) {
    return {
      ok: false,
      code: INVALID_PARAMS,
      message: result.error.message,
    };
  }
  return {
    ok: true,
    result: {
      content: [
        {
          type: "text",
          text: JSON.stringify(serializeDecision(result.value)),
        },
      ],
    },
  };
};

export const callRunReleaseGate = async (runReleaseGate: RunReleaseGateFn): Promise<ToolResult> => {
  const aggregate = await runReleaseGate();
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify({
          verdict: aggregate.verdict,
          totals: aggregate.totals,
          blocking: aggregate.blocking.length,
          outcomes: aggregate.outcomes.length,
        }),
      },
    ],
  };
};

const serializeDecision = (
  d: import("@ai-engineering/runtime").Decision,
): Record<string, unknown> => ({
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
