// Root-bound file operations, shared by the canon sweep, carrier cleanup, uninstall and
// receipt retention: a file is read, rewritten or removed only through its checked parent,
// and only while it is still the exact file that was read (R38). Kept free of the embedded
// assets so the chain bundle can import it.

import { createHash } from "node:crypto";
import { closeSync, constants, fstatSync, ftruncateSync, lstatSync, openSync, readFileSync, readSync, realpathSync, rmdirSync, unlinkSync, writeSync, type Stats } from "node:fs";
import { basename, dirname, isAbsolute, join, relative, resolve, sep } from "node:path";

export function safeProjectPath(root: string, rel: string): string | null {
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

/** A refusal from the filesystem (EACCES, EPERM, EBUSY, ENOTEMPTY, EROFS, ENOSPC…) carries
 *  an errno code. Anything without one is a bug, and callers rethrow it. */
export function isFilesystemRefusal(error: unknown): error is NodeJS.ErrnoException {
  return error instanceof Error && typeof (error as NodeJS.ErrnoException).code === "string";
}

/** Runs `action` from inside the checked parent. A filesystem refusal anywhere in it is a
 *  returned `false`, never a throw: every caller already keeps the file and says so, and the
 *  command around it still has to finish its other work and write its lock. It changes the
 *  process's working directory, so only the CLI commands (each its own process) use it;
 *  anything the chain reaches uses withCheckedProjectParent. */
export function withSafeProjectParent(root: string, absolute: string, action: (name: string) => boolean): boolean {
  let canonicalRoot: string;
  try {
    canonicalRoot = realpathSync(root);
  } catch (error) {
    if (isFilesystemRefusal(error)) return false;
    throw error;
  }
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
    try {
      return action(basename(absolute));
    } catch (error) {
      if (isFilesystemRefusal(error)) return false;
      throw error;
    }
  } finally {
    if (changedDirectory) process.chdir(previousDirectory);
  }
}

/** How a guarded operation reaches the folder it acts in: it checks that folder, then runs
 *  `action` on the name to act through. */
export type ParentBinding = (root: string, absolute: string, action: (name: string) => boolean) => boolean;

/** withSafeProjectParent without the chdir, for code that runs inside a host's process: the
 *  chain is imported by the OMP/OpenCode plugins, and their working directory is not ours to
 *  move. The parent is proven a real folder inside the root right before `action` runs on
 *  `absolute`; Node has no *at() calls, so the window between that check and the action is
 *  the accepted pathname TOCTOU, and each action re-checks the file's own identity before it
 *  acts. A filesystem refusal is a returned `false`, never a throw. */
export function withCheckedProjectParent(root: string, absolute: string, action: (path: string) => boolean): boolean {
  try {
    const canonicalRoot = realpathSync(root);
    const parent = dirname(absolute);
    if (!lstatSync(parent).isDirectory() || realpathSync(parent) !== parent || !pathIsWithin(canonicalRoot, parent)) return false;
    return action(absolute);
  } catch (error) {
    if (isFilesystemRefusal(error)) return false;
    throw error;
  }
}

export type ProjectFileSnapshot = Pick<Stats, "dev" | "ino" | "nlink" | "size" | "mtimeMs" | "ctimeMs"> & {
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

export function readProjectFileSnapshot(root: string, absolute: string, bindParent: ParentBinding = withSafeProjectParent): ProjectFileSnapshot | null {
  let snapshot: ProjectFileSnapshot | null = null;
  const didRead = bindParent(root, absolute, (name) => {
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
        nlink: afterRead.nlink,
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

export function unlinkProjectPath(root: string, absolute: string, snapshot: ProjectFileSnapshot, bindParent: ParentBinding = withSafeProjectParent): boolean {
  return bindParent(root, absolute, (name) => {
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

export function writeProjectFile(root: string, absolute: string, snapshot: ProjectFileSnapshot, contents: string): boolean {
  return withSafeProjectParent(root, absolute, (name) => {
    const descriptor = openMatchingProjectFile(name, snapshot, constants.O_RDWR);
    if (descriptor === null) return false;
    try {
      // A second name (a hard link from the user's home) would receive the rewrite too.
      if (fstatSync(descriptor).nlink !== 1 || !fileMatchesSnapshotAtPath(name, descriptor, snapshot)) return false;
      const bytes = Buffer.from(contents);
      try {
        ftruncateSync(descriptor, 0);
        writeAll(descriptor, bytes);
        return true;
      } catch (error) {
        // Refused midway (ENOSPC, EIO): put the bytes that were read back, so the file is
        // never left half-written. The refusal still reaches the caller as `false`.
        try {
          ftruncateSync(descriptor, 0);
          writeAll(descriptor, snapshot.content);
        } catch {
          /* nothing more this run can do; the caller keeps the path and names it */
        }
        throw error;
      }
    } finally {
      closeSync(descriptor);
    }
  });
}

function writeAll(descriptor: number, bytes: Buffer): void {
  let written = 0;
  while (written < bytes.length) {
    const count = writeSync(descriptor, bytes, written, bytes.length - written, written);
    if (count === 0) throw Object.assign(new Error("short write"), { code: "EIO" });
    written += count;
  }
}

export function pathIsWithin(root: string, candidate: string): boolean {
  const pathFromRoot = relative(root, candidate);
  return pathFromRoot === "" || (
    pathFromRoot !== ".." && !pathFromRoot.startsWith(`..${sep}`) && !isAbsolute(pathFromRoot)
  );
}

/** rmdir bound to the checked parent: a parent swapped for a link cannot redirect it. */
export function pruneEmptyDirectoryWithin(root: string, directory: string): boolean {
  try {
    return withSafeProjectParent(root, directory, (name) => {
      rmdirSync(name);
      return true;
    });
  } catch {
    return false;
  }
}
