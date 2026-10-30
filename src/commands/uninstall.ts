// `ai-eng uninstall` — two scopes, stated plainly: "This project" sweeps EVERY file the lock declares
// ai-eng's (hooks, settings entries, adapters, CI workflow, config, lock) and
// prunes the dirs that end up empty — nothing that depends on ai-eng is left
// behind. "Everything" ALSO removes the machine side (~/.ai-engineering: the
// global skill canon and mirrors). Deleting what the user edited is the worst
// class of bug a governance tool can have: edited files are kept and named,
// contract files survive "This project", and "Everything" asks twice.

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { closeSync, constants, existsSync, fstatSync, ftruncateSync, openSync, readFileSync, readSync, writeSync, unlinkSync, readdirSync, rmSync, lstatSync, realpathSync, rmdirSync, type Stats } from "node:fs";
import { basename, dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { SURFACES, removeMachineArtifacts, removeMachineCarriers, repoCarrier, readMachineState } from "../surfaces/adapters.ts";
import { restoreTemplateDir } from "../floor/template.ts";
import { repoRoot, home, enabledSurfaces, isGoverned } from "../env.ts";
import { parseLock, sha256, stripSharedText } from "../install.ts";
import { hashFile } from "../install.ts";
import { embeddedPath, embeddedTemplate, embeddedUnder } from "../embed.ts";
import { planEntries } from "./init-shared.ts";
import { select, isCancel } from "@clack/prompts";
import * as ui from "../ui.ts";
import { VERSION } from "../version.ts";
import { scriptedInput } from "../ui.ts";

/** Our hook entries out of a surface settings file; the user's hooks stay. The
 *  marker logic lives in install.ts beside its inverse, so what init merges in and
 *  what uninstall takes out can never drift apart. Unparseable → left alone with a
 *  warn: never rewrite what you cannot read. */
function stripAiEngHooks(root: string, absolute: string, rel: string, snapshot: ProjectFileSnapshot, removed: ui.Row[]): void {
  const stripped = stripSharedText(snapshot.content.toString("utf8"));
  if (stripped === null) {
    removed.push({ mark: "warn", text: `${rel} not rewritten — not JSON this installer can rewrite without reformatting it (review by hand)` });
    return;
  }
  if (Object.keys(JSON.parse(stripped) as Record<string, unknown>).length === 0) {
    if (!unlinkProjectPath(root, absolute, snapshot)) {
      removed.push({ mark: "warn", text: `${rel} kept`, dim: "file changed during uninstall — preserved" });
      return;
    }
    removed.push({ mark: "ok", text: `${rel} removed`, dim: "it held only ai-eng entries" });
    return;
  }
  if (!writeProjectFile(root, absolute, snapshot, stripped)) {
    removed.push({ mark: "warn", text: `${rel} kept`, dim: "file changed during uninstall — preserved" });
    return;
  }
  removed.push({ mark: "ok", text: `${rel}: removed the ai-eng hook entries, kept yours` });
}

/** Read the declared surfaces and build the asset map from the lock, falling
 *  back to the binary's own file list when the lock is missing or empty. The
 *  declaration must be read ONCE, before anything removes config.toml. */
function readAssetsFromLock(
  root: string,
  declared: string[],
  removed: ui.Row[],
): { assets: Record<string, string>; hasLock: boolean; lockSnapshot: ProjectFileSnapshot | null } {
  // The lock is the ownership register; when it is gone (a half-finished
  // uninstall, a hand-deletion), the binary's own planEntries list is the
  // fallback — same paths, hashes recomputed from the payload it installs.
  // Never a hardcoded subset, never a file it did not install.
  const lockRel = ".ai-engineering/ai-eng.lock";
  const lockPath = safeProjectPath(root, lockRel);
  const hasLock = lockPath !== null && existsSync(lockPath);
  if (lockPath === null && existsSync(join(root, lockRel))) {
    removed.push({ mark: "warn", text: "ai-eng.lock kept", dim: "linked path — not ai-eng's" });
  }
  const lockSnapshot = hasLock && lockPath !== null ? readProjectFileSnapshot(root, lockPath) : null;
  if (hasLock && lockSnapshot === null) {
    removed.push({ mark: "warn", text: "ai-eng.lock kept", dim: "file changed during uninstall — preserved" });
    return { assets: {}, hasLock: false, lockSnapshot: null };
  }
  let assets: Record<string, string> = lockSnapshot === null ? {} : parseLock(lockSnapshot.content.toString("utf8")).assets;
  if (Object.keys(assets).length === 0) {
    assets = Object.fromEntries(
      planEntries(declared).map((entry) => [entry.path, sha256(entry.ours)]),
    );
    removed.push({ mark: "muted", text: "no lock — swept by the binary's own file list" });
  }
  return { assets, hasLock, lockSnapshot };
}

/** Sweep every declared asset from the project tree and prune empty dirs. */
function sweepProjectSide(
  root: string,
  declared: string[],
  removed: ui.Row[],
): void {
  const { assets, hasLock, lockSnapshot } = readAssetsFromLock(root, declared, removed);
  const settingsByPath = collectSettingsByPath();
  for (const rel of Object.keys(assets)) {
    sweepAsset(root, rel, assets, settingsByPath, removed);
  }
  if (hasLock) {
    const lockPath = safeProjectPath(root, ".ai-engineering/ai-eng.lock");
    if (lockPath === null || lockSnapshot === null || !unlinkProjectPath(root, lockPath, lockSnapshot)) {
      removed.push({ mark: "warn", text: "ai-eng.lock kept", dim: "file changed during uninstall — preserved" });
    } else {
      removed.push({ mark: "ok", text: "ai-eng.lock deleted", dim: `${Object.keys(assets).length} owned files swept` });
    }
  } else {
    removed.push({ mark: "muted", text: `${Object.keys(assets).length} owned files swept` });
  }
  pruneCreatedDirs(root, removed);
}

/** Show the scope picker and the "are you sure?" confirmation. Returns the
 *  chosen scope, or null when the user cancelled. */
async function confirmUninstall(input: unknown): Promise<"project" | "everything" | null> {
  ui.section("Two scopes", [
    { mark: "info", text: "This project", dim: "sweeps every file the lock says ai-eng owns: hooks, settings entries, adapters, CI workflow, config, lock. Keeps AGENTS.md, DECISIONS.md, spec/plan." },
    { mark: "warn", text: "Everything", dim: `the project side ABOVE, plus the machine side: deletes ${home()} (global skills, mirrors, caches). Asks twice.` },
  ]);
  const scope = await pickScope(input);
  if (scope === null) {
    ui.cancelled("Nothing removed.");
    return null;
  }
  // Default is No: uninstall is destructive, a bare Enter must not raze the repo.
  const confirmed = await ui.confirmDefault("Confirm?", false, input as never);
  if (confirmed === false) {
    ui.cancelled("Nothing removed.");
    return null;
  }
  return scope;
}

/** Remove a directory only when it is empty — ai-eng created it, the sweep
 *  emptied it, and an empty scaffold is noise. */
function pruneIfEmpty(root: string, rel: string): boolean {
  const dir = safeProjectPath(root, rel);
  if (dir === null) return false;
  try {
    return withSafeProjectParent(root, dir, (name) => {
      rmdirSync(name);
      return true;
    });
  } catch {
    /* absent, non-empty, or unreadable: nothing to prune */
  }
  return false;
}

async function pickScope(input: unknown): Promise<"project" | "everything" | null> {
  const scope = await select({
    message: "What do you want to remove?",
    options: [
      { value: "project", label: "This project only — every file the lock says ai-eng owns" },
      { value: "everything", label: `Everything — this project AND ${home()} (global skills)` },
      { value: "cancel", label: "Cancel — remove nothing" },
    ],
    input: input as never,
  });
  if (isCancel(scope)) return null;
  if (scope === "cancel") return null;
  if (scope === "everything") return "everything";
  return "project";
}

function collectSettingsByPath(): Map<string, string> {
  const settingsByPath = new Map<string, string>();
  for (const surface of SURFACES) {
    const placement = repoCarrier(surface);
    if (placement?.kind === "settings") settingsByPath.set(placement.path, surface.label);
  }
  return settingsByPath;
}

function safeProjectPath(root: string, rel: string): string | null {
  let canonicalRoot: string;
  try {
    canonicalRoot = realpathSync(root);
  } catch {
    return null;
  }
  const absolute = resolve(canonicalRoot, rel);
  if (!pathIsWithin(canonicalRoot, absolute)) return null;

  let current = canonicalRoot;
  for (const component of relative(canonicalRoot, absolute).split(sep).filter(Boolean)) {
    current = join(current, component);
    try {
      if (lstatSync(current).isSymbolicLink() || !pathIsWithin(canonicalRoot, realpathSync(current))) return null;
    } catch {
      return null;
    }
  }
  return absolute;
}

function withSafeProjectParent(root: string, absolute: string, action: (name: string) => boolean): boolean {
  const canonicalRoot = realpathSync(root);
  const parent = dirname(absolute);
  const previousDirectory = process.cwd();
  let changedDirectory = false;
  try {
    try {
      process.chdir(parent);
      changedDirectory = true;
    } catch {
      return false;
    }
    let currentDirectory: string;
    try {
      currentDirectory = realpathSync(".");
    } catch {
      return false;
    }
    if (currentDirectory !== parent || !pathIsWithin(canonicalRoot, currentDirectory)) return false;
    // Relative operations stay anchored here if the parent pathname is replaced.
    return action(basename(absolute));
  } finally {
    if (changedDirectory) process.chdir(previousDirectory);
  }
}

type ProjectFileSnapshot = Pick<Stats, "dev" | "ino" | "size" | "mtimeMs" | "ctimeMs"> & {
  content: Buffer;
  hash: string;
};

function sameFileVersion(left: Stats, right: Stats): boolean {
  return left.isFile() && right.isFile()
    && left.dev === right.dev
    && left.ino === right.ino
    && left.size === right.size
    && left.mtimeMs === right.mtimeMs
    && left.ctimeMs === right.ctimeMs;
}

function matchesProjectFile(stat: Stats, snapshot: ProjectFileSnapshot): boolean {
  return stat.isFile()
    && stat.dev === snapshot.dev
    && stat.ino === snapshot.ino
    && stat.size === snapshot.size
    && stat.mtimeMs === snapshot.mtimeMs
    && stat.ctimeMs === snapshot.ctimeMs;
}

function readProjectFileSnapshot(root: string, absolute: string): ProjectFileSnapshot | null {
  let snapshot: ProjectFileSnapshot | null = null;
  const didRead = withSafeProjectParent(root, absolute, (name) => {
    let descriptor: number | null = null;
    try {
      const entryBefore = lstatSync(name);
      if (entryBefore.isSymbolicLink() || !entryBefore.isFile()) return false;
      descriptor = openSync(name, constants.O_RDONLY | constants.O_NOFOLLOW);
      const opened = fstatSync(descriptor);
      if (!sameFileVersion(entryBefore, opened)) return false;
      const content = readFileSync(descriptor);
      const afterRead = fstatSync(descriptor);
      const entryAfter = lstatSync(name);
      if (!sameFileVersion(opened, afterRead) || !sameFileVersion(afterRead, entryAfter) || content.length !== afterRead.size) {
        return false;
      }
      snapshot = {
        dev: afterRead.dev,
        ino: afterRead.ino,
        size: afterRead.size,
        mtimeMs: afterRead.mtimeMs,
        ctimeMs: afterRead.ctimeMs,
        content,
        hash: createHash("sha256").update(content).digest("hex"),
      };
      return true;
    } catch {
      return false;
    } finally {
      if (descriptor !== null) closeSync(descriptor);
    }
  });
  return didRead ? snapshot : null;
}

function fileMatchesSnapshotAtPath(name: string, descriptor: number, snapshot: ProjectFileSnapshot): boolean {
  try {
    const beforeRead = fstatSync(descriptor);
    if (!matchesProjectFile(beforeRead, snapshot)) return false;
    const content = Buffer.alloc(snapshot.size);
    let bytesRead = 0;
    while (bytesRead < content.length) {
      const count = readSync(descriptor, content, bytesRead, content.length - bytesRead, bytesRead);
      if (count === 0) return false;
      bytesRead += count;
    }
    const afterRead = fstatSync(descriptor);
    const currentEntry = lstatSync(name);
    return content.equals(snapshot.content)
      && matchesProjectFile(afterRead, snapshot)
      && sameFileVersion(beforeRead, afterRead)
      && sameFileVersion(afterRead, currentEntry);
  } catch {
    return false;
  }
}

function openMatchingProjectFile(name: string, snapshot: ProjectFileSnapshot, flags: number): number | null {
  let descriptor: number | null = null;
  let isValid = false;
  try {
    const entryBefore = lstatSync(name);
    if (!matchesProjectFile(entryBefore, snapshot)) return null;
    descriptor = openSync(name, flags | constants.O_NOFOLLOW);
    const opened = fstatSync(descriptor);
    if (!sameFileVersion(entryBefore, opened) || !fileMatchesSnapshotAtPath(name, descriptor, snapshot)) return null;
    isValid = true;
    return descriptor;
  } catch {
    return null;
  } finally {
    if (descriptor !== null && !isValid) closeSync(descriptor);
  }
}

function unlinkProjectPath(root: string, absolute: string, snapshot: ProjectFileSnapshot): boolean {
  return withSafeProjectParent(root, absolute, (name) => {
    const descriptor = openMatchingProjectFile(name, snapshot, constants.O_RDONLY);
    if (descriptor === null) return false;
    try {
      if (!fileMatchesSnapshotAtPath(name, descriptor, snapshot)) return false;
      unlinkSync(name);
      return true;
    } finally {
      closeSync(descriptor);
    }
  });
}

function writeProjectFile(root: string, absolute: string, snapshot: ProjectFileSnapshot, contents: string): boolean {
  return withSafeProjectParent(root, absolute, (name) => {
    const descriptor = openMatchingProjectFile(name, snapshot, constants.O_RDWR);
    if (descriptor === null) return false;
    try {
      if (!fileMatchesSnapshotAtPath(name, descriptor, snapshot)) return false;
      const bytes = Buffer.from(contents);
      ftruncateSync(descriptor, 0);
      let written = 0;
      while (written < bytes.length) {
        const count = writeSync(descriptor, bytes, written, bytes.length - written, written);
        if (count === 0) return false;
        written += count;
      }
      return true;
    } finally {
      closeSync(descriptor);
    }
  });
}

function sweepAsset(
  root: string,
  rel: string,
  assets: Record<string, string>,
  settingsByPath: Map<string, string>,
  removed: ui.Row[],
): void {
  // The lock is untrusted input: a crafted key can point outside the repo —
  // a lock entry escaping to $HOME with a matching hash makes the sweep
  // delete it. A path that escapes root is not ours, no matter what the lock
  // claims: skip it, keep the sweep honest.
  const absolute = resolve(root, rel);
  if (absolute !== root && !absolute.startsWith(root + sep)) {
    removed.push({ mark: "warn", text: `${rel} kept`, dim: "lock path escapes this repo — not ai-eng's" });
    return;
  }
  if (!existsSync(absolute)) return;
  const safeAbsolute = safeProjectPath(root, rel);
  if (safeAbsolute === null) {
    removed.push({ mark: "warn", text: `${rel} kept`, dim: "linked path — not ai-eng's" });
    return;
  }
  const snapshot = readProjectFileSnapshot(root, safeAbsolute);
  if (snapshot === null) {
    removed.push({ mark: "warn", text: `${rel} kept`, dim: "file changed during uninstall — preserved" });
    return;
  }
  if (settingsByPath.has(rel)) {
    // Unedited: the whole file is ai-eng's template — it goes. Edited: the
    // user's keys stay, only our hook entries come out.
    if (snapshot.hash === assets[rel]) {
      if (!unlinkProjectPath(root, safeAbsolute, snapshot)) {
        removed.push({ mark: "warn", text: `${rel} kept`, dim: "file changed during uninstall — preserved" });
        return;
      }
      removed.push({ mark: "ok", text: `${rel} removed`, dim: "still the template ai-eng installed" });
    } else {
      stripAiEngHooks(root, safeAbsolute, rel, snapshot, removed);
    }
    return;
  }
  // Git shims are judged by their marker (the only test that survives a
  // user re-chmod); everything else by the lock's hash: delete only what
  // still matches what we installed — an edited file is yours now, kept and named.
  if (rel.startsWith(".git/hooks/")) {
    if (snapshot.content.includes(Buffer.from("ai-eng git floor shim"))) {
      if (!unlinkProjectPath(root, safeAbsolute, snapshot)) {
        removed.push({ mark: "warn", text: `${rel} kept`, dim: "file changed during uninstall — preserved" });
        return;
      }
      removed.push({ mark: "ok", text: `${rel} removed`, dim: "marker-matched — never by name alone" });
    } else {
      removed.push({ mark: "warn", text: `${rel} kept`, dim: "no ai-eng marker: it is yours now" });
    }
    return;
  }
  if (snapshot.hash === assets[rel]) {
    if (!unlinkProjectPath(root, safeAbsolute, snapshot)) {
      removed.push({ mark: "warn", text: `${rel} kept`, dim: "file changed during uninstall — preserved" });
      return;
    }
    removed.push({ mark: "ok", text: `${rel} removed` });
  } else {
    removed.push({ mark: "warn", text: `${rel} kept`, dim: "you edited it after install — it is yours now" });
  }
}

function pruneCreatedDirs(root: string, removed: ui.Row[]): void {
  // Dirs ai-eng created are pruned only when the sweep left them empty.
  for (const dir of [".ai-engineering", ".claude", ".cursor", ".codex", ".copilot", ".opencode/plugins", ".agents/hooks", ".pi/extensions", ".github/workflows"]) {
    if (pruneIfEmpty(root, dir)) removed.push({ mark: "muted", text: `${dir}/ removed (empty)` });
  }
  for (const dir of [".opencode", ".agents", ".pi", ".github"]) {
    if (pruneIfEmpty(root, dir)) removed.push({ mark: "muted", text: `${dir}/ removed (empty)` });
  }
}

function pathIsWithin(root: string, candidate: string): boolean {
  const pathFromRoot = relative(root, candidate);
  return pathFromRoot === "" || (
    pathFromRoot !== ".." && !pathFromRoot.startsWith(`..${sep}`) && !isAbsolute(pathFromRoot)
  );
}

function pruneEmptyDirectory(directory: string): boolean {
  try {
    if (readdirSync(directory).length !== 0) return false;
    rmdirSync(directory);
    return true;
  } catch {
    return false;
  }
}

function removeEmbeddedAssets(machineDir: string, prefix: string): number {
  // The machine home can contain user data: remove only byte-identical payloads and never follow links.
  const assetRoot = join(machineDir, prefix.slice(0, -1));
  let rootStat;
  try {
    rootStat = lstatSync(assetRoot);
  } catch {
    return 0;
  }
  if (rootStat.isSymbolicLink() || !rootStat.isDirectory()) return 0;
  const canonicalRoot = realpathSync(assetRoot);
  let removed = 0;

  for (const [path, ref] of embeddedUnder(prefix)) {
    const components = path.slice(prefix.length).split("/");
    const destination = resolve(canonicalRoot, ...components);
    if (!pathIsWithin(canonicalRoot, destination)) continue;

    let parent = canonicalRoot;
    let isSafe = true;
    for (const component of components.slice(0, -1)) {
      parent = join(parent, component);
      try {
        const stat = lstatSync(parent);
        if (stat.isSymbolicLink() || !stat.isDirectory() || !pathIsWithin(canonicalRoot, realpathSync(parent))) {
          isSafe = false;
          break;
        }
      } catch {
        isSafe = false;
        break;
      }
    }
    if (!isSafe) continue;

    try {
      const stat = lstatSync(destination);
      const payload = embeddedPath(ref);
      if (stat.isSymbolicLink() || !stat.isFile() || !existsSync(payload) || hashFile(destination) !== hashFile(payload)) continue;
      unlinkSync(destination);
      removed += 1;
      let directory = dirname(destination);
      while (directory !== canonicalRoot) {
        if (!pruneEmptyDirectory(directory)) break;
        directory = dirname(directory);
      }
      pruneEmptyDirectory(canonicalRoot);
    } catch {
      /* changed, unreadable, or already removed: preserve it */
    }
  }
  return removed;
}

async function removeEverything(root: string, input: unknown, declared: string[]): Promise<ui.Row[]> {
  const extra: ui.Row[] = [];
  const agents = join(root, "AGENTS.md");
  const decisions = join(root, "DECISIONS.md");
  const confirmedAll = await ui.confirmDefault("Delete this project's AGENTS.md, DECISIONS.md, .gitignore and .ai-engineering/ too? They hold your work.", false, input as never);
  if (confirmedAll) {
    if (existsSync(agents)) unlinkSync(agents);
    if (existsSync(decisions)) unlinkSync(decisions);
    // A .gitignore is the one scaffold file a project very often already owned before
    // init: ours goes only while it is byte-identical to the template — an edited one
    // holds the user's rules and stays, named.
    const gitignore = join(root, ".gitignore");
    const ours = existsSync(gitignore) && hashFile(gitignore) === sha256(embeddedTemplate("gitignore.tpl"));
    if (ours) unlinkSync(gitignore);
    rmSync(join(root, ".ai-engineering"), { recursive: true, force: true });
    extra.push({ mark: "warn", text: "project contract files removed (your choice)", dim: `AGENTS.md · DECISIONS.md${ours ? " · .gitignore" : ""} · .ai-engineering/` });
  } else {
    extra.push({ mark: "ok", text: "kept: AGENTS.md, DECISIONS.md, .gitignore, .ai-engineering/" });
  }
  // The machine side: the global canon this binary installed.
  const machineDir = home();
  const confirmedMachine = await ui.confirmDefault(`Delete the machine side ${machineDir} (global skills, mirrors)?`, false, input as never);
  if (confirmedMachine) {
    // The carriers first, and by the table: they live in the HOSTS' directories, not
    // inside the canon home, so removing the canon would leave them behind pointing at a
    // chain that no longer exists — orphans with a marker.
    const carriers = removeMachineCarriers(declared);
    // The git floor first: the recorded state lives inside the canon home this scope is
    // about to delete, so reading it afterwards would restore nothing.
    const floorState = readMachineState().templateDir;
    const floor = floorState === undefined ? null : restoreTemplateDir(floorState.previous, floorState.ours);
    const swept = removeMachineArtifacts();
    const canonAssetsRemoved = ["skills/", "agents/", "scripts/"].reduce(
      (count, prefix) => count + removeEmbeddedAssets(machineDir, prefix),
      0,
    );
    pruneEmptyDirectory(machineDir);
    const userFilesRemain = existsSync(machineDir);
    const cleanup = `${canonAssetsRemoved} canon-owned file(s) removed · ${swept} machine artifacts swept`;
    extra.push(userFilesRemain
      ? { mark: "ok", text: `${machineDir} kept`, dim: `${cleanup} · other files kept` }
      : { mark: "warn", text: `${machineDir} deleted`, dim: cleanup });
    if (floor !== null) extra.push({ mark: "ok", text: floor });
    for (const line of carriers.lines) extra.push({ mark: "ok", text: line });
    for (const path of carriers.refused) extra.push({ mark: "warn", text: `${path} left alone — not JSON this installer can rewrite without reformatting it` });
  } else {
    extra.push({ mark: "ok", text: `kept: ${machineDir}`, dim: "global skills stay installed" });
  }
  return extra;
}

export async function uninstallMain(): Promise<number> {
  const input = scriptedInput();
  ui.frame(`Uninstall · ai-eng ${VERSION}`);
  const root = repoRoot();
  if (root === null || !isGoverned(root)) {
    ui.fail("you are not in a governed repo — nothing of this project to remove");
    ui.end("Nothing done.");
    return 2;
  }
  const scope = await confirmUninstall(input);
  if (scope === null) return 0;

  // Read the declaration ONCE, before anything removes it. The machine sweep runs after
  // the project side has deleted config.toml, and `enabledSurfaces()` then reports the
  // no-config fallback (["claude-code"]): a repo declaring any other surface kept that
  // host's carrier behind as an orphan pointing at a chain nothing serves.
  const declared = enabledSurfaces();
  // ── project side ──────────────────────────────────────────────
  const removed: ui.Row[] = [];
  spawnSync("git", ["-C", root, "config", "--unset", "core.hooksPath"]);
  removed.push({ mark: "ok", text: "git: core.hooksPath reverted to default" });
  sweepProjectSide(root, declared, removed);
  // Rendered as one block: what went, at a glance.
  ui.section("Removed", removed);
  if (scope === "everything") {
    const extra = await removeEverything(root, input, declared);
    ui.section("Everything scope — the extra sweep", extra);
  }
  ui.end(scope === "everything" ? "ai-eng removed from this machine as far as you chose. Your work survives unless you said otherwise." : "ai-eng is no longer active in this repo. Your contract files remain.");
  return 0;
}
