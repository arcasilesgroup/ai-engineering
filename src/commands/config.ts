// `ai-eng config` — add/remove surfaces, regenerate their adapters and mirrors.
// Never touches AGENTS.md and never writes overrides (those are manual, with reason).

import { existsSync, readFileSync, writeFileSync, unlinkSync } from "node:fs";
import { PassThrough } from "node:stream";
import { install, stripSharedText } from "../install.ts";
import { join } from "node:path";
import { multiselect, isCancel } from "@clack/prompts";
import { canonicalSurfaceId, repoRoot, enabledSurfaces, isGoverned } from "../env.ts";
import { SURFACES, mirrorTargets, surfaceCanGovern, repoCarrier, machineCarrier, installMachineCarriers, installCanon, type Surface } from "../surfaces/adapters.ts";
import { hasAdapter, installLineRow, planEntries, refuseLine, SURFACE_PICK_MESSAGE, surfaceOptions } from "./init-shared.ts";
import * as ui from "../ui.ts";
import { scriptedInput } from "../ui.ts";
import { VERSION } from "../version.ts";

type ResolveResult =
  | { kind: "continue"; current: string[]; addedNow: string | null; removing: string[] }
  | { kind: "exit"; code: number };

/** Resolve the new surface list by mutating branch. The two early exits — no adapter
 *  on `--add`, and a cancelled picker — are folded into the result so the caller can
 *  return their exit code without duplicating the message or the side-effect order.
 *  Nothing is removed here: the caller takes carriers out only once the declaration
 *  has been written, so a refused rewrite leaves the repo exactly as it was. */
async function resolveSurfaces(
  input: NodeJS.ReadStream | PassThrough,
  flags: { add?: string; remove?: string },
  surfacesBefore: string[],
): Promise<ResolveResult> {
  let addedNow: string | null = null;
  let current = surfacesBefore;
  let removing: string[] = [];
  if (flags.add) {
    flags.add = canonicalSurfaceId(flags.add);
    // Same rule as the picker: no adapter, no declaration.
    if (!hasAdapter(flags.add)) {
      ui.fail(`"${flags.add}" has no adapter in this release — nothing would enforce its guards.`);
      ui.end("Nothing changed.");
      return { kind: "exit", code: 2 };
    }
    if (!current.includes(flags.add)) {
      current = [...current, flags.add];
      addedNow = flags.add;
    }
  } else if (flags.remove) {
    flags.remove = canonicalSurfaceId(flags.remove);
    current = current.filter((id) => id !== flags.remove);
    removing = [flags.remove];
  } else {
    const picked = await pickSurfaces(input, current);
    if (picked === null) return { kind: "exit", code: 0 };
    removing = current.filter((id) => !picked.includes(id));
    current = picked;
  }
  return { kind: "continue", current, addedNow, removing };
}

/** The interactive multiselect (no flags). Returns null when the user cancels
 *  (the cancellation message is printed here, exactly as before). */
async function pickSurfaces(
  input: NodeJS.ReadStream | PassThrough,
  current: string[],
): Promise<string[] | null> {
  const picked = await multiselect({
    message: SURFACE_PICK_MESSAGE,
    options: surfaceOptions().map((s) => ({ value: s.id, label: s.label })),
    initialValues: current.filter((id) => SURFACES.some((s) => s.id === id)),
    required: true,
    input: input as never,
  });
  if (isCancel(picked)) {
    ui.cancelled("Nothing changed.");
    return null;
  }
  return picked;
}

/** The "Surfaces changed" rows: one per added surface, one per removed surface. */
function deltaRows(added: string[], removedSurfaces: string[]): ui.Row[] {
  return [
    ...added.map((id): ui.Row => ({ mark: "ok", text: `+ ${id}`, dim: "adapter + skill mirror written" })),
    ...removedSurfaces.map((id): ui.Row => ({ mark: "ok", text: `- ${id}`, dim: "off in this repo; the machine carrier stays — it serves every governed repo" })),
  ];
}

/** Write the new surface list, or refuse and write nothing. Returns whether it wrote. */
function writeConfigSurfaces(configPath: string, surfaces: string[]): boolean {
  // The config file holds what cannot be deduced: only the items of the surfaces list
  // change, in place — the comments, the layout, the line endings and the
  // [models]/[guards]/[gc] blocks the template ships are the user's, and a
  // re-serialize would rewrite them.
  const raw = existsSync(configPath) ? readFileSync(configPath, "utf8") : "";
  const rewritten = withSurfacesEnabled(raw, surfaces);
  if (rewritten === null || !isOnlySurfacesChange(raw, rewritten, surfaces)) {
    ui.fail(`.ai-engineering/config.toml is laid out in a way this command cannot rewrite without changing more than [surfaces].enabled.`);
    ui.info(`Edit it by hand: under [surfaces], set enabled = [${renderItems(surfaces, '"')}]`);
    ui.end("Nothing changed.");
    return false;
  }
  if (rewritten !== raw) writeFileSync(configPath, rewritten);
  return true;
}

/** The text edit below knows one layout family. Anything else — a dotted
 *  `surfaces.enabled`, an inline `surfaces = { … }`, a quoted key — would come out
 *  unparseable or saying something else, and an unparseable config.toml turns
 *  governance off. So the result is judged by what it means, not by its text: it must
 *  parse, and differ from the original only in `[surfaces].enabled` — which keeps the
 *  listed surfaces that stay, in their order, then names the new ones. A file that does
 *  not parse cannot be judged, so it is refused too. */
function isOnlySurfacesChange(raw: string, rewritten: string, surfaces: string[]): boolean {
  try {
    const before = Bun.TOML.parse(raw) as Record<string, unknown>;
    const after = Bun.TOML.parse(rewritten) as Record<string, unknown>;
    const tableBefore = before["surfaces"] ?? {};
    const tableAfter = after["surfaces"];
    if (!isTable(tableBefore) || !isTable(tableAfter)) return false;
    const enabledBefore = surfaceIds(tableBefore["enabled"] ?? []);
    const enabledAfter = surfaceIds(tableAfter["enabled"]);
    if (enabledBefore === null || enabledAfter === null) return false;
    const expected = [...enabledBefore.filter((id) => surfaces.includes(id)), ...surfaces.filter((id) => !enabledBefore.includes(id))];
    return (
      Bun.deepEquals(enabledAfter, expected) &&
      Bun.deepEquals({ ...after, surfaces: { ...tableAfter, enabled: null } }, { ...before, surfaces: { ...tableBefore, enabled: null } })
    );
  } catch {
    return false;
  }
}

function isTable(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** The canonical ids of a list of strings, or null when it is anything else. */
function surfaceIds(value: unknown): string[] | null {
  if (!Array.isArray(value) || !value.every((item): item is string => typeof item === "string")) return null;
  return value.map((id) => canonicalSurfaceId(id));
}

function installNewSurfaces(root: string, current: string[], before: string[], addedNow: string | null): void {
  // Declaring a surface and leaving it without a carrier is a governed repo that is not
  // governed on that host. The carriers are written right here, by the same code init uses.
  for (const id of current) {
    if (!before.includes(id) || id === addedNow) installSurfaceFiles(root, id);
  }
}

function showSurfaceDelta(current: string[], before: string[]): void {
  const added = current.filter((id) => !before.includes(id));
  const removed = before.filter((id) => !current.includes(id));
  const delta = deltaRows(added, removed);
  if (delta.length === 0) {
    ui.section("surfaces unchanged", [{ mark: "muted", text: current.join(", ") }], `${current.length} enabled`);
  } else {
    ui.section("Surfaces changed", delta, `${current.length} enabled: ${current.join(", ")}`);
  }
}

export async function configMain(flags: { add?: string; remove?: string }): Promise<number> {
  const input = scriptedInput();
  ui.frame(`Configuration · ai-eng ${VERSION}`);
  const root = repoRoot();
  // The gate, not "there is a .git above us": `config --add` in a bare repo would die
  // on writeFileSync with a raw ENOENT instead of telling the human to run init.
  if (root === null || !isGoverned(root)) {
    ui.fail("you are not in a governed repo — run ai-eng init first");
    ui.end("Nothing changed.");
    return 2;
  }
  // Governed means the declaration parsed, so enabledSurfaces() cannot be guessing here.
  const surfacesBefore = enabledSurfaces();
  const resolved = await resolveSurfaces(input, flags, surfacesBefore);
  if (resolved.kind === "exit") return resolved.code;
  const { current, addedNow, removing } = resolved;
  if (!writeConfigSurfaces(join(root, ".ai-engineering", "config.toml"), current)) return 2;
  for (const id of removing) removeSurfaceFiles(root, id);
  // The canon is refreshed quietly; only what it could not do is said, as a warning.
  const canonWarnings = installCanon(VERSION).filter((line) => line.startsWith("⚠ ")).map((line) => installLineRow(line));
  if (canonWarnings.length > 0) ui.section("Global canon", canonWarnings);
  installNewSurfaces(root, current, surfacesBefore, addedNow);
  showSurfaceDelta(current, surfacesBefore);
  const mirrors = mirrorTargets().length;
  ui.section("Mirrors verified", [{ mark: "ok", text: `${mirrors} targets` }], "model tier thresholds: edit .ai-engineering/config.toml directly, or ask your AI assistant");
  ui.end("Done. Run ai-eng doctor to verify.");
  return 0;
}

function removeSurfaceFiles(root: string, id: string): void {
  const surface = SURFACES.find((s) => s.id === id);
  if (!surface) return;
  const placement = repoCarrier(surface);
  if (!placement) return;
  const absolute = join(root, placement.path);
  if (existsSync(absolute)) {
    if (placement.kind === "module") {
      unlinkSync(absolute);
      ui.ok(`${placement.path} removed`);
    } else {
      // A settings carrier is a file the user also owns: ours come out by marker, exactly
      // as uninstall does it. A bare unlink here deleted their hooks and told them only
      // our entries were removed — the two verbs disagreeing about one file.
      const stripped = stripSharedText(readFileSync(absolute, "utf8"));
      if (stripped === null) {
        ui.warn(`${placement.path} left alone — not JSON this installer can rewrite without reformatting it`);
      } else if (Object.keys(JSON.parse(stripped) as Record<string, unknown>).length === 0) {
        unlinkSync(absolute);
        ui.ok(`${placement.path} removed (it held only ai-eng entries)`);
      } else {
        writeFileSync(absolute, stripped);
        ui.ok(`${placement.path}: ai-eng entries removed, yours kept`);
      }
    }
  }
  if (placement.chain) {
    const chainPath = join(root, placement.chain);
    if (existsSync(chainPath)) {
      unlinkSync(chainPath);
      ui.ok(`${placement.chain} removed (chain module)`);
    }
  }
}

/** Edit the surfaces list in place, and never grow a second `[surfaces]` table.
 *
 *  Two shapes would do exactly that, at exit 0: an `enabled` key indented under an
 *  existing table (valid TOML a blind `/^enabled\s*=/m` misses) and a `[surfaces]`
 *  table that has no `enabled` key yet. Each appends a fresh header, which makes the
 *  file unparseable — `declaration()` then reports the repository as undeclared and the
 *  command that manages governance silently turns it off. That is the one class of bug
 *  this product exists to prevent (§09.2), so the rewrite is table-aware: the key is
 *  scoped to `[surfaces]` (a bare `enabled =` also matched the `[notices]` key of the
 *  same name), and a file with no table gets one, at the end. New lines use the file's
 *  own line ending. Null: a list this edit cannot change item by item. */
function withSurfacesEnabled(raw: string, surfaces: string[]): string | null {
  const eol = raw.includes("\r\n") ? "\r\n" : "\n";
  const declared = `enabled = [${renderItems(surfaces, '"')}]`;
  const located = locateEnabled(raw);
  if (located === null) {
    const body = raw.trim() === "" ? "" : `${raw.trimEnd()}${eol}${eol}`;
    return `${body}[surfaces]${eol}${declared}${eol}`;
  }
  if ("valueStart" in located) return withListItems(raw, located.valueStart, surfaces);
  if (located.headerEnd > raw.length) return `${raw}${eol}${declared}`;
  return `${raw.slice(0, located.headerEnd)}${declared}${eol}${raw.slice(located.headerEnd)}`;
}

const SURFACES_HEADER = /^\s*\[\s*surfaces\s*\]\s*(?:#.*)?$/;

/** Where the `[surfaces]` table's `enabled` value starts; else where its header line
 *  ends (past the text when the header is the last line, with no newline); else null,
 *  there is no table. Lines are matched without their `\r`: a CRLF file is the same file. */
function locateEnabled(raw: string): { valueStart: number } | { headerEnd: number } | null {
  let headerEnd: number | null = null;
  let lineStart = 0;
  for (const line of raw.split("\n")) {
    const text = line.endsWith("\r") ? line.slice(0, -1) : line;
    const lineEnd = lineStart + line.length + 1;
    if (headerEnd === null) {
      if (SURFACES_HEADER.test(text)) headerEnd = lineEnd;
    } else {
      if (/^\s*\[/.test(text)) break; // the next table: `enabled` belongs to it, not to us
      const key = /^\s*enabled\s*=/.exec(text);
      if (key !== null) return { valueStart: lineStart + key[0].length };
    }
    lineStart = lineEnd;
  }
  return headerEnd === null ? null : { headerEnd };
}

interface ListItem {
  start: number;
  end: number;
  value: string;
}

interface ScannedList {
  open: number;
  close: number;
  items: ListItem[];
}

/** Add the surfaces the list lacks after its last item, then take out the ones no
 *  longer wanted. Each edit touches only that item's bytes — or, in a list written one
 *  item per line, that item's line — so the key, its spacing, every comment and every
 *  line ending elsewhere stay as the user wrote them. Additions go first, so a list
 *  whose old items all leave still has an item style to copy. */
function withListItems(raw: string, valueStart: number, surfaces: string[]): string | null {
  const list = scanList(raw, valueStart);
  if (list === null) return null;
  const listed = list.items.map((item) => canonicalSurfaceId(item.value));
  const adding = surfaces.filter((id) => !listed.includes(id));
  let text = adding.length === 0 ? raw : appendItems(raw, list, adding);
  if (text === null) return null;
  for (let current = scanList(text, valueStart); current !== null; current = scanList(text, valueStart)) {
    const unwanted = current.items.find((item) => !surfaces.includes(canonicalSurfaceId(item.value)));
    if (unwanted === undefined) return text;
    text = withoutItem(text, unwanted);
  }
  return null;
}

/** The string array whose `[` follows `from`, with each item's span; null for any other
 *  value (nested arrays, numbers, multi-line strings…), which is left to the human.
 *  Brackets inside strings and comments do not count. */
function scanList(raw: string, from: number): ScannedList | null {
  const opening = /^[ \t]*\[/.exec(raw.slice(from));
  if (opening === null) return null;
  const open = from + opening[0].length - 1;
  const items: ListItem[] = [];
  let i = open + 1;
  while (i < raw.length) {
    const char = raw[i] ?? "";
    if (char === "]") return { open, close: i, items };
    if (char === "#") {
      const newline = raw.indexOf("\n", i);
      i = newline < 0 ? raw.length : newline;
    } else if (/[\s,]/.test(char)) {
      i += 1;
    } else {
      const item = stringAt(raw, i);
      if (item === null) return null;
      items.push(item);
      i = item.end;
    }
  }
  return null;
}

/** The one-line TOML string that starts at `start`, decoded by the TOML parser itself. */
function stringAt(raw: string, start: number): ListItem | null {
  const quote = raw[start];
  if ((quote !== '"' && quote !== "'") || raw.startsWith(quote.repeat(3), start)) return null;
  for (let i = start + 1; i < raw.length && raw[i] !== "\n"; i += 1) {
    if (quote === '"' && raw[i] === "\\") {
      i += 1;
      continue;
    }
    if (raw[i] !== quote) continue;
    try {
      const value = (Bun.TOML.parse(`v = ${raw.slice(start, i + 1)}`) as Record<string, unknown>)["v"];
      return typeof value === "string" ? { start, end: i + 1, value } : null;
    } catch {
      return null;
    }
  }
  return null;
}

function renderItems(ids: string[], quote: string): string {
  return ids.map((id) => `${quote}${id}${quote}`).join(", ");
}

/** The item's line, when nothing but its comma and a comment shares it. */
function ownLine(raw: string, item: ListItem): { start: number; end: number } | null {
  const start = raw.lastIndexOf("\n", item.start - 1) + 1;
  const newline = raw.indexOf("\n", item.end);
  if (newline < 0) return null;
  const isAlone = /^[ \t]*$/.test(raw.slice(start, item.start)) && /^[ \t]*,?[ \t]*(?:#[^\n]*)?\r?$/.test(raw.slice(item.end, newline));
  return isAlone ? { start, end: newline + 1 } : null;
}

/** New items after the last one, in its style: its quote, and — when it has a line of
 *  its own — its indentation, trailing comma and line ending, one item per line. An empty
 *  list has no style to copy, so only `[]` on one line is filled in. */
function appendItems(raw: string, list: ScannedList, ids: string[]): string | null {
  const last = list.items.at(-1);
  if (last === undefined) {
    if (!/^[ \t]*$/.test(raw.slice(list.open + 1, list.close))) return null;
    return `${raw.slice(0, list.open + 1)}${renderItems(ids, '"')}${raw.slice(list.close)}`;
  }
  const quote = raw[last.start] ?? '"';
  const line = ownLine(raw, last);
  if (line === null) return `${raw.slice(0, last.end)}, ${renderItems(ids, quote)}${raw.slice(last.end)}`;
  const indent = raw.slice(line.start, last.start);
  const hasComma = /^[ \t]*,/.test(raw.slice(last.end, line.end));
  const eol = raw[line.end - 2] === "\r" ? "\r\n" : "\n";
  const added = ids.map((id, index) => `${indent}${quote}${id}${quote}${hasComma || index < ids.length - 1 ? "," : ""}${eol}`).join("");
  // The last item now has a successor: written without a trailing comma, it needs one.
  const comma = hasComma ? "" : ",";
  return `${raw.slice(0, last.end)}${comma}${raw.slice(last.end, line.end)}${added}${raw.slice(line.end)}`;
}

/** One item out: its whole line when it has one, else the item and one comma beside it. */
function withoutItem(raw: string, item: ListItem): string {
  const line = ownLine(raw, item);
  if (line !== null) return `${raw.slice(0, line.start)}${raw.slice(line.end)}`;
  const before = /[ \t]*,[ \t]*$/.exec(raw.slice(0, item.start))?.[0];
  if (before !== undefined) return `${raw.slice(0, item.start - before.length)}${raw.slice(item.end)}`;
  const after = /^[ \t]*,[ \t]*/.exec(raw.slice(item.end))?.[0] ?? "";
  return `${raw.slice(0, item.start)}${raw.slice(item.end + after.length)}`;
}

/** Write the carriers a surface needs, wherever it reads them. A `config --add` that
 *  only declared the surface would leave config.toml claiming governance while the host
 *  had no hook at all — with the summary still saying the adapter was written. */
function installSurfaceFiles(root: string, id: string): void {
  const surface = SURFACES.find((s) => s.id === id);
  if (!surface) return;
  const machine = machineCarrier(surface);
  if (machine !== null) {
    const report = installMachineCarriers([id]);
    for (const path of report.written) ui.ok(`${path} written (machine carrier)`);
    for (const refused of report.refused) ui.warn(refuseLine(refused));
    if (report.written.length === 0 && report.refused.length === 0 && report.untouched.length > 0) ui.info(`${machine.path} was already current`);
  }
  const repo = repoCarrier(surface);
  if (repo !== null) {
    const report = install(root, planEntries([id]).filter((entry) => entry.path === repo.path || entry.path === repo.chain));
    for (const path of report.written) ui.ok(`${path} written (repo carrier)`);
    for (const refused of report.refused) ui.warn(refuseLine(refused));
  }
}
