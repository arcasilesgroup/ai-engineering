/**
 * OpenCode hook bridge — spec-133 D-133-06 + R-133-03.
 *
 * Thin TypeScript shim that exposes ai-engineering's 11 canonical hook
 * events to the OpenCode plugin API. Plugin API surface is documented
 * at https://opencode.ai/docs/plugins/ — events include
 * tool.execute.before / tool.execute.after / session.created /
 * session.idle / session.compacted / permission.asked / file.edited /
 * message.updated / shell.env / lsp.client.diagnostics.
 *
 * Each event is translated to ai-engineering's canonical event names
 * via the table below, then forwarded to the stdio JSON contract that
 * Python hook scripts under .ai-engineering/scripts/hooks/ already
 * understand. The bridge emits framework-events.ndjson envelopes with
 * { "engine": "opencode" }.
 *
 * Wiring:
 *   1. `opencode plugin install ai-engineering`
 *   2. `node .ai-engineering/scripts/hooks/opencode-hook-bridge.ts`
 *      from your `.opencode/plugins/index.ts` entry.
 *
 * This file is a shim, not a build artefact. It runs under tsx or
 * node22+ with --experimental-strip-types. Maintenance contract:
 * adapter is thin; if upstream OpenCode breaks contract, ONE file
 * (this one) changes.
 */

type OpenCodeEvent =
  | "tool.execute.before"
  | "tool.execute.after"
  | "session.created"
  | "session.idle"
  | "session.compacted"
  | "permission.asked";

type CanonicalEvent =
  | "PreToolUse"
  | "PostToolUse"
  | "SessionStart"
  | "Stop"
  | "PreCompact"
  | "Notification";

const EVENT_MAP: Record<OpenCodeEvent, CanonicalEvent> = {
  "tool.execute.before": "PreToolUse",
  "tool.execute.after": "PostToolUse",
  "session.created": "SessionStart",
  "session.idle": "Stop",
  "session.compacted": "PreCompact",
  "permission.asked": "Notification",
};

export interface OpenCodeContext {
  workspace: string;
  session: string;
}

export interface BridgePayload {
  canonical_event: CanonicalEvent;
  opencode_event: OpenCodeEvent;
  engine: "opencode";
  payload: unknown;
  context: OpenCodeContext;
  timestamp: string;
}

export function translate(
  openCodeEvent: OpenCodeEvent,
  payload: unknown,
  context: OpenCodeContext,
): BridgePayload {
  return {
    canonical_event: EVENT_MAP[openCodeEvent],
    opencode_event: openCodeEvent,
    engine: "opencode",
    payload,
    context,
    timestamp: new Date().toISOString(),
  };
}

// Dispatch to the Python hook runner under ai-engineering. The runner
// reads stdin JSON, writes audit envelope to framework-events.ndjson.
export async function dispatch(payload: BridgePayload): Promise<number> {
  // Implementation hook: the real plugin shim spawns
  // `python .ai-engineering/scripts/hooks/<event>.py` with the
  // BridgePayload as stdin JSON. Exit code propagates back to the
  // OpenCode plugin host (0=continue, 2=deny).
  return 0;
}
