// The binary IS the payload (blueprint 07): init/update/installCanon read every
// skill and template from EMBEDDED — never from disk paths, never from the network.

import { EMBEDDED } from "./assets.ts";
import { randomBytes } from "node:crypto";
import { closeSync, constants, fstatSync, ftruncateSync, openSync, writeFileSync, mkdirSync, chmodSync, existsSync, readFileSync, readdirSync, renameSync, unlinkSync, lstatSync, realpathSync, type Dirent, type Stats } from "node:fs";
import { basename, join, dirname, resolve, relative, sep, isAbsolute } from "node:path";
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

export type CanonDrift = { verified: number; drift: number; missing: number; stale: number; foreign: number };

/** What sits in the machine home beside this binary's payload.
 *  - `stale`: an entry inside a skill folder this binary ships that the payload does not
 *    have. The folder is ai-eng's whole, so a renamed asset, a page an older release
 *    shipped and a file added there by hand are the same thing: swept.
 *  - `retired`: a skill folder, agent or script an earlier ai-eng installed (its ownership
 *    record names it) that this binary no longer ships. Swept whole.
 *  - `foreign`: anything else in the skills home — a skill of your own, in a folder of its
 *    own name. Never touched.
 *  Dot entries are the OS talking (.DS_Store) and are ignored. A payload walk never sees an
 *  orphan, so without this walk a renamed asset lives in every installed canon forever. */
export type CanonExtras = { stale: string[]; retired: string[]; foreign: string[] };

/** Every payload file ai-eng installs into the machine home, keyed as it lands there
 *  ("skills/…", "agents/…", "scripts/…"). */
function machinePayload(): Map<string, string> {
  return new Map([...canonSkills(), ...embeddedUnder("agents/"), ...embeddedUnder("scripts/")]);
}

export function canonExtras(homeDir: string): CanonExtras {
  const payload = machinePayload();
  const shipped = new Set([...canonSkills().keys()].map(skillFolderOf));
  const recorded = readCanonOwnership(homeDir) ?? new Map<string, string>();
  const recordedSkills = new Set([...recorded.keys()].filter((key) => key.startsWith("skills/")).map(skillFolderOf));
  const stale: string[] = [];
  const retired: string[] = [];
  const foreign: string[] = [];
  for (const entry of listEntries(join(homeDir, "skills"))) {
    if (entry.name.startsWith(".")) continue;
    const key = `skills/${entry.name}`;
    if (shipped.has(entry.name) && entry.isDirectory()) {
      stale.push(...walkEntries(join(homeDir, key), key).filter((path) => !payload.has(path)));
    } else if (recordedSkills.has(entry.name) && entry.isDirectory()) {
      retired.push(key);
    } else {
      foreign.push(key);
    }
  }
  // An agent or script ai-eng recorded and no longer ships: only the recorded name is ours,
  // because ~/.claude/agents may be a link into this folder and hold the user's own agents.
  for (const key of recorded.keys()) {
    if (key.startsWith("skills/") || payload.has(key)) continue;
    if (isFileOrLink(join(homeDir, key))) retired.push(key);
  }
  const byPath = (a: string, b: string): number => a.localeCompare(b, "en");
  return { stale: stale.sort(byPath), retired: retired.sort(byPath), foreign: foreign.sort(byPath) };
}

/** A payload file's key as an installer records it: `skills/<skill>/<file…>`, `agents/<file>`
 *  or `scripts/<file…>`, with no empty, `.` or `..` segment and no dot-led skill, agent or script name. */
function isRecordKey(key: string): boolean {
  const segments = key.split("/");
  if (segments.some((segment) => segment.length === 0 || segment === "." || segment === ".." || segment.includes("\\"))) return false;
  if (segments.length < 2 || segments[1]!.startsWith(".")) return false; // a dot-led skill, agent or script is never ours
  if (segments[0] === "skills") return segments.length >= 3;
  if (segments[0] === "agents") return segments.length === 2;
  return segments[0] === "scripts" && segments.length >= 2;
}

/** "skills/ai-verify/SKILL.md" → "ai-verify". */
function skillFolderOf(key: string): string {
  return key.split("/")[1] ?? "";
}

function listEntries(directory: string): Dirent[] {
  try {
    return readdirSync(directory, { withFileTypes: true });
  } catch {
    return []; // an unreadable directory is reported by nobody and breaks nothing
  }
}

/** Every file and link under a folder, as home-relative keys. Links are entries, never followed. */
function walkEntries(directory: string, key: string): string[] {
  const out: string[] = [];
  for (const entry of listEntries(directory)) {
    if (entry.name.startsWith(".")) continue;
    const childKey = `${key}/${entry.name}`;
    if (entry.isDirectory() && !entry.isSymbolicLink()) out.push(...walkEntries(join(directory, entry.name), childKey));
    else out.push(childKey);
  }
  return out;
}

/** The one line doctor and installCanon print for files of ours the filesystem would not let go. */
export function refusedStaleCanonText(paths: readonly string[]): string {
  return `${paths.length} file(s) ai-eng no longer ships — removal refused by the filesystem (a read-only, locked or busy folder), retried by the next ai-eng update: ${paths.join(", ")}. Make the folder writable, then run ai-eng update`;
}

/** The record of every machine payload file an installer wrote, path → sha256, in the
 *  machine home. It is how a later binary knows a skill, agent or script it stopped shipping
 *  was ai-eng's to remove. */
export const CANON_OWNERSHIP_NAME = "canon-owned.json";

/** Only a `{ files: { path: sha256 } }` document whose every path has the shape an installer
 *  writes is this installer's record (older releases wrote `unproven` and `refused` lists
 *  beside it; they are read past). The record decides what gets deleted, so one odd key —
 *  "", "agents", "skills/.." — makes the whole record untrusted rather than a delete target. */
function parseCanonOwnership(text: string): Map<string, string> | null {
  try {
    const record = JSON.parse(text) as { files?: unknown };
    if (record === null || typeof record !== "object" || record.files === null || typeof record.files !== "object") return null;
    const files = new Map<string, string>();
    for (const [path, hash] of Object.entries(record.files as Record<string, unknown>)) {
      if (typeof hash !== "string" || !isRecordKey(path)) return null;
      files.set(path, hash);
    }
    return files;
  } catch {
    return null;
  }
}

/** The `{ version, ts }` record installCanon and the notice check write to version.json, and nothing else. */
export function isVersionCacheRecord(text: string): boolean {
  try {
    const record = JSON.parse(text) as Record<string, unknown>;
    const keys = Object.keys(record).sort((left, right) => left.localeCompare(right));
    return keys.length === 2 && keys[0] === "ts" && keys[1] === "version"
      && typeof record["version"] === "string" && typeof record["ts"] === "number";
  } catch {
    return false;
  }
}

/** The record is removable only while it parses and nothing it vouches for is left: it is
 *  the one proof that such a file is ai-eng's, so deleting it first strands that file. */
export function isRemovableCanonOwnershipRecord(homeDir: string, text: string): boolean {
  const owned = parseCanonOwnership(text);
  if (owned === null) return false;
  return ![...owned.keys()].some((path) => isPathPresent(join(homeDir, path)));
}

/** A file or a link at the path (a folder is never a recorded agent or script). */
function isFileOrLink(path: string): boolean {
  try {
    const entry = lstatSync(path);
    return entry.isFile() || entry.isSymbolicLink();
  } catch {
    return false;
  }
}

/** Present as a name: a dangling link counts, which existsSync (it follows links) misses. */
export function isPathPresent(path: string): boolean {
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
function readCanonOwnership(homeDir: string): Map<string, string> | null {
  const absolute = safeProjectPath(homeDir, CANON_OWNERSHIP_NAME);
  const snapshot = absolute === null ? null : readProjectFileSnapshot(homeDir, absolute);
  return snapshot === null ? null : parseCanonOwnership(snapshot.content.toString("utf8"));
}

/** The skill folders, agents and scripts the ownership record names: what ai-eng installed
 *  on this machine, now or in an earlier release. Uninstall removes these whole. */
export function recordedMachinePaths(homeDir: string): string[] {
  const keys = new Set([...machinePayload().keys(), ...(readCanonOwnership(homeDir)?.keys() ?? [])]);
  const paths = new Set<string>();
  for (const key of keys) paths.add(key.startsWith("skills/") ? `skills/${skillFolderOf(key)}` : key);
  return [...paths].sort((a, b) => a.localeCompare(b, "en"));
}

/** Remember the payload this binary just installed, so a later binary that stops shipping a
 *  skill, agent or script knows it is ai-eng's to remove. Whatever an earlier record names
 *  that is still on disk (a removal the filesystem refused) stays named, so the next run
 *  retries it; so does `alsoKeep`, a retired path (or skill folder) still left outside the
 *  home (an agent's copy in ~/.claude/agents, a skill's slash command). The record is staged under a private name and renamed over its own: a rename
 *  replaces the directory entry, so a file of the user's hard-linked at that name keeps its
 *  bytes. A link or a non-file at the name is refused, and the warning is returned. */
export function recordCanonOwnership(homeDir: string, alsoKeep: readonly string[] = []): string | null {
  const files: Record<string, string> = {};
  for (const [path, hash] of readCanonOwnership(homeDir) ?? []) {
    const left = path.startsWith("skills/") ? join(homeDir, "skills", skillFolderOf(path)) : join(homeDir, path);
    if (isPathPresent(left) || alsoKeep.some((kept) => path === kept || path.startsWith(`${kept}/`))) files[path] = hash;
  }
  for (const [path, ref] of machinePayload()) {
    const embedded = embeddedPath(ref);
    if (existsSync(embedded)) files[path] = hashFile(embedded);
  }
  const refusal = `${join(homeDir, CANON_OWNERSHIP_NAME)} is a link, not a regular file, or not writable — ownership record not written; a skill ai-eng stops shipping will not be swept`;
  let canonicalHome: string;
  try {
    canonicalHome = realpathSync(homeDir);
  } catch {
    return refusal;
  }
  const record = `${JSON.stringify({ files: Object.fromEntries(Object.entries(files).sort(([a], [b]) => a.localeCompare(b, "en"))) }, null, 2)}\n`;
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

/** Remove one file or link under the machine home, bound to its checked parent. A link goes
 *  as a link: what it points at is never touched. */
export function removeMachineEntry(homeDir: string, key: string): boolean {
  const parent = safeProjectPath(homeDir, dirname(key));
  if (parent === null) return false;
  const absolute = join(parent, basename(key));
  let entry: Stats;
  try {
    entry = lstatSync(absolute);
  } catch {
    return true; // already gone
  }
  if (entry.isSymbolicLink()) {
    return withSafeProjectParent(homeDir, absolute, (name) => {
      // Still the very link that was judged: a file swapped in at the name is not removed.
      const current = lstatSync(name);
      if (!current.isSymbolicLink() || current.dev !== entry.dev || current.ino !== entry.ino) return false;
      unlinkSync(name);
      return true;
    });
  }
  const snapshot = readProjectFileSnapshot(homeDir, absolute);
  return snapshot !== null && unlinkProjectPath(homeDir, absolute, snapshot);
}

/** Remove a machine path ai-eng owns — a file, a link, or a folder with everything in it —
 *  then the folders it leaves empty, up to (not including) the home's top-level folder.
 *  Returns the keys the filesystem would not let go. */
export function removeMachinePath(homeDir: string, key: string): string[] {
  // The home's real spelling: the folder prune checks each parent against its realpath, and
  // a home under a linked folder (macOS /var → /private/var) would fail that check.
  let canonicalHome: string;
  let isFolder = false;
  try {
    canonicalHome = realpathSync(homeDir);
    const entry = lstatSync(join(canonicalHome, key));
    isFolder = entry.isDirectory() && !entry.isSymbolicLink();
  } catch {
    return [];
  }
  const absolute = join(canonicalHome, key);
  const refused = (isFolder ? walkEntries(absolute, key) : [key]).filter((entry) => !removeMachineEntry(homeDir, entry));
  if (isFolder) pruneEmptyFoldersUnder(homeDir, absolute);
  const top = join(canonicalHome, key.split("/")[0]!);
  let directory = isFolder ? absolute : dirname(absolute);
  while (directory !== top && pathIsWithin(top, directory)) {
    if (!pruneEmptyDirectoryWithin(homeDir, directory)) break;
    directory = dirname(directory);
  }
  return refused;
}

/** Empty folders below `directory` (deepest first) go; the walk never follows a link. */
function pruneEmptyFoldersUnder(homeDir: string, directory: string): void {
  for (const entry of listEntries(directory)) {
    if (!entry.isDirectory() || entry.isSymbolicLink()) continue;
    const child = join(directory, entry.name);
    pruneEmptyFoldersUnder(homeDir, child);
    pruneEmptyDirectoryWithin(homeDir, child);
  }
}

/** Sweep everything canonExtras calls ai-eng's and not shipped: stale entries inside the
 *  skill folders we ship, and retired skills, agents and scripts. Edited or not, they are
 *  ai-eng's — a file of your own belongs in a folder of your own. */
export function removeStaleCanonFiles(homeDir: string): { removed: string[]; refused: string[] } {
  const extras = canonExtras(homeDir);
  const removed: string[] = [];
  const refused: string[] = [];
  for (const key of [...extras.stale, ...extras.retired]) {
    const left = removeMachinePath(homeDir, key);
    if (left.length === 0) removed.push(key);
    else refused.push(...left);
  }
  return { removed, refused };
}

/** The installed canon against this binary's payload, byte for byte — the one
 *  predicate `init` and `doctor` share (health is a measurement, not a claim).
 *  Existence probes and a marker file are not enough: notice.ts caches the
 *  REGISTRY version in the same version.json that installCanon wrote the
 *  INSTALLED version into, so a canon reads "intact · nothing to install" with
 *  34 files missing. It counts the entries the payload does not have as well: a
 *  canon can be complete and dirty at once, and only the extras walk sees both
 *  halves. */
export function canonDrift(homeDir: string): CanonDrift {
  const extras = canonExtras(homeDir);
  const out: CanonDrift = { verified: 0, drift: 0, missing: 0, stale: extras.stale.length + extras.retired.length, foreign: extras.foreign.length };
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
export function materializeSkills(destRoot: string): string[] {
  return materializePrefix("skills/", destRoot);
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
  let descriptor = openSync(dest, constants.O_WRONLY | constants.O_CREAT | constants.O_NOFOLLOW, 0o666);
  if (fstatSync(descriptor).nlink > 1) {
    // A second name (a hard link from the user's dotfiles) would receive our bytes too: our
    // name gets a fresh file of its own, and the other name keeps what it holds.
    closeSync(descriptor);
    unlinkSync(dest);
    descriptor = openSync(dest, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | constants.O_NOFOLLOW, 0o666);
  }
  try {
    ftruncateSync(descriptor, 0);
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
