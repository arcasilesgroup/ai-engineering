// Payload normalization and fingerprints. Both spellings, one shape — without
// this a guard scoped to file edits receives every tool call in a shape it does
// not expect, crashes, and correctly blocks everything.

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

/** The host spellings every lowercase-name surface shares (pi and its OMP descendant).
 *  pi's web tools (pi.getAllTools()) are named lowercase too, so the containment arm's
 *  matcher would miss them and fetched pages would go unscanned. */
const LOWER_TOOLS: Record<string, string> = {
  bash: "Bash",
  powershell: "PowerShell",
  read: "Read",
  edit: "Edit",
  write: "Write",
  grep: "Grep",
  glob: "Glob",
  web_search: "WebSearch",
  fetch_content: "WebFetch",
  source_check: "WebFetch",
  get_search_content: "WebFetch",
};

/** Host spellings for the same tool, measured per host: Cursor calls the shell
 *  `Shell` (cursor.com/docs/hooks, cursor-agent 2026.09.08); pi sends lowercase names
 *  (pi-coding-agent 0.85.1, dist/core/extensions/types.d.ts). Every guard matcher,
 *  wrap's rewrite, the loop signature and the receipts read `tool_name` — so the
 *  alias lives here, once, instead of case-folding five matchers per host. */
const TOOL_ALIASES_BY_SURFACE: Record<string, Record<string, string>> = {
  cursor: { Shell: "Bash" },
  // pi sends lowercase names (pi-coding-agent 0.85.1, dist/core/extensions/types.d.ts)
  // and OMP — same API lineage — sends them the same way: a live probe on omp 18.1.17
  // recorded `tool=bash` for a shell call. Measured names are the ones in this map;
  // anything else passes through untouched, so a new host tool can never be mangled.
  pi: LOWER_TOOLS,
  "oh-my-pi": LOWER_TOOLS,
};

/** Copilot CLI runtime tool names → the guard names (docs.github.com/en/copilot/reference/hooks-reference,
 *  "Claude-format matchers" table). The PascalCase hook already sends the right column. */
const COPILOT_TOOLS: Record<string, string> = {
  bash: "Bash",
  powershell: "PowerShell",
  view: "Read",
  create: "Write",
  edit: "Edit",
  str_replace_editor: "Edit",
  apply_patch: "Edit",
  grep: "Grep",
  rg: "Grep",
  glob: "Glob",
  web_fetch: "WebFetch",
  web_search: "WebSearch",
  ask_user: "AskUserQuestion",
  update_todo: "TodoWrite",
  task: "Task",
};

/** Guard names a Copilot call may arrive as. Anything else is a tool nobody measured. */
const COPILOT_GUARDED = new Set([...Object.values(COPILOT_TOOLS), "Agent"]);

/** The agent's own bookkeeping: no file, shell or network effect a guard could judge,
 *  so a governed session keeps them. Shell keystrokes (write_bash) are NOT here. */
const COPILOT_INTERNAL = new Set([
  "report_intent", "task_complete", "skill", "sql", "session_store_sql",
  "read_bash", "stop_bash", "list_bash", "read_powershell", "stop_powershell", "list_powershell",
  "read_agent", "list_agents", "write_agent", "store_memory", "vote_memory",
  "fetch_copilot_cli_documentation", "exit_plan_mode",
]);

/** MCP tools measured as read-only queries, by their Copilot runtime name (`<server>-<tool>`).
 *  Every other MCP tool stays unknown and denies. codegraph_explore reads the local graph. */
const COPILOT_READ_ONLY_MCP = new Set(["codegraph-codegraph_explore"]);

/** Tools that read or steer the session without acting on the repo or the machine. Asking
 *  the same question twice is not a stuck loop, so the loop guard does not count them. */
const READ_OR_CONTROL = new Set([
  ...COPILOT_INTERNAL, ...COPILOT_READ_ONLY_MCP,
  "Read", "NotebookRead", "ReadFile", "LS", "Grep", "Glob",
  "AskUserQuestion", "TodoWrite", "Skill", "ExitPlanMode",
]);

export function isReadOrControl(tool: string): boolean {
  return READ_OR_CONTROL.has(tool);
}

/** SQLite statements that write a file the guards cannot see. */
const SQL_FILE_WRITE = /\b(attach|vacuum|load_extension|backup|writefile)\b/i;

/** Copilot's argument spellings → the keys every guard reads. */
const COPILOT_ARGS: Record<string, string> = {
  path: "file_path",
  old_str: "old_string",
  new_str: "new_string",
  file_text: "content",
};

const PATCH_FILE = /^\*\*\* (Add|Update|Delete) File: (.+)$/;
const PATCH_MOVE = /^\*\*\* Move to: (.+)$/;

/** Every path an apply_patch body touches. Throws on anything the apply_patch parser could
 *  read differently: a `***` line that is not a known header, a move without an update, a
 *  missing envelope. A patch we cannot read is a patch we cannot allow. */
export function patchPaths(patch: string): string[] {
  // A line break the parser here and the one applying the patch could disagree about.
  if (/[\v\f\u0085\u2028\u2029]/.test(patch)) throw new TypeError("apply_patch input uses an ambiguous line separator.");
  const lines = patch.replace(/\r\n?/g, "\n").split("\n").map((line) => line.trim());
  while (lines.length > 0 && lines[0] === "") lines.shift();
  while (lines.length > 0 && lines.at(-1) === "") lines.pop();
  if (lines[0] !== "*** Begin Patch" || lines.at(-1) !== "*** End Patch" || lines.length < 3) {
    throw new TypeError("apply_patch input is not one *** Begin Patch / *** End Patch envelope.");
  }
  const paths: string[] = [];
  let previous = "";
  for (const line of lines.slice(1, -1)) {
    if (!line.startsWith("***")) {
      previous = "body";
      continue;
    }
    const file = PATCH_FILE.exec(line);
    const move = PATCH_MOVE.exec(line);
    if (file) {
      paths.push(file[2]!.trim());
      previous = file[1]!;
    } else if (move && previous === "Update") {
      paths.push(move[1]!.trim());
      previous = "Move";
    } else if (line !== "*** End of File") {
      throw new TypeError(`apply_patch header cannot be read safely: ${line.slice(0, 80)}`);
    }
  }
  if (paths.length === 0 || paths.some((path) => path.length === 0 || path.includes("\0"))) {
    throw new TypeError("apply_patch names no file, or an empty one.");
  }
  return paths;
}

/** Every path an apply_patch block inside a longer text touches: all blocks, not the first. */
export function embeddedPatchPaths(text: string): string[] {
  const paths: string[] = [];
  const end = "*** End Patch";
  let from = 0;
  for (;;) {
    const start = text.indexOf("*** Begin Patch", from);
    if (start < 0) return paths;
    const close = text.indexOf(end, start);
    paths.push(...patchPaths(text.slice(start, close < 0 ? undefined : close + end.length)));
    if (close < 0) return paths;
    from = close + end.length;
  }
}

/** The patch text a host handed over: the raw string, or the one field that carries it. */
function patchText(input: unknown): string | null {
  if (typeof input === "string") return input;
  if (input === null || typeof input !== "object" || Array.isArray(input)) return null;
  const record = input as Record<string, unknown>;
  const texts = ["input", "patch"].map((key) => record[key]).filter((value): value is string => typeof value === "string" && value.includes("*** Begin Patch"));
  // Two different patches in one call: the tool applies one of them, and not which we know.
  if (new Set(texts).size > 1) throw new TypeError("the call carries two different patches.");
  return texts[0] ?? null;
}

/** One Edit payload for a patch: every path for self-protect, the added lines for no-verify.
 *  A path the call names beside the patch is judged too: it may be what the tool writes. */
function patchInput(patch: string, explicitPath?: string): Record<string, unknown> {
  const filePaths = [...new Set([...(explicitPath === undefined ? [] : [explicitPath]), ...patchPaths(patch)])];
  const added = patch.split(/\r?\n/).filter((line) => line.startsWith("+")).map((line) => line.slice(1));
  return { file_path: filePaths[0], file_paths: filePaths, patch, content: added.join("\n") };
}

/** The one target path a call names, after refusing a call that names two. */
function targetOf(input: unknown): string | undefined {
  if (input === null || typeof input !== "object" || Array.isArray(input)) return undefined;
  const record = input as Record<string, unknown>;
  assertOneTarget(record);
  return TARGET_KEYS.map((key) => record[key]).find((value): value is string => typeof value === "string" && value.length > 0);
}

/** toolArgs as an object, or as raw text when the host sent text (apply_patch is freeform). */
function decodeArgs(args: unknown): Record<string, unknown> | string {
  let parsed: unknown = args ?? {};
  if (typeof parsed === "string") {
    try {
      parsed = JSON.parse(parsed) as unknown;
    } catch {
      return parsed as string;
    }
    if (typeof parsed === "string") return parsed;
  }
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) throw new TypeError("Copilot toolArgs must be an object.");
  return parsed as Record<string, unknown>;
}

const TARGET_KEYS = ["file_path", "path", "filePath", "notebook_path", "notebookPath"];

/** Two different target paths in one call is a call the guards would judge by one and the
 *  tool might execute by the other. */
function assertOneTarget(input: Record<string, unknown>): void {
  const targets = new Set(TARGET_KEYS.map((key) => input[key]).filter((value) => typeof value === "string" && value.length > 0));
  if (targets.size > 1) throw new TypeError("the call names more than one target path.");
}

function parseArgs(args: unknown): Record<string, unknown> {
  const decoded = decodeArgs(args);
  if (typeof decoded === "string") throw new TypeError("Copilot toolArgs must contain a JSON object.");
  return decoded;
}

/** Copilot CLI (both hook spellings) → one payload, or a throw the chain turns into a deny.
 *  Fail closed on a tool nobody measured, on shell keystrokes, and on missing arguments. */
function normaliseCopilot(out: Record<string, unknown>, strict: boolean): void {
  const spellings = [out.tool_name, out.tool, out.toolName].filter((name) => typeof name === "string");
  if (strict && new Set(spellings).size > 1) throw new TypeError("the payload names two different tools.");
  const runtimeName = out.tool_name ?? out.tool ?? out.toolName;
  if (typeof runtimeName !== "string" || runtimeName.length === 0) {
    out.tool_name = "";
    out.tool_input = {};
    return;
  }
  const rawArgs = out.tool_input ?? out.input ?? out.toolArgs;
  out.session_id ??= out.sessionId;
  out.tool_response ??= out.tool_result ?? out.toolResult;
  if (!strict) {
    out.tool_name = COPILOT_TOOLS[runtimeName] ?? runtimeName;
    out.tool_input = typeof rawArgs === "object" && rawArgs !== null ? rawArgs : {};
    return;
  }
  if (COPILOT_INTERNAL.has(runtimeName) || COPILOT_READ_ONLY_MCP.has(runtimeName)) {
    out.tool_name = runtimeName;
    const args = parseArgs(rawArgs);
    const query = typeof args["query"] === "string" ? args["query"] : "";
    if (runtimeName === "sql" && SQL_FILE_WRITE.test(query)) {
      throw new TypeError("Copilot sql calls that attach or write database files cannot be inspected safely.");
    }
    out.tool_input = args;
    return;
  }
  const name = COPILOT_TOOLS[runtimeName] ?? runtimeName;
  if (!COPILOT_GUARDED.has(name)) throw new TypeError(`Copilot tool ${runtimeName} is not one the guards can inspect.`);
  const decoded = decodeArgs(rawArgs);
  if (typeof decoded === "string" && name !== "Edit") throw new TypeError("Copilot toolArgs must contain a JSON object.");
  // A patch is many writes in one call: read every path or refuse the call. A patch beside
  // an edit's own `path` adds paths to judge; it never replaces the one the tool writes.
  const patch = name === "Edit" || name === "Write" ? patchText(decoded) : null;
  if (runtimeName === "apply_patch" && patch === null) throw new TypeError("Copilot apply_patch input is not a readable patch.");
  if (patch !== null) {
    out.tool_name = "Edit";
    out.tool_input = patchInput(patch, targetOf(decoded));
    return;
  }
  const args = decoded as Record<string, unknown>;
  assertOneTarget(args);
  const mapped: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(args)) mapped[COPILOT_ARGS[key] ?? key] = value;
  // str_replace_editor carries its own verb; leaving it as `command` would hand a shell
  // guard a word that is not a shell command.
  let guardName = name;
  if (runtimeName === "str_replace_editor") {
    const verb = mapped["command"];
    delete mapped["command"];
    mapped["editor_command"] = verb;
    guardName = verb === "view" ? "Read" : verb === "create" ? "Write" : "Edit";
  }
  out.tool_name = guardName;
  out.tool_input = mapped;
}

function requireArgs(tool: string, input: Record<string, unknown>): void {
  const text = (key: string): boolean => typeof input[key] === "string" && (input[key] as string).trim().length > 0;
  if ((tool === "Bash" || tool === "PowerShell") && !text("command")) throw new TypeError(`${tool} calls must include a command.`);
  if ((tool === "Write" || tool === "Edit" || tool === "Read") && !text("file_path")) throw new TypeError(`${tool} calls must include a path.`);
  if (tool === "WebFetch" && !text("url")) throw new TypeError("WebFetch calls must include a url.");
}

export function normalise(raw: Record<string, unknown>, surface?: string, event?: string): Payload {
  const out: Record<string, unknown> = { ...raw };
  // PostToolUse cannot stop anything: an unmeasured tool there is noise, not a risk.
  const strict = event === undefined || event === "PreToolUse";
  const isCopilot = surface === "copilot-cli" || surface === "copilot";
  if (isCopilot) {
    normaliseCopilot(out, strict);
  } else {
    out.tool_name = out.tool_name ?? out.tool ?? "";
    if (surface && typeof out.tool_name === "string") {
      out.tool_name = TOOL_ALIASES_BY_SURFACE[surface]?.[out.tool_name] ?? out.tool_name;
    }
    const toolInput = out.tool_input ?? out.input ?? {};
    // A patch is many writes in one call: read every path or refuse the call, never `{}`.
    const isPatchTool = out.tool_name === "apply_patch";
    const patch = isPatchTool || out.tool_name === "Edit" || out.tool_name === "Write" ? patchText(toolInput) : null;
    if (isPatchTool && patch === null) throw new TypeError("apply_patch input is not a readable patch.");
    if (patch !== null) {
      out.tool_name = "Edit";
      out.tool_input = patchInput(patch, targetOf(toolInput));
    } else {
      out.tool_input = toolInput;
    }
  }
  if (typeof out.tool_input !== "object" || out.tool_input === null) out.tool_input = {};
  const input = out.tool_input as Record<string, unknown>;
  assertOneTarget(input);
  // A tool's own arguments are not a surface's payload: an MCP tool whose params
  // are `args`/`tool` would be rewritten into a call the surface never made — only
  // the camelCase floor is translated.
  const mapped: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(input)) mapped[BUILT_IN_ALIASES[k] ?? k] = v;
  // Notebook tools send notebook_path and nothing else; both write guards read file_path.
  // Only fill it when a notebook path exists: an empty string is NOT nullish, so a
  // fabricated "" shadows the real `path` key and the read guards get nothing —
  // Copilot sends tool_input.path, and the injection guard would run and allow the
  // read it exists to stop.
  if (!mapped.file_path && typeof mapped.notebook_path === "string") mapped.file_path = mapped.notebook_path;
  if (isCopilot && strict && typeof out.tool_name === "string") {
    if (!mapped.file_path && typeof mapped.path === "string") mapped.file_path = mapped.path;
    requireArgs(out.tool_name, mapped);
  }
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
