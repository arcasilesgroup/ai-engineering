import { createHash } from "node:crypto";
import { mkdir, readFile, readdir, rm, stat, writeFile } from "node:fs/promises";
import { dirname } from "node:path";

import { IOError } from "../../shared/kernel/errors.ts";
import { type Result, err, ok } from "../../shared/kernel/result.ts";
import type { FilesystemPort } from "../../shared/ports/filesystem.ts";

/**
 * NodeFilesystemAdapter — driven adapter for `node:fs/promises`.
 *
 * Wraps every operation in try/catch and translates exceptions into
 * `Result.err(IOError)`. Cross-platform via `node:path` only — never
 * concatenates paths with raw separators or shells out.
 *
 * `write` creates parent directories implicitly so callers don't have to
 * mkdir before each write. `remove` is recursive and idempotent: removing
 * a missing path is treated as success (matches `rm -f` semantics).
 */
export class NodeFilesystemAdapter implements FilesystemPort {
  async read(path: string): Promise<Result<string, IOError>> {
    try {
      const content = await readFile(path, "utf8");
      return ok(content);
    } catch (e) {
      return err(toIOError("read", path, e));
    }
  }

  async write(path: string, content: string): Promise<Result<void, IOError>> {
    try {
      await mkdir(dirname(path), { recursive: true });
      await writeFile(path, content, "utf8");
      return ok(undefined);
    } catch (e) {
      return err(toIOError("write", path, e));
    }
  }

  async exists(path: string): Promise<boolean> {
    try {
      await stat(path);
      return true;
    } catch {
      return false;
    }
  }

  async list(path: string): Promise<Result<string[], IOError>> {
    try {
      const entries = await readdir(path);
      return ok(entries);
    } catch (e) {
      return err(toIOError("list", path, e));
    }
  }

  async remove(path: string): Promise<Result<void, IOError>> {
    try {
      await rm(path, { recursive: true, force: true });
      return ok(undefined);
    } catch (e) {
      return err(toIOError("remove", path, e));
    }
  }

  async hash(path: string): Promise<Result<string, IOError>> {
    try {
      const buf = await readFile(path);
      const digest = createHash("sha256").update(buf).digest("hex");
      return ok(digest);
    } catch (e) {
      return err(toIOError("hash", path, e));
    }
  }
}

const toIOError = (op: string, path: string, e: unknown): IOError => {
  const cause = e instanceof Error ? e.message : String(e);
  return new IOError(`fs.${op} failed for ${path}: ${cause}`);
};
