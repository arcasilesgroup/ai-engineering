// Payload normalization and fingerprints, ported from v1 chain.py. Both spellings,
// one shape — without this a guard scoped to file edits receives every tool call in
// a shape it does not expect, crashes, and correctly blocks everything.

import { createHash } from "node:crypto";

export type Payload = {
  tool_name: string;
  tool_input: Record<string, unknown>;
  tool_response?: unknown;
  tool_use_id?: string;
  session_id?: string;
  hook_event_name?: string;
  model?: string;
  _event?: string;
  [key: string]: unknown;
};

/** The floor: what every surface may send, before any adapter adds spellings. */
export const BUILT_IN_ALIASES: Record<string, string> = {
  toolName: "tool_name",
  toolInput: "tool_input",
  toolResponse: "tool_response",
  sessionId: "session_id",
  hookEventName: "hook_event_name",
  toolUseId: "tool_use_id",
  filePath: "file_path",
  workspaceRoot: "cwd",
  workspacePath: "cwd",
};

/** Host spellings for the same tool, measured per host: Cursor calls the shell
 *  `Shell` (cursor.com/docs/hooks, cursor-agent 2026.09.08); pi sends lowercase names
 *  (pi-coding-agent 0.85.1, dist/core/extensions/types.d.ts). Every guard matcher,
 *  wrap's rewrite, the loop signature and the receipts read `tool_name` — so the
 *  alias lives here, once, instead of case-folding five matchers per host. */
const TOOL_ALIASES_BY_SURFACE: Record<string, Record<string, string>> = {
  cursor: { Shell: "Bash" },
  pi: { bash: "Bash", powershell: "PowerShell", read: "Read", edit: "Edit", write: "Write", grep: "Grep" },
};

export function normalise(raw: Record<string, unknown>, surface?: string): Payload {
  const out: Record<string, unknown> = { ...raw };
  out.tool_name = out.tool_name ?? out.tool ?? "";
  if (surface && typeof out.tool_name === "string") {
    out.tool_name = TOOL_ALIASES_BY_SURFACE[surface]?.[out.tool_name] ?? out.tool_name;
  }
  out.tool_input = out.tool_input ?? out.input ?? {};
  if (typeof out.tool_input !== "object" || out.tool_input === null) out.tool_input = {};
  const input = out.tool_input as Record<string, unknown>;
  // A tool's own arguments are not a surface's payload (v1 measured an MCP tool
  // whose params were `args`/`tool` getting rewritten into a call the surface
  // never made) — only the camelCase floor is translated.
  const mapped: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(input)) mapped[BUILT_IN_ALIASES[k] ?? k] = v;
  // Notebook tools send notebook_path and nothing else; both write guards read file_path.
  // Only fill it when a notebook path exists: an empty string is NOT nullish, so a
  // fabricated "" shadowed the real `path` key and the read guards got nothing
  // (measured 2026-09-10 — Copilot sends tool_input.path, the injection guard ran
  // and allowed the read it exists to stop).
  if (!mapped.file_path && typeof mapped.notebook_path === "string") mapped.file_path = mapped.notebook_path;
  out.tool_input = mapped;
  return out as Payload;
}

/** One physical tool call — dedup key. The surface's tool_use_id is what makes two
 *  deliveries of the same call the same call instead of blinding the loop guard. */
export function fingerprint(payload: Payload): string {
  const body = JSON.stringify([
    payload.session_id ?? "",
    payload.tool_name,
    payload.tool_input,
    payload.tool_use_id ?? "",
  ]);
  return sha256Short(body);
}

export function deduplicable(payload: Payload): boolean {
  return Boolean(payload.tool_use_id);
}

/** Tool + whole input, without tool_use_id — what the loop guard counts. */
export function loopExact(payload: Payload): string {
  return sha256Short(JSON.stringify([payload.tool_name, payload.tool_input]));
}

/** Coarse signature for the failure arm: tool + discriminating-tail of the first arg. */
export function loopSignature(payload: Payload): string {
  const args = payload.tool_input;
  let first = "";
  for (const key of ["command", "file_path", "path", "pattern", "url", "query"]) {
    const value = args[key];
    if (typeof value === "string" && value.length > 0) {
      first = (value.split(/\s+/)[0] ?? "").slice(-60);
      break;
    }
  }
  return `${payload.tool_name}:${first}`;
}

function sha256Short(body: string): string {
  return createHash("sha256").update(body).digest("hex").slice(0, 16);
}
