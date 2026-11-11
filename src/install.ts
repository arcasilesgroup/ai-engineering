// The installer behind init/uninstall/update: templates → disk, idempotent. One rule
// decides every file: what ai-eng wrote is ai-eng's and always holds this binary's
// bytes, edited or not (an edit is overwritten: commit or copy it first). What it never wrote — a file the project
// already had — is the project's and is never touched. The one exception is the config
// ai-eng seeds for the project to own (SEEDED_CONFIG): it is the project's from its
// first edit.

import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, dirname, relative } from "node:path";
import { createHash } from "node:crypto";
import { embeddedTemplate, embeddedUnder, isFilesystemRefusal, isPathPresent, readProjectFileSnapshot, safeProjectPath, writeProjectFile } from "./embed.ts";
export { hashFile } from "./shared-hash.ts";

export type PlanEntry = {
  path: string; // repo-relative, e.g. ".claude/settings.json"
  ours: string; // the new content from the binary's templates
  /** A file the user also owns (settings, hooks.json). Ours are MERGED in by marker
   *  and never written whole — the difference between installing a hook and
   *  overwriting the hooks, permissions and env of somebody's editor (§03). */
  merge?: boolean;
};

/** The config ai-eng seeds for the project to own: written while absent, refreshed while
 *  it still holds the bytes ai-eng recorded, and the project's from its first edit. */
export const SEEDED_CONFIG: ReadonlySet<string> = new Set([
  ".ai-engineering/config.toml",
  ".ai-engineering/overrides.toml",
  ".ai-engineering/arch.rules.json",
]);

export type InstallReport = {
  written: string[];
  untouched: string[]; // already byte-identical to ours (or a merge with nothing to add)
  yours: string[]; // the project's: never written by ai-eng, or seeded config it edited
  /** Files we were asked to merge into and could not: not JSON, or not an object.
   *  Untouched, and named — an installer that quietly skips a surface's carrier
   *  leaves a repo that believes it is governed and is not (§13). */
  refused: Array<{ path: string; reason: string }>;
};

export function sha256(text: string): string {
  // Identity-ledger hashing, not a data hash: a CRLF checkout (core.autocrlf on
  // Windows) holds ai-eng's LF bytes as CRLF, and that is not an edit. Normalizing
  // is identity on the LF-canonical side, so hashes recorded by past releases still match.
  return createHash("sha256").update(text.replace(/\r\n/g, "\n")).digest("hex");
}

let managedHookCommands: Set<string> | undefined;

function collectHookCommands(value: unknown, commands: Set<string>): void {
  if (Array.isArray(value)) {
    for (const entry of value) collectHookCommands(entry, commands);
    return;
  }
  if (value === null || typeof value !== "object") return;
  const record = value as Record<string, unknown>;
  if (typeof record["command"] === "string") commands.add(record["command"]);
  for (const entry of Object.values(record)) collectHookCommands(entry, commands);
}

/** Match only exact hook commands emitted by the embedded settings templates. */
function managedCommands(): Set<string> {
  if (managedHookCommands !== undefined) return managedHookCommands;
  const commands = new Set<string>();
  for (const path of embeddedUnder("templates/settings.").keys()) {
    if (!path.endsWith(".json.tpl")) continue;
    const settings = JSON.parse(embeddedTemplate(path.slice("templates/".length))) as { hooks?: unknown };
    collectHookCommands(settings.hooks, commands);
  }
  managedHookCommands = commands;
  return commands;
}

const LEGACY_CHECKPOINT_HOOK = /^(?:\[ -f "\$HOME\/\.ai-engineering\/scripts\/checkpoint-gate\.py" \] \|\| exit 0; )?python3 "\$HOME\/\.ai-engineering\/scripts\/checkpoint-gate\.py" --surface [a-z0-9-]+$/;

/** 3.0.0's two Copilot lines — the bare repo one and the machine one whose `|| exit 0`
 *  also swallowed a crashing chain — are still ours to replace and to take out. */
const LEGACY_COPILOT_HOOK = /^(?:command -v ai-eng >\/dev\/null 2>&1 && )?ai-eng chain (?:PreToolUse|PostToolUse) --surface copilot-cli(?: \|\| exit 0)?$/;

/** What a Windows render appends to a hook line whose host reads the exit status
 *  (adapters.ts withLauncher): `powershell -Command` would turn exit 2 into exit 1. */
export const KEEP_EXIT_STATUS = "; exit $LASTEXITCODE";
// Only right after `chain <Event>`: Copilot's own PowerShell line ends in the same words.
const KEEP_EXIT_STATUS_TAIL = new RegExp(`( chain [A-Za-z]+)${KEEP_EXIT_STATUS.replace(/[$]/g, "\\$&")}(?=$|")`, "g");

/** A hook text with this machine's launcher taken back out: the `.cmd`/`.exe` name and the
 *  exit-status tail a Windows render adds. The same line on every OS, so the same marker,
 *  and the same hash whichever shim PATH happens to put first. */
export function portableHookText(text: string): string {
  return text.replace(/ai-eng\.(?:cmd|exe) chain /g, "ai-eng chain ").replace(KEEP_EXIT_STATUS_TAIL, "$1");
}

function isOurs(value: unknown): boolean {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
  const command = (value as { command?: unknown }).command;
  if (typeof command !== "string") return false;
  const portable = portableHookText(command);
  return managedCommands().has(portable) || LEGACY_CHECKPOINT_HOOK.test(portable) || LEGACY_COPILOT_HOOK.test(portable);
}

const isEmptyContainer = (value: unknown): boolean =>
  Array.isArray(value) ? value.length === 0 : value !== null && typeof value === "object" ? Object.keys(value).length === 0 : false;
const REMOVE = Symbol("remove");

/** Merge our entries into a file the user also owns. Objects merge key by key, arrays
 *  keep every foreign entry and append ours — dropping our own previous ones first,
 *  which is what makes a second install a no-op — and a scalar from our template is
 *  ours. Nothing foreign is ever dropped: an entry is ours only when it carries the
 *  marker command (§03). */
function mergeValue(existing: unknown, ours: unknown): unknown {
  if (Array.isArray(ours)) {
    const stripped = Array.isArray(existing) ? stripValue(existing) : [];
    const kept = Array.isArray(stripped) ? stripped : [];
    return [...kept, ...ours];
  }
  if (ours !== null && typeof ours === "object") {
    const base: Record<string, unknown> = existing !== null && typeof existing === "object" && !Array.isArray(existing) ? { ...existing } : {};
    for (const [key, value] of Object.entries(ours)) base[key] = mergeValue(base[key], value);
    return base;
  }
  return ours;
}

/** The inverse of the merge — `uninstall`'s half. Our entries come out deepest-first, and
 *  the containers that existed only to hold them go with them, so a settings file a user
 *  had before init is one again after uninstall.
 *
 *  What does NOT come out: the top-level scalars our template declares (`version`,
 *  `failClosed`, a description). Removing a key whose value happens to equal ours would
 *  delete a key the user wrote themselves — a `version` their host requires, which is a
 *  broken file, not a restored one — and telling the two apart needs a ledger of what each
 *  merge added. The ledger costs more than it saves here; the entries are what matters and
 *  those are exact. */
function stripValue(node: unknown): unknown {
  if (Array.isArray(node)) {
    const kept: unknown[] = [];
    for (const entry of node) {
      if (isOurs(entry)) continue;
      const stripped = stripValue(entry);
      if (stripped === REMOVE) continue;
      if (isEmptyContainer(stripped) && !isEmptyContainer(entry)) continue;
      kept.push(stripped);
    }
    return kept;
  }
  if (node !== null && typeof node === "object") {
    const out: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(node)) {
      // Our banner, not a hook — matched by the sentence we write, never by the word
      // "ai-eng": a comment of the user's that mentions the product is theirs, and the
      // marker rule for hooks is the command itself for exactly this reason.
      if (key === "$comment" && typeof value === "string" && value.startsWith("Generated by ai-eng")) continue;
      const stripped = stripValue(value);
      if (
        key === "hooks" &&
        Array.isArray(value) &&
        value.length > 0 &&
        Array.isArray(stripped) &&
        stripped.length === 0 &&
        Object.keys(node).every((property) => property === "hooks" || property === "matcher")
      ) {
        return REMOVE;
      }
      if (stripped === REMOVE) continue;
      if (isEmptyContainer(stripped) && !isEmptyContainer(value)) continue;
      out[key] = stripped;
    }
    return out;
  }
  return node;
}

type Shape = { indent: string; crlf: boolean; newline: boolean };

/** Serialize in the file's own shape. The only literal newlines JSON.stringify emits
 *  are the ones between tokens — everything inside a string is escaped — so the CRLF
 *  pass is safe. */
const serialize = (value: unknown, shape: Shape): string => {
  const text = `${JSON.stringify(value, null, shape.indent)}${shape.newline ? "\n" : ""}`;
  return shape.crlf ? text.replace(/\n/g, "\r\n") : text;
};

/** The file's own indentation, line endings and trailing newline — and only when this
 *  code can reproduce the file's bytes exactly with them. `nada ajeno se toca ni se
 *  reformatea` (§03): the layout (four spaces, tabs, CRLF, a compact one-liner) is the
 *  user's, so a file we cannot reproduce is a file we do not merge into. Null means
 *  exactly that. */
function shapeOf(text: string, parsed: unknown): Shape | null {
  const shape: Shape = { indent: /\n([ \t]+)"/.exec(text)?.[1] ?? "  ", crlf: text.includes("\r\n"), newline: text.endsWith("\n") };
  return serialize(parsed, shape) === text ? shape : null;
}

type SharedText = { text: string; changed: boolean } | { refused: "not-json" | "not-object" | "reformat" };

/** Merge our template into the text of a file the user owns. Refuses — and says which
 *  way — on anything it cannot merge without changing bytes it does not own: a settings
 *  file with comments or a typo is the user's, and so is one laid out in a style this
 *  installer would have to rewrite. */
export function mergeSharedText(current: string, ours: string): SharedText {
  let existing: unknown;
  try {
    existing = JSON.parse(current);
  } catch {
    return { refused: "not-json" };
  }
  if (existing === null || typeof existing !== "object" || Array.isArray(existing)) return { refused: "not-object" };
  const shape = shapeOf(current, existing);
  if (shape === null) return { refused: "reformat" };
  const text = serialize(mergeValue(existing, JSON.parse(ours)), shape);
  return { text, changed: text !== current };
}

/** Our entries out of the text of a file we share, leaving the user's. Null when it
 *  cannot be read, or cannot be rewritten without reformatting it — the caller never
 *  rewrites what it cannot parse, and never reformats what the user wrote. */
export function stripSharedText(current: string): string | null {
  let existing: unknown;
  try {
    existing = JSON.parse(current);
  } catch {
    return null;
  }
  const shape = shapeOf(current, existing);
  if (shape === null) return null;
  return serialize(stripValue(existing), shape);
}

/** Idempotent install. A file byte-identical to ours is a no-op; a file ai-eng wrote
 *  (`previousOurs` answers with its recorded `sha256:<hex>`) receives ours, edited or
 *  not — except seeded config the project edited, which is the project's now. A file
 *  ai-eng never wrote is the project's and is left alone. */
export function install(
  repoRoot: string,
  entries: PlanEntry[],
  previousOurs?: (path: string) => string | null,
): InstallReport {
  const report: InstallReport = { written: [], untouched: [], yours: [], refused: [] };
  for (const entry of entries) {
    const absolute = join(repoRoot, entry.path);
    const oursHash = sha256(entry.ours);
    if (existsSync(absolute)) {
      const current = readFileSync(absolute, "utf8");
      // A file the user also owns never takes the whole-file path: ours go in by
      // marker and everything else comes out as it went in. The 3-way below cannot
      // do this — its "the user edited it" branch is a CONFLICT, and a settings file
      // with the user's own hooks in it is not a conflict, it is Tuesday.
      if (entry.merge === true) {
        const merged = mergeSharedText(current, entry.ours);
        if ("refused" in merged) {
          report.refused.push({ path: entry.path, reason: merged.refused });
          continue;
        }
        if (!merged.changed) {
          report.untouched.push(entry.path);
          continue;
        }
        // The user's file, so never written through a link or a second name: that is another file.
        const mergeRefusal = rewriteInPlace(repoRoot, entry.path, merged.text);
        if (mergeRefusal !== null) {
          report.refused.push({ path: entry.path, reason: mergeRefusal });
          continue;
        }
        report.written.push(entry.path);
        continue;
      }
      if (sha256(current) === oursHash) {
        report.untouched.push(entry.path);
        continue;
      }
      const previous = previousOurs?.(entry.path) ?? null;
      const isEditedConfig = SEEDED_CONFIG.has(entry.path) && sha256(current) !== previous?.slice("sha256:".length);
      if (previous === null || isEditedConfig) {
        report.yours.push(entry.path);
        continue;
      }
      const refusal = rewriteInPlace(repoRoot, entry.path, entry.ours);
      if (refusal !== null) {
        report.refused.push({ path: entry.path, reason: refusal });
        continue;
      }
      report.written.push(entry.path);
      continue;
    }
    // existsSync said absent, yet a name is there: a dangling link. Windows' exclusive create
    // follows one to create its target, so it is refused here, before any write.
    if (isPathPresent(absolute) || !isRealFolderChain(repoRoot, dirname(absolute))) {
      report.refused.push({ path: entry.path, reason: LINKED });
      continue;
    }
    mkdirSync(dirname(absolute), { recursive: true });
    try {
      // wx: a name that appears after the check above is refused (EEXIST), never overwritten.
      writeFileSync(absolute, entry.ours, { flag: "wx" });
    } catch (error) {
      if (!isFilesystemRefusal(error)) throw error;
      report.refused.push({ path: entry.path, reason: error.code === "EEXIST" ? LINKED : WRITE_REFUSED });
      continue;
    }
    report.written.push(entry.path);
  }
  return report;
}

/** The refusal for a path ai-eng owns that is a link, sits under one, or has a second name. */
export const LINKED = "linked";
/** The refusal for a path ai-eng owns that the filesystem would not let it write. */
export const WRITE_REFUSED = "write-refused";

/** True when the folders that already exist on the way to `folder` are real folders inside
 *  the repo: a linked .github or .ai-engineering would make mkdir and the create land outside
 *  it. The missing rest is created by mkdir as real folders. */
function isRealFolderChain(root: string, folder: string): boolean {
  let existing = folder;
  while (!isPathPresent(existing) && dirname(existing) !== existing) existing = dirname(existing);
  return safeProjectPath(root, relative(root, existing)) !== null;
}

/** Rewrite a file ai-eng owns through its checked parent: never through a link (the file or
 *  a folder above it), and never a file with a second name (a hard link from elsewhere would
 *  receive the bytes too). Null when written, else the reason it was refused. */
function rewriteInPlace(root: string, rel: string, contents: string): string | null {
  const absolute = safeProjectPath(root, rel);
  if (absolute === null) return LINKED;
  const snapshot = readProjectFileSnapshot(root, absolute);
  if (snapshot === null) return WRITE_REFUSED;
  if (snapshot.nlink !== 1) return LINKED;
  return writeProjectFile(root, absolute, snapshot, contents) ? null : WRITE_REFUSED;
}

/** The lockfile: sha256 per installed asset + the approved-spec pin. Nothing downloads;
 *  it is an assertion of what this repo expects, not a package manager (§08). */
export type Lock = {
  version: string;
  assets: Record<string, string>;
  spec_sha256?: string;
  /** The commit the live milestone started from: without it a conditional node has no
   *  diff to judge, and "if it touches UI" stays a sentence nobody can check (§20.1). */
  base_sha?: string;
};

export function buildLock(
  entries: PlanEntry[],
  version: string,
  carry: { spec_sha256?: string | undefined; base_sha?: string | undefined } = {},
): Lock {
  const assets: Record<string, string> = {};
  for (const entry of entries) {
    assets[entry.path] = sha256(entry.ours);
  }
  const lock: Lock = { version, assets };
  // The two contract fields are the milestone's, not the installer's. Rebuilding the
  // lock must not drop them: any `update` between `spec approve` and `spec close`
  // would erase the approval, and spec close would treat a pinned contract as unpinned.
  if (carry.spec_sha256) lock.spec_sha256 = carry.spec_sha256;
  if (carry.base_sha) lock.base_sha = carry.base_sha;
  return lock;
}

export function lockText(lock: Lock): string {
  const lines = ["# ai-eng.lock — sha256 of the global canon this repo expects (§08).", `version = "${lock.version}"`, ""];
  if (lock.spec_sha256) lines.push(`spec_sha256 = "${lock.spec_sha256}"`, "");
  if (lock.base_sha) lines.push(`base_sha = "${lock.base_sha}"`, "");
  lines.push("[assets]");
  for (const [path, hash] of Object.entries(lock.assets)) lines.push(`"${path}" = "${hash}"`);
  return `${lines.join("\n")}\n`;
}

export function parseLock(text: string): Lock {
  const doc = Bun.TOML.parse(text) as Record<string, unknown>;
  const assets: Record<string, string> = {};
  const raw = doc["assets"];
  if (raw && typeof raw === "object" && !Array.isArray(raw)) {
    for (const [path, hash] of Object.entries(raw as Record<string, unknown>)) {
      if (typeof hash === "string") assets[path] = hash;
    }
  }
  const lock: Lock = { version: typeof doc["version"] === "string" ? doc["version"] : "", assets };
  if (typeof doc["spec_sha256"] === "string") lock.spec_sha256 = doc["spec_sha256"];
  // A commit id, or nothing. A value beginning with `-` reaches `git diff` as an
  // option, and `--output=<path>` overwrites an arbitrary file while the command
  // still reports success (audit AI-ENG-INJ-001).
  const base = doc["base_sha"];
  if (typeof base === "string" && /^[0-9a-f]{40}$/.test(base)) lock.base_sha = base;
  return lock;
}
