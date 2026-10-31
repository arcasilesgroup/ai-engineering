// The binary IS the payload (blueprint 07): init/update/installCanon read every
// skill and template from EMBEDDED — never from disk paths, never from the network.

import { EMBEDDED } from "./assets.ts";
import { randomBytes } from "node:crypto";
import { closeSync, constants, openSync, writeFileSync, mkdirSync, chmodSync, existsSync, readFileSync, readdirSync, renameSync, unlinkSync, lstatSync, realpathSync, type Stats } from "node:fs";
import { join, dirname, resolve, relative, sep, isAbsolute } from "node:path";
import { fileURLToPath } from "node:url";
import { hashFile } from "./shared-hash.ts";
import {
  isFilesystemRefusal, pathIsWithin, pruneEmptyDirectoryWithin, readProjectFileSnapshot, safeProjectPath, unlinkProjectPath,
  withSafeProjectParent, writeProjectFile, type ProjectFileSnapshot,
} from "./shared-project-fs.ts";

/** Every embedded path under a prefix (e.g. "skills/" or "templates/"). Keys are
 *  normalized: generated as "../skills/..." relative to src/, stripped to "skills/...". */
export function embeddedUnder(prefix: string): Map<string, string> {
  const out = new Map<string, string>();
  for (const [rawPath, ref] of Object.entries(EMBEDDED)) {
    const path = rawPath.replace(/^(\.\.\/)+/, "");
    if (path.startsWith(prefix)) out.set(path, ref);
  }
  return out;
}

/** The skills canon proper: dot-entries under skills/ hold the generated chain
 *  bundle, payload for the plugin hosts and not a skill anyone loads. Materializing
 *  them writes a 33 KB build artifact in every canon and every mirror, counted as
 *  canon by doctor. One predicate, every consumer. */
export function canonSkills(): Map<string, string> {
  const out = new Map<string, string>();
  for (const [path, ref] of embeddedUnder("skills/")) {
    if (path.slice("skills/".length).startsWith(".")) continue;
    out.set(path, ref);
  }
  return out;
}

/** Existing canon files without a matching payload hash are not safe to replace:
 *  unlike repo assets, the machine canon has no ownership lock. */
export function changedCanonSkills(homeDir: string): string[] {
  return [...canonSkills()]
    .filter(([path, ref]) => {
      const installed = join(homeDir, path);
      const embedded = embeddedPath(ref);
      return existsSync(installed) && existsSync(embedded) && hashFile(installed) !== hashFile(embedded);
    })
    .map(([path]) => path);
}

export type CanonDrift = { verified: number; drift: number; missing: number; stale: number; kept: number; unproven: number; foreign: number };

export type CanonExtras = { stale: string[]; kept: string[]; unproven: string[]; foreign: string[] };

/** Files sitting in the canon home that this binary does not ship. Inside a folder we
 *  ship, a file is `stale` — ours to sweep, a renamed asset or a deleted page — only
 *  while its bytes still equal the hash recorded when an installer wrote it. It is
 *  `unproven` when no record covered it: releases before the record wrote no canon
 *  hashes anywhere, so such a file may be an outdated page of ours or a file of the
 *  user's, and nothing can tell which. Any other file there is a `kept` user file,
 *  added or edited by hand after the record existed. Neither is ever deleted. Anything
 *  else in the canon home (a skill of your own, a symlink) is `foreign`. Dot entries are
 *  the OS talking (.DS_Store) and are ignored either way. A payload walk never sees an
 *  orphan, so without this walk a renamed asset lives in every installed canon forever. */
export function canonExtras(homeDir: string): CanonExtras {
  const payload = canonSkills();
  const shipped = new Set([...payload.keys()].map((path) => path.split("/")[1] ?? ""));
  const owned = readCanonOwnership(homeDir);
  const stale: string[] = [];
  const kept: string[] = [];
  const unproven: string[] = [];
  const foreign: string[] = [];
  const walk = (dir: string, relative: string): void => {
    let entries;
    try {
      entries = readdirSync(dir, { withFileTypes: true });
    } catch {
      return; // an unreadable directory is reported by nobody and breaks nothing
    }
    for (const entry of entries) {
      if (entry.name.startsWith(".")) continue;
      const rel = relative.length === 0 ? entry.name : `${relative}/${entry.name}`;
      const absolute = join(dir, entry.name);
      if (entry.isSymbolicLink()) {
        foreign.push(`skills/${rel}`); // someone linked something in: never ours
        continue;
      }
      if (entry.isDirectory()) {
        walk(absolute, rel);
        continue;
      }
      const key = `skills/${rel}`;
      if (payload.has(key)) continue;
      if (!shipped.has(rel.split("/")[0]!)) foreign.push(key);
      else if (owned !== null && isRecordedCanonFile(owned.files, key, absolute)) stale.push(key);
      else if (owned === null || owned.unproven.has(key)) unproven.push(key);
      else kept.push(key);
    }
  };
  walk(join(homeDir, "skills"), "");
  const byPath = (a: string, b: string): number => a.localeCompare(b, "en");
  return { stale: stale.sort(byPath), kept: kept.sort(byPath), unproven: unproven.sort(byPath), foreign: foreign.sort(byPath) };
}

/** The one line doctor and installCanon print for stale files ai-eng proved its own but could
 *  not remove: they stay stale, so the next run tries again once the folder lets it. */
export function refusedStaleCanonText(paths: readonly string[]): string {
  return `${paths.length} stale file(s) ai-eng shipped earlier — removal refused by the filesystem (a read-only, locked or busy folder), kept and retried by the next ai-eng update: ${paths.join(", ")}. Make the folder writable, then run ai-eng update`;
}

/** The stale files whose removal the last install was refused. */
export function refusedStaleCanonFiles(homeDir: string): string[] {
  const refused = readCanonOwnership(homeDir)?.refused ?? new Set<string>();
  return canonExtras(homeDir).stale.filter((path) => refused.has(path));
}

/** The one line doctor and installCanon print for unproven files, with the step that clears it. */
export function unprovenCanonText(paths: readonly string[]): string {
  return `${paths.length} file(s) in shipped skill folders that ai-eng cannot prove it wrote (left from before ownership was recorded: an outdated page of ours or a file of yours) — never deleted: ${paths.join(", ")}. Review each: delete it by hand, or move a file you keep out of the skill folder`;
}

function isRecordedCanonFile(owned: Map<string, string>, key: string, absolute: string): boolean {
  const recorded = owned.get(key);
  if (recorded === undefined) return false;
  try {
    return hashFile(absolute) === recorded;
  } catch {
    return false;
  }
}

/** The record of every canon file installCanon last wrote, path → sha256, in the canon home,
 *  the extras it found with no record to prove them either way (`unproven`), and the stale
 *  files it proved its own but could not remove (`refused`, whose hashes stay in `files`). */
export const CANON_OWNERSHIP_NAME = "canon-owned.json";

type CanonOwnership = { files: Map<string, string>; unproven: Set<string>; refused: Set<string> };

/** Only a `{ files: { path: sha256 }, unproven?: path[], refused?: path[] }` document is this installer's record. */
function parseCanonOwnership(text: string): CanonOwnership | null {
  try {
    const record = JSON.parse(text) as { files?: unknown; unproven?: unknown; refused?: unknown };
    if (record === null || typeof record !== "object" || record.files === null || typeof record.files !== "object") return null;
    const files = new Map<string, string>();
    for (const [path, hash] of Object.entries(record.files as Record<string, unknown>)) {
      if (typeof hash !== "string") return null;
      files.set(path, hash);
    }
    const unproven = record.unproven ?? [];
    const refused = record.refused ?? [];
    if (!isPathList(unproven) || !isPathList(refused)) return null;
    return { files, unproven: new Set(unproven), refused: new Set(refused) };
  } catch {
    return null;
  }
}

function isPathList(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((path) => typeof path === "string");
}

/** The `{ version, ts }` record installCanon and the notice check write to version.json, and nothing else. */
export function isVersionCacheRecord(text: string): boolean {
  try {
    const record = JSON.parse(text) as Record<string, unknown>;
    const keys = Object.keys(record).sort();
    return keys.length === 2 && keys[0] === "ts" && keys[1] === "version"
      && typeof record["version"] === "string" && typeof record["ts"] === "number";
  } catch {
    return false;
  }
}

/** The record is removable only while it parses and no file it vouches for is left: it is
 *  the one proof that such a file is ai-eng's, so deleting it first strands that file. */
export function isRemovableCanonOwnershipRecord(homeDir: string, text: string): boolean {
  const owned = parseCanonOwnership(text);
  if (owned === null) return false;
  return ![...owned.files.keys()].some((path) => isPathPresent(join(homeDir, path)));
}

function isPathPresent(path: string): boolean {
  try {
    lstatSync(path);
    return true;
  } catch (error) {
    // Only a plain "no such entry" is absence; anything we cannot inspect may still be there.
    const code = typeof error === "object" && error !== null && "code" in error ? error.code : null;
    return code !== "ENOENT" && code !== "ENOTDIR";
  }
}

/** Null when there is no record this installer can trust: none yet, unreadable, or not its shape. */
function readCanonOwnership(homeDir: string): CanonOwnership | null {
  const absolute = safeProjectPath(homeDir, CANON_OWNERSHIP_NAME);
  const snapshot = absolute === null ? null : readProjectFileSnapshot(homeDir, absolute);
  return snapshot === null ? null : parseCanonOwnership(snapshot.content.toString("utf8"));
}

/** Remember the payload this binary just installed, so a later binary that stops shipping
 *  a page can prove the page on disk is still the one it wrote. `unproven` carries the
 *  extras no record covered forward: the new record lists only this payload, and without
 *  the list they would read as files the user added after it. `refused` carries the stale
 *  files whose removal the filesystem refused, with the hash that proved them ours: without
 *  it they would read as user files too, and no later run would retry. The record is staged under
 *  a private name and renamed over its own: a rename replaces the directory entry, so a
 *  file of the user's hard-linked at that name keeps its bytes. A link or a non-file at
 *  the name is refused, and the warning is returned. */
export function recordCanonOwnership(homeDir: string, unproven: readonly string[] = [], refused: readonly string[] = []): string | null {
  const files: Record<string, string> = {};
  for (const [path, ref] of canonSkills()) {
    const embedded = embeddedPath(ref);
    if (existsSync(embedded)) files[path] = hashFile(embedded);
  }
  const previous = readCanonOwnership(homeDir)?.files ?? new Map<string, string>();
  const stillOwned = refused.filter((path) => previous.has(path));
  for (const path of stillOwned) files[path] = previous.get(path)!;
  const refusal = `${join(homeDir, CANON_OWNERSHIP_NAME)} is a link, not a regular file, or not writable — ownership record not written; stale canon files will be kept, not swept`;
  let canonicalHome: string;
  try {
    canonicalHome = realpathSync(homeDir);
  } catch {
    return refusal;
  }
  const byPath = (a: string, b: string): number => a.localeCompare(b, "en");
  const record = `${JSON.stringify({ files, unproven: [...unproven].sort(byPath), refused: stillOwned.sort(byPath) }, null, 2)}\n`;
  const isWritten = withSafeProjectParent(canonicalHome, join(canonicalHome, CANON_OWNERSHIP_NAME), (name) => replaceRegularFile(name, record));
  return isWritten ? null : refusal;
}

/** Replace `name` (in the current directory) through a private staged file and a rename. */
function replaceRegularFile(name: string, contents: string): boolean {
  try {
    if (!lstatSync(name).isFile()) return false;
  } catch (error) {
    if (!(typeof error === "object" && error !== null && "code" in error && error.code === "ENOENT")) return false;
  }
  const staged = `.${name}.${process.pid}.${randomBytes(6).toString("hex")}.tmp`;
  let isStaged = false;
  try {
    writeFileSync(staged, contents, { flag: "wx", mode: 0o644 });
    isStaged = true;
    renameSync(staged, name);
    return true;
  } catch {
    if (isStaged) {
      try {
        unlinkSync(staged);
      } catch {
        /* already gone */
      }
    }
    return false;
  }
}

/** Sweep the stale files inside folders we ship, then the directories they leave empty.
 *  A stale file goes only while its bytes equal the hash recorded when this installer
 *  wrote it: a page the user added or edited has no such proof and stays (§14.3). A stale
 *  file still ours that could not be removed (a refused delete, or one that could not be
 *  re-read) is `refused`: still ai-eng's, never a user file. */
export function removeStaleCanonFiles(homeDir: string): { removed: string[]; kept: string[]; unproven: string[]; refused: string[] } {
  const removed: string[] = [];
  const refused: string[] = [];
  const extras = canonExtras(homeDir);
  const kept: string[] = [...extras.kept];
  const owned = readCanonOwnership(homeDir)?.files ?? new Map<string, string>();
  const skillsRoot = safeProjectPath(homeDir, "skills");
  for (const key of extras.stale) {
    const absolute = safeProjectPath(homeDir, key);
    const snapshot = absolute === null ? null : readProjectFileSnapshot(homeDir, absolute);
    if (snapshot !== null && snapshot.hash !== owned.get(key)) {
      kept.push(key); // edited since the walk proved it ours: the user's now
      continue;
    }
    if (absolute === null || snapshot === null || !unlinkProjectPath(homeDir, absolute, snapshot)) {
      refused.push(key);
      continue;
    }
    removed.push(key);
    let directory = dirname(absolute);
    while (skillsRoot !== null && directory !== skillsRoot && pathIsWithin(skillsRoot, directory)) {
      if (!pruneEmptyDirectoryWithin(homeDir, directory)) break;
      directory = dirname(directory);
    }
  }
  return { removed, kept: kept.sort((a, b) => a.localeCompare(b, "en")), unproven: extras.unproven, refused };
}

/** The installed canon against this binary's payload, byte for byte — the one
 *  predicate `init` and `doctor` share (health is a measurement, not a claim).
 *  Existence probes and a marker file are not enough: notice.ts caches the
 *  REGISTRY version in the same version.json that installCanon wrote the
 *  INSTALLED version into, so a canon reads "intact · nothing to install" with
 *  34 files missing. It counts the files the payload does not have as well: a
 *  canon can be complete and dirty at once, and only the payload walk sees both
 *  halves. */
export function canonDrift(homeDir: string): CanonDrift {
  const extras = canonExtras(homeDir);
  const out: CanonDrift = { verified: 0, drift: 0, missing: 0, stale: extras.stale.length, kept: extras.kept.length, unproven: extras.unproven.length, foreign: extras.foreign.length };
  for (const [path, ref] of canonSkills()) {
    const installed = join(homeDir, path);
    const embedded = embeddedPath(ref);
    if (!existsSync(installed)) out.missing += 1;
    else if (existsSync(embedded) && hashFile(installed) === hashFile(embedded)) out.verified += 1;
    else out.drift += 1;
  }
  return out;
}

/** Materialize all embedded skills into a target directory. The embedded refs are
 *  absolute paths at runtime — Bun rewrites the import to the asset's real location,
 *  and in a compiled binary it is the virtualized copy inside the executable. */
export function materializeSkills(
  destRoot: string,
  preserve: readonly string[] = [],
): string[] {
  const skills = new Map(embeddedUnder("skills/"));
  for (const path of preserve) skills.delete(path);
  return materializePrefix("skills/", destRoot, skills);
}

/** Materialize embedded agents/*.md into a target directory (workflow-kit agents canon). */
export function materializeAgents(destRoot: string): string[] {
  return materializePrefix("agents/", destRoot);
}

/** Materialize embedded scripts into ~/.ai-engineering/scripts. */
export function materializeScripts(destRoot: string): string[] {
  return materializePrefix("scripts/", destRoot);
}

function materializePrefix(prefix: string, destRoot: string, embedded = embeddedUnder(prefix)): string[] {
  const lines: string[] = [];
  const executablePattern = /\.(mjs|sh)$/;
  try {
    ensureRealDirectory(destRoot);
  } catch (error) {
    if (error instanceof LinkedPathRefusal) return [`⚠ ${linkedPathsText([error.path])}`];
    if (!isFilesystemRefusal(error)) throw error;
    return [`⚠ ${refusedChangeText(destRoot, error)}`];
  }
  const canonicalRoot = realpathSync(destRoot);
  let count = 0;
  const refused: string[] = [];
  const linked: string[] = [];
  for (const [path, ref] of embedded) {
    const dest = resolve(canonicalRoot, path.slice(prefix.length));
    assertInsideRoot(canonicalRoot, dest);
    // Everything under a link already refused is skipped: it is named once, by the link.
    if (linked.some((link) => pathIsWithin(link, dest))) continue;
    const pathname = embeddedPath(ref);
    // Inside a compiled binary the asset lives at its ORIGINAL absolute path —
    // Bun --compile preserves the string. The ref is already the path.
    const source = existsSync(pathname) ? pathname : ref;
    try {
      resolvedFromRef(source, dest, executablePattern, canonicalRoot);
    } catch (error) {
      // One refused file must not stop the rest of the payload, or the lock after it.
      if (error instanceof LinkedPathRefusal) {
        linked.push(error.path);
        continue;
      }
      if (!isFilesystemRefusal(error)) throw error;
      refused.push(`${dest} (${error.code})`);
      continue;
    }
    count += 1;
  }
  lines.push(`materialized ${count} assets → ${destRoot}`);
  if (linked.length > 0) lines.push(`⚠ ${linkedPathsText(linked)}`);
  if (refused.length > 0) lines.push(`⚠ ${refused.length} file(s) not written — the filesystem refused (read-only, locked or busy); left as they are: ${refused.join(", ")}. Make them writable, then run ai-eng update`);
  return lines;
}

/** A link, or a file where a folder belongs (or the reverse), on a path the payload writes.
 *  It is somebody's setup (a dotfiles link, say): a refusal to report, never written through. */
class LinkedPathRefusal extends Error {
  readonly code = "ELOOP";
  constructor(readonly path: string) {
    super(`refusing to materialize through a symlink or a path of another kind: ${path}`);
  }
}

/** The one line for the paths materialize would not write through. */
function linkedPathsText(paths: readonly string[]): string {
  return `${paths.length} path(s) where ai-eng installs are links or not its own folders or files — never written through, left as they are (the link and what it points at untouched): ${paths.join(", ")}. Move one aside to let ai-eng install there`;
}

/** The root folder of a payload: created when absent, refused when a link or not a folder. */
function ensureRealDirectory(directory: string): void {
  let stat: Stats;
  try {
    stat = lstatSync(directory);
  } catch (error) {
    if (!isFilesystemRefusal(error) || error.code !== "ENOENT") throw error;
    mkdirSync(directory, { recursive: true });
    stat = lstatSync(directory);
  }
  if (stat.isSymbolicLink() || !stat.isDirectory()) throw new LinkedPathRefusal(directory);
}

/** One warning for a write, delete or rename the filesystem refused: the path, the errno and the step. */
export function refusedChangeText(path: string, error: NodeJS.ErrnoException): string {
  return `${path} — the filesystem refused the change (${error.code}); left as it is. Make it writable, then run again`;
}

/** The filesystem path an embedded ref points at. In a compiled binary the ref is
 *  already the path Bun reads the asset from; in the source tree it is relative to
 *  this module. It must NOT be round-tripped through a URL when it is already
 *  absolute: the pathname of a file URL carries a leading slash and, on Windows,
 *  drops the drive letter, so init cannot read a template (ENOENT
 *  /~BUN/root/settings.claude.json-*.tpl) there, while macOS and Linux resolve
 *  the mangled path anyway. */
export function embeddedPath(ref: string, base: string = import.meta.url): string {
  if (ref.startsWith("/") || /^[A-Za-z]:[\\/]/.test(ref)) return ref;
  return fileURLToPath(new URL(ref, base));
}

function assertInsideRoot(root: string, candidate: string): void {
  const pathFromRoot = relative(root, candidate);
  if (pathFromRoot === ".." || pathFromRoot.startsWith(`..${sep}`) || isAbsolute(pathFromRoot)) {
    throw new Error(`embedded asset destination escapes its root: ${candidate}`);
  }
}

function ensureContainedDirectory(root: string, directory: string): void {
  assertInsideRoot(root, directory);
  let current = root;
  for (const component of relative(root, directory).split(sep).filter(Boolean)) {
    current = join(current, component);
    let stat;
    try {
      stat = lstatSync(current);
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
      mkdirSync(current);
      stat = lstatSync(current);
    }
    if (stat.isSymbolicLink() || !stat.isDirectory()) throw new LinkedPathRefusal(current);
    assertInsideRoot(root, realpathSync(current));
  }
}

function resolvedFromRef(source: string, dest: string, executablePattern: RegExp, root: string): void {
  if (!existsSync(source)) return; // missing asset: init reports the count, doctor catches drift
  ensureContainedDirectory(root, dirname(dest));
  try {
    const stat = lstatSync(dest);
    if (stat.isSymbolicLink() || !stat.isFile()) throw new LinkedPathRefusal(dest);
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
  }
  // O_NOFOLLOW: a link that appears after the check is refused (ELOOP), never written through.
  const descriptor = openSync(dest, constants.O_WRONLY | constants.O_CREAT | constants.O_TRUNC | constants.O_NOFOLLOW, 0o666);
  try {
    writeFileSync(descriptor, readFileSync(source));
  } finally {
    closeSync(descriptor);
  }
  if (executablePattern.test(dest)) chmodSync(dest, 0o755);
}

function readEmbeddedText(ref: string): string {
  return readFileSync(embeddedPath(ref), "utf8");
}

/** One embedded template, rendered with {{vars}}. Lookup by suffix so callers can
 *  use plain names ("AGENTS.md.tpl") regardless of the generated key prefix. */
export function embeddedTemplate(name: string, vars: Record<string, string> = {}): string {
  for (const [key, ref] of Object.entries(EMBEDDED)) {
    if (key === `templates/${name}` || key === `../templates/${name}`) {
      const content = readEmbeddedText(ref);
      let out = content;
      for (const [k, v] of Object.entries(vars)) out = out.split(`{{${k}}}`).join(v);
      return out;
    }
  }
  throw new Error(`template not embedded: ${name}`);
}
/** Source of the chain bundle for in-process plugin hosts (P0-2). The bundle is
 *  generated by scripts/gen-assets.ts into skills/.chain-bundle/ and travels
 *  embedded like any other payload file — a self-contained module, not a
 *  pointer into src/ (whose relative imports die in a foreign repo). */
export function embeddedChainBundle(): string {
  const bundled = embeddedUnder("skills/.chain-bundle/");
  const ref = bundled.get("skills/.chain-bundle/ai-eng-chain.ts");
  if (!ref) throw new Error("chain bundle not embedded — regenerate assets: bun scripts/gen-assets.ts");
  return readEmbeddedText(ref);
}

// The root-bound file operations live in shared-project-fs.ts so the chain bundle can use
// them without the embedded assets; installers keep importing them from here.
export {
  isFilesystemRefusal, pathIsWithin, pruneEmptyDirectoryWithin, readProjectFileSnapshot, safeProjectPath, unlinkProjectPath,
  withSafeProjectParent, writeProjectFile, type ProjectFileSnapshot,
};
